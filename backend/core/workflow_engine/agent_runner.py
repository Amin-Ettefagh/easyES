"""The agent runner: execute one AgentTask node and record everything.

Given an execution, a node bound to an Agent, and the current iteration, the
runner:

1. Resolves the agent's model/provider/credential and system prompt version.
2. Builds a :class:`~core.model_gateway.base.ModelRequest` (passing the stage,
   iteration and scenario so the deterministic FakeModelProvider can pick the
   right canned response).
3. Calls the provider, updates token/cost accounting.
4. Parses the structured response and persists Artifacts, inter-agent Messages,
   and (for QA/evaluation stages) an Evaluation.
5. Writes a :class:`~apps.executions.models.NodeRun` capturing the auditable
   summary — decision, inputs, outputs, cost — but never hidden chain-of-thought.

The runner returns a small result object the engine uses for branching.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from django.db.models import Q
from django.utils import timezone

from core import events
from core.model_gateway.base import ModelRequest, ProviderError
from core.model_gateway.registry import get_provider


@dataclass
class RunResult:
    node_run: object
    summary: str = ""
    evaluation: dict = field(default_factory=dict)
    artifacts: list = field(default_factory=list)
    messages: list = field(default_factory=list)
    error: str = ""
    succeeded: bool = True

    @property
    def passed(self) -> Optional[bool]:
        """QA/eval verdict if this node produced one, else None."""
        ev = self.evaluation or {}
        if not ev:
            return None
        return bool(
            ev.get("tests_passed")
            and ev.get("critical_errors", 0) == 0
            and ev.get("requirement_coverage", 0)
            >= ev.get("coverage_threshold", 0.8)
        )


def _resolve_actor(agent):
    """Return the ai_agent Actor backing this agent, if one exists."""
    return getattr(agent, "actor", None)


def _resolve_prompt_version(agent):
    assignment = agent.prompt_assignments.filter(kind="system").first()
    if assignment is None:
        return None
    return assignment.resolve_version()


def run_agent_node(execution, node, *, iteration: int = 0, context=None):
    """Execute an AgentTask node and persist a NodeRun. Returns RunResult."""
    from apps.artifacts.models import Artifact
    from apps.communications.models import Conversation, Message
    from apps.evaluations.models import Evaluation
    from apps.executions.models import NodeRun

    agent = node.agent
    stage = (node.config or {}).get("stage", node.key)
    scenario = execution.scenario or "fail_once"

    node_run = NodeRun.objects.create(
        execution=execution,
        node=node,
        node_key=node.key,
        node_type=node.type,
        status=NodeRun.Status.RUNNING,
        iteration=iteration,
        started_at=timezone.now(),
    )
    events.emit(
        execution,
        "node.started",
        f"{node.name} started",
        data={"node": node.key, "type": node.type, "iteration": iteration},
        node_run=node_run,
    )

    # An AgentTask without a bound agent still runs as a deterministic stage so
    # control-flow scaffolding never blocks the demo.
    prompt_version = _resolve_prompt_version(agent) if agent else None
    system_text = prompt_version.content if prompt_version else ""
    memory_text = ""
    if agent:
        from apps.agents.models import MemoryEntry

        knowledge = agent.knowledge_sources.filter(is_enabled=True).exclude(content="").order_by("created_at")[:12]
        if knowledge:
            memory_text += "\n\nAgent knowledge sources:\n" + "\n".join(f"[{item.name}] {item.content}" for item in knowledge)
        memories = MemoryEntry.objects.filter(agent=agent).filter(
            Q(workspace=execution.project) | Q(workspace=None)
        ).order_by("-importance", "-updated_at")[:5]
        if memories:
            memory_text += "\n\nRelevant persistent memory:\n" + "\n".join(f"- {item.content}" for item in memories)

    model_key = "fake-1"
    provider_key = "fake"
    api_key = ""
    credentials = {}
    base_url = ""
    provider_options = {}
    temperature = 0.7
    max_tokens = 1024

    if agent is not None:
        temperature = agent.temperature
        max_tokens = agent.max_output_tokens
        model = agent.model
        if model is not None:
            model_key = model.remote_id or model.key
            provider = model.provider
            provider_key = provider.adapter
            base_url = provider.base_url or ""
            provider_options = {**(provider.config or {})}
            provider_options["extra_body"] = {
                **(provider_options.get("extra_body") or {}),
                **(model.default_params or {}),
            }
        if agent.credential is not None:
            credentials = agent.credential.get_secret_data()
            api_key = credentials.get("api_key", "")
        elif model is not None:
            default_credential = model.provider.credentials.filter(label="default").first()
            if default_credential:
                credentials = default_credential.get_secret_data()
                api_key = credentials.get("api_key", "")

    request = ModelRequest(
        model=model_key,
        messages=[
            {"role": "system", "content": (system_text or f"You are the {stage} stage.") + memory_text},
            {"role": "user", "content": _build_user_prompt(execution, node, iteration)},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        metadata={"stage": stage, "iteration": iteration, "scenario": scenario},
    )

    provider = get_provider(
        provider_key,
        api_key=api_key,
        credentials=credentials,
        base_url=base_url,
        **provider_options,
    )

    try:
        response = provider.call(request)
    except ProviderError as exc:
        node_run.status = NodeRun.Status.FAILED
        node_run.error = str(exc)
        node_run.finished_at = timezone.now()
        node_run.save(update_fields=["status", "error", "finished_at", "updated_at"])
        events.emit(
            execution,
            "node.failed",
            f"{node.name} failed: {exc}",
            level="error",
            data={"node": node.key},
            node_run=node_run,
        )
        return RunResult(node_run=node_run, error=str(exc), succeeded=False)

    if agent is not None and agent.model is not None:
        response.cost = round(
            response.input_tokens / 1000 * float(agent.model.input_cost_per_1k)
            + response.output_tokens / 1000 * float(agent.model.output_cost_per_1k),
            6,
        )

    payload = _parse_payload(response.text)
    summary = payload.get("summary", "")
    evaluation = payload.get("evaluation", {}) or {}
    if agent and summary:
        from apps.agents.models import MemoryEntry

        MemoryEntry.objects.update_or_create(
            organization=execution.organization,
            namespace="execution-outcomes",
            key=f"{execution.uuid}:{node.key}:{iteration}",
            defaults={"workspace": execution.project, "workflow": execution.workflow, "agent": agent, "content": summary, "importance": 0.65, "metadata": {"execution": str(execution.uuid), "node": node.key, "iteration": iteration}},
        )

    # -- accounting --------------------------------------------------------
    node_run.summary = summary
    node_run.model_key = response.model
    node_run.input_tokens = response.input_tokens
    node_run.output_tokens = response.output_tokens
    node_run.cost = Decimal(str(response.cost))
    node_run.prompt_version = prompt_version
    node_run.inputs = {"stage": stage, "iteration": iteration}
    node_run.outputs = {
        "summary": summary,
        "artifact_count": len(payload.get("artifacts", [])),
        "evaluation": evaluation,
    }

    execution.total_input_tokens += response.input_tokens
    execution.total_output_tokens += response.output_tokens
    execution.total_cost = execution.total_cost + Decimal(str(response.cost))

    actor = _resolve_actor(agent) if agent else None

    # -- persist artifacts -------------------------------------------------
    artifacts = []
    for art in payload.get("artifacts", []):
        obj = Artifact.objects.create(
            organization=execution.organization,
            project=execution.project,
            node_run=node_run,
            produced_by=actor,
            kind=_artifact_kind(art.get("type", "")),
            name=art.get("name", "artifact"),
            content=art.get("content", ""),
            iteration=iteration,
            metadata={"stage": stage, "type": art.get("type", "")},
        )
        try:
            from core.workspace_git import snapshot_artifact

            obj.path = snapshot_artifact(obj)
            obj.save(update_fields=["path", "updated_at"])
        except Exception as exc:  # Git history must never lose the model output.
            events.emit(execution, "repository.warning", f"Artifact saved, but Git snapshot failed: {exc}", level="warning", data={"artifact": obj.name})
        artifacts.append(obj)
    if artifacts:
        events.emit(
            execution,
            "artifact.created",
            f"{len(artifacts)} artifact(s) from {node.name}",
            data={"names": [a.name for a in artifacts]},
            node_run=node_run,
        )

    # -- persist inter-agent messages -------------------------------------
    messages = payload.get("messages", [])
    if messages:
        convo, _ = Conversation.objects.get_or_create(
            organization=execution.organization,
            project=execution.project,
            execution=execution,
            kind=Conversation.Kind.AGENT,
            defaults={"topic": "Project collaboration"},
        )
        for msg in messages:
            Message.objects.create(
                conversation=convo,
                sender_actor=actor,
                node_run=node_run,
                role=Message.Role.ASSISTANT,
                content=msg.get("content", ""),
                metadata={"to_role": msg.get("to_role"), "type": msg.get("type")},
            )
            events.emit(
                execution,
                "agent.message",
                msg.get("content", ""),
                data={"to_role": msg.get("to_role"), "type": msg.get("type")},
                node_run=node_run,
            )

    # -- persist evaluation (QA / review stages) --------------------------
    if evaluation:
        threshold = (node.config or {}).get("coverage_threshold", 0.8)
        passed = bool(
            evaluation.get("tests_passed")
            and evaluation.get("critical_errors", 0) == 0
            and evaluation.get("requirement_coverage", 0) >= threshold
        )
        Evaluation.objects.create(
            organization=execution.organization,
            project=execution.project,
            node_run=node_run,
            evaluator_actor=actor,
            iteration=iteration,
            verdict=(
                Evaluation.Verdict.PASS if passed else Evaluation.Verdict.FAIL
            ),
            passed=passed,
            tests_passed=evaluation.get("tests_passed", False),
            requirement_coverage=evaluation.get("requirement_coverage", 0.0),
            critical_errors=evaluation.get("critical_errors", 0),
            coverage_threshold=threshold,
            score=evaluation.get("score", 0.0),
            summary=summary,
            feedback=evaluation.get("feedback", ""),
            details=evaluation,
        )
        evaluation = {**evaluation, "passed": passed, "coverage_threshold": threshold}
        events.emit(
            execution,
            "evaluation.passed" if passed else "evaluation.failed",
            evaluation.get("feedback", ""),
            level="info" if passed else "warning",
            data=evaluation,
            node_run=node_run,
        )

    node_run.status = NodeRun.Status.SUCCEEDED
    node_run.finished_at = timezone.now()
    node_run.save()
    execution.save(
        update_fields=[
            "total_input_tokens",
            "total_output_tokens",
            "total_cost",
            "updated_at",
        ]
    )
    events.emit(
        execution,
        "node.succeeded",
        summary or f"{node.name} completed",
        data={"node": node.key, "cost": float(response.cost)},
        node_run=node_run,
    )

    return RunResult(
        node_run=node_run,
        summary=summary,
        evaluation=evaluation,
        artifacts=artifacts,
        messages=messages,
    )


def _build_user_prompt(execution, node, iteration: int) -> str:
    project = execution.project
    base = (
        f"Project: {project.name}\n"
        f"Idea: {project.idea}\n"
        f"Stage: {node.name}\n"
        f"Iteration: {iteration}\n"
    )
    feedback = (execution.context or {}).get("last_feedback")
    if feedback and iteration > 0:
        base += f"\nPrevious QA feedback to address:\n{feedback}\n"
    return base


def _parse_payload(text: str) -> dict:
    """Structured (fake) providers return JSON; real ones return free text.

    Degrade gracefully: on non-JSON, treat the whole response as a summary plus
    a single note artifact so the run still produces something visible.
    """
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return {
        "summary": text[:280],
        "artifacts": [{"type": "note", "name": "Model output", "content": text}],
    }


def _artifact_kind(type_str: str) -> str:
    from apps.artifacts.models import Artifact

    t = (type_str or "").lower()
    if "code" in t:
        return Artifact.Kind.CODE
    if "test" in t or "report" in t:
        return Artifact.Kind.TEST
    if "spec" in t or "api" in t:
        return Artifact.Kind.SPEC
    if "diagram" in t or "architecture" in t:
        return Artifact.Kind.DIAGRAM
    return Artifact.Kind.DOCUMENT
