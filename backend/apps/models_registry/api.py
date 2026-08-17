"""Provider, model and encrypted credential management API."""
from __future__ import annotations

from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api_common import OrgScopedViewSet, current_org_id
from core.model_gateway.base import ModelRequest, ProviderError
from core.model_gateway.registry import get_provider
from core.provider_catalog import get_catalog_entry, provider_catalog
from core.security import mask
from apps.models_registry.models import Credential, Model, ModelProvider


class ModelProviderSerializer(serializers.ModelSerializer):
    adapter_label = serializers.CharField(source="get_adapter_display", read_only=True)
    credential_count = serializers.IntegerField(source="credentials.count", read_only=True)
    model_count = serializers.IntegerField(source="models.count", read_only=True)

    class Meta:
        model = ModelProvider
        fields = [
            "id", "uuid", "key", "name", "adapter", "adapter_label", "base_url",
            "config", "is_active", "credential_count", "model_count", "created_at",
        ]
        read_only_fields = ["id", "uuid", "created_at"]
        extra_kwargs = {"key": {"required": False}}

    def validate(self, attrs):
        if not attrs.get("key") and not self.instance:
            attrs["key"] = slugify(attrs.get("name", "provider"))[:80] or "provider"
        return attrs


class ModelSerializer(serializers.ModelSerializer):
    provider_key = serializers.CharField(source="provider.key", read_only=True)
    provider_name = serializers.CharField(source="provider.name", read_only=True)

    class Meta:
        model = Model
        fields = [
            "id", "uuid", "key", "remote_id", "name", "provider", "provider_key",
            "provider_name", "context_window", "max_output_tokens", "input_cost_per_1k",
            "output_cost_per_1k", "default_params", "is_active",
        ]
        read_only_fields = ["id", "uuid"]
        extra_kwargs = {"key": {"required": False}}

    def validate(self, attrs):
        if not attrs.get("key") and not self.instance:
            source = attrs.get("remote_id") or attrs.get("name", "model")
            attrs["key"] = slugify(source)[:120] or "model"
        return attrs


class CredentialSerializer(serializers.ModelSerializer):
    secret = serializers.CharField(write_only=True, required=False, allow_blank=True)
    secret_data = serializers.DictField(write_only=True, required=False)
    secret_hint = serializers.SerializerMethodField()
    configured_fields = serializers.SerializerMethodField()
    provider_name = serializers.CharField(source="provider.name", read_only=True)

    class Meta:
        model = Credential
        fields = [
            "id", "uuid", "provider", "provider_name", "label", "secret", "secret_data",
            "secret_hint", "configured_fields",
        ]
        read_only_fields = ["id", "uuid"]

    def get_secret_hint(self, obj) -> str:
        values = obj.get_secret_data()
        raw = values.get("api_key") or values.get("aws_access_key_id") or ""
        return mask(str(raw)) if raw else ""

    def get_configured_fields(self, obj) -> dict:
        hints = {}
        for key, value in obj.get_secret_data().items():
            if value in (None, ""):
                continue
            raw = str(value)
            hints[key] = f"configured ({len(raw)} chars)" if len(raw) > 40 else mask(raw)
        return hints

    def _take_secret_data(self, validated_data):
        values = validated_data.pop("secret_data", None)
        legacy = validated_data.pop("secret", "")
        if values is None and legacy:
            values = {"api_key": legacy}
        return values

    def create(self, validated_data):
        values = self._take_secret_data(validated_data)
        credential = Credential(**validated_data)
        if values:
            credential.set_secret_data(values)
        credential.save()
        return credential

    def update(self, instance, validated_data):
        values = self._take_secret_data(validated_data)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if values:
            instance.set_secret_data({**instance.get_secret_data(), **values})
        instance.save()
        return instance


def _org_id(request):
    return current_org_id(request)


def _adapter_for(provider: ModelProvider, credential: Credential | None = None):
    credentials = credential.get_secret_data() if credential else {}
    return get_provider(
        provider.adapter,
        api_key=credentials.get("api_key", ""),
        credentials=credentials,
        base_url=provider.base_url,
        **(provider.config or {}),
    )


class ModelProviderViewSet(OrgScopedViewSet):
    queryset = ModelProvider.objects.prefetch_related("credentials", "models").all()
    serializer_class = ModelProviderSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

    def perform_create(self, serializer):
        serializer.save(organization_id=_org_id(self.request))

    @action(detail=False, methods=["get"])
    def catalog(self, request):
        entries = provider_catalog()
        search = request.query_params.get("search", "").strip().lower()
        category = request.query_params.get("category", "").strip()
        if search:
            entries = [item for item in entries if search in item["name"].lower() or search in item["key"]]
        if category:
            entries = [item for item in entries if item["category"] == category]
        categories = sorted({item["category"] for item in provider_catalog()})
        return Response({"count": len(entries), "categories": categories, "results": entries})

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def connect(self, request):
        """Create/update a provider, encrypted credential and optional model."""
        catalog_key = str(request.data.get("catalog_key", "")).strip()
        entry = get_catalog_entry(catalog_key)
        if not entry:
            return Response({"detail": "Unknown provider catalogue key."}, status=400)
        org_id = _org_id(request)
        instance_key = slugify(request.data.get("key") or catalog_key)[:80] or catalog_key
        config = {**(request.data.get("config") or {})}
        config.setdefault("catalog_key", catalog_key)
        config.setdefault("capabilities", entry["capabilities"])
        provider, _ = ModelProvider.objects.update_or_create(
            organization_id=org_id,
            key=instance_key,
            defaults={
                "name": request.data.get("name") or entry["name"],
                "adapter": request.data.get("adapter") or entry["adapter"],
                "base_url": request.data.get("base_url", entry["base_url"]),
                "config": config,
                "is_active": True,
            },
        )
        credential = None
        secret_data = request.data.get("credentials") or {}
        if secret_data:
            credential, _ = Credential.objects.get_or_create(provider=provider, label=request.data.get("credential_label") or "default")
            credential.set_secret_data({**credential.get_secret_data(), **secret_data})
            credential.save()

        model = None
        remote_id = str(request.data.get("model_id") or "").strip()
        if remote_id:
            model_key = slugify(request.data.get("model_key") or f"{provider.key}-{remote_id}")[:120] or "model"
            model, _ = Model.objects.update_or_create(
                organization_id=org_id,
                key=model_key,
                defaults={
                    "provider": provider,
                    "remote_id": remote_id,
                    "name": request.data.get("model_name") or remote_id,
                    "context_window": int(request.data.get("context_window") or 8192),
                    "max_output_tokens": int(request.data.get("max_output_tokens") or 2048),
                    "default_params": request.data.get("default_params") or {},
                    "is_active": True,
                },
            )
        return Response({
            "provider": ModelProviderSerializer(provider, context={"request": request}).data,
            "credential": CredentialSerializer(credential, context={"request": request}).data if credential else None,
            "model": ModelSerializer(model, context={"request": request}).data if model else None,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def test(self, request, uuid=None):
        provider = self.get_object()
        credential = provider.credentials.filter(uuid=request.data.get("credential_uuid")).first() if request.data.get("credential_uuid") else provider.credentials.first()
        adapter = _adapter_for(provider, credential)
        mode = request.data.get("mode", "discovery")
        try:
            if mode == "inference":
                model_id = request.data.get("model_id") or provider.models.filter(is_active=True).values_list("remote_id", flat=True).first()
                if not model_id:
                    return Response({"detail": "model_id is required for an inference test"}, status=400)
                result = adapter.call(ModelRequest(
                    model=model_id,
                    messages=[{"role": "user", "content": request.data.get("prompt") or "Reply with OK."}],
                    temperature=0,
                    max_tokens=min(int(request.data.get("max_tokens") or 16), 64),
                ))
                return Response({"ok": True, "mode": mode, "text": result.text, "model": result.model, "usage": {"input_tokens": result.input_tokens, "output_tokens": result.output_tokens}})
            models = adapter.list_models()
            return Response({"ok": True, "mode": "discovery", "model_count": len(models), "models": models[:200]})
        except ProviderError as exc:
            return Response({"ok": False, "detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    @action(detail=True, methods=["post"], url_path="sync-models")
    @transaction.atomic
    def sync_models(self, request, uuid=None):
        provider = self.get_object()
        rows = request.data.get("models") or []
        if not isinstance(rows, list):
            return Response({"detail": "models must be a list"}, status=400)
        output = []
        for row in rows[:500]:
            remote_id = str(row.get("id") or "").strip()
            if not remote_id:
                continue
            key = slugify(f"{provider.key}-{remote_id}")[:120] or f"{provider.key}-model-{len(output) + 1}"
            model, _ = Model.objects.update_or_create(
                organization=provider.organization,
                key=key,
                defaults={"provider": provider, "remote_id": remote_id, "name": row.get("name") or remote_id, "is_active": True},
            )
            output.append(ModelSerializer(model, context={"request": request}).data)
        return Response({"count": len(output), "models": output})


class ModelViewSet(OrgScopedViewSet):
    queryset = Model.objects.select_related("provider").all()
    serializer_class = ModelSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        provider = self.request.query_params.get("provider")
        if provider:
            queryset = queryset.filter(provider__uuid=provider)
        return queryset

    def perform_create(self, serializer):
        provider = serializer.validated_data["provider"]
        if provider.organization_id != _org_id(self.request):
            raise serializers.ValidationError({"provider": "Provider belongs to another organization."})
        serializer.save(organization=provider.organization)


class CredentialViewSet(OrgScopedViewSet):
    queryset = Credential.objects.select_related("provider").all()
    serializer_class = CredentialSerializer
    org_field = "provider__organization"

    def perform_create(self, serializer):
        provider = serializer.validated_data["provider"]
        if provider.organization_id != _org_id(self.request):
            raise serializers.ValidationError({"provider": "Provider belongs to another organization."})
        serializer.save()
