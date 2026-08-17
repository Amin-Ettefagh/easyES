# R&D References

This document maps each subsystem of the easyES to the
open-source projects we studied as **R&D references**, and states the
specific pattern or design decision each one informed.

## Ground rules (read first)

- **No source code was copied.** These projects were read, analyzed, and
  understood as prior art. We borrowed *patterns and design decisions*,
  not code.
- **`D:\AgentPlayground` is read-only.** Every referenced repository lives
  under that tree and was treated strictly as `READ / ANALYZE /
  UNDERSTAND`. Nothing there was edited, renamed, moved, built, or
  committed.
- **If any code were ever reused directly**, it would be copied *into*
  this project under its own license with full source/license
  attribution — not modified in place, and never with the original
  license stripped. No such reuse exists in the Foundation/Demo.
- The goal of the R&D was to see these repos not as finished products but
  as reference implementations of the *primitives* easyES needs:
  durable workflow, agent runtime, tool contract, integration, sandbox,
  memory, and governance.

## Subsystem → reference → borrowed pattern

### Workflow, conditions & loops
| Reference | Pattern / decision borrowed |
| --------- | --------------------------- |
| **LangGraph** | Model a workflow as a graph/state-machine with Node, Edge, State, Condition, Loop, Human Approval, Checkpoint, Resume. Directly shaped our node/edge model and the fix→retest loop. |
| **Temporal** | The *concept* of durable execution — retry, recovery, resume after crash — and why the engine must persist all progress. We keep the Core decoupled so a Temporal backend can slot in later. |
| **n8n** | Visual node/trigger/action/condition/loop editor UX; informed the React Flow canvas and node-type taxonomy. |
| **Conductor (conductor-oss)** | Long-running workflows, task dependencies, retries, events, distributed workers — the event-driven orchestration mindset. |
| **Hatchet** | Background task + agent orchestration with queues, retries, and monitoring — reference for the ExecutionBackend seam. |

### Agent organization (multi-agent company)
| Reference | Pattern / decision borrowed |
| --------- | --------------------------- |
| **MetaGPT** | Turning a software company into a role-based multi-agent system (PM/Architect/Engineer/QA) with SOP-driven collaboration — the shape of the `amin` demo. |
| **ChatDev** | A virtual software company with role-holding agents (CEO/CTO/Programmer/Tester/Reviewer); studied the project lifecycle run by an agent org. |
| **CrewAI** | Agent / Role / Goal / Tool / Crew and delegation — informed `Actor → Agent → Role → Goal → Delegation`. |
| **AutoGen (+ AG2)** | Multi-agent conversation patterns and human-in-the-loop group conversation — informed the Communication domain and the Human/AI/AI-AI message flows. |

### Agent runtime / execution
| Reference | Pattern / decision borrowed |
| --------- | --------------------------- |
| **OpenHands** | An AI software-developer runtime: Agent + Workspace + Terminal + Files + Runtime + Sandbox + Events + Conversation — shaped the per-project workspace and tool abstractions. |
| **SWE-agent** | The real software loop: Issue → Analyze → Edit → Test → Retry → Patch — the canonical fix→retest loop the demo reproduces. |
| **aider** | Human + AI + repository pairing — reference for hybrid (human-owner + AI-copilot) actors and Git-centric tools. |

### Sandbox
| Reference | Pattern / decision borrowed |
| --------- | --------------------------- |
| **E2B** | Isolated execution of AI-generated code (files, terminal, python, network, process). Reference for the *future* containerized sandbox; the demo uses a filesystem-scoped workspace as the first step. |

### Model gateway
| Reference | Pattern / decision borrowed |
| --------- | --------------------------- |
| **LiteLLM** | A single unified interface over many providers → our `ModelProvider` abstraction and the plan to replace bespoke adapters with a unified backend. |
| **Portkey Gateway** | Provider routing, load balancing, and guardrails — informed where cost/budget checks and routing live in the gateway. |

### Observability & evaluation
| Reference | Pattern / decision borrowed |
| --------- | --------------------------- |
| **Langfuse** | Tracing of agent run / model call / tool call / prompt / cost / latency, plus prompt management and evaluation — shaped the Event fields (Agent/Model/PromptVersion/Tool/Cost/Tokens). |
| **Phoenix (Arize)** | Observability + evaluation + experimentation — reference for the Evaluation layer and the future Arena/Experiment. |
| **OpenLLMetry** | OpenTelemetry-based LLM instrumentation — reference for standardizing traces on OTel later. |

### Memory & knowledge / RAG
| Reference | Pattern / decision borrowed |
| --------- | --------------------------- |
| **Mem0** | A dedicated memory layer for agents (working/episodic/long-term) — informed the Knowledge ≠ Memory decoupling. |
| **Graphiti** | Temporal knowledge graph: facts change over time with provenance — reference for storing the *history* of org knowledge, not just current state. |
| **LlamaIndex** | Ingestion, indexing, retrieval, query building — reference for the future Knowledge/RAG layer. |
| **Qdrant** | Vector DB for semantic retrieval — reference store for knowledge/memory retrieval. |

### Tools & connectors
| Reference | Pattern / decision borrowed |
| --------- | --------------------------- |
| **MCP (servers + Python SDK)** | A standard contract for exposing Tools/Resources/Prompts — reinforced the Tool ≠ Connector split and the plan to make MCP a first-class tool protocol. |
| **Nango** | Integration platform: connector registry, OAuth, credential, sync/action/trigger — reference for the future Connector layer (distinct from in-runtime Tools). |

### Authorization / identity
| Reference | Pattern / decision borrowed |
| --------- | --------------------------- |
| **OpenFGA** | Relationship-based fine-grained authorization (Zanzibar-style): "Alice can use Agent X in Project A; Agent X can read Dataset B but not Finance" — the target model for future authz. |
| **Keycloak** | Identity/IAM, SSO, OIDC/OAuth — reference for future federated human/org identity. |
| **Casbin** | Pluggable access-control models — reference for the policy/permission engine; our demo uses a simpler hierarchical resolver. |

### Project management UI
| Reference | Pattern / decision borrowed |
| --------- | --------------------------- |
| **Plane** | Project / Cycle / Module / Issue / Task / State domain and UI — informed the Project domain and status model. |
| **OpenProject** | Enterprise project/portfolio/task/roadmap breadth — reference for how much richer the Project domain can grow. |
| **Taiga** | Agile constructs (Epic/Sprint/Story/Task/Issue/Kanban) — reference for future task/board views. |

### No-code builder UI
| Reference | Pattern / decision borrowed |
| --------- | --------------------------- |
| **Dify** | App / Workflow / Model / Prompt / Knowledge / Tool / Variable / Execution Log — one of the strongest UI/UX references for the builder and run views. |
| **Flowise** | Visual LLM/agent workflow builder — reference for the node editor. |
| **Langflow** | Visual flow builder for agents/LLMs — reference for the workflow designer interactions. |

## How this maps to the architecture

The composite picture from these references is essentially our three-layer
architecture (see [ARCHITECTURE.md](ARCHITECTURE.md)):

```text
Organization (Plane/OpenProject/ERPNext)   Execution (Temporal/Hatchet/Conductor/n8n)
Intelligence (LangGraph/CrewAI/AutoGen)     Runtime (OpenHands/SWE-agent/aider)
Memory/Knowledge (Mem0/Graphiti/LlamaIndex/Qdrant)   Tools (MCP/Nango)
Sandbox (E2B)   Model Layer (LiteLLM/Portkey)   Observability (Langfuse/Phoenix/OpenLLMetry)
Governance (OpenFGA/Keycloak/Casbin)   Builder UI (Dify/Flowise/Langflow)
```

The Foundation/Demo implements the smallest correct slice of each,
deliberately leaving the heavier references (Temporal, E2B, OpenFGA,
Nango, LiteLLM, Mem0/Graphiti) as roadmap targets whose integration seams
already exist in the Core. See [ROADMAP.md](ROADMAP.md).
