# Product Vision — easyES

> **Universal Human + AI Organization & Execution Platform**

## 1. What we are building

easyES is **not** a chatbot, an agent builder, or an
n8n clone. It is a foundation for a **digital operating environment for
organizations in which humans, software, and AI are all first-class
Actors**. Any organization — a startup, an enterprise, a research lab, a
hospital, a factory, an agency — can model its own structure, bring in
people and AI agents, define its own roles, spin up projects, design a
completely different workflow per project, connect its own tools and
models, and then **execute, observe, control, measure, compare, and
improve** the work — regardless of whether the work is done by a human,
an AI, or a hybrid of both.

At the highest level the product is:

> An Operating System for Human + AI Organizations — a universal
> execution platform where an organization can choose *any* ratio of
> human work, AI-assisted human work, human-supervised AI work, and
> autonomous AI work, **without changing the core architecture.**

## 2. The founding principle

The most important architectural rule is that the system is **not
designed around the AI agent.** An Agent is only *one* of the entities
that can do work. The same is true of the Company, the Project, and the
Workflow — none of them is the center of the architecture. The platform
must be general enough that new kinds of organization, project, actor,
workflow, intelligence, tool, and runtime can enter the system **without
modifying the Core.**

This forces a strict set of decoupling rules that run through every
document in this set:

```text
Role       ≠ Actor        Actor    ≠ Agent       Agent      ≠ Model
Capability ≠ Role          Task     ≠ Actor        Tool       ≠ Connector
Knowledge  ≠ Memory        Workflow ≠ Project      Execution  ≠ Task
Evaluation ≠ Execution
```

Each of these is an independent domain. The decoupling is not academic:
it is what lets the *same* engine run a software team today and a trading
arena, a support desk, or a research lab tomorrow. See
[DOMAIN_MODEL.md](DOMAIN_MODEL.md) for why each rule matters.

## 3. The five (plus one) fundamental questions

Almost every event in the platform can be described by these questions.
The domain model exists to answer them:

| Question           | Answered by                                                    |
| ------------------ | -------------------------------------------------------------- |
| **WHO?**           | Actor, Role, Team, Organization                                |
| **WHY?**           | Mission, Goal, Objective                                       |
| **WHAT?**          | Project, Workflow, Task, Process                               |
| **HOW?**           | Capability, Intelligence, Prompt, Tool, Knowledge, Memory, Runtime |
| **UNDER WHAT RULES?** | Contract, Policy, Permission, Budget, Risk, SLA, Governance |
| **HOW WELL?**      | Evaluation, Metric, Benchmark, Analytics, Experience           |

## 4. The three macro layers

The whole platform is understood as three conceptual layers. The demo
implements a working slice of all three.

```text
┌──────────────────────────────────────────────────────────────┐
│ A. FOUNDATION                                                  │
│    Platform, Identity, Auth, Governance, Storage, Events,      │
│    Audit, Observability, Multi-tenant Organizations            │
├──────────────────────────────────────────────────────────────┤
│ B. BUSINESS & EXECUTION                                        │
│    Organization, Space, Structure, Role, Project, Goal,        │
│    Workflow, Task, Assignment, Execution, Artifact, Deliverable│
├──────────────────────────────────────────────────────────────┤
│ C. INTELLIGENCE & EVOLUTION                                    │
│    Actor, Capability, Skill, Agent, Model, Prompt, Knowledge,  │
│    Memory, Tool, Runtime, Evaluation, Benchmark, Experience    │
└──────────────────────────────────────────────────────────────┘
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for how these map onto Django apps
and the `core/` engine.

## 5. The demo — a Software Company named "amin"

The Foundation/Demo proves the architecture with one concrete,
end-to-end scenario that runs **offline and deterministically** (no
external API keys required):

1. Seed one Organization — a Software Company named **`amin`**.
2. Seed a set of specialized AI Agents (PM, Architect, Engineer, QA,
   Reviewer), each with a *different* prompt, model binding, budget,
   tools, and permissions.
3. Seed a **Software Development Workflow** as a graph of nodes.
4. Create a Project against that workflow and **start** it.
5. Watch the workflow run live: Idea → Research → Planning →
   Development → **Testing (fails QA on the first pass)** →
   Feedback → Fix → Re-test (**loop**) → passes the Quality Gate →
   Review → Completion/Archive.
6. The user can watch every event stream in real time over SSE and can
   intervene: pause, resume, stop, retry, approve, reject, or send an
   instruction.

The failing-then-passing QA loop is deliberate. It exercises the parts
of the engine that are hardest to get right — conditional branching,
bounded loops, loop-safety stop conditions, quality gates, and
idempotent retries — and it demonstrates that the platform records
*decisions and evidence*, not private chain-of-thought.

The determinism comes from a **FakeModelProvider** that returns scripted
outputs keyed on the node/agent/iteration, so the demo produces the same
narrative every run. See [MODEL_GATEWAY.md](MODEL_GATEWAY.md).

## 6. What the demo covers vs. what it defers

| Concern                     | In the Demo                                   | Deferred (see [ROADMAP.md](ROADMAP.md)) |
| --------------------------- | --------------------------------------------- | --------------------------------------- |
| Multi-tenant Organizations  | Yes — tenant isolation from day one           | Cross-org marketplace                    |
| Structure / Roles / Capab.  | Yes — OrgUnit tree, Role, Capability, Skill   | Rich HR / positions / reporting lines    |
| Actors (human / ai / hybrid)| Yes — human→User, ai→Agent                    | Bots, services, devices, external orgs   |
| Agents                      | Yes — per-agent provider/model/prompt/budget  | Multi-model composite agents             |
| Model Gateway               | Fake (default) + OpenAICompatible stub        | LiteLLM/Portkey real routing             |
| Workflow engine             | Graph + conditions + bounded loops + gates    | Sub-workflows at depth, event triggers   |
| Execution backend           | Thread-based, in-process                       | Celery / Temporal durable execution      |
| Realtime                    | SSE tailing an append-only Event table        | WebSocket / Channels, presence           |
| Tools                       | File/Code/Shell/TestRunner/Git/Search/HTTP    | MCP + Nango connectors                    |
| Evaluation                  | Metrics + quality gate + loop feedback        | Arena / Experiment / Benchmark           |
| Knowledge / Memory          | Placeholder domains, not wired                | Mem0 / Graphiti / LlamaIndex / Qdrant     |
| Authorization               | Org membership + simple role checks           | OpenFGA / Casbin fine-grained authz       |
| Spaces                      | Organization is the only concrete Space       | Departments, Experiments, Arenas, Meetings|

## 7. Non-goals (for this stage)

- **Not** a general-purpose no-code automation tool. Workflows model
  *organizational work*, not arbitrary SaaS glue.
- **Not** coupled to any single LLM vendor. The Core never imports a
  provider SDK directly; everything goes through the Model Gateway.
- **Not** coupled to any single execution engine. The Core is not
  hard-wired to Celery or Temporal; those are pluggable backends.
- **Not** a place to store private chain-of-thought. We store Decision
  Summary, Action Summary, Evidence, Tool Calls, Inputs, Outputs, and
  Result — never hidden reasoning traces.
- **Not** a single-tenant app retrofitted for multi-tenancy later.
  Multi-organization is present from the first migration.
- **Not** attempting durable, distributed, at-scale execution yet. The
  demo runs in-process; durability is a roadmap item, and the seams for
  it already exist (`ExecutionBackend`).

## 8. The long-term north star

Every Execution becomes data that improves future Executions:

```text
Execution → Events → Artifacts → Evaluation → Metrics
          → Experience → Learning → Optimization → (better) Future Execution
```

The end state is a platform where an organization declares its
structure, people, agents, models, tools, knowledge, roles, projects,
and per-project workflows — and the platform is responsible to
**execute, observe, control, measure, compare, learn, and optimize.**
The Foundation/Demo is the first, deliberately narrow, fully working
slice of that vision.
