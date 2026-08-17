# Roadmap

A phased path from the current Foundation/Demo toward the full
**Universal Human + AI Organization & Execution Platform**. Each phase
adds capability by filling in seams the Core already exposes — not by
rewriting the domain model. See [PRODUCT_VISION.md](PRODUCT_VISION.md) for
the destination and [ARCHITECTURE.md](ARCHITECTURE.md) for the seams.

## Phase 0 — Foundation / Demo (current)

Delivered:

- Modular-monolith backend (Django 5 + DRF), Next.js 14 frontend.
- Multi-tenant Organizations from day one; the decoupled domain model
  (Role ≠ Actor ≠ Agent ≠ Model, etc.).
- Agents with per-agent provider/model/credential/prompt/budget/tools/
  permissions.
- Workflow engine: graph, conditions, bounded loops, quality gate,
  idempotent start/retry; the state machine.
- Deterministic offline demo: the `amin` software company runs
  Idea→…→Testing (fails QA)→loop→passes→Complete.
- Model Gateway with FakeModelProvider (+ OpenAICompatible stub).
- SSE realtime over the append-only Event table.
- Thread-based ExecutionBackend; filesystem-scoped tool workspaces.
- Simple hierarchical policy resolution; JWT + session auth.

## Phase 1 — Real providers & richer execution

| Item | What it adds | Seam it uses |
| ---- | ------------ | ------------ |
| **Real model providers via LiteLLM/Portkey** | OpenAI/Anthropic/Gemini/local models behind the existing gateway | `ModelProvider` interface ([MODEL_GATEWAY.md](MODEL_GATEWAY.md)) |
| **Streaming responses end-to-end** | Token streaming into the UI | `stream()` + SSE |
| **Broker-based execution backend** | Celery/Redis worker for out-of-process runs | `ExecutionBackend` ([adr/0006](adr/0006-background-execution.md)) |
| **Cost analytics & budgets rollups** | Per-agent/project/model dashboards | Existing ModelCall/Event cost/token fields |

## Phase 2 — Durable execution & sandboxing

| Item | What it adds | Reference |
| ---- | ------------ | --------- |
| **Temporal durable execution** | Crash-safe, resumable, retryable long-running workflows | Temporal ([RND_REFERENCES.md](RND_REFERENCES.md)) |
| **Containerized/E2B sandboxes** | Isolated per-execution filesystem, network policy, resource limits for code/shell tools | E2B |
| **Richer tool runtime** | Browser/computer-use tools; safer shell | OpenHands, browser-use |

Because the engine persists all progress and emits events, moving to a
durable backend requires no change to node handlers or the state machine.

## Phase 3 — Connectors, knowledge & memory

| Item | What it adds | Reference |
| ---- | ------------ | --------- |
| **MCP tool protocol** | First-class Model Context Protocol tools/resources | MCP |
| **Nango connectors** | Connector registry, OAuth, credential, sync/action/trigger for external systems (Tool ≠ Connector realized) | Nango |
| **Knowledge / RAG layer** | Org/project/agent knowledge with retrieval | LlamaIndex, Qdrant |
| **Memory layer** | Working/episodic/long-term actor memory with provenance/history | Mem0, Graphiti |

These land as **new domains** alongside the existing model — the
Knowledge ≠ Memory and Tool ≠ Connector decouplings mean they don't
disturb agents, tasks, or workflows.

## Phase 4 — Governance & identity

| Item | What it adds | Reference |
| ---- | ------------ | --------- |
| **OpenFGA fine-grained authz** | Relationship-based permissions ("Alice can use Agent X in Project A; Agent X can read Dataset B but not Finance") | OpenFGA |
| **Keycloak SSO/OIDC** | Federated human/org identity | Keycloak |
| **DB row-level security** | Defense-in-depth tenant isolation | — |

The current policy hierarchy (Platform→Org→Project→Workflow→Agent→Task)
is the interface these engines implement behind.

## Phase 5 — Spaces, evaluation & competition

| Item | What it adds |
| ---- | ------------ |
| **Spaces** | Departments, Team Workspaces, Experiments, Arenas, Meetings as first-class Spaces (Organization is today's only concrete Space) |
| **Experiment** | Hypothesis, variables, configurations, runs, metrics, result |
| **Arena** | Competitive comparison of participants (AI/human/hybrid/team) with rules, judge, leaderboard |
| **Benchmark** | Standardized datasets, tasks, environment, evaluator, ranking |
| **AI-judge & human evaluation** | Beyond rule/metric evaluation |

The demo's Evaluation domain (metrics + quality gate) is the nucleus of
this phase.

## Phase 6 — Evolution & learning

| Item | What it adds |
| ---- | ------------ |
| **Experience capture** | Every Execution → Experience record (agent/prompt/tool/score/cost/time) |
| **Analytics** | Organization/project/actor/agent/model/cost/quality analytics |
| **Routing Intelligence** | Assignment by quality × cost × availability × experience × risk × SLA (the resolver grows into a routing engine — see [AGENT_SYSTEM.md](AGENT_SYSTEM.md) §4) |
| **Continuous improvement** | System suggestions ("use model A for research", "prompt v7 is 12% better") |

This closes the north-star loop: Execution → Events → Evaluation →
Experience → Learning → Optimization → better future Execution.

## Phase 7 — Marketplace & ecosystem

| Item | What it adds |
| ---- | ------------ |
| **Marketplace** | Share/install Agents, Roles, Prompts, Tools, Connectors, Workflows, Templates, Skills, Capabilities, Knowledge Packs, Benchmarks |
| **Templates everywhere** | Organization/Department/Team/Project/Role/Agent/Workflow/Experiment/Arena templates |
| **Cross-org collaboration** | Organization ↔ Organization interactions |

## Phasing at a glance

| Phase | Theme | Headline capability | Primary seam / new domain |
| ----- | ----- | ------------------- | ------------------------- |
| 0 | Foundation / Demo | Deterministic offline software-company run with QA loop | — (baseline) |
| 1 | Real providers & execution | Real LLMs + broker backend + cost analytics | `ModelProvider`, `ExecutionBackend` |
| 2 | Durability & sandbox | Temporal durable runs + isolated code sandboxes | `ExecutionBackend`, tool runtime |
| 3 | Connectors & knowledge | MCP tools, Nango connectors, RAG + memory | new Knowledge/Memory/Connector domains |
| 4 | Governance & identity | OpenFGA authz + Keycloak SSO + RLS | policy resolver interface |
| 5 | Spaces & competition | Spaces, Experiment, Arena, Benchmark | new Space kinds, Evaluation growth |
| 6 | Evolution & learning | Experience capture + routing intelligence | Actor Resolver → routing engine |
| 7 | Marketplace | Share/install agents, workflows, templates | new Marketplace domain |

Phases 1–2 are execution-focused and unlock production use; 3–4 make the
platform enterprise-ready; 5–7 realize the differentiating vision
(competition, learning, ecosystem). Phases can overlap where they touch
independent seams.

## Guiding principle across all phases

Every phase adds capability **through an existing seam** —
`ModelProvider`, `ExecutionBackend`, the Event stream, the Tool
abstraction, the Actor Resolver, the policy resolver — or as a **new
decoupled domain**. The Foundation was designed so that Spaces, durable
execution, connectors, memory, fine-grained authz, arenas, and a
marketplace can each arrive without changing what an Actor, Agent, Task,
Workflow, or Execution fundamentally *is*.
