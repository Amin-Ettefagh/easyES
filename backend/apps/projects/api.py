"""Projects API: a Project is an *instance* of running a Workflow toward a goal.

Project ≠ Workflow (decoupling rule): the workflow is the reusable graph; the
project is one concrete pursuit of an idea, with its own tasks and executions.
"""
from __future__ import annotations

from django.db.models import Q
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api_common import OrgScopedViewSet
from apps.actors.models import Actor
from apps.projects.models import Project, Task


class TaskSerializer(serializers.ModelSerializer):
    project = serializers.SlugRelatedField(slug_field="uuid", queryset=Project.objects.all())
    assigned_actor = serializers.SlugRelatedField(slug_field="uuid", queryset=Actor.objects.all(), required=False, allow_null=True)
    node_key = serializers.CharField(source="node.key", read_only=True, default="")
    assigned_actor_name = serializers.CharField(
        source="assigned_actor.name", read_only=True, default=""
    )

    class Meta:
        model = Task
        fields = [
            "uuid", "project", "title", "description", "kind", "issue_type", "priority", "status", "labels", "acceptance_criteria", "due_at", "rank", "node_key",
            "assigned_actor", "assigned_actor_name", "iteration", "inputs", "outputs", "created_at", "updated_at",
        ]
        read_only_fields = ["uuid", "node_key", "assigned_actor_name", "created_at", "updated_at"]


class ProjectSerializer(serializers.ModelSerializer):
    workflow_key = serializers.CharField(source="workflow.key", read_only=True, default="")
    owner_name = serializers.CharField(source="owner.username", read_only=True, default="")
    task_count = serializers.IntegerField(source="tasks.count", read_only=True)
    execution_count = serializers.IntegerField(source="executions.count", read_only=True)
    workflow_count = serializers.IntegerField(source="workflows.count", read_only=True)
    workflows = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "uuid", "key", "name", "idea", "requirements", "status",
            "workflow", "workflow_key", "owner_name", "workspace_key", "context",
            "task_count", "execution_count", "workflow_count", "workflows", "created_at",
        ]
        read_only_fields = ["uuid", "workspace_key", "created_at"]

    def get_workflows(self, obj):
        return [
            {"uuid": str(workflow.uuid), "key": workflow.key, "name": workflow.name, "status": workflow.status, "node_count": workflow.nodes.count()}
            for workflow in obj.workflows.all()
        ]


class ProjectDetailSerializer(ProjectSerializer):
    tasks = TaskSerializer(many=True, read_only=True)

    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + ["tasks"]


class ProjectViewSet(OrgScopedViewSet):
    queryset = Project.objects.select_related("workflow", "owner").prefetch_related("workflows__nodes").all()
    serializer_class = ProjectSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list" and self.request.query_params.get("include_tests") != "1":
            # A JSON lookup for a missing key evaluates to SQL NULL.  Using
            # ``exclude(key=True)`` therefore also hid ordinary projects whose
            # context had no test flag. Keep explicit false values and missing
            # keys, and hide only rows deliberately marked as studio tests.
            queryset = queryset.filter(
                Q(context__is_workflow_test=False)
                | ~Q(context__has_key="is_workflow_test")
            )
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProjectDetailSerializer
        return ProjectSerializer

    def perform_create(self, serializer):
        # Attach the workspace to the explicitly selected company and stamp a
        # stable filesystem key.
        from core.api_common import current_org_id

        workflow = serializer.validated_data.get("workflow")
        org_id = current_org_id(self.request)
        if workflow and workflow.organization_id != org_id:
            raise serializers.ValidationError({"workflow": "Workflow belongs to another organization."})
        key = serializer.validated_data.get("key", "project")
        instance = serializer.save(organization_id=org_id, owner=self.request.user)
        if workflow and workflow.workspace_id is None:
            workflow.workspace = instance
            workflow.save(update_fields=["workspace", "updated_at"])
        if not instance.workspace_key:
            instance.workspace_key = f"{instance.organization.slug}-{key}"
            instance.save(update_fields=["workspace_key"])

    @action(detail=True, methods=["get"], url_path="repository")
    def repository(self, request, uuid=None):
        from core.workspace_git import WorkspaceGitError, repository_state

        project = self.get_object()
        try:
            return Response(repository_state(project.workspace_key))
        except WorkspaceGitError as exc:
            return Response({"detail": str(exc)}, status=500)

    @action(detail=True, methods=["get"], url_path="repository-diff")
    def repository_diff(self, request, uuid=None):
        from core.workspace_git import WorkspaceGitError, repository_diff

        try:
            return Response({"diff": repository_diff(self.get_object().workspace_key, request.query_params.get("revision", "HEAD"))})
        except WorkspaceGitError as exc:
            return Response({"detail": str(exc)}, status=500)

    @action(detail=True, methods=["post"], url_path="repository-commit")
    def repository_commit(self, request, uuid=None):
        from core.workspace_git import WorkspaceGitError, commit_workspace

        try:
            return Response(commit_workspace(self.get_object().workspace_key, str(request.data.get("message") or "Manual workspace checkpoint")))
        except WorkspaceGitError as exc:
            return Response({"detail": str(exc)}, status=500)


class TaskViewSet(OrgScopedViewSet):
    queryset = Task.objects.select_related("project", "node", "assigned_actor").all()
    serializer_class = TaskSerializer
    org_field = "project__organization"

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("project"):
            queryset = queryset.filter(project__uuid=self.request.query_params["project"])
        if self.request.query_params.get("status"):
            queryset = queryset.filter(status=self.request.query_params["status"])
        return queryset.order_by("rank", "-created_at")

    def perform_create(self, serializer):
        from core.api_common import current_org_id

        project = serializer.validated_data["project"]
        actor = serializer.validated_data.get("assigned_actor")
        if project.organization_id != current_org_id(self.request):
            raise serializers.ValidationError({"project": "Workspace belongs to another organization."})
        if actor and actor.organization_id != project.organization_id:
            raise serializers.ValidationError({"assigned_actor": "Actor belongs to another organization."})
        serializer.save()
