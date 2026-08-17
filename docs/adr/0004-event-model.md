# ADR 0004 — Event Model

- **Status:** Accepted
- **Date:** 2026-08-08
- **Deciders:** Platform architecture

## Context

The platform must answer "what happened, who did it, when, at what cost"
for every meaningful action — a hard requirement for a Human + AI
organization where accountability matters. It must also drive a **live
UI** showing executions as they run, and it must lay groundwork for a
future **Experience/Learning** loop that mines past executions.

These are three needs — audit, realtime, and learning — that are often
built as three separate systems (audit log, message bus, analytics
pipeline). For the Foundation we want one source of truth, minimal moving
parts, and no premature infrastructure.

## Decision

Adopt a single **append-only `Event` table** as the backbone of audit,
realtime, and future learning.

- The table is **insert-only** — no `UPDATE`/`DELETE` in application
  code; corrections are new events.
- Primary key is a **monotonically increasing integer**, so a cursor
  (`WHERE id > last_seen`) tails new events cheaply.
- Every event records **WHO / WHAT / WHEN / PROJECT / TASK / EXECUTION /
  RESULT**, and for AI actions additionally **Agent / Model /
  PromptVersion / Tool / Cost / Tokens**. A JSON `payload` holds
  type-specific detail; the queryable dimensions are real columns.
- Event types cover the full lifecycle (`PROJECT_*`, `WORKFLOW_STARTED`,
  `NODE_*`, `TASK_*`, `AGENT_*`, `MODEL_CALL_*`, `TOOL_CALL_*`,
  `ARTIFACT_CREATED`, `EVALUATION_*`, `LOOP_*`, `USER_INTERVENTION`).
- The SSE realtime stream is a cursor over this same table (see
  [adr/0005-realtime-transport.md](0005-realtime-transport.md)).
- **No private chain-of-thought** is ever stored — only Decision/Action
  summaries, evidence, inputs, outputs, results.

See [DATABASE.md](../DATABASE.md) §6 and [DOMAIN_MODEL.md](../DOMAIN_MODEL.md) §15.

## Consequences

**Positive**

- One source of truth serves audit, realtime, and learning — no separate
  bus or pipeline for the demo.
- Append-only gives a tamper-evident, replayable trail and a natural
  event-sourcing seam.
- Monotonic id makes the SSE tail trivial and reconnection lossless via
  `Last-Event-ID`.
- Uniform WHO/WHAT/WHEN + AI cost/tokens fields make cost analytics and
  future routing possible.

**Negative / trade-offs**

- The table grows unbounded; needs partitioning/archival at scale
  (roadmap).
- Tailing via polling the table is fine for the demo but is not push;
  a Redis pub/sub fan-out is the scale path (see ADR 0005).
- Discipline required to keep secrets and chain-of-thought out of
  payloads (enforced in the emit layer).

## Alternatives considered

- **Separate audit log + message broker (Kafka/NATS) + analytics store**
  — rejected for the Foundation: three systems, heavy ops, premature.
- **Mutable status columns only (no event log)** — rejected: loses
  history, cannot drive a timeline UI or learning.
- **External APM/observability only (Langfuse/Phoenix)** — deferred: great
  for tracing later, but we still need an owned, queryable, org-scoped
  audit trail as the source of truth.
