"""Executions API: start a run and observe the loop.

This is the heart of the Project Control Room. ``POST /executions/`` (or the
``start`` action on a project) kicks off a real run through the workflow engine;
the read endpoints expose node-by-node runs and the live loop state (iteration,
consecutive failures, budgets, stop reason) so the UI can show the QA→fix→retry
cycle as it happens.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api_common import ReadOnlyOrgScopedViewSet, current_org_id
from apps.executions.models import Execution, Intervention, LoopState, NodeRun
from apps.projects.models import Project, Task


class NodeRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodeRun
        fields = [
            "uuid", "node_key", "node_type", "status", "iteration", "summary",
            "outputs", "model_key", "input_tokens", "output_tokens", "cost",
            "started_at", "finished_at", "error", "created_at",
        ]


class LoopStateSerializer(serializers.ModelSerializer):
    node_key = serializers.CharField(source="node.key", read_only=True, default="")

    class Meta:
        model = LoopState
        fields = [
            "uuid", "node_key", "iteration", "consecutive_failures",
            "max_iterations", "max_duration_seconds", "max_cost", "failure_threshold",
            "is_active", "stop_reason", "started_at",
        ]


class InterventionSerializer(serializers.ModelSerializer):
    node_key = serializers.CharField(source="node.key", read_only=True, default="")
    assigned_actor_name = serializers.CharField(source="assigned_actor.name", read_only=True, default="")
    resolved_by_name = serializers.CharField(source="resolved_by.username", read_only=True, default="")

    class Meta:
        model = Intervention
        fields = ["uuid", "execution", "node_key", "task", "kind", "status", "iteration", "prompt", "response", "assigned_actor_name", "resolved_by_name", "metadata", "resolved_at", "created_at"]
        read_only_fields = fields


class ExecutionSerializer(serializers.ModelSerializer):
    project_key = serializers.CharField(source="project.key", read_only=True, default="")
    workflow_key = serializers.CharField(source="workflow.key", read_only=True, default="")

    class Meta:
        model = Execution
        fields = [
            "uuid", "project", "project_key", "workflow", "workflow_key",
            "status", "stop_reason", "scenario", "context",
            "total_input_tokens", "total_output_tokens", "total_cost",
            "started_at", "finished_at", "error", "created_at",
        ]
        read_only_fields = fields


class ExecutionDetailSerializer(ExecutionSerializer):
    node_runs = NodeRunSerializer(many=True, read_only=True)
    loop_states = LoopStateSerializer(many=True, read_only=True)
    interventions = InterventionSerializer(many=True, read_only=True)

    class Meta(ExecutionSerializer.Meta):
        fields = ExecutionSerializer.Meta.fields + ["node_runs", "loop_states", "interventions"]


class ExecutionViewSet(ReadOnlyOrgScopedViewSet):
    """Executions are created via the ``start`` action, not raw POST — starting a
    run has side effects (spawns the engine) that a plain serializer create can't
    express cleanly."""

    queryset = Execution.objects.select_related("project", "workflow").all()
    serializer_class = ExecutionSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ExecutionDetailSerializer
        return ExecutionSerializer

    @action(detail=False, methods=["post"])
    def start(self, request):
        """Start a run. Body: ``{"project": "<uuid>", "scenario": "fail_once"}``.

        ``scenario`` is optional (defaults to the project's configured scenario).
        """
        from core.workflow_engine import start_execution

        project_uuid = request.data.get("project")
        if not project_uuid:
            return Response({"detail": "project (uuid) is required"}, status=400)

        try:
            project = Project.objects.select_related("workflow").get(
                uuid=project_uuid, organization_id=current_org_id(request)
            )
        except (Project.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "project not found"}, status=404)

        workflow = None
        if request.data.get("workflow"):
            workflow = project.workflows.filter(uuid=request.data["workflow"]).first()
            if workflow is None:
                return Response({"detail": "workflow is not part of this workspace"}, status=400)
        workflow = workflow or project.workflow or project.workflows.first()
        if workflow is None:
            return Response({"detail": "workspace has no workflow"}, status=400)

        scenario = request.data.get("scenario")
        execution = start_execution(
            project, workflow=workflow, scenario=scenario, triggered_by=request.user
        )
        serializer = ExecutionDetailSerializer(execution, context={"request": request})
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["get"])
    def runs(self, request, uuid=None):
        """The node-by-node run log for one execution (ordered)."""
        execution = self.get_object()
        runs = execution.node_runs.order_by("created_at")
        return Response(NodeRunSerializer(runs, many=True).data)

    @action(detail=True, methods=["post"])
    def pause(self, request, uuid=None):
        execution = self.get_object()
        if execution.is_terminal:
            return Response({"detail": "A terminal execution cannot be paused."}, status=409)
        cursor_key = (execution.context or {}).get("_cursor")
        node = execution.workflow.nodes.filter(key=cursor_key).first() if execution.workflow and cursor_key else None
        intervention, _ = Intervention.objects.get_or_create(
            organization=execution.organization, execution=execution, node=node,
            kind=Intervention.Kind.OPERATOR, iteration=(execution.context or {}).get("iteration", 0),
            status=Intervention.Status.PENDING,
            defaults={"prompt": request.data.get("prompt") or "Operator paused this execution for review.", "requested_by": request.user},
        )
        execution.status = Execution.Status.PAUSED
        execution.save(update_fields=["status", "updated_at"])
        return Response(InterventionSerializer(intervention).data, status=201)


class InterventionViewSet(ReadOnlyOrgScopedViewSet):
    queryset = Intervention.objects.select_related("execution", "node", "task", "assigned_actor", "resolved_by").all()
    serializer_class = InterventionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("execution"):
            queryset = queryset.filter(execution__uuid=self.request.query_params["execution"])
        if self.request.query_params.get("status"):
            queryset = queryset.filter(status=self.request.query_params["status"])
        return queryset

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def resolve(self, request, uuid=None):
        from core.workflow_engine.backend import get_backend

        intervention = self.get_object()
        if intervention.status != Intervention.Status.PENDING:
            return Response({"detail": "This intervention has already been resolved."}, status=409)
        decision = str(request.data.get("decision") or "approve").lower()
        response_text = str(request.data.get("response") or "").strip()
        if intervention.kind == Intervention.Kind.HUMAN_TASK and not response_text:
            return Response({"detail": "A human task requires a response or delivery note."}, status=400)
        intervention.status = Intervention.Status.REJECTED if decision == "reject" else (Intervention.Status.COMPLETED if intervention.kind == Intervention.Kind.HUMAN_TASK else Intervention.Status.APPROVED)
        intervention.response = response_text
        intervention.resolved_by = request.user
        intervention.resolved_at = timezone.now()
        intervention.save(update_fields=["status", "response", "resolved_by", "resolved_at", "updated_at"])
        if intervention.task:
            intervention.task.status = Task.Status.FAILED if decision == "reject" else Task.Status.DONE
            intervention.task.outputs = {**(intervention.task.outputs or {}), "human_response": response_text, "decision": decision}
            intervention.task.save(update_fields=["status", "outputs", "updated_at"])
        execution = intervention.execution
        if not execution.is_terminal:
            execution.status = Execution.Status.QUEUED
            execution.save(update_fields=["status", "updated_at"])
            transaction.on_commit(lambda: get_backend().start(Execution.objects.get(pk=execution.pk)))
        return Response(InterventionSerializer(intervention, context={"request": request}).data)
