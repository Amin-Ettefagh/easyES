from django.conf import settings
from django.db import models

from core.db import BaseModel


class Event(BaseModel):
    """An append-only, immutable record of something that happened during a
    run — the backbone of live observability (DemoPrompt §14, ADR: SSE).

    The realtime layer tails this table (ordered by ``seq``) and streams new
    rows to the Project Control Room via Server-Sent Events, avoiding heavy
    polling. Events are never updated or deleted; they are the source of truth
    for the timeline, live logs, and metrics.
    """

    class Level(models.TextChoices):
        DEBUG = "debug", "Debug"
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="events"
    )
    execution = models.ForeignKey(
        "executions.Execution",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="events",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="events",
    )
    node_run = models.ForeignKey(
        "executions.NodeRun",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )

    # Monotonic per-execution sequence used by SSE clients to resume with a
    # Last-Event-ID and to order strictly (created_at can collide).
    seq = models.BigIntegerField(default=0, db_index=True)

    # Dotted event type, e.g. execution.started, node.started, node.succeeded,
    # loop.iteration, evaluation.failed, agent.message, execution.finished.
    type = models.CharField(max_length=80, db_index=True)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INFO)
    message = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        ordering = ["seq", "created_at"]
        indexes = [
            models.Index(fields=["execution", "seq"]),
            models.Index(fields=["organization", "type"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.type}@{self.seq}"


class AuditLog(BaseModel):
    """Who did what, when — for security-sensitive actions (login, prompt
    edits, credential changes, manual stops). Distinct from :class:`Event`,
    which is about run mechanics; AuditLog is about human/governance actions.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=120)
    target_type = models.CharField(max_length=120, blank=True)
    target_id = models.CharField(max_length=120, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        indexes = [models.Index(fields=["organization", "action"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.action} by {self.actor_user_id}"
