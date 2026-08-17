# API

The backend exposes a versioned REST API built with Django REST Framework
and documented with drf-spectacular (OpenAPI 3). This document covers
conventions, auth, the resource endpoints, the control endpoints, and the
realtime stream.

## 1. Conventions

- **Base path:** all endpoints live under `/api/v1/`. The version is in
  the path so `/api/v2/` can coexist during future migrations.
- **Format:** JSON request/response, UTF-8. `Content-Type:
  application/json`.
- **Resource naming:** plural nouns, kebab or snake consistent with DRF
  routers (`/api/v1/workflow-runs/`). Nested resources are expressed
  either as filters (`?project=<id>`) or as sub-routes for actions.
- **IDs:** UUIDs everywhere except `Event.id` (monotonic integer, used as
  the SSE cursor).
- **Pagination:** cursor/offset pagination on list endpoints
  (`?limit=&offset=`), with `count`, `next`, `previous`.
- **Filtering:** list endpoints accept org-scoped filters; results are
  always implicitly scoped to the caller's active organization.
- **Errors:** standard HTTP status codes with a consistent body
  `{ "detail": "...", "code": "...", "fields": {...} }`.
- **Idempotency:** control actions are idempotent where it matters (see
  §6 and [WORKFLOW_ENGINE.md](WORKFLOW_ENGINE.md)); re-issuing `start` on
  an already-running project is a no-op that returns the current run.
- **Tenancy:** the active organization is derived from the authenticated
  principal's membership; cross-org access returns `404` (not `403`) so
  the API does not leak the existence of other tenants' objects.

## 2. Auth

Two mechanisms, both first-class:

| Mechanism      | Use                                             |
| -------------- | ----------------------------------------------- |
| **JWT** (SimpleJWT) | Programmatic / frontend API clients        |
| **Django session**  | Browsable API, Swagger UI, server-rendered |

Endpoints:

| Method | Path                          | Description |
| ------ | ----------------------------- | ----------- |
| POST   | `/api/v1/auth/login/`         | Obtain JWT access + refresh (also sets session) |
| POST   | `/api/v1/auth/refresh/`       | Refresh access token |
| POST   | `/api/v1/auth/logout/`        | Invalidate session / blacklist refresh |
| GET    | `/api/v1/auth/me/`            | Current user + memberships + active org |

Demo credentials (dev only): user `amin` / password `123456`, seeded
solely in development. Access tokens are short-lived; refresh tokens
rotate. See [SECURITY.md](SECURITY.md).

## 3. OpenAPI / Swagger

- Schema: `GET /api/schema/` (OpenAPI 3 JSON/YAML, via drf-spectacular).
- Swagger UI: `GET /api/schema/swagger-ui/`.
- ReDoc: `GET /api/schema/redoc/`.

Every endpoint below is described in the generated schema with request
and response serializers.

## 4. Resource endpoints

Standard REST verbs apply: `GET` (list/retrieve), `POST` (create), `PUT`
/ `PATCH` (update), `DELETE` (soft-delete/archive where applicable).
Below, only the collection path is shown; item paths append `/{id}/`.

### Organizations & structure
| Path | Verbs | Description |
| ---- | ----- | ----------- |
| `/api/v1/organizations/` | GET, POST, PATCH | Tenants the user belongs to |
| `/api/v1/organizations/{id}/members/` | GET, POST, DELETE | Memberships & org roles |
| `/api/v1/org-units/` | GET, POST, PATCH, DELETE | Department/Team tree |
| `/api/v1/roles/` | GET, POST, PATCH, DELETE | Org roles (Role ≠ Actor) |
| `/api/v1/positions/` | GET, POST, PATCH, DELETE | Role×OrgUnit positions |
| `/api/v1/capabilities/` | GET, POST, PATCH | Capability registry |
| `/api/v1/skills/` | GET, POST, PATCH | Skills under capabilities |

### Actors
| Path | Verbs | Description |
| ---- | ----- | ----------- |
| `/api/v1/actors/` | GET, POST, PATCH | Actors (human/ai_agent/hybrid) |
| `/api/v1/actors/{id}/roles/` | GET, POST, DELETE | Role assignments |
| `/api/v1/actors/{id}/capabilities/` | GET, POST, DELETE | Actor capabilities |

### Agents
| Path | Verbs | Description |
| ---- | ----- | ----------- |
| `/api/v1/agents/` | GET, POST, PATCH | Agents with per-agent provider/model/prompt/budget/tools/permissions |
| `/api/v1/agents/{id}/tools/` | GET, POST, DELETE | ToolPermission grants |
| `/api/v1/agents/{id}/prompt/` | GET, PUT | Bound PromptVersion assignment |

### Model registry
| Path | Verbs | Description |
| ---- | ----- | ----------- |
| `/api/v1/providers/` | GET, POST, PATCH | ModelProviders (fake, openai_compatible) |
| `/api/v1/models/` | GET, POST, PATCH | Models exposed by providers |
| `/api/v1/credentials/` | GET, POST, DELETE | Encrypted credentials (secret write-only, never returned) |

### Prompts
| Path | Verbs | Description |
| ---- | ----- | ----------- |
| `/api/v1/prompts/` | GET, POST, PATCH | Prompt definitions |
| `/api/v1/prompts/{id}/versions/` | GET, POST | PromptVersions (immutable once used) |

### Tools
| Path | Verbs | Description |
| ---- | ----- | ----------- |
| `/api/v1/tools/` | GET, POST, PATCH | Tool abstractions (File/Code/Shell/TestRunner/Git/Search/HTTP) |

### Projects, workflows, runs
| Path | Verbs | Description |
| ---- | ----- | ----------- |
| `/api/v1/projects/` | GET, POST, PATCH | Projects (belong to an org, reference a workflow) |
| `/api/v1/projects/{id}/goals/` | GET, POST | Project goals |
| `/api/v1/workflows/` | GET, POST, PATCH | Workflow graphs |
| `/api/v1/workflows/{id}/nodes/` | GET, POST, PATCH, DELETE | WorkflowNodes |
| `/api/v1/workflows/{id}/edges/` | GET, POST, PATCH, DELETE | WorkflowEdges |
| `/api/v1/workflow-templates/` | GET, POST | Reusable templates (seeded software workflow) |
| `/api/v1/workflow-runs/` | GET | Runs (created via project start; read-mostly) |
| `/api/v1/workflow-runs/{id}/node-executions/` | GET | Per-node execution records |
| `/api/v1/tasks/` | GET | Tasks spawned by node executions |
| `/api/v1/executions/` | GET | Execution attempts (with ModelCall/ToolCall) |

### Communication, artifacts, evaluation
| Path | Verbs | Description |
| ---- | ----- | ----------- |
| `/api/v1/conversations/` | GET, POST | Conversations (scoped to project/task/execution) |
| `/api/v1/messages/` | GET, POST | Structured messages (no chain-of-thought) |
| `/api/v1/artifacts/` | GET, POST | Produced, versioned artifacts |
| `/api/v1/evaluations/` | GET, POST | Evaluations with metrics & quality-gate result |

### Rules & audit
| Path | Verbs | Description |
| ---- | ----- | ----------- |
| `/api/v1/rules/` | GET, POST, PATCH, DELETE | Policy/Rule records across the hierarchy |
| `/api/v1/events/` | GET | Append-only audit events (filter by project/task/execution/type) |

### Events stream (realtime)
| Path | Verbs | Description |
| ---- | ----- | ----------- |
| `/api/v1/projects/{id}/events/stream` | GET (SSE) | Live tail of events for a project (see [REALTIME.md](REALTIME.md)) |
| `/api/v1/workflow-runs/{id}/events/stream` | GET (SSE) | Live tail scoped to a single run |

SSE responses use `Content-Type: text/event-stream`, emit an `id:` per
event (the monotonic `Event.id`), and honor the `Last-Event-ID` request
header for reconnection.

## 5. Control endpoints

Control actions are `POST` sub-routes on the resource they act on. They
mutate domain state, emit a `USER_INTERVENTION` (and domain-specific)
event, hand work to the ExecutionBackend, and return the updated resource
— they do **not** block on execution.

### Project / run lifecycle
| Method | Path | Description |
| ------ | ---- | ----------- |
| POST | `/api/v1/projects/{id}/start` | Create a WorkflowRun and begin execution (idempotent: returns active run if already running) |
| POST | `/api/v1/projects/{id}/pause` | Pause the active run → `PAUSED` |
| POST | `/api/v1/projects/{id}/resume` | Resume a paused run → `RUNNING` |
| POST | `/api/v1/projects/{id}/stop` | Graceful stop (stop condition `MANUAL_STOP`) |
| POST | `/api/v1/projects/{id}/cancel` | Hard cancel → `CANCELLED` |
| POST | `/api/v1/projects/{id}/archive` | Archive the project → `Archived` |

### Node / execution controls
| Method | Path | Description |
| ------ | ---- | ----------- |
| POST | `/api/v1/workflow-runs/{id}/retry` | Retry from the last failed node (idempotent per iteration) |
| POST | `/api/v1/node-executions/{id}/retry` | Retry a specific node execution |
| POST | `/api/v1/node-executions/{id}/approve` | Approve a node in `WAITING_FOR_APPROVAL` |
| POST | `/api/v1/node-executions/{id}/reject` | Reject an approval node (stop condition `REJECTED`) |
| POST | `/api/v1/executions/{id}/cancel` | Cancel a single execution attempt |

### Instruction (human-in-the-loop)
| Method | Path | Description |
| ------ | ---- | ----------- |
| POST | `/api/v1/projects/{id}/instruct` | Inject a human instruction (a `Message` of type `Delegation`/`Feedback`) into the running context |
| POST | `/api/v1/node-executions/{id}/instruct` | Instruct a specific in-flight node/agent |

Request bodies for control endpoints are minimal (`{"reason": "...",
"payload": {...}}`); all are recorded as events with WHO/WHAT/WHEN.

## 6. Idempotency & concurrency

- `start`, `resume`, `retry`, `approve`, and `reject` are keyed on the
  current run/node state; issuing them twice produces one effect. This is
  backed by the unique `(workflow_run, node, iteration)` constraint (see
  [DATABASE.md](DATABASE.md)).
- Control endpoints validate the current state machine transition and
  return `409 Conflict` if the action is invalid for the current state
  (e.g. `resume` on a `RUNNING` run).

## 7. Status codes summary

| Code | Meaning in this API |
| ---- | ------------------- |
| 200  | Read / update success |
| 201  | Resource created |
| 202  | Control action accepted; execution proceeds asynchronously |
| 204  | Deleted / archived |
| 400  | Validation error (`fields` populated) |
| 401  | Missing/invalid auth |
| 403  | Authenticated but not permitted by policy within the org |
| 404  | Not found *or* belongs to another tenant |
| 409  | Invalid state transition for a control action |
| 422  | Semantically invalid workflow graph (e.g. cycle without a Loop node) |
