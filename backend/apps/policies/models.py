from django.db import models

from core.db import BaseModel


class Policy(BaseModel):
    """An org-level rule that constrains what actors/agents may do (Idea.md §41).

    Policies are data, not code: the demo ships a few (budget caps, tool
    allow-lists, approval requirements) and the engine/service layer consults
    them. Keeping them here — rather than hard-coded — is what lets an org
    tune governance without a redeploy.
    """

    class Kind(models.TextChoices):
        BUDGET = "budget", "Budget cap"
        TOOL_ACCESS = "tool_access", "Tool access"
        APPROVAL = "approval", "Approval required"
        RATE_LIMIT = "rate_limit", "Rate limit"
        DATA_ACCESS = "data_access", "Data access"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="policies"
    )
    key = models.SlugField(max_length=100)
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=30, choices=Kind.choices)
    description = models.TextField(blank=True)
    rules = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)

    class Meta(BaseModel.Meta):
        unique_together = ("organization", "key")
        ordering = ["-priority", "name"]

    def __str__(self) -> str:  # pragma: no cover
        return self.name
