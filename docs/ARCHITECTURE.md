# Architecture

This document describes the physical and logical architecture of the
easyES Foundation/Demo: the modular-monolith layout, the
three-layer decomposition, the request and execution flows, and the
seams that keep the Core decoupled from any specific execution engine or
model vendor.

See also: [PRODUCT_VISION.md](PRODUCT_VISION.md),
[DOMAIN_MODEL.md](DOMAIN_MODEL.md),
[WORKFLOW_ENGINE.md](WORKFLOW_ENGINE.md),
[MODEL_GATEWAY.md](MODEL_GATEWAY.md), [REALTIME.md](REALTIME.md).

## 1. Style: modular monolith

The backend is a **modular monolith** — a single Django project composed
of many well-bounded apps that communicate through explicit service
functions and domain events, not a distributed microservice mesh. This
is a deliberate choice for the Foundation stage (see
[adr/0001-modular-monolith.md](adr/0001-modular-monolith.md)): it gives
us strong module boundaries and a clean domain model without paying the
operational tax of distributed systems before we need it. Each app owns
its models, serializers, services, and tests; cross-app coupling is
allowed downward through layers but discouraged sideways.

## 2. The three layers, mapped to code

```text
                         ┌─────────────────────────────┐
   Next.js 14 frontend   │  React Flow canvas · SSE     │
   (App Router, TS)      │  dashboards · control panel  │
                         └──────────────┬──────────────┘
                                        │ HTTPS  /api/v1  +  /events (SSE)
┌───────────────────────────────────────┼──────────────────────────────┐
│ Django 5 + DRF backend (modular monolith)                             │
│                                                                        │
│  ── C. INTELLIGENCE & EVOLUTION ────────────────────────────────────  │
│     apps/agents  apps/models_registry  apps/prompts  apps/tools        │
│     apps/evaluations                                                   │
│                                                                        │
│  ── B. BUSINESS & EXECUTION ────────────────────────────────────────  │
│     apps/projects  apps/workflows  apps/executions                     │
│     apps/communications  apps/artifacts                                │
│                                                                        │
│  ── A. FOUNDATION ──────────────────────────────────────────────────  │
│     apps/accounts  apps/organizations  apps/structure  apps/actors     │
│     apps/capabilities  apps/policies  apps/audit                       │
│                                                                        │
│  ── core/ (shared engine, no HTTP, no app-specific imports) ─────────  │
│     core/model_gateway   core/workflow_engine   core/events            │
│     core/tools           core/rules                                    │
└───────────────────────────────────────┬──────────────────────────────┘
                                         │
                            ┌────────────┴────────────┐
                            │ PostgreSQL (prod/Docker) │
                            │ SQLite   (local/tests)   │
                            └──────────────────────────┘
```

### Directory layout

```text
backend/
  config/                 # Django settings, urls, asgi/wsgi, DRF + spectacular
  core/                   # framework-agnostic engine, importable by any app
    model_gateway/        # ModelProvider interface + Fake/OpenAICompatible
    workflow_engine/      # graph runner, node handlers, state machine
    events/               # event names, emit(), append-only writer
    tools/                # tool abstractions (File/Code/Shell/TestRunner/...)
    rules/                # policy resolution hierarchy
  apps/
    accounts/             # User, auth, JWT/session
    organizations/        # Organization (tenant), Membership
    structure/            # OrgUnit tree, Role, Position, (Capability, Skill)
    actors/               # Actor (human|ai_agent|hybrid) + role assignments
    capabilities/         # Capability/Skill registry (may fold into structure)
    agents/               # Agent entity and its bindings
    models_registry/      # ModelProvider, Model, Credential
    prompts/              # Prompt, PromptVersion, AgentPromptAssignment
    tools/                # Tool, ToolPermission (per-agent)
    projects/             # Project, Goal
    workflows/            # Workflow, WorkflowNode, WorkflowEdge, Template
    executions/           # WorkflowRun, NodeExecution, Task, Assignment,
                          #   Execution/Run, ModelCall, ToolCall
    communications/       # Conversation, Message
    artifacts/            # Artifact
    evaluations/          # Evaluation
    policies/             # Policy/Rule records
    audit/                # Event (append-only), audit views, SSE stream
frontend/                 # Next.js 14 app (App Router, TypeScript, React Flow)
data/
  workspaces/<project-id>/  # isolated per-project tool workspace
```

`apps/capabilities` is a thin domain and **may be folded into
`structure`**; it is listed separately here to keep the Capability ≠
Role decoupling visible.

## 3. Layering rule (dependency direction)

Dependencies point **downward and inward** only:

```text
Intelligence/Evolution  ──▶  Business/Execution  ──▶  Foundation  ──▶  core/
```

- `core/` imports nothing from `apps/`. It is pure engine code
  (interfaces, algorithms, dataclasses) that could be unit-tested with
  no database. This is what keeps the workflow engine and model gateway
  swappable.
- Foundation apps (`organizations`, `structure`, `actors`, `audit`) do
  not import execution or intelligence apps.
- Higher layers orchestrate lower ones through **service functions**
  (e.g. `executions.services.start_workflow_run(...)`) and by **emitting
  events**, never by reaching into another app's ORM internals.

## 4. Request flow (synchronous control plane)

A control action — "start this project", "approve this node" — is a
normal REST request. It validates, mutates domain state, enqueues work
on the execution backend, and returns immediately. It does **not** block
on the workflow running.

```text
Client ──POST /api/v1/projects/{id}/start──▶ DRF view
   │
   ▼
Auth (JWT/session)  ─▶  Org-scope check (membership)  ─▶  Policy check (rules)
   │
   ▼
projects.services.start_project(project)
   │  creates WorkflowRun (state=PENDING→QUEUED)
   │  emits PROJECT_STARTED, WORKFLOW_STARTED  ─────────────▶ audit.Event (append)
   ▼
ExecutionBackend.submit(run_id)   # hands off; returns a handle
   │
   ▼
HTTP 202 + WorkflowRun representation   ◀── returns without waiting
```

## 5. Execution flow (asynchronous data plane)

The workflow engine runs *behind* the execution backend. In the demo the
default backend is **thread-based and in-process**: it runs the engine on
a worker thread in the same Django process. The engine walks the graph,
and every meaningful step appends an Event, which the SSE endpoint tails.

```text
ExecutionBackend (thread)                       core/workflow_engine
      │                                                 │
      └── run(run_id) ───────────────────────────────▶ Runner.execute(run)
                                                        │
             ┌──────────────────────────────────────────┘
             ▼
   for each ready node (topological + condition-gated):
     ├─ resolve NodeHandler by node.type          (Start/AgentTask/Tool/…)
     ├─ create NodeExecution (PENDING→RUNNING)     emit NODE_STARTED
     ├─ handler.run(ctx):
     │     ├─ AgentTask → resolve Actor by Capability → Agent
     │     │     └─ ModelGateway.call(provider, model, prompt_version, …)
     │     │           emit MODEL_CALL_STARTED / MODEL_CALL_COMPLETED
     │     ├─ Tool      → core/tools → emit TOOL_CALL_STARTED / _COMPLETED
     │     ├─ Evaluation→ compute metrics → Quality Gate
     │     └─ Condition/Loop → pick next edge(s) by condition
     ├─ write Artifacts, Messages, Evaluation as produced
     ├─ NodeExecution (→ SUCCEEDED|FAILED)          emit NODE_COMPLETED|FAILED
     └─ advance along satisfied WorkflowEdges (may loop back)
   until terminal node (End/Archive) or a stop condition fires
      │
      ▼
   WorkflowRun → SUCCEEDED|FAILED|CANCELLED         emit PROJECT_COMPLETED|FAILED
```

The state machine (`PENDING, QUEUED, RUNNING, WAITING,
WAITING_FOR_APPROVAL, PAUSED, SUCCEEDED, FAILED, CANCELLED`) is defined
once in `core/workflow_engine` and reused by `WorkflowRun`,
`NodeExecution`, and `Execution`. See
[WORKFLOW_ENGINE.md](WORKFLOW_ENGINE.md) for the full transition table,
loop safety, and the worked fix→retest example.

## 6. Keeping the Core decoupled — the ExecutionBackend seam

The domain must never `import celery` or `import temporalio`. Instead the
engine is submitted through a narrow interface (see
[adr/0006-background-execution.md](adr/0006-background-execution.md)):

```python
# core/workflow_engine/backends.py  (illustrative)
class ExecutionBackend(Protocol):
    def submit(self, run_id: UUID) -> str: ...     # returns a handle/task id
    def cancel(self, run_id: UUID) -> None: ...
    def status(self, run_id: UUID) -> BackendStatus: ...

class ThreadedBackend(ExecutionBackend):     # default, in-process, no broker
    ...

class CeleryBackend(ExecutionBackend): ...   # future: enqueue a task
class TemporalBackend(ExecutionBackend): ... # future: start a durable workflow
```

The backend is selected by settings (`EXECUTION_BACKEND=threaded`). The
engine itself only knows how to execute a run given a `run_id`; *where*
that execution physically happens is the backend's concern. This is the
single most important seam for the roadmap: Temporal or Celery can be
introduced later **without touching the domain model or the engine's node
handlers.**

## 7. Realtime via SSE

Realtime updates use **Server-Sent Events** tailing the append-only
`audit.Event` table, rather than WebSocket (see
[adr/0005-realtime-transport.md](adr/0005-realtime-transport.md) and
[REALTIME.md](REALTIME.md)). Because every meaningful step already writes
an Event for audit, the realtime feed is *free*: the SSE endpoint is a
cursor over that table filtered by organization/project/run. This avoids
heavy polling, needs no extra message broker for the demo, and keeps a
single source of truth for both "what happened" (audit) and "what's
happening now" (stream).

```text
engine emits ──▶ audit.Event (append-only, monotonic id)
                        ▲
                        │  cursor: WHERE id > last_seen AND project = P
Client  ◀── SSE ── GET /api/v1/projects/{id}/events/stream
   (auto-reconnect with Last-Event-ID)
```

## 8. Model gateway boundary

All model use flows through `core/model_gateway`, which exposes a
`ModelProvider` interface (`call / stream / estimate_cost /
health_check`). The default provider is the deterministic
**FakeModelProvider**; an **OpenAICompatibleProvider** stub shows how a
real adapter plugs in. Credentials live in `models_registry`, encrypted
at rest, and are resolved per-agent at call time. The engine never sees a
raw API key. See [MODEL_GATEWAY.md](MODEL_GATEWAY.md) and
[adr/0003-provider-abstraction.md](adr/0003-provider-abstraction.md).

## 9. Persistence

- **PostgreSQL** in Docker for realistic dev/prod; **SQLite** for local
  dev and the test suite (fast, zero-setup). Migrations target both.
- The append-only `Event` table is the backbone of audit + realtime and
  is only ever inserted into, never updated (see
  [adr/0004-event-model.md](adr/0004-event-model.md)).
- JSON fields are used *only* where genuine schema extensibility is
  needed (node `configuration`, `inputs/outputs`, event `payload`,
  `metadata`); everything with a fixed shape and query needs is
  relational. See [DATABASE.md](DATABASE.md).

## 10. Frontend

Next.js 14 (App Router) with TypeScript and React. The workflow canvas
uses **React Flow** to render `WorkflowNode`/`WorkflowEdge` graphs and to
overlay live `NodeExecution` status. The live activity view subscribes to
the SSE stream and renders the event timeline, model/tool calls,
artifacts, and evaluations as they arrive, alongside the control panel
(start/pause/resume/stop/retry/approve/reject/instruct).

## 11. Cross-cutting concerns

| Concern        | Where it lives                                              |
| -------------- | ---------------------------------------------------------- |
| AuthN          | `apps/accounts` — Django session + SimpleJWT               |
| Tenant scoping | `apps/organizations` — every business query filtered by Org |
| AuthZ          | `apps/policies` + `core/rules` — hierarchical rule resolve  |
| Audit + events | `apps/audit` + `core/events` — append-only Event table      |
| Observability  | events carry WHO/WHAT/WHEN/PROJECT/TASK/EXECUTION/RESULT + AI cost/tokens/prompt version |
| API docs       | drf-spectacular → OpenAPI at `/api/schema/`, Swagger UI     |

The result is a system that is small enough to run entirely on one
machine with no external services, yet whose seams (ExecutionBackend,
ModelProvider, Event stream, Tool abstraction, Rule resolver) are exactly
the ones the full platform will need to grow into.
