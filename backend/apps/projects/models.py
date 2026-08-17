from django.conf import settings
from django.db import models

from core.db import BaseModel


class Project(BaseModel):
    """A concrete piece of work an organization is doing (Project ≠ Workflow ≠
    Execution, Idea.md §72).

    A Project instantiates a Workflow and carries the business context (the
    idea/goal, requirements, owner, status). Running it produces one or more
    :class:`~apps.executions.models.Execution` records; the Project itself
    holds the durable outcome, not the per-run state.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        RUNNING = "running", "Running"
        BLOCKED = "blocked", "Blocked"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="projects"
    )
    workflow = models.ForeignKey(
        "workflows.Workflow",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    key = models.SlugField(max_length=100)
    name = models.CharField(max_length=200)
    idea = models.TextField(blank=True, help_text="The initiating idea / goal.")
    requirements = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_projects",
    )
    # Filesystem sandbox for this project's artifacts:
    # data/workspaces/<workspace_key>/ (DemoPrompt security: workspace isolation).
    workspace_key = models.CharField(max_length=100, blank=True)
    context = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        unique_together = ("organization", "key")
        indexes = [models.Index(fields=["organization", "status"])]

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Task(BaseModel):
    """A unit of work within a Project (Task ≠ Actor, Idea.md §72).

    Tasks are created as the workflow runs (one per work node, plus any
    fix-tasks the QA loop spawns). A Task is assigned to an Actor — human or AI
    — but is not the actor itself. The QA-fail→feedback→fix→re-execute loop
    works by creating a fix Task and re-running the developer node against it.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        BLOCKED = "blocked", "Blocked"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class Kind(models.TextChoices):
        WORK = "work", "Work"
        FIX = "fix", "Fix"
        REVIEW = "review", "Review"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    node = models.ForeignKey(
        "workflows.Node",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.WORK)
    issue_type = models.CharField(max_length=30, default="task")
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    labels = models.JSONField(default=list, blank=True)
    acceptance_criteria = models.TextField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    rank = models.PositiveIntegerField(default=0)

    assigned_actor = models.ForeignKey(
        "actors.Actor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    # Fix tasks point back at the task whose failure spawned them, giving the
    # loop an auditable chain.
    parent_task = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="subtasks"
    )
    iteration = models.PositiveIntegerField(default=0)
    inputs = models.JSONField(default=dict, blank=True)
    outputs = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        indexes = [models.Index(fields=["project", "status"])]

    def __str__(self) -> str:  # pragma: no cover
        return self.title
