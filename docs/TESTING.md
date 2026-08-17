# Testing

The test strategy proves the architecture the same way the demo does:
deterministically and offline. The FakeModelProvider makes every layer —
including full workflow runs with a failing-then-passing QA loop —
reproducible without a network or API keys.

See also: [MODEL_GATEWAY.md](MODEL_GATEWAY.md),
[WORKFLOW_ENGINE.md](WORKFLOW_ENGINE.md), [SECURITY.md](SECURITY.md).

## 1. Test layers

```text
        ┌─────────────────────────────────────────────┐
  E2E   │ 1 scenario: Login→Create→Start→Run→Fail QA→  │  Playwright + live stack
        │            Loop→Pass→Complete                │
        ├─────────────────────────────────────────────┤
  API   │ DRF endpoints, auth, tenancy, control verbs  │  pytest + APIClient
        ├─────────────────────────────────────────────┤
  Flow  │ workflow engine, conditions, loops, gate     │  pytest (core/, offline)
        ├─────────────────────────────────────────────┤
 Domain │ models, resolver, policy resolution, budgets │  pytest (ORM)
        ├─────────────────────────────────────────────┤
  Unit  │ pure functions in core/ (no DB, no HTTP)     │  pytest
        └─────────────────────────────────────────────┘
                    +  frontend component tests (Vitest/RTL)
```

| Layer | Scope | Tooling |
| ----- | ----- | ------- |
| **Unit** | Pure `core/` logic: state machine, condition evaluator, cost math, resolver ranking | pytest, no DB |
| **Domain** | Django models, constraints, actor resolver, policy hierarchy, budget enforcement | pytest + SQLite |
| **API** | Endpoints, serializers, JWT/session auth, pagination, error codes | pytest + DRF `APIClient` |
| **Workflow** | Engine drives a whole graph to completion via the Fake provider | pytest |
| **Loop** | The fix→retest loop and every loop-safety stop condition | pytest |
| **Permission** | Tenant isolation and authorization | pytest |
| **Frontend component** | React Flow canvas, activity feed, control panel | Vitest + React Testing Library |
| **E2E** | One full user journey against the running stack | Playwright |

## 2. Running the tests

Backend (from `backend/`, venv active):

```bash
pytest                          # full suite (SQLite, FakeModelProvider)
pytest apps/executions          # one app
pytest -k loop                  # loop tests only
pytest -m e2e                   # the end-to-end scenario (needs the stack)
pytest --cov=apps --cov=core    # coverage
```

Frontend (from `frontend/`):

```bash
npm run test                    # component tests
npm run test:e2e                # Playwright E2E (starts/uses the dev stack)
```

Tests default to `DJANGO_ENV=test`, `DATABASE_URL=sqlite://…` (in-memory
where possible), `MODEL_PROVIDER_DEFAULT=fake`, and
`EXECUTION_BACKEND=threaded` so no external services are required.

## 3. The FakeModelProvider in tests

The deterministic provider (see [MODEL_GATEWAY.md](MODEL_GATEWAY.md)) is
what makes workflow and loop tests assertable:

- Responses are keyed on `(agent, node, iteration)`, so a test can assert
  the *exact* narrative: iteration 1 fails QA, iteration 2 passes.
- Token counts and costs are constants, so budget checks and the
  `MAX_COST` stop condition are testable to the cent.
- Error scenarios are scripted, so `FATAL_ERROR` and retry paths are
  exercised without flakiness.

A test can also install a per-test script to force a scenario:

```python
def test_qa_loop_fails_then_passes(fake_provider, seeded_project, run_engine):
    fake_provider.script.update({
        ("Engineer", "Development", 1): buggy_code_response(),
        ("QA",        "Testing",     1): failing_tests_response(),
        ("Engineer", "Development", 2): fixed_code_response(),
        ("QA",        "Testing",     2): passing_tests_response(),
    })
    run = run_engine(seeded_project)
    assert run.state == "SUCCEEDED"
    assert run.stop_condition == "PASS"
    assert run.iteration_counters["qa"] == 2
    node_execs = run.node_executions.filter(node__name="Development")
    assert node_execs.count() == 2                      # looped exactly once
    assert EvaluationResult.for_run(run).gate_passed is True
```

## 4. Loop and stop-condition coverage

Dedicated tests assert each loop-safety exit (see
[WORKFLOW_ENGINE.md](WORKFLOW_ENGINE.md) §5):

| Test | Setup | Asserts |
| ---- | ----- | ------- |
| pass | iter 1 fail, iter 2 pass | `stop=PASS`, run `SUCCEEDED` |
| max_iterations | always-failing QA, `max_iterations=3` | `stop=MAX_ITERATIONS`, run `FAILED`, exactly 3 iterations |
| max_cost | scripted high per-call cost | `stop=MAX_COST` before iteration cap |
| max_time | injected clock past `max_duration` | `stop=MAX_TIME` |
| manual_stop | `stop` control mid-run | `stop=MANUAL_STOP`, run `CANCELLED` |
| rejected | reject the Approval node | `stop=REJECTED`, run `FAILED` |
| fatal_error | provider raises | `stop=FATAL_ERROR`, run `FAILED` |

Idempotency tests assert that re-issuing `start`/`retry` and re-running an
iteration do not duplicate `NodeExecution` rows (backed by the unique
`(workflow_run, node, iteration)` constraint).

## 5. Permission / tenancy tests

- A user in org A receives `404` (not `403`) when reading, listing, or
  streaming any object in org B.
- Control endpoints reject unauthorized actors with `403` and invalid
  state transitions with `409`.
- Credential responses never contain the secret (write-only field).
- Tool calls outside the project workspace are rejected before any
  filesystem operation (workspace sandbox test).

## 6. API tests

- Auth: login returns JWT access+refresh; refresh rotates; logout
  blacklists; `/auth/me/` reflects memberships.
- CRUD + pagination + filtering per resource.
- Control verbs (`start/pause/resume/stop/cancel/retry/approve/reject/
  archive/instruct`) return the documented status codes (`202`/`409`/
  `403`/`404`) and emit the expected events.
- OpenAPI schema builds without warnings (drf-spectacular).

## 7. Frontend component tests

- The React Flow canvas renders nodes/edges from a workflow payload and
  updates node badges on injected `NODE_*` events.
- The activity feed consumes a mocked SSE stream and renders the timeline
  with cost/token counters.
- The control panel calls the right endpoints and disables actions that
  are invalid for the current state.

## 8. The one E2E scenario

A single Playwright test proves the whole vision end-to-end against the
running stack (backend threaded engine + FakeModelProvider + frontend):

```text
Login (amin/123456)
  → Create Project (against the seeded Software Development workflow)
  → Start
  → observe agents run (Research → Planning → Development)
  → observe Testing FAIL the Quality Gate (iteration 1)
  → observe Feedback → Fix → re-Development → re-Testing
  → observe Quality Gate PASS (loop exits, stop=PASS)
  → Approve the Review node
  → Project reaches Completed
```

The test asserts the visible milestones (a failing QA event, a
`LOOP_ITERATION`, a passing gate, and `PROJECT_COMPLETED`) and that the
event timeline contains the expected WHO/WHAT/WHEN records. Because the
provider is deterministic, this test is stable in CI with no external
dependencies.

## 9. CI

CI runs the backend suite on SQLite and the frontend component tests on
every change, then the Playwright E2E against a Compose-brought-up stack.
Coverage gates target `core/` and the execution/workflow apps most
heavily, since they encode the engine invariants the platform depends on.
