"""Agents API: list/configure specialized AI agents.

Exposes exactly the knobs the demo must let a user edit (DemoPrompt DoD):
model, sampling params, token/cost budgets, status/enabled — plus a dedicated
``prompt`` action that edits the agent's system prompt by creating a new
immutable :class:`~apps.prompts.models.PromptVersion` (never mutating history).
"""
from __future__ import annotations

from time import perf_counter

from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api_common import OrgScopedViewSet, current_org_id
from core.model_gateway.base import ProviderError
from apps.agents.models import Agent, KnowledgeSource, MemoryEntry
from apps.models_registry.models import Credential, Model
from apps.models_registry.runtime import call_registered_model
from apps.projects.models import Project
from apps.workflows.models import Workflow


class AgentSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True, default="")
    model_key = serializers.CharField(source="model.key", read_only=True, default="")
    provider = serializers.CharField(source="model.provider.adapter", read_only=True, default="")
    provider_name = serializers.CharField(source="model.provider.name", read_only=True, default="")
    credential_label = serializers.CharField(source="credential.label", read_only=True, default="")
    system_prompt = serializers.SerializerMethodField()
    initial_prompt = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Agent
        fields = [
            "uuid", "key", "name", "title", "description", "role", "role_name",
            "model", "model_key", "provider", "provider_name", "credential",
            "credential_label", "temperature", "max_output_tokens",
            "context_limit", "token_budget", "cost_budget", "status", "is_enabled",
            "system_prompt", "initial_prompt", "config", "created_at",
        ]
        read_only_fields = ["uuid", "created_at"]
        extra_kwargs = {
            "key": {"required": False},
            "model": {"required": False},
            "credential": {"required": False},
            "role": {"required": False},
        }

    def validate(self, attrs):
        if not attrs.get("key") and not getattr(self, "instance", None):
            attrs["key"] = slugify(attrs.get("name", "agent")) or "agent"
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        from apps.actors.models import Actor, RoleAssignment

        initial_prompt = validated_data.pop("initial_prompt", "")
        agent = super().create(validated_data)
        actor = Actor.objects.create(
            organization=agent.organization,
            kind=Actor.Kind.AI_AGENT,
            name=agent.name,
            agent=agent,
            presence=Actor.Presence.AVAILABLE,
        )
        if agent.role_id:
            RoleAssignment.objects.create(actor=actor, role=agent.role, is_primary=True)
        if initial_prompt.strip():
            _set_agent_prompt(agent, initial_prompt, self.context.get("request"))
        return agent

    def get_system_prompt(self, obj) -> str:
        assignment = obj.prompt_assignments.filter(kind="system").first()
        version = assignment.resolve_version() if assignment else None
        return version.content if version else ""


class AgentViewSet(OrgScopedViewSet):
    queryset = Agent.objects.select_related("role", "role__unit", "model", "model__provider", "credential").prefetch_related("prompt_assignments__prompt__versions").all()
    serializer_class = AgentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get("search", "").strip()
        unit = self.request.query_params.get("unit", "").strip()
        status_value = self.request.query_params.get("status", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(role__name__icontains=search)
                | Q(description__icontains=search)
            )
        if unit:
            queryset = queryset.filter(role__unit__uuid=unit)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset.order_by("role__name", "name")

    def perform_create(self, serializer):
        org_id = current_org_id(self.request)
        role = serializer.validated_data.get("role")
        model = serializer.validated_data.get("model")
        credential = serializer.validated_data.get("credential")
        if role and role.organization_id != org_id:
            raise serializers.ValidationError({"role": "Role belongs to another organization."})
        if model and model.provider.organization_id != org_id:
            raise serializers.ValidationError({"model": "Model belongs to another organization."})
        if credential and credential.provider.organization_id != org_id:
            raise serializers.ValidationError({"credential": "Credential belongs to another organization."})
        if model and credential and credential.provider_id != model.provider_id:
            raise serializers.ValidationError({"credential": "Credential must belong to the selected model provider."})
        serializer.save(organization_id=org_id)

    def perform_update(self, serializer):
        from apps.actors.models import Actor, RoleAssignment

        model = serializer.validated_data.get("model", serializer.instance.model)
        credential = serializer.validated_data.get("credential", serializer.instance.credential)
        if model and credential and credential.provider_id != model.provider_id:
            raise serializers.ValidationError({"credential": "Credential must belong to the selected model provider."})
        instance = serializer.save()
        try:
            actor = instance.actor
        except Actor.DoesNotExist:
            actor = None
        if actor:
            actor.name = instance.name
            actor.save(update_fields=["name", "updated_at"])
            actor.role_assignments.all().delete()
            if instance.role_id:
                RoleAssignment.objects.create(actor=actor, role=instance.role, is_primary=True)

    def perform_destroy(self, instance):
        from apps.actors.models import Actor

        try:
            actor = instance.actor
        except Actor.DoesNotExist:
            actor = None
        if actor:
            actor.delete()
        instance.delete()

    @action(detail=True, methods=["put", "patch"])
    def prompt(self, request, uuid=None):
        """Edit the agent's system prompt: creates a new PromptVersion and
        points the assignment at it. Body: ``{"content": "..."}``."""
        agent = self.get_object()
        content = request.data.get("content", "")
        if not content.strip():
            return Response({"detail": "content is required"}, status=400)

        version = _set_agent_prompt(agent, content, request)
        return Response({"version": version.version, "content": version.content})

    @action(detail=False, methods=["post"], url_path="test-runtime")
    def test_runtime(self, request):
        """Run a real, low-token inference before an Agent is saved."""
        org_id = current_org_id(request)
        model_id = request.data.get("model")
        if not model_id:
            return Response({"ok": False, "detail": "Select a model before testing."}, status=400)
        model = Model.objects.select_related("provider").filter(
            id=model_id, organization_id=org_id, is_active=True
        ).first()
        if model is None:
            return Response({"ok": False, "detail": "The selected model is not available in this company."}, status=400)
        credential = None
        if request.data.get("credential"):
            credential = Credential.objects.select_related("provider").filter(
                id=request.data["credential"], provider__organization_id=org_id
            ).first()
            if credential is None:
                return Response({"ok": False, "detail": "The selected credential is not available in this company."}, status=400)
            if credential.provider_id != model.provider_id:
                return Response({"ok": False, "detail": "Credential must belong to the selected model provider."}, status=400)

        prompt = str(request.data.get("prompt") or "You are a helpful company operations agent.").strip()
        user_input = str(request.data.get("input") or "Reply with OK and one short sentence confirming that you are ready.").strip()
        started = perf_counter()
        try:
            response, resolved_credential = call_registered_model(
                model,
                credential,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_input},
                ],
                temperature=float(request.data.get("temperature", 0.2)),
                max_tokens=min(max(int(request.data.get("max_tokens") or 128), 1), 512),
                metadata={"stage": "agent_runtime_test", "scenario": "success"},
            )
        except (ProviderError, ValueError) as exc:
            return Response({
                "ok": False,
                "detail": str(exc),
                "provider": model.provider.name,
                "adapter": model.provider.adapter,
                "model": model.remote_id or model.key,
                "latency_ms": round((perf_counter() - started) * 1000),
            }, status=502 if isinstance(exc, ProviderError) else 400)
        return Response({
            "ok": True,
            "text": response.text,
            "provider": model.provider.name,
            "adapter": model.provider.adapter,
            "model": response.model or model.remote_id or model.key,
            "credential": resolved_credential.label if resolved_credential else None,
            "usage": {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "total_tokens": response.total_tokens,
            },
            "cost": response.cost,
            "latency_ms": round((perf_counter() - started) * 1000),
        })


class KnowledgeSourceSerializer(serializers.ModelSerializer):
    agent = serializers.SlugRelatedField(slug_field="uuid", queryset=Agent.objects.all())
    agent_name = serializers.CharField(source="agent.name", read_only=True)

    class Meta:
        model = KnowledgeSource
        fields = ["uuid", "agent", "agent_name", "name", "kind", "content", "url", "metadata", "is_enabled", "created_at", "updated_at"]
        read_only_fields = ["uuid", "created_at", "updated_at"]


class KnowledgeSourceViewSet(OrgScopedViewSet):
    queryset = KnowledgeSource.objects.select_related("agent").all()
    serializer_class = KnowledgeSourceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("agent"):
            queryset = queryset.filter(agent__uuid=self.request.query_params["agent"])
        return queryset

    def perform_create(self, serializer):
        org_id = current_org_id(self.request)
        agent = serializer.validated_data["agent"]
        if agent.organization_id != org_id:
            raise serializers.ValidationError({"agent": "Agent belongs to another organization."})
        serializer.save(organization_id=org_id)


class MemoryEntrySerializer(serializers.ModelSerializer):
    workspace = serializers.SlugRelatedField(slug_field="uuid", queryset=Project.objects.all(), required=False, allow_null=True)
    workflow = serializers.SlugRelatedField(slug_field="uuid", queryset=Workflow.objects.all(), required=False, allow_null=True)
    agent = serializers.SlugRelatedField(slug_field="uuid", queryset=Agent.objects.all(), required=False, allow_null=True)

    class Meta:
        model = MemoryEntry
        fields = ["uuid", "workspace", "workflow", "agent", "namespace", "key", "content", "importance", "metadata", "last_accessed_at", "created_at", "updated_at"]
        read_only_fields = ["uuid", "last_accessed_at", "created_at", "updated_at"]


class MemoryEntryViewSet(OrgScopedViewSet):
    queryset = MemoryEntry.objects.select_related("workspace", "workflow", "agent").all()
    serializer_class = MemoryEntrySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("workspace"):
            queryset = queryset.filter(workspace__uuid=self.request.query_params["workspace"])
        if self.request.query_params.get("agent"):
            queryset = queryset.filter(agent__uuid=self.request.query_params["agent"])
        if self.request.query_params.get("namespace"):
            queryset = queryset.filter(namespace=self.request.query_params["namespace"])
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(Q(key__icontains=search) | Q(content__icontains=search))
        return queryset.order_by("-importance", "-updated_at")

    def perform_create(self, serializer):
        org_id = current_org_id(self.request)
        for field in ("workspace", "workflow", "agent"):
            value = serializer.validated_data.get(field)
            if value and value.organization_id != org_id:
                raise serializers.ValidationError({field: f"{field.title()} belongs to another organization."})
        serializer.save(organization_id=org_id)


@transaction.atomic
def _set_agent_prompt(agent, content, request=None):
    from apps.prompts.models import AgentPromptAssignment, Prompt, PromptVersion

    assignment = agent.prompt_assignments.filter(kind="system").first()
    if assignment is None:
        prompt = Prompt.objects.create(
            organization=agent.organization,
            key=f"{agent.key}_system",
            name=f"{agent.name} System Prompt",
            kind=Prompt.Kind.SYSTEM,
        )
        assignment = AgentPromptAssignment.objects.create(agent=agent, prompt=prompt, kind="system")
    else:
        prompt = assignment.prompt
    last = prompt.versions.order_by("-version").first()
    next_version = (last.version + 1) if last else 1
    prompt.versions.update(is_active=False)
    version = PromptVersion.objects.create(
        prompt=prompt,
        version=next_version,
        content=content,
        is_active=True,
        created_by=request.user if request and request.user.is_authenticated else None,
    )
    assignment.version = version
    assignment.save(update_fields=["version", "updated_at"])
    return version
