from django.db import models

from core.db import BaseModel


class Evaluation(BaseModel):
    """A quality judgement about a piece of work (Evaluation ≠ Execution,
    Idea.md §72).

    Evaluations back the Quality Gate: the QA/Evaluation node scores a run and
    the engine gates on ``passed`` (tests_passed AND requirement_coverage ≥
    threshold AND critical_errors == 0). Scores are stored per iteration so the
    loop's improvement across cycles is visible.
    """

    class Verdict(models.TextChoices):
        PASS = "pass", "Pass"
        FAIL = "fail", "Fail"
        NEEDS_WORK = "needs_work", "Needs Work"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="evaluations"
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="evaluations"
    )
    node_run = models.ForeignKey(
        "executions.NodeRun",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluations",
    )
    evaluator_actor = models.ForeignKey(
        "actors.Actor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluations",
    )

    iteration = models.PositiveIntegerField(default=0)
    verdict = models.CharField(max_length=20, choices=Verdict.choices, default=Verdict.FAIL)
    passed = models.BooleanField(default=False)

    # Quality-gate signals.
    tests_passed = models.BooleanField(default=False)
    tests_total = models.PositiveIntegerField(default=0)
    tests_failed = models.PositiveIntegerField(default=0)
    requirement_coverage = models.FloatField(default=0.0, help_text="0.0 – 1.0")
    critical_errors = models.PositiveIntegerField(default=0)
    coverage_threshold = models.FloatField(default=0.8)

    score = models.FloatField(default=0.0)
    summary = models.TextField(blank=True)
    feedback = models.TextField(blank=True, help_text="Actionable feedback fed into the fix task.")
    details = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        indexes = [models.Index(fields=["project", "iteration"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"Evaluation<{self.project_id}#{self.iteration}:{self.verdict}>"
