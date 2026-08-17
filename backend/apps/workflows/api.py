"""Workflows API: the reusable execution graph (nodes + edges).

The graph is returned in a shape the React Flow canvas can render directly:
``nodes`` carry ``position`` and ``type``; ``edges`` carry ``source``/``target``
keys plus the branch ``label``/``condition`` that drives the real loop.
"""
from __future__ import annotations

from uuid import uuid4

from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api_common import OrgScopedViewSet, current_org_id
from apps.projects.models import Project
from apps.workflows.models import Arena, Edge, Node, Workflow, WorkflowLink


class NodeSerializer(serializers.ModelSerializer):
    agent_key = serializers.CharField(source="agent.key", read_only=True, default="")
    role_key = serializers.CharField(source="role.key", read_only=True, default="")
    arena_uuid = serializers.UUIDField(source="arena.uuid", read_only=True, allow_null=True)
    arena_name = serializers.CharField(source="arena.name", read_only=True, default="")

    class Meta:
        model = Node
        fields = [
            "uuid", "key", "name", "type", "agent_key", "role_key", "arena_uuid", "arena_name",
            "config", "position_x", "position_y",
        ]


class EdgeSerializer(serializers.ModelSerializer):
    source_key = serializers.CharField(source="source.key", read_only=True)
    target_key = serializers.CharField(source="target.key", read_only=True)

    class Meta:
        model = Edge
        fields = ["uuid", "source_key", "target_key", "label", "condition", "order"]


class ArenaSerializer(serializers.ModelSerializer):
    workspace = serializers.SlugRelatedField(slug_field="uuid", queryset=Project.objects.all())
    workflow = serializers.SlugRelatedField(slug_field="uuid", queryset=Workflow.objects.all())

    class Meta:
        model = Arena
        fields = ["uuid", "workspace", "workflow", "name", "description", "color", "order", "config", "created_at"]
        read_only_fields = ["uuid", "created_at"]


class WorkflowSerializer(serializers.ModelSerializer):
    node_count = serializers.IntegerField(source="nodes.count", read_only=True)
    workspace = serializers.SlugRelatedField(slug_field="uuid", queryset=Project.objects.all(), required=False, allow_null=True)
    workspace_name = serializers.CharField(source="workspace.name", read_only=True, default="")

    class Meta:
        model = Workflow
        fields = [
            "id", "uuid", "key", "name", "description", "workspace", "workspace_name", "version", "status",
            "config", "node_count", "created_at",
        ]
        read_only_fields = ["uuid", "created_at"]
        extra_kwargs = {"key": {"required": False}}

    def validate(self, attrs):
        if not attrs.get("key") and not getattr(self, "instance", None):
            attrs["key"] = slugify(attrs.get("name", "workflow")) or "workflow"
        return attrs


class WorkflowGraphSerializer(WorkflowSerializer):
    nodes = NodeSerializer(many=True, read_only=True)
    edges = EdgeSerializer(many=True, read_only=True)
    arenas = ArenaSerializer(many=True, read_only=True)

    class Meta(WorkflowSerializer.Meta):
        fields = WorkflowSerializer.Meta.fields + ["arenas", "nodes", "edges"]


class WorkflowViewSet(OrgScopedViewSet):
    queryset = Workflow.objects.prefetch_related(
        "workspace", "arenas", "nodes__agent", "nodes__role", "nodes__arena", "edges__source", "edges__target"
    ).all()
    serializer_class = WorkflowSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return WorkflowGraphSerializer
        return WorkflowSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("workspace"):
            queryset = queryset.filter(workspace__uuid=self.request.query_params["workspace"])
        return queryset

    def perform_create(self, serializer):
        org_id = current_org_id(self.request)
        workspace = serializer.validated_data.get("workspace")
        if workspace and workspace.organization_id != org_id:
            raise serializers.ValidationError({"workspace": "Workspace belongs to another organization."})
        serializer.save(organization_id=org_id)

    def perform_update(self, serializer):
        workspace = serializer.validated_data.get("workspace", serializer.instance.workspace)
        if workspace and workspace.organization_id != current_org_id(self.request):
            raise serializers.ValidationError({"workspace": "Workspace belongs to another organization."})
        serializer.save()

    @action(detail=True, methods=["post"], url_path="validate")
    def validate_graph(self, request, uuid=None):
        workflow = self.get_object()
        errors, warnings = _validate_graph_payload(request.data, workflow)
        return Response(
            {"valid": not errors, "errors": errors, "warnings": warnings},
            status=200 if not errors else 400,
        )

    @action(detail=True, methods=["put"], url_path="graph")
    def save_graph(self, request, uuid=None):
        """Atomically persist graph metadata, nodes, positions, and edges."""
        workflow = self.get_object()
        errors, warnings = _validate_graph_payload(request.data, workflow)
        if errors:
            return Response({"valid": False, "errors": errors, "warnings": warnings}, status=400)

        nodes_payload = request.data.get("nodes", [])
        edges_payload = request.data.get("edges", [])
        requested_keys = {row["key"] for row in nodes_payload}
        stale_nodes = workflow.nodes.exclude(key__in=requested_keys)
        protected = [
            node.key for node in stale_nodes
            if node.runs.exists() or node.loop_states.exists() or node.tasks.exists()
        ]
        if protected:
            return Response({
                "valid": False,
                "errors": ["Cannot remove nodes used by execution history: " + ", ".join(protected)],
                "warnings": warnings,
            }, status=409)

        agents = {agent.key: agent for agent in workflow.organization.agents.all()}
        roles = {role.key: role for role in workflow.organization.roles.all()}
        arenas = {str(arena.uuid): arena for arena in workflow.arenas.all()}
        with transaction.atomic():
            for field in ("name", "description", "status", "config"):
                if field in request.data:
                    setattr(workflow, field, request.data[field])
            workflow.save()

            saved_nodes = {}
            for row in nodes_payload:
                node, _ = Node.objects.update_or_create(
                    workflow=workflow,
                    key=row["key"],
                    defaults={
                        "name": row.get("name") or row["key"].replace("_", " ").title(),
                        "type": row["type"],
                        "agent": agents.get(row.get("agent_key")),
                        "role": roles.get(row.get("role_key")),
                        "arena": arenas.get(str(row.get("arena_uuid") or "")),
                        "config": row.get("config") or {},
                        "position_x": float(row.get("position_x", 0)),
                        "position_y": float(row.get("position_y", 0)),
                    },
                )
                saved_nodes[node.key] = node

            workflow.edges.all().delete()
            Edge.objects.bulk_create([
                Edge(
                    workflow=workflow,
                    source=saved_nodes[row["source_key"]],
                    target=saved_nodes[row["target_key"]],
                    label=row.get("label", ""),
                    condition=row.get("condition", ""),
                    order=int(row.get("order", index)),
                )
                for index, row in enumerate(edges_payload)
            ])
            stale_nodes.delete()

        workflow.refresh_from_db()
        saved = self.get_queryset().get(pk=workflow.pk)
        return Response(WorkflowGraphSerializer(saved, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="test")
    def test_workflow(self, request, uuid=None):
        """Run the saved graph synchronously in an isolated test project."""
        from apps.executions.api import ExecutionDetailSerializer
        from apps.projects.models import Project
        from core.workflow_engine import start_execution

        workflow = self.get_object()
        graph_payload = {
            "nodes": NodeSerializer(workflow.nodes.all(), many=True).data,
            "edges": EdgeSerializer(workflow.edges.all(), many=True).data,
        }
        errors, warnings = _validate_graph_payload(graph_payload, workflow)
        if errors:
            return Response({"valid": False, "errors": errors, "warnings": warnings}, status=400)

        suffix = uuid4().hex[:8]
        project = Project.objects.create(
            organization=workflow.organization,
            workflow=workflow,
            owner=request.user,
            key=f"test-{slugify(workflow.key)[:70]}-{suffix}",
            name=f"Test — {workflow.name}",
            idea="Workflow Studio test run",
            status=Project.Status.DRAFT,
            workspace_key=f"{workflow.organization.slug}-workflow-test-{suffix}",
            context={"is_workflow_test": True},
        )
        execution = start_execution(
            project,
            scenario=request.data.get("scenario", "success"),
            triggered_by=request.user,
            backend="inline",
        )
        execution.refresh_from_db()
        data = ExecutionDetailSerializer(execution, context={"request": request}).data
        return Response({
            "execution": data,
            "project_uuid": str(project.uuid),
            "warnings": warnings,
        }, status=201)


def _validate_graph_payload(payload, workflow):
    nodes = payload.get("nodes")
    edges = payload.get("edges")
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(nodes, list) or not nodes:
        return ["Add at least one node."], warnings
    if not isinstance(edges, list):
        errors.append("Edges must be a list.")
        edges = []

    keys = [str(row.get("key", "")).strip() for row in nodes]
    if any(not key for key in keys):
        errors.append("Every node needs a key.")
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        errors.append("Duplicate node keys: " + ", ".join(duplicates))
    if sum(row.get("type") == Node.Type.START for row in nodes) != 1:
        errors.append("A workflow must contain exactly one Start node.")

    valid_types = {value for value, _ in Node.Type.choices}
    invalid_types = sorted({str(row.get("type")) for row in nodes if row.get("type") not in valid_types})
    if invalid_types:
        errors.append("Unknown node types: " + ", ".join(invalid_types))

    key_set = set(keys)
    for index, edge in enumerate(edges, start=1):
        source = edge.get("source_key")
        target = edge.get("target_key")
        if source not in key_set or target not in key_set:
            errors.append(f"Edge {index} references a missing node ({source} → {target}).")

    agent_keys = set(workflow.organization.agents.values_list("key", flat=True))
    role_keys = set(workflow.organization.roles.values_list("key", flat=True))
    for row in nodes:
        if row.get("agent_key") and row["agent_key"] not in agent_keys:
            errors.append(f"Node {row.get('key')} references an unknown agent.")
        if row.get("role_key") and row["role_key"] not in role_keys:
            errors.append(f"Node {row.get('key')} references an unknown role.")

    outgoing = {edge.get("source_key") for edge in edges}
    for row in nodes:
        if row.get("type") not in {Node.Type.END, Node.Type.ARCHIVE} and row.get("key") not in outgoing:
            warnings.append(f"Node {row.get('name') or row.get('key')} has no outgoing connection.")
    return errors, warnings


class ArenaViewSet(OrgScopedViewSet):
    queryset = Arena.objects.select_related("workspace", "workflow").all()
    serializer_class = ArenaSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("workspace"):
            queryset = queryset.filter(workspace__uuid=self.request.query_params["workspace"])
        if self.request.query_params.get("workflow"):
            queryset = queryset.filter(workflow__uuid=self.request.query_params["workflow"])
        return queryset

    def perform_create(self, serializer):
        org_id = current_org_id(self.request)
        workspace = serializer.validated_data["workspace"]
        workflow = serializer.validated_data["workflow"]
        if workspace.organization_id != org_id or workflow.organization_id != org_id:
            raise serializers.ValidationError("Workspace and workflow must belong to the selected company.")
        if workflow.workspace_id and workflow.workspace_id != workspace.id:
            raise serializers.ValidationError({"workflow": "Workflow belongs to another workspace."})
        if workflow.workspace_id is None:
            workflow.workspace = workspace
            workflow.save(update_fields=["workspace", "updated_at"])
        serializer.save(organization_id=org_id)


class WorkflowLinkSerializer(serializers.ModelSerializer):
    workspace = serializers.SlugRelatedField(slug_field="uuid", queryset=Project.objects.all())
    source = serializers.SlugRelatedField(slug_field="uuid", queryset=Workflow.objects.all())
    target = serializers.SlugRelatedField(slug_field="uuid", queryset=Workflow.objects.all())

    class Meta:
        model = WorkflowLink
        fields = ["uuid", "workspace", "source", "target", "kind", "condition", "config", "created_at"]
        read_only_fields = ["uuid", "created_at"]


class WorkflowLinkViewSet(OrgScopedViewSet):
    queryset = WorkflowLink.objects.select_related("workspace", "source", "target").all()
    serializer_class = WorkflowLinkSerializer

    def perform_create(self, serializer):
        org_id = current_org_id(self.request)
        workspace = serializer.validated_data["workspace"]
        source = serializer.validated_data["source"]
        target = serializer.validated_data["target"]
        if source == target:
            raise serializers.ValidationError({"target": "A workflow cannot link to itself."})
        if any(item.organization_id != org_id for item in (workspace, source, target)):
            raise serializers.ValidationError("All linked objects must belong to the selected company.")
        if source.workspace_id != workspace.id or target.workspace_id != workspace.id:
            raise serializers.ValidationError("Both workflows must belong to this workspace.")
        serializer.save(organization_id=org_id)
