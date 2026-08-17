# ADR 0005 — Realtime Transport

- **Status:** Accepted
- **Date:** 2026-08-08
- **Deciders:** Platform architecture

## Context

The user must watch a workflow execute live — node transitions, model and
tool calls, messages, evaluations, loop iterations — and control it
(start/pause/approve/instruct). The realtime need is essentially a
**one-way, server→client activity feed**; control is a separate,
request/response concern handled by REST.

We already persist every meaningful step to an append-only `Event` table
(see [adr/0004-event-model.md](0004-event-model.md)), so "what's happening
now" is already in the database. We want live updates without heavy client
polling and without standing up extra infrastructure for the demo.

## Decision

Use **Server-Sent Events (SSE)** that tail the append-only Event table.

- Endpoints: `GET /api/v1/projects/{id}/events/stream` and
  `.../workflow-runs/{id}/events/stream`, returning `text/event-stream`.
- Each new `Event` row becomes one SSE event; the `id:` field carries the
  monotonic `Event.id`.
- Reconnection is automatic; the client resumes with `Last-Event-ID`, so
  no events are lost or duplicated.
- Control actions stay on REST (they mutate state and return immediately).

See [REALTIME.md](../REALTIME.md).

## Consequences

**Positive**

- Trivial to implement over plain HTTP — a Django view, no new server,
  no broker, no ASGI consumer layer for the demo.
- Native browser reconnection with `Last-Event-ID` gives lossless resume.
- Reuses the Event table as the single source of truth — realtime is a
  cursor, not a second system.
- Works cleanly through ordinary proxies/CDNs.

**Negative / trade-offs**

- One-way only (fine here; control is REST).
- Tailing is poll-on-the-server rather than push; acceptable for the demo,
  but a busy instance will want a push fan-out.
- One long-lived HTTP connection per watched stream (mitigated by scoping
  and heartbeats).

## Alternatives considered

- **WebSocket / Django Channels** — rejected for the demo: bidirectional
  capability we don't need, plus ASGI + consumers + a channel layer to
  operate. Chosen as the *future* transport when presence and interactive
  dashboards justify it; the SSE seam is designed to swap to it (keep the
  Event table as truth, keep the wire format, replace the delivery).
- **Client polling of `/events/`** — rejected: higher latency and load,
  worse UX.
- **Third-party realtime service** — rejected: external dependency and
  data egress for a demo that must run offline.

## Future path

Keep events as the source of truth; when needed, add a Redis pub/sub
fan-out on event write and deliver via a Channels consumer using the same
`event: <type>` + JSON `data` format, so frontend code and tests are
largely unchanged. See [ROADMAP.md](../ROADMAP.md).
