from django.db import models

from core.db import BaseModel


class Capability(BaseModel):
    """What an actor *can do* (e.g. Coding, Research, Testing, Review).

    Kept separate from Role (a Role bundles capabilities + responsibilities).
    Organizations may define custom capabilities, hence the FK to org with a
    null option for platform-global ones.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="capabilities",
        null=True,
        blank=True,
    )
    key = models.SlugField(max_length=80)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        unique_together = ("organization", "key")

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Skill(BaseModel):
    """A domain of expertise (e.g. Python, PostgreSQL). Narrower than Capability."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="skills",
        null=True,
        blank=True,
    )
    key = models.SlugField(max_length=80)
    name = models.CharField(max_length=120)

    class Meta(BaseModel.Meta):
        unique_together = ("organization", "key")

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class OrgUnit(BaseModel):
    """A node in the organization structure tree (Division/Department/Team).

    Self-referential so any org can model its own shape. This is Seed/Template
    data for the demo — the Core does not assume any particular tree.
    """

    class Kind(models.TextChoices):
        DIVISION = "division", "Division"
        DEPARTMENT = "department", "Department"
        TEAM = "team", "Team"
        GROUP = "group", "Group"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="units"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    name = models.CharField(max_length=150)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.DEPARTMENT)
    order = models.PositiveIntegerField(default=0)

    class Meta(BaseModel.Meta):
        ordering = ["order", "name"]

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Role(BaseModel):
    """A job in the organization (Backend Engineer, QA Engineer, ...).

    A Role is NOT a person and NOT an agent — it can be performed by a Human,
    an AI Agent, or a Hybrid worker (Idea.md §9, §72). Roles are editable seed
    data, never hard-coded into the Core.
    """

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="roles"
    )
    unit = models.ForeignKey(
        OrgUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name="roles"
    )
    key = models.SlugField(max_length=80)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    capabilities = models.ManyToManyField(Capability, blank=True, related_name="roles")
    is_seed = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        unique_together = ("organization", "key")

    def __str__(self) -> str:  # pragma: no cover
        return self.name
