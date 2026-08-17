from django.db import models

from core.db import BaseModel


class Workflow(BaseModel):
    """A reusable process definition expressed as a directed graph
    (Workflow ≠ Project ≠ Execution, Idea.md §72).

    A Workflow is a *template*: it owns Nodes and Edges but holds no runtime
    state. A Project instantiates a Workflow, and an Execution is one run of
    that instantiation. The software-lifecycle demo workflow
    (Idea→Research→Planning→Development→Testing→Review→Improvement→Completion)
    is stored as rows here, never hard-coded in the engine.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="workflows"
    )
    workspace = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, null=True, blank=True, related_name="workflows"
    )
    key = models.SlugField(max_length=100)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    config = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        unique_together = ("organization", "key", "version")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} v{self.version}"

    @property
    def start_node(self) -> "Node | None":
        return self.nodes.filter(type=Node.Type.START).first()


class Node(BaseModel):
    """A single step in a Workflow graph.

    ``type`` covers the full palette from DemoPrompt §12 — control-flow
    (Start/Condition/Decision/Parallel/Join/Loop/End/Archive) and work
    (Task/AgentTask/HumanTask/Tool/Review/Approval/Evaluation/Wait/Event/
    Subworkflow). The engine dispatches on this field via registered node
    handlers.
    """

    class Type(models.TextChoices):
        START = "start", "Start"
        TASK = "task", "Task"
        AGENT_TASK = "agent_task", "Agent Task"
        HUMAN_TASK = "human_task", "Human Task"
        TOOL = "tool", "Tool"
        CONDITION = "condition", "Condition"
        DECISION = "decision", "Decision"
        PARALLEL = "parallel", "Parallel (fork)"
        JOIN = "join", "Join"
        LOOP = "loop", "Loop"
        REVIEW = "review", "Review"
        APPROVAL = "approval", "Approval"
        EVALUATION = "evaluation", "Evaluation"
        WAIT = "wait", "Wait"
        EVENT = "event", "Event"
        SUBWORKFLOW = "subworkflow", "Subworkflow"
        END = "end", "End"
        ARCHIVE = "archive", "Archive"

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="nodes")
    arena = models.ForeignKey(
        "workflows.Arena", on_delete=models.SET_NULL, null=True, blank=True, related_name="nodes"
    )
    key = models.SlugField(max_length=100)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=30, choices=Type.choices)

    # Optional bindings — which role/agent performs the work, which tool/prompt
    # to invoke. Kept nullable so control-flow nodes carry none of them.
    role = models.ForeignKey(
        "structure.Role", on_delete=models.SET_NULL, null=True, blank=True, related_name="nodes"
    )
    agent = models.ForeignKey(
        "agents.Agent", on_delete=models.SET_NULL, null=True, blank=True, related_name="nodes"
    )
    tool = models.ForeignKey(
        "tools.Tool", on_delete=models.SET_NULL, null=True, blank=True, related_name="nodes"
    )

    # ``config`` holds type-specific settings: for LOOP the safety limits
    # (max_iterations/max_duration/max_cost/failure_threshold) and stop
    # conditions; for CONDITION the expression; for EVALUATION the gate
    # thresholds; for AGENT_TASK the stage name handed to the model gateway.
    config = models.JSONField(default=dict, blank=True)

    # Canvas coordinates for the React Flow editor.
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)

    class Meta(BaseModel.Meta):
        unique_together = ("workflow", "key")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.workflow.key}:{self.key}({self.type})"


class Edge(BaseModel):
    """A directed connection between two Nodes.

    ``condition`` lets an edge fire only when an expression evaluates true
    (used by Condition/Decision/Loop branches); ``label`` names branches such
    as ``pass`` / ``fail`` for the QA loop.
    """

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="edges")
    source = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="outgoing_edges")
    target = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="incoming_edges")
    label = models.CharField(max_length=100, blank=True)
    condition = models.TextField(
        blank=True, help_text="Optional boolean expression evaluated against run context."
    )
    order = models.PositiveIntegerField(default=0)

    class Meta(BaseModel.Meta):
        ordering = ["order"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.source.key} -> {self.target.key}"


class Arena(BaseModel):
    """A visual/operational lane used to separate teams inside a workflow."""

    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="arenas")
    workspace = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="arenas")
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="arenas")
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=20, default="#9b5f34")
    order = models.PositiveIntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        unique_together = ("workflow", "name")
        ordering = ["order", "name"]


class WorkflowLink(BaseModel):
    """Explicit relation between workflows in the same workspace."""

    class Kind(models.TextChoices):
        RELATED = "related", "Related"
        DEPENDS_ON = "depends_on", "Depends on"
        TRIGGERS = "triggers", "Triggers"
        SUBWORKFLOW = "subworkflow", "Subworkflow"

    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="workflow_links")
    workspace = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="workflow_links")
    source = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="outgoing_workflow_links")
    target = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="incoming_workflow_links")
    kind = models.CharField(max_length=30, choices=Kind.choices, default=Kind.RELATED)
    condition = models.TextField(blank=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        unique_together = ("source", "target", "kind")
