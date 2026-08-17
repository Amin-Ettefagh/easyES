"""Prompts API: prompts and their immutable versions."""
from __future__ import annotations

from rest_framework import serializers

from core.api_common import OrgScopedViewSet
from apps.prompts.models import Prompt, PromptVersion


class PromptVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptVersion
        fields = ["uuid", "version", "content", "is_active", "notes", "created_at"]


class PromptSerializer(serializers.ModelSerializer):
    versions = PromptVersionSerializer(many=True, read_only=True)
    active_content = serializers.SerializerMethodField()

    class Meta:
        model = Prompt
        fields = ["uuid", "key", "name", "kind", "description", "active_content", "versions"]

    def get_active_content(self, obj) -> str:
        version = obj.active_version
        return version.content if version else ""


class PromptViewSet(OrgScopedViewSet):
    queryset = Prompt.objects.prefetch_related("versions").all()
    serializer_class = PromptSerializer
