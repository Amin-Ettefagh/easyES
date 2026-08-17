"""Unit tests for the safe condition evaluator (core.workflow_engine.conditions).

The evaluator drives every branch in the graph, so it must be both correct and
locked down: no calls, no attribute access on arbitrary objects, no imports.
"""
from __future__ import annotations

import pytest

from core.workflow_engine import conditions


@pytest.mark.parametrize(
    "expr,ns,expected",
    [
        ("", {}, True),                                   # empty = unconditional
        ("   ", {}, True),
        ("evaluation.passed == True", {"evaluation": {"passed": True}}, True),
        ("evaluation.passed == True", {"evaluation": {"passed": False}}, False),
        ("evaluation.passed == False", {"evaluation": {"passed": False}}, True),
        ("iteration >= 3", {"iteration": 5}, True),
        ("iteration >= 3", {"iteration": 1}, False),
        ("iteration < 3 and evaluation.passed == False",
         {"iteration": 1, "evaluation": {"passed": False}}, True),
        ("score > 90 or iteration == 0", {"score": 50, "iteration": 0}, True),
        ("status in statuses", {"status": "done", "statuses": ["todo", "done"]}, True),
        ("not blocked", {"blocked": False}, True),
    ],
)
def test_evaluate(expr, ns, expected):
    assert conditions.evaluate(expr, ns) is expected


def test_unknown_name_raises():
    with pytest.raises(conditions.ConditionError):
        conditions.evaluate("missing == 1", {})


def test_calls_are_forbidden():
    """A condition can never invoke a function — no code execution path."""
    with pytest.raises(conditions.ConditionError):
        conditions.evaluate("__import__('os').system('echo hi')", {})


def test_attribute_access_on_non_dict_is_forbidden():
    class Evil:
        secret = "nope"

    with pytest.raises(conditions.ConditionError):
        conditions.evaluate("obj.secret == 'nope'", {"obj": Evil()})


def test_syntax_error_raises_condition_error():
    with pytest.raises(conditions.ConditionError):
        conditions.evaluate("1 ===", {})
