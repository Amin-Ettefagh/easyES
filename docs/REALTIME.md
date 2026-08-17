# Realtime

The platform surfaces live execution state — node transitions, model
calls, tool calls, messages, evaluations, loop iterations — through
**Server-Sent Events (SSE)** tailing the append-only `Event` table.
This document explains why SSE was chosen over WebSocket for the demo,
how the tailing mechanism works, the endpoints, reconnection behavior,
and the path to swapping in WebSocket/Channels later.

See also: [adr/0005-realtime-transport.md](adr/0005-realtime-transport.md),
[ARCHITECTURE.md](ARCHITECTURE.md), [DATABASE.md](DATABASE.md) (§6).

## 1. Why SSE instead of WebSocket

| Consideration | SSE | WebSocket |
| ------------- | --- | --------- |
| Direction | Server → client (all we need) | Bidirectional |
| Transport | Plain HTTP `text/event-stream` | Upgraded TCP socket |
| Reconnection | Automatic via browser + `Last-Event-ID` | Manual protocol work |
| Protocol complexity | Trivial (headers + `data:` lines) | Handshake, frames, ping/pong, subprotocols |
| Proxies/CDNs | Works through ordinary HTTP stacks | Often requires sticky sessions / special config |
| Backend needs | Django view, no new server | Channels + ASGI + consumers + layer for the demo |

The demo's realtime need is a **live activity feed**: the user watches
events as the workflow runs and uses REST for all control (start/pause/
approve/instruct). That is a one-way, high-volume-*ish* server→client
stream with frequent reconnects — exactly SSE's sweet spot. WebSocket
would add a second transport, a second protocol, and an ASGI consumer
layer for no capability the demo uses. Realtime is an optimization on top
of a source of truth that is already in the database, not a separate
system. See [adr/0005-realtime-transport.md](adr/0005-realtime-transport.md)
for the trade-off analysis.

## 2. The tailing mechanism

Every meaningful step already writes an `Event` row (append-only, no
UPDATE/DELETE) for audit. The SSE stream is therefore a **cursor over that
table** — there is no separate queue, bus, or notification channel:

```text
engine emits ──▶ audit.Event  (id is monotonic; row is immutable)
                        ▲
                        │   SELECT ... WHERE id > :last_id
                        │         AND organization_id = :org
                        │         AND project_id = :project
                        ▼
                SSE endpoint (Django view, event-stream response)
                        │
                        ▼
                  Client (browser / Next.js)

   each new Event row  ──▶  one SSE event:
        id: <event.id>
        event: <event.type>
        data: { ...serialized event... }
```

Because the Event table is append-only and the primary key is monotonic,
"new events" is exactly "rows with `id > last_seen`". The stream polls
the table in small increments (a short blocking loop or a polling query
with a small sleep inside the view) — this is *tailing*, not client
polling; the client sends one request and holds the connection.

## 3. Endpoints

| Endpoint | Streams |
| -------- | ------- |
| `GET /api/v1/projects/{id}/events/stream` | All events for a project (default view) |
| `GET /api/v1/workflow-runs/{id}/events/stream` | Events scoped to one run |

Both are org-scoped: events are filtered by the caller's organization, and
non-members get `404` (see [SECURITY.md](SECURITY.md)).

### Response format

```text
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no        # disable proxy buffering

id: 1281
event: NODE_COMPLETED
data: {"id": 1281, "type": "NODE_COMPLETED", "node_id": "...", "state": "SUCCEEDED", ...}

id: 1282
event: MODEL_CALL_COMPLETED
data: {"id": 1282, "type": "MODEL_CALL_COMPLETED", "agent": "Engineer", "tokens": 812, "cost": "0.000400", ...}
```

A heartbeat comment (`: ping`) is sent when the table is idle so proxies
don't time the connection out.

## 4. Client reconnection

- The browser's native `EventSource` (or the frontend's SSE wrapper)
  reconnects automatically after drops.
- The server echoes the last delivered `Event.id` in the `id:` field of
  each event; on reconnect the client sends `Last-Event-ID:
  <id>` and the stream resumes from the next row — **no events are lost
  and none are re-delivered** (at-most-once semantics per event, because
  the client can reconcile from `GET /api/v1/events/` if it ever needs
  to backfill).
- If the client has been disconnected long enough that the tail is far
  ahead, the endpoint simply replays from `Last-Event-ID`; the client can
  coalesce older events without reloading state.

## 5. Frontend usage

The Next.js activity view opens one `EventSource` per visible project and
renders events into the timeline; it updates the React Flow canvas node
badges on `NODE_STARTED/COMPLETED/FAILED`, the cost/token counters on
`MODEL_CALL_*`, and the artifact/evaluation lists on their events. The
control panel is plain REST, so interactive latency stays low even on a
slow stream.

## 6. How to swap to WebSocket / Channels later

The SSE tail is intentionally thin so it can be replaced without touching
the engine or the event model:

1. **Keep events as the source of truth.** Everything the stream needs is
   already in the Event table — the new transport only changes *how rows
   are delivered*, not *what is delivered*.
2. **Replace the view with a Channels consumer.** A consumer can re-run
   the same tail query inside `async_to_sync`-safe DB access, or —
   better — the engine can additionally fan out to a Redis pub/sub
   channel when an Event is written, giving push delivery with no
   polling.
3. **Keep the wire format.** Serialize events identically
   (`event: <type>` + JSON `data`), so frontend code and tests barely
   change.
4. **Keep REST control.** Even with WebSocket in place, mutating control
   actions stay on REST; a socket would be used for presence (see
   [ROADMAP.md](ROADMAP.md)) and for the future Arena/Experiment
   dashboards where bidirectional messaging earns its complexity.

The demo ships SSE because it delivers the full live experience with one
view, one protocol, and zero extra infrastructure — and the seam to a
fuller transport is already drawn.
