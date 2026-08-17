# ADR 0006 — Background Execution

- **Status:** Accepted
- **Date:** 2026-08-08
- **Deciders:** Platform architecture

## Context

Workflow runs are long-running and asynchronous: a control request
("start this project") must return immediately while the engine executes
in the background. Ultimately the platform wants **durable, distributed,
retryable** execution (the R&D references point to Temporal and Hatchet).
But adopting a broker or a durable-workflow engine now would add
significant infrastructure and operational cost before the domain and the
engine are proven — and the demo must run on a single machine with no
external services.

The critical constraint is that the **domain and the workflow engine must
never be hard-coupled** to any particular executor. Whatever we choose for
the demo must not leak `import celery` or `import temporalio` into node
handlers, the state machine, or the domain model.

## Decision

Define a narrow **`ExecutionBackend` interface** and make the default a
**thread-based, in-process backend**.

- Interface: `submit(run_id) -> handle`, `cancel(run_id)`,
  `status(run_id)`. The engine only knows how to `execute(run_id)`; the
  backend decides *where* that runs.
- Default `ThreadedBackend` runs the engine on a worker thread in the
  Django process — no broker, no extra services.
- The backend is selected by settings (`EXECUTION_BACKEND=threaded`).
- Future `CeleryBackend` / `TemporalBackend` implement the same interface;
  because the engine persists all progress to the DB, emits events for
  every step, and keys work by `(run, node, iteration)` for idempotency,
  swapping the backend requires **no change to node handlers or the state
  machine**.

See [ARCHITECTURE.md](../ARCHITECTURE.md) §6 and
[WORKFLOW_ENGINE.md](../WORKFLOW_ENGINE.md) §7–8.

## Consequences

**Positive**

- The demo runs entirely in one process with zero infrastructure.
- The domain stays executor-agnostic; the seam for durable execution is
  explicit and small.
- Idempotent, persisted execution means a future durable backend can
  resume/retry safely by re-invoking `execute(run_id)`.

**Negative / trade-offs**

- The thread-based backend is **not durable**: a process crash loses
  in-flight run progress beyond the last persisted step (acceptable for a
  demo; the persisted state limits the loss).
- No cross-process scaling until a broker/durable backend is enabled.
- Thread-based concurrency requires care with DB connections and the GIL
  for CPU-bound work (the demo is I/O/model-bound, so this is fine).

## Alternatives considered

- **Celery + Redis from day one** — rejected for the demo: extra services
  and ops; offered later behind the same interface via a Compose
  `workers` profile.
- **Temporal from day one** — rejected now: powerful but heavy to operate
  and premature before the engine is proven; it is the Phase 2 target and
  slots in behind `ExecutionBackend`.
- **Run synchronously in the request** — rejected: long runs would block
  HTTP requests and break the live/observe/control UX.
