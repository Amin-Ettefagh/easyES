"""Workflow execution engine package.

Public surface:

* :class:`WorkflowEngine` — runs one Execution through its Workflow graph.
* :func:`get_backend` — resolve the configured ExecutionBackend.
* :func:`start_execution` — create an Execution for a Project and launch it.
"""
from __future__ import annotations

from core.workflow_engine.backend import get_backend
from core.workflow_engine.engine import WorkflowEngine


def start_execution(project, *, workflow=None, scenario: str | None = None, triggered_by=None,
                    backend: str | None = None):
    """Create an :class:`~apps.executions.models.Execution` for ``project`` and
    start it on the configured backend. Returns the Execution.
    """
    from apps.executions.models import Execution

    execution = Execution.objects.create(
        organization=project.organization,
        project=project,
        workflow=workflow or project.workflow,
        scenario=scenario or "fail_once",
        status=Execution.Status.QUEUED,
        triggered_by=triggered_by,
        context={"iteration": 0},
    )
    get_backend(backend).start(execution)
    return execution


__all__ = ["WorkflowEngine", "get_backend", "start_execution"]
