"""The workflow execution engine.

Drives one :class:`~apps.executions.models.Execution` through its Workflow
graph: dispatches each Node to a handler, records a NodeRun, evaluates edge
conditions to pick the next node, and enforces loop safety. It is deliberately
independent of *how* it is run — the :mod:`core.workflow_engine.backend`
ExecutionBackend decides thread vs. inline vs. (future) Celery/Temporal.

Design notes
------------
* The graph is data (Nodes/Edges in the DB); the engine hard-codes no stages.
* The QA loop is real: a Condition/Decision node marked ``loop`` in its config
  is the loop *controller*. Each time it routes down its ``loop_back_label``
  branch we advance a :class:`~apps.executions.models.LoopState` and check the
  safety limits (max_iterations / max_cost / max_duration / failure_threshold).
  When a limit trips we divert to the ``give_up`` branch and fail the run with
  the matching stop reason.
* ``MAX_STEPS`` is an absolute backstop against a malformed graph.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from django.utils import timezone

from core import events
from core.workflow_engine import conditions
from core.workflow_engine.agent_runner import run_agent_node
from core.workflow_engine.context import RunContext

logger = logging.getLogger(__name__)

MAX_STEPS = 200

# Stop reasons mirror LoopState.StopReason / Execution.stop_reason.
STOP_PASS = "pass"
STOP_MAX_ITERATIONS = "max_iterations"
STOP_MAX_COST = "max_cost"
STOP_MAX_TIME = "max_time"
STOP_MANUAL = "manual_stop"
STOP_FATAL = "fatal_error"
STOP_REJECTED = "rejected"


class Outcome:
    """What a node handler reports back to the driver."""

    def __init__(self, *, succeeded=True, branch="", pause=False, stop="", data=None):
        self.succeeded = succeeded
        self.branch = branch          # preferred edge label
        self.pause = pause            # halt the run, resumable (approvals)
        self.stop = stop              # terminal stop reason
        self.data = data or {}


class WorkflowEngine:
    def __init__(self, execution):
        self.execution = execution
        self.workflow = execution.workflow
        self.ctx = RunContext(execution)
        self.nodes = {n.key: n for n in self.workflow.nodes.all()}
        self._pending_stop = ""

    # -- public API --------------------------------------------------------
    def run(self):
        """Run (or resume) the execution to a terminal or paused state."""
        from apps.executions.models import Execution
        from apps.projects.models import Project

        execution = self.execution
        if execution.status in {Execution.Status.SUCCEEDED, Execution.Status.CANCELLED}:
            return execution

        execution.status = Execution.Status.RUNNING
        if execution.started_at is None:
            execution.started_at = timezone.now()
        execution.save(update_fields=["status", "started_at", "updated_at"])
        execution.project.status = Project.Status.RUNNING
        execution.project.save(update_fields=["status", "updated_at"])
        events.emit(execution, "execution.started", f"Run started for {execution.project.name}")

        latest_operator_gate = execution.interventions.filter(kind="operator").order_by("-created_at").first()
        if latest_operator_gate and latest_operator_gate.status == "rejected":
            return self._finalize(STOP_REJECTED, error=latest_operator_gate.response or "Rejected by operator")

        # Resume from a saved cursor if present, else the workflow start node.
        cursor_key = self.ctx.get("_cursor")
        cursor = self.nodes.get(cursor_key) if cursor_key else self.workflow.start_node

        steps = 0
        try:
            while cursor is not None:
                execution.refresh_from_db(fields=["status"])
                if execution.status == Execution.Status.PAUSED:
                    events.emit(execution, "execution.paused", "Execution paused by an operator")
                    return execution
                steps += 1
                if steps > MAX_STEPS:
                    return self._finalize(STOP_FATAL, error="Step limit exceeded (cycle?)")

                self.ctx.set("_cursor", cursor.key)
                execution.save(update_fields=["context", "updated_at"])
                outcome = self._handle(cursor)

                if outcome.pause:
                    self.ctx.set("_cursor", cursor.key)
                    execution.status = Execution.Status.WAITING_FOR_APPROVAL
                    execution.save(update_fields=["status", "context", "updated_at"])
                    events.emit(execution, "execution.waiting", f"Awaiting approval at {cursor.name}")
                    return execution

                if outcome.stop:
                    return self._finalize(outcome.stop, error=outcome.data.get("error", ""))

                nxt = self._choose_next(cursor, outcome)
                if self._pending_stop:
                    reason, self._pending_stop = self._pending_stop, ""
                    if nxt is None:
                        return self._finalize(reason)
                    # divert to give_up target, then finalize when the path ends
                    self.ctx.set("_final_stop", reason)
                cursor = nxt
                self.ctx.set("_cursor", cursor.key if cursor else "")
                self.execution.save(update_fields=["context", "updated_at"])
        except Exception as exc:  # noqa: BLE001 - engine must never leak a crash
            logger.exception("Engine crashed")
            return self._finalize(STOP_FATAL, error=str(exc))

        # Path ended without an explicit End/Archive stop.
        return self._finalize(self.ctx.get("_final_stop") or STOP_PASS)

    # -- node dispatch -----------------------------------------------------
    def _handle(self, node) -> Outcome:
        from apps.workflows.models import Node

        handler = {
            Node.Type.START: self._h_passthrough,
            Node.Type.END: self._h_end,
            Node.Type.ARCHIVE: self._h_archive,
            Node.Type.AGENT_TASK: self._h_agent,
            Node.Type.TASK: self._h_agent,
            Node.Type.REVIEW: self._h_agent,
            Node.Type.EVALUATION: self._h_agent,
            Node.Type.HUMAN_TASK: self._h_approval,
            Node.Type.APPROVAL: self._h_approval,
            Node.Type.TOOL: self._h_tool,
            Node.Type.CONDITION: self._h_passthrough,
            Node.Type.DECISION: self._h_passthrough,
            Node.Type.PARALLEL: self._h_passthrough,
            Node.Type.JOIN: self._h_passthrough,
            Node.Type.LOOP: self._h_passthrough,
            Node.Type.WAIT: self._h_passthrough,
            Node.Type.EVENT: self._h_passthrough,
            Node.Type.SUBWORKFLOW: self._h_passthrough,
        }.get(node.type, self._h_passthrough)
        return handler(node)

    def _h_passthrough(self, node) -> Outcome:
        return Outcome(succeeded=True)

    def _h_end(self, node) -> Outcome:
        return Outcome(stop=self.ctx.get("_final_stop") or STOP_PASS)

    def _h_archive(self, node) -> Outcome:
        # Archive is terminal: succeed unless a loop give_up set a failure stop.
        return Outcome(stop=self.ctx.get("_final_stop") or STOP_PASS)

    def _h_agent(self, node) -> Outcome:
        max_retries = int((node.config or {}).get("max_retries", 0))
        attempt = 0
        while True:
            result = run_agent_node(
                self.execution, node, iteration=self.ctx.iteration, context=self.ctx
            )
            if result.succeeded or attempt >= max_retries:
                break
            attempt += 1
            events.emit(
                self.execution, "node.retry",
                f"Retrying {node.name} ({attempt}/{max_retries})",
                level="warning", data={"node": node.key},
            )

        if not result.succeeded:
            return Outcome(succeeded=False, stop=STOP_FATAL, data={"error": result.error})

        if result.evaluation:
            ev = result.evaluation
            self.ctx.set("evaluation", ev)
            if not ev.get("passed") and ev.get("feedback"):
                self.ctx.set("last_feedback", ev.get("feedback"))
            self.ctx.set("last_evaluation_passed", bool(ev.get("passed")))
        return Outcome(succeeded=True)

    def _h_approval(self, node) -> Outcome:
        from apps.actors.models import Actor
        from apps.executions.models import Intervention, NodeRun
        from apps.projects.models import Task

        cfg = node.config or {}
        if cfg.get("auto_approve", False):
            events.emit(
                self.execution, "approval.auto",
                f"{node.name} auto-approved",
                data={"node": node.key},
            )
            return Outcome(succeeded=True)

        gate = Intervention.objects.filter(
            execution=self.execution, node=node, iteration=self.ctx.iteration
        ).order_by("-created_at").first()
        if gate and gate.status in {Intervention.Status.APPROVED, Intervention.Status.COMPLETED}:
            NodeRun.objects.filter(execution=self.execution, node=node, iteration=self.ctx.iteration, status=NodeRun.Status.WAITING).update(
                status=NodeRun.Status.SUCCEEDED, summary=gate.response or "Human gate completed", outputs={"response": gate.response}, finished_at=timezone.now()
            )
            return Outcome(succeeded=True, data={"human_response": gate.response})
        if gate and gate.status == Intervention.Status.REJECTED:
            return Outcome(succeeded=False, stop=STOP_REJECTED, data={"error": gate.response or "Rejected by operator"})
        if gate:
            return Outcome(pause=True)

        assigned_actor = None
        actor_uuid = cfg.get("actor_uuid")
        if actor_uuid:
            assigned_actor = Actor.objects.filter(uuid=actor_uuid, organization=self.execution.organization, kind__in=[Actor.Kind.HUMAN, Actor.Kind.HYBRID]).first()
        if assigned_actor is None and node.role_id:
            assigned_actor = Actor.objects.filter(organization=self.execution.organization, kind__in=[Actor.Kind.HUMAN, Actor.Kind.HYBRID], role_assignments__role=node.role).first()

        kind = Intervention.Kind.HUMAN_TASK if node.type == "human_task" else Intervention.Kind.APPROVAL
        prompt = str(cfg.get("prompt") or (f"Complete and report: {node.name}" if kind == Intervention.Kind.HUMAN_TASK else f"Review and approve before continuing: {node.name}"))
        task = None
        if kind == Intervention.Kind.HUMAN_TASK:
            task = Task.objects.create(
                project=self.execution.project, node=node, title=node.name, description=prompt,
                kind=Task.Kind.WORK, status=Task.Status.BLOCKED, assigned_actor=assigned_actor,
                priority=cfg.get("priority", Task.Priority.MEDIUM), iteration=self.ctx.iteration,
                acceptance_criteria=cfg.get("acceptance_criteria", ""),
                inputs={"execution_uuid": str(self.execution.uuid), "requires_human": True},
            )
        gate = Intervention.objects.create(
            organization=self.execution.organization, execution=self.execution, node=node, task=task,
            kind=kind, iteration=self.ctx.iteration, prompt=prompt, assigned_actor=assigned_actor,
            requested_by=self.execution.triggered_by, metadata={"node_key": node.key},
        )
        NodeRun.objects.create(
            execution=self.execution, node=node, node_key=node.key, node_type=node.type,
            task=task, status=NodeRun.Status.WAITING, iteration=self.ctx.iteration,
            summary=prompt, started_at=timezone.now(), inputs={"intervention_uuid": str(gate.uuid)},
        )
        events.emit(self.execution, "human_task.requested" if kind == Intervention.Kind.HUMAN_TASK else "approval.requested", prompt, level="warning", data={"node": node.key, "intervention_uuid": str(gate.uuid), "assigned_actor": assigned_actor.name if assigned_actor else ""})
        return Outcome(pause=True)

    def _h_tool(self, node) -> Outcome:
        from core import tools
        from apps.executions.models import NodeRun

        cfg = node.config or {}
        handler_name = cfg.get("handler", "echo")
        args = dict(cfg.get("args", {}))
        if self.execution.project.workspace_key:
            args.setdefault("workspace_key", self.execution.project.workspace_key)

        nr = NodeRun.objects.create(
            execution=self.execution, node=node, node_key=node.key,
            node_type=node.type, status=NodeRun.Status.RUNNING,
            iteration=self.ctx.iteration, started_at=timezone.now(),
        )
        try:
            out = tools.get_handler(handler_name)(**args)
            nr.status = NodeRun.Status.SUCCEEDED
            nr.summary = f"Tool {handler_name} ok"
            nr.outputs = out if isinstance(out, dict) else {"result": out}
        except tools.ToolError as exc:
            nr.status = NodeRun.Status.FAILED
            nr.error = str(exc)
        nr.finished_at = timezone.now()
        nr.save()
        return Outcome(succeeded=nr.status == NodeRun.Status.SUCCEEDED)

    # -- edge selection & loop control ------------------------------------
    def _choose_next(self, node, outcome: Outcome):
        from apps.workflows.models import Node

        edges = list(node.outgoing_edges.select_related("target").order_by("order"))
        if not edges:
            return None

        matching = []
        ns = self.ctx.namespace()
        for edge in edges:
            try:
                if conditions.evaluate(edge.condition, ns):
                    matching.append(edge)
            except conditions.ConditionError as exc:
                events.emit(
                    self.execution, "condition.error", str(exc),
                    level="warning", data={"edge": edge.label, "expr": edge.condition},
                )

        if outcome.branch:
            preferred = [e for e in matching if e.label == outcome.branch]
            matching = preferred or matching
        if not matching:
            return None

        chosen = matching[0]
        cfg = node.config or {}
        is_controller = node.type in {Node.Type.DECISION, Node.Type.CONDITION, Node.Type.LOOP}
        loop_back = cfg.get("loop_back_label", "fail")
        if is_controller and cfg.get("loop") and chosen.label == loop_back:
            reason = self._loop_step(node, cfg)
            if reason:
                give_up = cfg.get("give_up_label", "give_up")
                alt = [e for e in edges if e.label == give_up]
                self._pending_stop = reason
                return alt[0].target if alt else None
        return chosen.target

    def _loop_step(self, node, cfg) -> str:
        """Advance the loop controller's LoopState; return a stop reason or ""."""
        from apps.executions.models import LoopState

        ls, created = LoopState.objects.get_or_create(
            execution=self.execution, node=node,
            defaults={
                "max_iterations": int(cfg.get("max_iterations", 5)),
                "max_duration_seconds": int(cfg.get("max_duration_seconds", 0)),
                "max_cost": Decimal(str(cfg.get("max_cost", 0))),
                "failure_threshold": int(cfg.get("failure_threshold", 0)),
                "started_at": timezone.now(),
            },
        )
        ls.iteration += 1
        ls.consecutive_failures += 1
        self.ctx.iteration = ls.iteration

        reason = ""
        if ls.max_iterations and ls.iteration >= ls.max_iterations:
            reason = STOP_MAX_ITERATIONS
        elif ls.max_cost and self.execution.total_cost >= ls.max_cost:
            reason = STOP_MAX_COST
        elif ls.max_duration_seconds and ls.started_at:
            elapsed = (timezone.now() - ls.started_at).total_seconds()
            if elapsed >= ls.max_duration_seconds:
                reason = STOP_MAX_TIME
        if not reason and ls.failure_threshold and ls.consecutive_failures >= ls.failure_threshold:
            reason = STOP_REJECTED

        if reason:
            ls.is_active = False
            ls.stop_reason = reason
        ls.save()
        events.emit(
            self.execution, "loop.iteration",
            f"Loop iteration {ls.iteration}" + (f" — stopping ({reason})" if reason else ""),
            data={"iteration": ls.iteration, "node": node.key, "stop_reason": reason},
        )
        return reason

    # -- finalization ------------------------------------------------------
    def _finalize(self, stop_reason: str, error: str = ""):
        from apps.executions.models import Execution
        from apps.projects.models import Project

        execution = self.execution
        passed = stop_reason == STOP_PASS
        execution.status = Execution.Status.SUCCEEDED if passed else Execution.Status.FAILED
        execution.stop_reason = stop_reason
        execution.finished_at = timezone.now()
        if error:
            execution.error = error
        self.ctx.set("_cursor", "")
        execution.save()

        project = execution.project
        project.status = Project.Status.COMPLETED if passed else Project.Status.ARCHIVED
        project.save(update_fields=["status", "updated_at"])

        events.emit(
            execution,
            "execution.succeeded" if passed else "execution.failed",
            f"Run finished: {stop_reason}",
            level="info" if passed else "error",
            data={"stop_reason": stop_reason, "cost": float(execution.total_cost)},
        )
        return execution
