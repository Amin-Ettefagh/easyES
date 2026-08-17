from django.conf import settings
from django.db import models

from core.db import BaseModel


class Actor(BaseModel):
    """Anything that can do work: a Human, an AI Agent, or a Hybrid worker.

    This is the key decoupling from Idea.md §10: the Execution engine is
    *actor-aware*, not user- or agent-specific. A human actor points at a
    User; an AI actor points at an Agent; a hybrid can have both.
    """

    class Kind(models.TextChoices):
        HUMAN = "human", "Human"
        AI_AGENT = "ai_agent", "AI Agent"
        HYBRID = "hybrid", "Hybrid"
        SYSTEM = "system", "System"

    class Presence(models.TextChoices):
        AVAILABLE = "available", "Available"
        BUSY = "busy", "Busy"
        WORKING = "working", "Working"
        OFFLINE = "offline", "Offline"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="actors"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    name = models.CharField(max_length=200)
    presence = models.CharField(
        max_length=20, choices=Presence.choices, default=Presence.AVAILABLE
    )

    # Human actors link to a login user.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actors",
    )
    # AI actors link to an Agent (nullable to avoid a hard import cycle at
    # migration time; enforced logically in the service layer).
    agent = models.OneToOneField(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actor",
    )

    capabilities = models.ManyToManyField(
        "structure.Capability", blank=True, related_name="actors"
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        indexes = [models.Index(fields=["organization", "kind"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.kind})"


class RoleAssignment(BaseModel):
    """Assigns an Actor to a Role. Role ≠ Actor, so this is an explicit link."""

    actor = models.ForeignKey(Actor, on_delete=models.CASCADE, related_name="role_assignments")
    role = models.ForeignKey(
        "structure.Role", on_delete=models.CASCADE, related_name="assignments"
    )
    is_primary = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        unique_together = ("actor", "role")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.actor} -> {self.role}"
