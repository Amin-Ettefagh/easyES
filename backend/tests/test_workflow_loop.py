"""Execution-engine tests: the real workflow run and the real QA loop.

These are the DoD's core claim — that the loop is genuine control flow driven by
data (a DECISION node + condition edges + a loop-back edge), not a scripted
demo. We assert three scenarios end differently:

* ``success``    → passes on the first QA run, no loop.
* ``fail_once``  → fails QA once, loops back through fix→backend→…→qa, then passes.
* ``always_fail``→ never passes, loops to max_iterations, diverts to give-up archive.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.django_db


def _run(demo_org, scenario):
    from core.seed import create_demo_project
    from core.workflow_engine import start_execution

    project = create_demo_project(demo_org, key=f"proj-{scenario}", scenario=scenario)
    return start_execution(project, scenario=scenario, backend="inline"), project


def test_success_scenario_passes_without_looping(demo_org):
    from apps.executions.models import Execution, LoopState

    execution, project = _run(demo_org, "success")

    assert execution.status == Execution.Status.SUCCEEDED
    assert execution.stop_reason == "pass"
    project.refresh_from_db()
    assert project.status == project.Status.COMPLETED
    # No loop iteration was ever taken.
    ls = LoopState.objects.filter(execution=execution).first()
    assert ls is None or ls.iteration == 0


def test_fail_once_scenario_loops_then_passes(demo_org):
    from apps.evaluations.models import Evaluation
    from apps.executions.models import Execution, LoopState, NodeRun

    execution, project = _run(demo_org, "fail_once")

    # It ultimately succeeds...
    assert execution.status == Execution.Status.SUCCEEDED
    assert execution.stop_reason == "pass"

    # ...but only after exactly one loop-back.
    ls = LoopState.objects.get(execution=execution)
    assert ls.iteration == 1
    assert ls.is_active is True  # never tripped a safety limit

    # There are two QA evaluations: a fail (iter 0) then a pass (iter 1).
    qa_evals = Evaluation.objects.filter(project=project).order_by("iteration")
    verdicts = list(qa_evals.values_list("iteration", "passed"))
    assert (0, False) in verdicts
    assert (1, True) in verdicts

    # The backend node ran twice (first buggy pass, then the fix).
    backend_runs = NodeRun.objects.filter(execution=execution, node_key="backend")
    assert backend_runs.count() == 2

    # The fix-planning node ran on the loop.
    assert NodeRun.objects.filter(execution=execution, node_key="fix_planning").exists()


def test_always_fail_scenario_gives_up_at_max_iterations(demo_org):
    from apps.executions.models import Execution, LoopState

    execution, project = _run(demo_org, "always_fail")

    assert execution.status == Execution.Status.FAILED
    assert execution.stop_reason == "max_iterations"

    ls = LoopState.objects.get(execution=execution)
    assert ls.is_active is False
    assert ls.stop_reason == "max_iterations"
    assert ls.iteration == ls.max_iterations == 5

    project.refresh_from_db()
    assert project.status == project.Status.ARCHIVED


def test_run_emits_ordered_events(demo_org):
    """The event log is append-only with a monotonic per-execution seq — this is
    what the SSE stream tails."""
    from apps.audit.models import Event

    execution, _ = _run(demo_org, "fail_once")
    seqs = list(
        Event.objects.filter(execution=execution).order_by("seq").values_list("seq", flat=True)
    )
    assert seqs == sorted(seqs)
    assert seqs[0] == 1
    types = set(
        Event.objects.filter(execution=execution).values_list("type", flat=True)
    )
    assert "execution.started" in types
    assert "loop.iteration" in types
    assert "execution.succeeded" in types


def test_cost_and_tokens_are_accumulated(demo_org):
    execution, _ = _run(demo_org, "fail_once")
    assert execution.total_cost > 0
    assert execution.total_input_tokens > 0
    assert execution.total_output_tokens > 0
