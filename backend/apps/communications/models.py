from django.db import models

from core.db import BaseModel


class Conversation(BaseModel):
    """A thread of messages between actors during a run (Idea.md §29).

    Agents and humans coordinate through Conversations — e.g. QA reporting a
    failure back to the developer. A Conversation is scoped to a Project/
    Execution so the control room can show "who said what to whom".
    """

    class Kind(models.TextChoices):
        AGENT = "agent", "Agent ↔ Agent"
        HUMAN = "human", "Human ↔ Agent"
        SYSTEM = "system", "System"
        REVIEW = "review", "Review"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="conversations"
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="conversations",
    )
    execution = models.ForeignKey(
        "executions.Execution",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="conversations",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.AGENT)
    topic = models.CharField(max_length=250, blank=True)

    class Meta(BaseModel.Meta):
        indexes = [models.Index(fields=["organization", "project"])]

    def __str__(self) -> str:  # pragma: no cover
        return self.topic or f"Conversation<{self.pk}>"


class Message(BaseModel):
    """A single message in a Conversation.

    ``sender_actor`` is the Actor that produced it (human, ai_agent, or
    system). We store the visible content and structured metadata — decision,
    tool calls, evidence — but never hidden chain-of-thought (Idea.md §63).
    """

    class Role(models.TextChoices):
        SYSTEM = "system", "System"
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        TOOL = "tool", "Tool"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender_actor = models.ForeignKey(
        "actors.Actor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages",
    )
    node_run = models.ForeignKey(
        "executions.NodeRun",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ASSISTANT)
    content = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        ordering = ["created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.role}: {self.content[:40]}"
