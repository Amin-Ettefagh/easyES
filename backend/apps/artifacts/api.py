"""Artifacts API: deliverables produced by the run (docs, code, plans, reports).

Read-only — artifacts are outputs of node runs. Filterable by project so the
Control Room can show "what this project has produced so far".
"""
from __future__ import annotations

from rest_framework import serializers

from core.api_common import ReadOnlyOrgScopedViewSet
from apps.artifacts.models import Artifact


class ArtifactSerializer(serializers.ModelSerializer):
    project_key = serializers.CharField(source="project.key", read_only=True, default="")
    produced_by_name = serializers.CharField(
        source="produced_by.name", read_only=True, default=""
    )
    node_key = serializers.CharField(source="node_run.node_key", read_only=True, default="")

    class Meta:
        model = Artifact
        fields = [
            "uuid", "kind", "name", "path", "content", "content_type",
            "iteration", "project", "project_key", "produced_by_name", "node_key",
            "metadata", "created_at",
        ]


class ArtifactListSerializer(ArtifactSerializer):
    """List view omits full content — the canvas shows names, detail shows body."""

    class Meta(ArtifactSerializer.Meta):
        fields = [
            "uuid", "kind", "name", "path", "content_type", "iteration",
            "project_key", "produced_by_name", "node_key", "created_at",
        ]


class ArtifactViewSet(ReadOnlyOrgScopedViewSet):
    queryset = Artifact.objects.select_related("project", "produced_by", "node_run").all()
    serializer_class = ArtifactSerializer
    filterset_fields = ["project", "kind"]

    def get_serializer_class(self):
        if self.action == "list":
            return ArtifactListSerializer
        return ArtifactSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        project = self.request.query_params.get("project")
        if project:
            qs = qs.filter(project__uuid=project)
        return qs
