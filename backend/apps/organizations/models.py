from django.conf import settings
from django.db import models

from core.db import BaseModel


class Organization(BaseModel):
    """A tenant: the top-level container for a company / org.

    Multi-tenant from day one — every domain object ultimately hangs off an
    Organization. In the Idea.md model an Organization is one kind of *Space*;
    Space is deferred for the demo but the boundary is respected (nothing
    assumes a single global company).
    """

    class Type(models.TextChoices):
        SOFTWARE_COMPANY = "software_company", "Software Company"
        STARTUP = "startup", "Startup"
        ENTERPRISE = "enterprise", "Enterprise"
        RESEARCH_LAB = "research_lab", "Research Lab"
        AGENCY = "agency", "Agency"
        OTHER = "other", "Other"

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    type = models.CharField(max_length=40, choices=Type.choices, default=Type.SOFTWARE_COMPANY)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_organizations",
    )
    settings_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        indexes = [models.Index(fields=["slug"])]

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Membership(BaseModel):
    """Links a User to an Organization with an org-level role.

    This is distinct from a structural :class:`~apps.structure.models.Role`:
    membership is about access ("is this user part of the org and at what
    level"), Role is about the job a Human/AI performs.
    """

    class Level(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"
        VIEWER = "viewer", "Viewer"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.MEMBER)

    class Meta(BaseModel.Meta):
        unique_together = ("organization", "user")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user} @ {self.organization} ({self.level})"
