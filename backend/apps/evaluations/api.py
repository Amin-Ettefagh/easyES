"""Evaluations API: QA verdicts that drive the loop.

Evaluation ≠ Execution (decoupling rule): an evaluation is a judgement about a
run's output — its ``passed`` flag and ``feedback`` are exactly what the DECISION
gate reads to decide pass / fix-and-retry / give-up.
"""
from __future__ import annotations

from rest_framework import serializers

from core.api_common import ReadOnlyOrgScopedViewSet
from apps.evaluations.models import Evaluation


class EvaluationSerializer(serializers.ModelSerializer):
    project_key = serializers.CharField(source="project.key", read_only=True, default="")
    node_key = serializers.CharField(source="node_run.node_key", read_only=True, default="")

    class Meta:
        model = Evaluation
        fields = [
            "uuid", "project", "project_key", "node_key", "iteration",
            "verdict", "passed", "score",
            "tests_passed", "tests_total", "tests_failed",
            "requirement_coverage", "critical_errors", "coverage_threshold",
            "summary", "feedback", "details", "created_at",
        ]


class EvaluationViewSet(ReadOnlyOrgScopedViewSet):
    queryset = Evaluation.objects.select_related("project", "node_run").all()
    serializer_class = EvaluationSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        project = self.request.query_params.get("project")
        if project:
            qs = qs.filter(project__uuid=project)
        return qs
