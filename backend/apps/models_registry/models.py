import json

from django.db import models

from core.db import BaseModel
from core.security import decrypt_secret, encrypt_secret


class ModelProvider(BaseModel):
    """A source of LLM inference (OpenAI, Anthropic, local, or the built-in
    deterministic Fake provider used for offline demos).

    The ``adapter`` string selects a concrete
    :class:`core.model_gateway.base.BaseModelProvider` implementation, keeping
    the domain independent of any single vendor (Idea.md §4, §36).
    """

    class Adapter(models.TextChoices):
        FAKE = "fake", "Fake (deterministic, offline)"
        OPENAI_RESPONSES = "openai_responses", "OpenAI Responses API"
        OPENAI_COMPATIBLE = "openai_compatible", "OpenAI-compatible Chat Completions"
        ANTHROPIC = "anthropic", "Anthropic"
        GEMINI = "gemini", "Google Gemini"
        AZURE_OPENAI = "azure_openai", "Azure OpenAI / Foundry"
        BEDROCK = "bedrock", "Amazon Bedrock"
        VERTEX = "vertex", "Google Vertex AI"
        COHERE = "cohere", "Cohere"
        REPLICATE = "replicate", "Replicate Predictions"
        CLOUDFLARE = "cloudflare", "Cloudflare Workers AI"
        GENERIC_REST = "generic_rest", "Configurable REST"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="model_providers",
    )
    key = models.SlugField(max_length=80)
    name = models.CharField(max_length=150)
    adapter = models.CharField(max_length=40, choices=Adapter.choices, default=Adapter.FAKE)
    base_url = models.URLField(blank=True)
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        unique_together = ("organization", "key")

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Credential(BaseModel):
    """An encrypted API key for a provider. Values are never stored in plain
    text and never serialized back to clients (Idea.md §64)."""

    provider = models.ForeignKey(
        ModelProvider, on_delete=models.CASCADE, related_name="credentials"
    )
    label = models.CharField(max_length=120, default="default")
    _secret = models.TextField(db_column="secret_encrypted", blank=True)

    class Meta(BaseModel.Meta):
        unique_together = ("provider", "label")

    def set_secret(self, raw: str) -> None:
        self._secret = encrypt_secret(raw)

    def get_secret(self) -> str:
        return decrypt_secret(self._secret) if self._secret else ""

    def set_secret_data(self, values: dict) -> None:
        """Encrypt a structured credential document as one atomic secret."""
        self.set_secret(json.dumps(values, ensure_ascii=False))

    def get_secret_data(self) -> dict:
        """Return structured credentials, preserving legacy single API keys."""
        raw = self.get_secret()
        if not raw:
            return {}
        try:
            value = json.loads(raw)
            if isinstance(value, dict):
                return value
        except (json.JSONDecodeError, TypeError):
            pass
        return {"api_key": raw}

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.provider.key}:{self.label}"


class Model(BaseModel):
    """A specific model exposed by a provider (e.g. ``gpt-4o``, ``fake-smart``).

    Agents reference a Model, and the Model carries limits/cost so runs can be
    metered without hard-coding vendor specifics.
    """

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="models"
    )
    provider = models.ForeignKey(ModelProvider, on_delete=models.CASCADE, related_name="models")
    key = models.SlugField(max_length=120)
    # Exact vendor identifier (may contain slashes, colons and uppercase).
    # ``key`` remains the local stable slug used by URLs and relationships.
    remote_id = models.CharField(max_length=250, blank=True)
    name = models.CharField(max_length=150)
    context_window = models.PositiveIntegerField(default=8192)
    max_output_tokens = models.PositiveIntegerField(default=2048)
    input_cost_per_1k = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    output_cost_per_1k = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    default_params = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        unique_together = ("organization", "key")

    def __str__(self) -> str:  # pragma: no cover
        return self.name
