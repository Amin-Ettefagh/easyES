from django.db import models

from core.db import BaseModel


class Artifact(BaseModel):
    """A concrete output produced during a run — a spec, a source file, a test
    report, a diagram (DemoPrompt §15).

    Artifacts are versioned by ``iteration`` so the control room can show how
    the code evolved across QA-fix cycles. Content is stored inline for small
    text artifacts and/or referenced by ``path`` inside the project workspace
    sandbox (data/workspaces/<project>/).
    """

    class Kind(models.TextChoices):
        DOCUMENT = "document", "Document"
        SPEC = "spec", "Specification"
        CODE = "code", "Source code"
        TEST = "test", "Test / report"
        DIAGRAM = "diagram", "Diagram"
        DATA = "data", "Data"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="artifacts"
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="artifacts"
    )
    node_run = models.ForeignKey(
        "executions.NodeRun",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="artifacts",
    )
    produced_by = models.ForeignKey(
        "actors.Actor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="artifacts",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.DOCUMENT)
    name = models.CharField(max_length=250)
    path = models.CharField(max_length=500, blank=True)
    content = models.TextField(blank=True)
    content_type = models.CharField(max_length=100, default="text/plain")
    iteration = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        indexes = [models.Index(fields=["project", "kind"])]

    def __str__(self) -> str:  # pragma: no cover
        return self.name
