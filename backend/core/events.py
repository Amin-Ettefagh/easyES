"""Append-only event emitter — the backbone of live observability.

Every meaningful thing the engine does is written here as an immutable
:class:`apps.audit.models.Event` row with a monotonic per-execution ``seq``.
The realtime API tails this table and streams new rows to the Project Control
Room over SSE (see docs/ADR-realtime-sse.md), so the UI never polls the engine
directly.

Django models are imported lazily inside functions so this module is safe to
import before the app registry is ready.
"""
from __future__ import annotations

from typing import Any, Optional

from django.db import transaction
from django.db.models import Max


def emit(
    execution,
    type: str,
    message: str = "",
    *,
    level: str = "info",
    data: Optional[dict[str, Any]] = None,
    node_run=None,
    project=None,
):
    """Append one event to the log and return it.

    ``seq`` is assigned atomically per execution so SSE clients can order
    strictly and resume with a Last-Event-ID. Emitting is best-effort in the
    sense that it never raises past the caller for a malformed ``data`` payload,
    but the row itself is written transactionally.
    """
    from apps.audit.models import Event

    with transaction.atomic():
        last = (
            Event.objects.select_for_update()
            .filter(execution=execution)
            .aggregate(m=Max("seq"))["m"]
            if execution is not None
            else None
        )
        seq = (last or 0) + 1
        event = Event.objects.create(
            organization=execution.organization if execution else None,
            execution=execution,
            project=project or (execution.project if execution else None),
            node_run=node_run,
            seq=seq,
            type=type,
            level=level,
            message=message or "",
            data=data or {},
        )
    return event
