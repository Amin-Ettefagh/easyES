# Workflow Engine

The workflow engine lives in `core/workflow_engine` and is deliberately
free of Django HTTP concerns and of any specific background executor. It
takes a `WorkflowRun`, walks the graph of `WorkflowNode`/`WorkflowEdge`,
drives the execution state machine, evaluates conditions and loops, and
emits events. This document defines the graph model, the node handler
contract, the state machine, conditional/loop execution (with a worked
example), the loop-safety limits, and the idempotency guarantees.

See also: [DOMAIN_MODEL.md](DOMAIN_MODEL.md),
[ARCHITECTURE.md](ARCHITECTURE.md),
[adr/0002-workflow-graph-model.md](adr/0002-workflow-graph-model.md).

## 1. Graph model

A Workflow is a **directed graph**, not a linear pipeline. Cycles are
allowed *only* through a `Loop` construct so the engine can bound them.

- **WorkflowNode** — a unit of work or control. `type`, `name`,
  `configuration`, `inputs`, `outputs`, `position`, `metadata`.
- **WorkflowEdge** — a directed transition. `source`, `target`,
  `condition` (optional expression), `priority`, `metadata`.

Node types and their role:

| Category  | Types |
| --------- | ----- |
| Terminal  | `Start`, `End`, `Archive` |
| Work      | `Task`, `AgentTask`, `HumanTask`, `Tool` |
| Control   | `Condition`, `Decision`, `Parallel`, `Join`, `Loop`, `Wait`, `Event` |
| Quality   | `Review`, `Approval`, `Evaluation` |
| Composition | `Subworkflow` |

Edge selection: from a node, the engine gathers outgoing edges, evaluates
each `condition` against the run context, and follows the satisfied
edge(s) in `priority` order. A `Condition`/`Decision` node has multiple
outgoing edges whose conditions are mutually exclusive; a `Parallel` node
follows *all* outgoing edges; a `Join` waits for its inbound branches.

## 2. Node handler contract

Every node type maps to a **NodeHandler**. Handlers are pure with respect
to the engine: they receive a context, do work, and return a result plus
the outputs the engine writes back. This is the extension point — new
node types are new handlers, no engine changes.

```python
# core/workflow_engine/handlers.py  (illustrative)
class NodeContext:
    run: WorkflowRun
    node: WorkflowNode
    node_execution: NodeExecution
    inputs: dict            # resolved from upstream outputs + node.inputs
    services: EngineServices  # actor resolver, model gateway, tools, emit()

class NodeResult:
    status: Literal["SUCCEEDED", "FAILED", "WAITING", "WAITING_FOR_APPROVAL"]
    outputs: dict
    next_hint: str | None = None   # optional edge label for Decision nodes

class NodeHandler(Protocol):
    node_type: str
    def run(self, ctx: NodeContext) -> NodeResult: ...
```

Handler responsibilities by type (selected):

- **AgentTask** — resolve an Actor by the node's required Capability
  (see [AGENT_SYSTEM.md](AGENT_SYSTEM.md)), build the prompt from the
  bound `PromptVersion`, call the Model Gateway, record `ModelCall`,
  write any `Artifact`/`Message`, return outputs. Records which prompt
  version was used.
- **Tool** — invoke a `core/tools` abstraction under the project
  workspace, record `ToolCall`.
- **HumanTask / Approval / Review** — return `WAITING` /
  `WAITING_FOR_APPROVAL`; the run parks until a control endpoint
  (`approve`/`reject`/`instruct`) resumes it.
- **Evaluation** — compute metrics, apply the Quality Gate, return a
  pass/fail signal used by downstream `Condition` edges.
- **Condition / Decision** — evaluate expressions; select outgoing
  edge(s).
- **Loop** — manage iteration counters and stop conditions (see §5).

The handler contract is the same regardless of whether the underlying
actor is human, AI, or hybrid — the engine is Actor-aware, not
model-aware.

## 3. State machine

One state machine is shared by `WorkflowRun`, `NodeExecution`, and
`Execution`.

```text
        ┌─────────┐
        │ PENDING │
        └────┬────┘
             ▼
        ┌─────────┐        ┌─────────────────────┐
        │ QUEUED  │        │ WAITING_FOR_APPROVAL │◀── Approval/Review node
        └────┬────┘        └──────────┬──────────┘
             ▼                        │ approve
        ┌─────────┐   wait   ┌────────▼─┐
        │ RUNNING │────────▶ │ WAITING  │  HumanTask/Wait/Event
        │         │◀──────── │          │  (resume / event arrives)
        └──┬───┬──┘  resume  └──────────┘
   pause  │   │ done
          ▼   │
     ┌────────┐          ┌───────────┐   ┌───────────┐   ┌────────────┐
     │ PAUSED │          │ SUCCEEDED │   │  FAILED   │   │ CANCELLED  │
     └───┬────┘          └───────────┘   └───────────┘   └────────────┘
         │ resume            ▲                ▲                ▲
         └───────────────────┘   terminal ────┴────────────────┘
```

Transitions (authoritative subset):

| From | Event | To |
| ---- | ----- | -- |
| PENDING | submit | QUEUED |
| QUEUED | pick up | RUNNING |
| RUNNING | node needs human | WAITING |
| RUNNING | node needs approval | WAITING_FOR_APPROVAL |
| RUNNING | pause | PAUSED |
| RUNNING | all terminal nodes reached | SUCCEEDED |
| RUNNING | fatal error / gate fail w/o recovery | FAILED |
| WAITING / WAITING_FOR_APPROVAL | resume / approve | RUNNING |
| WAITING_FOR_APPROVAL | reject | FAILED (stop `REJECTED`) |
| PAUSED | resume | RUNNING |
| any non-terminal | cancel | CANCELLED |

Terminal states (`SUCCEEDED`, `FAILED`, `CANCELLED`) never transition
out. Every transition emits a corresponding event (`NODE_STARTED`,
`NODE_COMPLETED`, `NODE_FAILED`, `LOOP_*`, `PROJECT_COMPLETED`, …).

## 4. Condition execution

A `Condition`/`Decision` node routes based on run context. Conditions are
simple, sandboxed boolean expressions over named context values (no
arbitrary code execution):

```text
Node "QA Gate" (Evaluation) writes:  test_score, requirement_coverage, critical_errors
Edge A condition:  test_score >= threshold and requirement_coverage >= 0.8 and critical_errors == 0
Edge B condition:  not (Edge A)      # the failing branch
```

The engine evaluates each outgoing edge's condition against the context,
picks the first satisfied edge by `priority`, and advances. If no edge is
satisfied the run enters `FAILED` with `FATAL_ERROR` (a graph
authored-correctly always has an exhaustive set of conditions).

## 5. Loop execution and safety

Cycles are expressed with a `Loop` construct: a back-edge whose target is
an earlier node, gated by a `Loop` node that owns the safety counters.
The engine tracks per-loop counters on the `WorkflowRun`
(`iteration_counters`) and per-iteration `NodeExecution` rows.

### Loop safety limits (all enforced)

| Limit | Meaning |
| ----- | ------- |
| `max_iterations` | Hard cap on loop passes |
| `max_duration` | Wall-clock ceiling for the loop |
| `max_cost` | Accumulated model/tool cost ceiling |
| `failure_threshold` | Consecutive failures before giving up |

### Stop conditions

A loop (and a run) exits with exactly one recorded stop condition:

| Stop condition | Trigger |
| -------------- | ------- |
| `PASS` | The quality gate / exit condition is satisfied |
| `MAX_ITERATIONS` | `max_iterations` reached |
| `MAX_COST` | `max_cost` exceeded |
| `MAX_TIME` | `max_duration` exceeded |
| `MANUAL_STOP` | Operator called `stop` |
| `FATAL_ERROR` | Unrecoverable engine/handler error |
| `REJECTED` | An Approval node was rejected |

When any non-`PASS` stop condition fires inside a loop, the loop exits and
the run resolves to `FAILED` (or `CANCELLED` for `MANUAL_STOP`), with the
stop condition recorded on the run for audit.

## 6. Worked example — the demo QA loop

This is the seeded Software Development workflow. It intentionally fails
QA on the first pass, loops fix→retest, then passes.

```text
 Start
   │
   ▼
 Research (AgentTask: PM)      ──▶ Artifact: requirements.md
   │
   ▼
 Planning (AgentTask: Architect) ─▶ Artifact: design.md
   │
   ▼
 ┌───────────────── LOOP  (max_iterations=3, max_cost=$5) ─────────────────┐
 │                                                                         │
 │  Development (AgentTask: Engineer) ─▶ Artifact: source code (v_iter)    │
 │      │                                                                  │
 │      ▼                                                                  │
 │  Testing (Tool: TestRunner) ─▶ test_score, critical_errors             │
 │      │                                                                  │
 │      ▼                                                                  │
 │  QA Gate (Evaluation) ─▶ requirement_coverage, quality-gate result     │
 │      │                                                                  │
 │      ▼                                                                  │
 │  Decision:  gate passed?                                                │
 │      ├── NO  ─▶ Feedback (Message: Review) ─▶ Fix task ─┐ (back-edge)   │
 │      │                                                  └── re-enter    │
 │      │                                                      Development │
 │      └── YES ─────────────────────────────────────────────────────────┼─▶ exit loop (PASS)
 └─────────────────────────────────────────────────────────────────────────┘
                                                                           │
                                                                           ▼
                                                                        Review (Approval)
                                                                           │ approve
                                                                           ▼
                                                                          End → Archive
```

### Iteration trace (deterministic, via FakeModelProvider)

```text
LOOP_STARTED  loop=qa  max_iterations=3

── iteration 1 ──────────────────────────────────────────────
NODE_STARTED   Development     agent=Engineer  prompt=v1
MODEL_CALL_*   provider=fake   tokens=…  cost=$0.30
ARTIFACT_CREATED  code v1
NODE_STARTED   Testing         tool=TestRunner
TOOL_CALL_*    result: 2 failing tests
EVALUATION_COMPLETED  test_score=0.55  coverage=0.60  critical_errors=1
QA Gate:  FAIL   (test_score < threshold AND critical_errors > 0)
AGENT_MESSAGE  type=Review  "2 tests fail; null check missing in handler X"
LOOP_ITERATION loop=qa  n=1  outcome=fail

── iteration 2 ──────────────────────────────────────────────
NODE_STARTED   Development     agent=Engineer  prompt=v1  (with feedback in context)
ARTIFACT_CREATED  code v2
NODE_STARTED   Testing
TOOL_CALL_*    result: all tests pass
EVALUATION_COMPLETED  test_score=0.95  coverage=0.86  critical_errors=0
QA Gate:  PASS
LOOP_ITERATION loop=qa  n=2  outcome=pass
LOOP_EXITED    loop=qa  stop_condition=PASS  iterations=2

NODE_STARTED   Review (Approval)  →  WAITING_FOR_APPROVAL
USER_INTERVENTION  approve
PROJECT_COMPLETED
```

The **Quality Gate** predicate is the single source of the pass/fail
decision:

```text
gate_pass = tests_passed
            AND requirement_coverage >= threshold   # demo threshold 0.8
            AND critical_errors == 0
```

The feedback from iteration 1 is written as a structured `Message`
(Decision Summary / Evidence / Result), not as hidden reasoning, and is
placed into the Development node's context on iteration 2 — which is how
the FakeModelProvider deterministically "fixes" the code.

## 7. Idempotency of start and retry

Execution must be safe to re-drive after crashes, double-clicks, or
backend hand-offs. Two mechanisms guarantee this:

1. **Addressable iterations.** Each `(workflow_run, node, iteration)` is
   unique in the database (see [DATABASE.md](DATABASE.md)). A node's work
   for a given iteration is written under that key; re-running the same
   iteration updates the same row rather than creating a duplicate.
2. **State-guarded transitions.** `start` on a run already in
   `RUNNING`/`QUEUED` is a no-op returning the current run. `retry`
   recomputes the *last failed* node from persisted `NodeExecution`
   state and resumes from there — it never restarts completed upstream
   nodes. `resume`/`approve`/`reject` validate the current state and
   reject invalid transitions with `409`.

Because upstream outputs (artifacts, evaluations, messages) are persisted
as they are produced, a resumed run reads them back rather than
recomputing them, so a retry is cheap and consistent.

## 8. Execution backend independence

The engine only knows how to `execute(run_id)`. Where that runs — a
thread in-process (default), a Celery worker, or a Temporal workflow — is
the `ExecutionBackend`'s concern (see
[adr/0006-background-execution.md](adr/0006-background-execution.md)).
Because the engine persists all progress to the database and emits events
for every step, moving to a durable backend later requires **no change to
node handlers or the state machine** — only a backend that can re-invoke
`execute(run_id)` and honor the same idempotency keys.
