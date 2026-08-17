"""The mutable context passed between nodes during a run.

Wraps ``Execution.context`` (a JSON dict) with convenience accessors and a
flattened namespace used to evaluate edge conditions. Keeping this in one place
means node handlers never touch the raw dict directly.
"""
from __future__ import annotations

from typing import Any


class RunContext:
    def __init__(self, execution):
        self.execution = execution
        # The persisted dict lives on the execution; we mutate it in place and
        # the engine saves the execution after each node. Re-attach it so an
        # empty/None starting context still round-trips to the DB.
        self.data: dict[str, Any] = execution.context or {}
        execution.context = self.data

    # -- basic get/set -----------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def update(self, values: dict[str, Any]) -> None:
        self.data.update(values)

    # -- derived views -----------------------------------------------------
    @property
    def iteration(self) -> int:
        return int(self.data.get("iteration", 0))

    @iteration.setter
    def iteration(self, value: int) -> None:
        self.data["iteration"] = int(value)

    @property
    def evaluation(self) -> dict:
        return self.data.get("evaluation", {}) or {}

    def namespace(self) -> dict[str, Any]:
        """The read-only namespace exposed to condition expressions.

        Nested dicts are wrapped so ``evaluation.passed`` resolves via attribute
        access in the safe evaluator.
        """
        ns = dict(self.data)
        ns.setdefault("iteration", self.iteration)
        return ns
