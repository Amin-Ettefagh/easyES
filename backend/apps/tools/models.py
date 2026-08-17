from django.db import models

from core.db import BaseModel


class Tool(BaseModel):
    """A capability an agent can invoke during a run (Tool ≠ Connector,
    Idea.md §72).

    Tools are the *safe*, allow-listed operations the engine exposes to agents:
    reading/writing files inside a project workspace, running a sandboxed
    command, fetching a URL, etc. A Connector (external system integration)
    lives elsewhere; a Tool may *use* a connector but is not one.
    """

    class Kind(models.TextChoices):
        WORKSPACE_WRITE = "workspace_write", "Write file to workspace"
        WORKSPACE_READ = "workspace_read", "Read file from workspace"
        SHELL = "shell", "Sandboxed shell command"
        HTTP = "http", "HTTP fetch"
        BUILTIN = "builtin", "Built-in function"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="tools",
        null=True,
        blank=True,
        help_text="Null = global/system tool available to every org.",
    )
    key = models.SlugField(max_length=80)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=40, choices=Kind.choices, default=Kind.BUILTIN)
    handler = models.CharField(
        max_length=200,
        blank=True,
        help_text="Dotted path to the registered handler in core.tools.",
    )
    input_schema = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        unique_together = ("organization", "key")

    def __str__(self) -> str:  # pragma: no cover
        return self.name
