# ADR 0002 — Workflow Graph Model

- **Status:** Accepted
- **Date:** 2026-08-08
- **Deciders:** Platform architecture

## Context

Every project in the platform can have a *completely different* flow —
software development, trading, support, research, incident response. The
engine therefore cannot assume a fixed pipeline. It must express
branching, parallelism, human approvals, and — crucially for the demo —
**bounded loops** (test fails → fix → retest until it passes).

We also need the flow to be persisted, inspectable, editable in a visual
canvas (React Flow), and executed idempotently with full auditability.
The R&D references (LangGraph, n8n, Temporal, Conductor) all converge on
representing work as a graph/state-machine rather than imperative code.

## Decision

Model a Workflow as a **directed graph** of `WorkflowNode` and
`WorkflowEdge`, executed by a state machine.

- Node types cover terminal (Start/End/Archive), work
  (Task/AgentTask/HumanTask/Tool), control
  (Condition/Decision/Parallel/Join/Loop/Wait/Event), quality
  (Review/Approval/Evaluation), and composition (Subworkflow).
- Edges carry an optional `condition` expression and a `priority`;
  routing evaluates conditions against run context.
- **Cycles are allowed only through a `Loop` construct**, which owns the
  safety counters (`max_iterations`, `max_duration`, `max_cost`,
  `failure_threshold`) and records a stop condition (`PASS`,
  `MAX_ITERATIONS`, `MAX_COST`, `MAX_TIME`, `MANUAL_STOP`, `FATAL_ERROR`,
  `REJECTED`).
- Each node type maps to a **NodeHandler** with a uniform contract, so
  new node types are new handlers — no engine changes.
- Node-type-specific settings live in JSON (`configuration`,
  `inputs`, `outputs`); everything queried or state-bearing is
  relational.

See [WORKFLOW_ENGINE.md](../WORKFLOW_ENGINE.md).

## Consequences

**Positive**

- One engine runs arbitrarily different project flows.
- Loops are first-class *and* safe — the demo's fix→retest is native, not
  a hack.
- The graph is directly renderable/editable in React Flow.
- Handler contract makes the node-type set extensible.
- Persisted graph + persisted `NodeExecution` per `(run, node,
  iteration)` gives idempotent start/retry and full audit.

**Negative / trade-offs**

- Graph validation is required (unbounded cycles must be rejected with
  `422`).
- A sandboxed condition-expression evaluator is needed (no arbitrary
  code).
- Slightly more upfront modeling than a hardcoded pipeline.

## Alternatives considered

- **Linear/staged pipeline** — rejected: cannot express branching,
  parallelism, or loops; wrong for heterogeneous project flows.
- **Imperative code per workflow (BPMN-in-code)** — rejected: not
  data-driven, not visually editable, hard to audit and version.
- **DAG-only (no cycles)** — rejected: the core demo *is* a loop; a DAG
  would force awkward unrolling and lose loop-safety semantics.
