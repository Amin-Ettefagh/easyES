from django.conf import settings
from django.db import models

from core.db import BaseModel


class Execution(BaseModel):
    """One run of a Project's Workflow (Execution ≠ Project ≠ Workflow).

    Holds all *runtime* state: the state-machine status, the mutable run
    context passed between nodes, cost/token accounting, and start/finish
    timing. Re-running a project creates a new Execution; the Project keeps
    only the durable outcome.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        WAITING = "waiting", "Waiting"
        WAITING_FOR_APPROVAL = "waiting_for_approval", "Waiting for Approval"
        PAUSED = "paused", "Paused"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="executions"
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="executions"
    )
    workflow = models.ForeignKey(
        "workflows.Workflow",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executions",
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)

    # Which stop condition ended the run (mirrors DemoPrompt loop outcomes:
    # PASS / MAX_ITERATIONS / MAX_COST / MAX_TIME / MANUAL_STOP / FATAL_ERROR /
    # REJECTED). Blank while running.
    stop_reason = models.CharField(max_length=40, blank=True)

    context = models.JSONField(default=dict, blank=True)
    scenario = models.CharField(
        max_length=40,
        default="fail_once",
        help_text="Drives the deterministic FakeModelProvider (fail_once/success/always_fail).",
    )

    total_input_tokens = models.PositiveIntegerField(default=0)
    total_output_tokens = models.PositiveIntegerField(default=0)
    total_cost = models.DecimalField(max_digits=14, decimal_places=6, default=0)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executions",
    )

    class Meta(BaseModel.Meta):
        indexes = [models.Index(fields=["organization", "status"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"Execution<{self.project_id}:{self.status}>"

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            self.Status.SUCCEEDED,
            self.Status.FAILED,
            self.Status.CANCELLED,
        }


class NodeRun(BaseModel):
    """The execution record for a single Node within an Execution.

    A node may run more than once (loop bodies), so each attempt is its own
    NodeRun carrying its own iteration, cost, and result. This is the atom the
    timeline and control-room UIs render.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        WAITING = "waiting", "Waiting"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    execution = models.ForeignKey(
        Execution, on_delete=models.CASCADE, related_name="node_runs"
    )
    node = models.ForeignKey(
        "workflows.Node", on_delete=models.SET_NULL, null=True, blank=True, related_name="runs"
    )
    node_key = models.CharField(max_length=100, blank=True)
    node_type = models.CharField(max_length=30, blank=True)
    task = models.ForeignKey(
        "projects.Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="node_runs",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    iteration = models.PositiveIntegerField(default=0)

    # Auditable summary of what happened — decision, action summary, evidence,
    # tool calls, inputs, outputs, result. NO raw private chain-of-thought
    # (Idea.md §63).
    summary = models.TextField(blank=True)
    inputs = models.JSONField(default=dict, blank=True)
    outputs = models.JSONField(default=dict, blank=True)

    prompt_version = models.ForeignKey(
        "prompts.PromptVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="node_runs",
    )
    model_key = models.CharField(max_length=120, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=6, default=0)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        ordering = ["created_at"]
        indexes = [models.Index(fields=["execution", "status"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"NodeRun<{self.node_key}#{self.iteration}:{self.status}>"


class LoopState(BaseModel):
    """Tracks a Loop node's iteration/safety accounting within an Execution.

    The engine reads this to enforce the loop-safety guard (max_iterations,
    max_duration, max_cost, failure_threshold) and to decide the stop reason.
    One row per (execution, loop node).
    """

    class StopReason(models.TextChoices):
        PASS = "pass", "Passed"
        MAX_ITERATIONS = "max_iterations", "Max iterations"
        MAX_COST = "max_cost", "Max cost"
        MAX_TIME = "max_time", "Max time"
        MANUAL_STOP = "manual_stop", "Manual stop"
        FATAL_ERROR = "fatal_error", "Fatal error"
        REJECTED = "rejected", "Rejected"

    execution = models.ForeignKey(
        Execution, on_delete=models.CASCADE, related_name="loop_states"
    )
    node = models.ForeignKey(
        "workflows.Node", on_delete=models.CASCADE, related_name="loop_states"
    )
    iteration = models.PositiveIntegerField(default=0)
    consecutive_failures = models.PositiveIntegerField(default=0)

    max_iterations = models.PositiveIntegerField(default=5)
    max_duration_seconds = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    max_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    failure_threshold = models.PositiveIntegerField(default=0, help_text="0 = unlimited")

    is_active = models.BooleanField(default=True)
    stop_reason = models.CharField(max_length=30, choices=StopReason.choices, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        unique_together = ("execution", "node")

    def __str__(self) -> str:  # pragma: no cover
        return f"LoopState<{self.node_id}:iter={self.iteration}>"


class Intervention(BaseModel):
    """Durable human/operator gate that must be resolved before resuming."""

    class Kind(models.TextChoices):
        APPROVAL = "approval", "Approval"
        HUMAN_TASK = "human_task", "Human task"
        OPERATOR = "operator", "Operator intervention"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="interventions")
    execution = models.ForeignKey(Execution, on_delete=models.CASCADE, related_name="interventions")
    node = models.ForeignKey("workflows.Node", on_delete=models.SET_NULL, null=True, blank=True, related_name="interventions")
    task = models.OneToOneField("projects.Task", on_delete=models.SET_NULL, null=True, blank=True, related_name="intervention")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    iteration = models.PositiveIntegerField(default=0)
    prompt = models.TextField()
    response = models.TextField(blank=True)
    assigned_actor = models.ForeignKey("actors.Actor", on_delete=models.SET_NULL, null=True, blank=True, related_name="interventions")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="requested_interventions")
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_interventions")
    metadata = models.JSONField(default=dict, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        indexes = [models.Index(fields=["organization", "status"]), models.Index(fields=["execution", "node", "iteration"])]
