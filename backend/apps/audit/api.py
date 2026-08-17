"""Audit / observability API: the event log and its live SSE stream.

Two surfaces:

* ``EventViewSet`` — a paginated, filterable read of the append-only event log
  (the timeline behind the Control Room).
* ``stream_events`` — a Server-Sent Events endpoint that tails the same log for
  one execution. The engine writes rows (see :mod:`core.events`); this endpoint
  polls for rows with ``seq`` greater than the client's ``Last-Event-ID`` and
  pushes them, so the browser gets a live feed without WebSockets or a broker
  (see docs/ADR-realtime-sse.md).
"""
from __future__ import annotations

import json
import time

from django.http import StreamingHttpResponse
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from core.api_common import ReadOnlyOrgScopedViewSet, user_org_ids
from apps.audit.models import AuditLog, Event
from apps.executions.models import Execution


class EventSerializer(serializers.ModelSerializer):
    node_key = serializers.CharField(source="node_run.node_key", read_only=True, default="")

    class Meta:
        model = Event
        fields = [
            "uuid", "seq", "type", "level", "message", "data",
            "node_key", "created_at",
        ]


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(
        source="actor_user.username", read_only=True, default=""
    )

    class Meta:
        model = AuditLog
        fields = [
            "uuid", "action", "actor_username", "target_type", "target_id",
            "ip_address", "metadata", "created_at",
        ]


class EventViewSet(ReadOnlyOrgScopedViewSet):
    queryset = Event.objects.select_related("node_run").all()
    serializer_class = EventSerializer

    def get_queryset(self):
        qs = super().get_queryset().order_by("seq", "created_at")
        execution = self.request.query_params.get("execution")
        if execution:
            qs = qs.filter(execution__uuid=execution)
        project = self.request.query_params.get("project")
        if project:
            qs = qs.filter(project__uuid=project)
        return qs


class AuditLogViewSet(ReadOnlyOrgScopedViewSet):
    queryset = AuditLog.objects.select_related("actor_user").all()
    serializer_class = AuditLogSerializer


def _sse_pack(event: Event) -> str:
    payload = {
        "seq": event.seq,
        "type": event.type,
        "level": event.level,
        "message": event.message,
        "data": event.data,
        "node_key": event.node_run.node_key if event.node_run_id else "",
        "created_at": event.created_at.isoformat(),
    }
    return f"id: {event.seq}\nevent: {event.type}\ndata: {json.dumps(payload)}\n\n"


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stream_events(request, uuid):
    """SSE stream of events for one execution.

    Terminates when the execution reaches a terminal state and all rows have
    been flushed, so ``EventSource`` clients see the run end cleanly. Honours
    ``Last-Event-ID`` (header or ``?last`` query param) for resume.
    """
    org_ids = user_org_ids(request.user)
    try:
        execution = Execution.objects.get(uuid=uuid, organization_id__in=org_ids)
    except (Execution.DoesNotExist, ValueError, TypeError):
        from rest_framework.response import Response

        return Response({"detail": "execution not found"}, status=404)

    last_id = request.headers.get("Last-Event-ID") or request.query_params.get("last") or 0
    try:
        last_seq = int(last_id)
    except (TypeError, ValueError):
        last_seq = 0

    terminal = {
        Execution.Status.SUCCEEDED,
        Execution.Status.FAILED,
        Execution.Status.CANCELLED,
    }

    def gen():
        nonlocal last_seq
        # A short keep-alive so proxies don't buffer the connection shut.
        yield ": connected\n\n"
        idle_ticks = 0
        while True:
            new_events = list(
                Event.objects.filter(execution=execution, seq__gt=last_seq)
                .select_related("node_run")
                .order_by("seq")[:200]
            )
            if new_events:
                for event in new_events:
                    yield _sse_pack(event)
                    last_seq = event.seq
                idle_ticks = 0
            else:
                idle_ticks += 1
                yield ": keep-alive\n\n"

            execution.refresh_from_db(fields=["status"])
            if execution.status in terminal and not new_events:
                # Flush any final rows written between the query and the refresh.
                tail = list(
                    Event.objects.filter(execution=execution, seq__gt=last_seq)
                    .order_by("seq")
                )
                for event in tail:
                    yield _sse_pack(event)
                    last_seq = event.seq
                yield "event: done\ndata: {}\n\n"
                return
            # Cap total idle wait so a stuck run can't hold the worker forever.
            if idle_ticks > 600:  # ~10 min at 1s cadence
                yield "event: timeout\ndata: {}\n\n"
                return
            time.sleep(1.0)

    response = StreamingHttpResponse(gen(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
