from django.conf import settings
from django.db import models

from core.db import BaseModel


class Prompt(BaseModel):
    """A named, versioned prompt (Idea.md §37, DemoPrompt §11/§27).

    The ``Prompt`` row is the stable identity ("Backend Engineer system
    prompt"); the actual text lives in :class:`PromptVersion` so edits are
    non-destructive and every execution can record exactly which version it
    used. This is what lets the demo edit an agent's prompt and still audit
    past runs against the old text.
    """

    class Kind(models.TextChoices):
        SYSTEM = "system", "System"
        TASK = "task", "Task"
        EVALUATION = "evaluation", "Evaluation"
        REVIEW = "review", "Review"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="prompts"
    )
    key = models.SlugField(max_length=100)
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=30, choices=Kind.choices, default=Kind.SYSTEM)
    description = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        unique_together = ("organization", "key")

    def __str__(self) -> str:  # pragma: no cover
        return self.name

    @property
    def active_version(self) -> "PromptVersion | None":
        return self.versions.filter(is_active=True).order_by("-version").first()


class PromptVersion(BaseModel):
    """One immutable revision of a :class:`Prompt`.

    New edits create a new version and (optionally) flip ``is_active``; old
    versions are retained so run records stay reproducible.
    """

    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField(default=1)
    content = models.TextField()
    variables = models.JSONField(
        default=list, blank=True, help_text="Names of {{template}} variables used."
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prompt_versions",
    )
    notes = models.CharField(max_length=300, blank=True)

    class Meta(BaseModel.Meta):
        unique_together = ("prompt", "version")
        ordering = ["-version"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.prompt.key} v{self.version}"


class AgentPromptAssignment(BaseModel):
    """Binds an Agent to the PromptVersion it should use for a given role/kind.

    Decoupling a prompt from the agent (rather than storing text on the agent)
    means the same prompt can be shared, versioned, and reassigned without
    touching agent config.
    """

    agent = models.ForeignKey(
        "agents.Agent", on_delete=models.CASCADE, related_name="prompt_assignments"
    )
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE, related_name="assignments")
    # Pin to a specific version, or leave null to always use the prompt's
    # active version at call time.
    version = models.ForeignKey(
        PromptVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments",
    )
    kind = models.CharField(
        max_length=30, choices=Prompt.Kind.choices, default=Prompt.Kind.SYSTEM
    )

    class Meta(BaseModel.Meta):
        unique_together = ("agent", "kind")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.agent.key}:{self.kind} -> {self.prompt.key}"

    def resolve_version(self) -> "PromptVersion | None":
        return self.version or self.prompt.active_version
