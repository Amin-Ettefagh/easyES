"""Pluggable execution backends.

The Core is *not* coupled to Celery or Temporal (ADR-background-execution). An
ExecutionBackend decides how :meth:`WorkflowEngine.run` is invoked:

* ``ThreadExecutionBackend`` — runs the engine in a daemon thread so the API
  request returns immediately while the run proceeds and streams events. This
  is the default and needs no extra infrastructure.
* ``InlineExecutionBackend`` — runs synchronously in the caller. Used by tests
  and the ``run_demo`` management command so assertions can inspect the final
  state deterministically.

A future ``CeleryExecutionBackend`` / ``TemporalExecutionBackend`` would
implement the same :meth:`start` contract without touching the engine.
"""
from __future__ import annotations

import logging
import threading

from django.conf import settings

from core.workflow_engine.engine import WorkflowEngine

logger = logging.getLogger(__name__)


class ExecutionBackend:
    def start(self, execution):  # pragma: no cover - interface
        raise NotImplementedError


class InlineExecutionBackend(ExecutionBackend):
    def start(self, execution):
        return WorkflowEngine(execution).run()


class ThreadExecutionBackend(ExecutionBackend):
    def start(self, execution):
        execution_id = execution.pk

        def _run():
            from django.db import connection
            from apps.executions.models import Execution

            try:
                exec_obj = Execution.objects.get(pk=execution_id)
                WorkflowEngine(exec_obj).run()
            except Exception:  # noqa: BLE001
                logger.exception("Threaded execution %s failed", execution_id)
            finally:
                connection.close()

        thread = threading.Thread(target=_run, name=f"exec-{execution_id}", daemon=True)
        thread.start()
        return execution


_BACKENDS = {
    "thread": ThreadExecutionBackend,
    "inline": InlineExecutionBackend,
}


def get_backend(name: str | None = None) -> ExecutionBackend:
    key = name or getattr(settings, "EXECUTION_BACKEND", "thread")
    cls = _BACKENDS.get(key, ThreadExecutionBackend)
    return cls()
