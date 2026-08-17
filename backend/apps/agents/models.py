from django.db import models

from core.db import BaseModel


class Agent(BaseModel):
    """A configurable AI worker.

    An Agent is NOT a Role and NOT an Actor (Idea.md §72): a Role is the job, an
    Actor is who performs it, and the Agent is the concrete AI configuration an
    ai_agent Actor points at. Every knob the demo lets you edit lives here or on
    the linked prompt assignment (DemoPrompt §11): model/provider/credential,
    sampling params, context limit, token & cost budgets, tools, permissions,
    capabilities, and an enabled/status switch.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        DISABLED = "disabled", "Disabled"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="agents"
    )
    role = models.ForeignKey(
        "structure.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agents",
    )
    key = models.SlugField(max_length=80)
    name = models.CharField(max_length=150)
    title = models.CharField(max_length=180, blank=True)
    description = models.TextField(blank=True)

    # Model / provider / credential are decoupled: an Agent references a Model,
    # the Model references a Provider, and the Credential is resolved at call
    # time. Any of these may be overridden per-agent; nulls fall back to org
    # defaults in the service layer.
    model = models.ForeignKey(
        "models_registry.Model",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agents",
    )
    credential = models.ForeignKey(
        "models_registry.Credential",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agents",
    )

    # Sampling / context configuration.
    temperature = models.FloatField(default=0.7)
    max_output_tokens = models.PositiveIntegerField(default=1024)
    context_limit = models.PositiveIntegerField(default=8192)

    # Budgets — enforced by the execution engine's loop-safety guard.
    token_budget = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    cost_budget = models.DecimalField(
        max_digits=12, decimal_places=4, default=0, help_text="0 = unlimited (USD)"
    )

    capabilities = models.ManyToManyField(
        "structure.Capability", blank=True, related_name="agents"
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        unique_together = ("organization", "key")
        indexes = [models.Index(fields=["organization", "status"])]

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class AgentToolGrant(BaseModel):
    """Grants an Agent access to a Tool (Tool ≠ Connector, Idea.md §72).

    Agent tool access is *allow-listed*: an agent can only invoke tools it has
    been explicitly granted, which is how the demo keeps agents from running
    arbitrary shell (DemoPrompt security constraints)."""

    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="tool_grants")
    tool = models.ForeignKey(
        "tools.Tool", on_delete=models.CASCADE, related_name="agent_grants"
    )
    is_enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        unique_together = ("agent", "tool")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.agent.key} -> {self.tool_id}"


class AgentPermission(BaseModel):
    """A single scoped capability flag for an Agent (e.g. ``fs.write``,
    ``net.fetch``). Kept as explicit rows so the UI can toggle them and the
    engine can check them without parsing free-form config."""

    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="permissions")
    scope = models.CharField(max_length=120)
    is_allowed = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        unique_together = ("agent", "scope")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.agent.key}:{self.scope}={self.is_allowed}"


class KnowledgeSource(BaseModel):
    """Editable knowledge attached to an Agent without baking it into prompts."""

    class Kind(models.TextChoices):
        TEXT = "text", "Text"
        URL = "url", "URL"
        FILE = "file", "File"
        MEMORY = "memory", "Memory"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="knowledge_sources"
    )
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="knowledge_sources")
    name = models.CharField(max_length=180)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.TEXT)
    content = models.TextField(blank=True)
    url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_enabled = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        indexes = [models.Index(fields=["organization", "agent", "kind"])]


class MemoryEntry(BaseModel):
    """Persistent, tenant-scoped agent memory with explicit provenance."""

    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="memory_entries")
    workspace = models.ForeignKey("projects.Project", on_delete=models.CASCADE, null=True, blank=True, related_name="memory_entries")
    workflow = models.ForeignKey("workflows.Workflow", on_delete=models.CASCADE, null=True, blank=True, related_name="memory_entries")
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, null=True, blank=True, related_name="memory_entries")
    namespace = models.SlugField(max_length=100, default="default")
    key = models.CharField(max_length=200)
    content = models.TextField()
    importance = models.FloatField(default=0.5)
    metadata = models.JSONField(default=dict, blank=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        unique_together = ("organization", "namespace", "key")
        indexes = [models.Index(fields=["organization", "namespace", "importance"])]
