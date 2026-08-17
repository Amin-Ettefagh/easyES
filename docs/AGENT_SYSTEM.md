# Agent System

This document describes the Agent domain: the Agent entity and its
per-agent bindings, the Actor↔Agent↔Role separation, capability-based
assignment with a simple resolver, and tool permissions. It complements
[DOMAIN_MODEL.md](DOMAIN_MODEL.md) and
[WORKFLOW_ENGINE.md](WORKFLOW_ENGINE.md).

## 1. Where the Agent sits

The platform is **not** designed around agents. An Agent is the AI
*implementation* behind an ai-kind Actor — one of several things that can
do work. Three domains are kept strictly separate:

```text
 Role            Actor                     Agent
 (org position)  (who does work)           (AI implementation)
 "Backend Eng"   kind = human|ai|hybrid    persona + prompt + model
      ▲               │  │                        + tools + budget
      │               │  └── if ai/hybrid ───────▶ Agent
      └── assigned ───┘  └── if human/hybrid ────▶ User
```

- **Role ≠ Actor**: a Role is a slot; it can be filled by a human Actor,
  an ai Actor, or a hybrid.
- **Actor ≠ Agent**: the Assignment/Execution machinery targets Actors,
  so a human and an AI can be assigned the *same* Task through the *same*
  path. The Agent is only reached when the resolved Actor is ai/hybrid.
- **Agent ≠ Model**: the Agent owns configuration (persona, prompt,
  budget, tools, permissions); the Model is a raw inference endpoint the
  Agent points at and can swap.

This separation is what lets the demo swap a human reviewer for an AI
reviewer, or re-point an Agent from the FakeModelProvider to a real one,
**without touching the workflow graph.**

## 2. The Agent entity

Each Agent is an independent entity, and — critically — **each Agent can
use a different provider, model, credential, prompt, budget, tool set,
and permission set.** No global model or global prompt is assumed.

| Field | Purpose |
| ----- | ------- |
| `name`, `description` | Identity |
| `role` (nullable) | Default org role this agent tends to fill |
| `persona` | Voice/behavior framing |
| `system_prompt` → **PromptVersion** | The system prompt is a *versioned* reference, never an inline string; the used version is recorded per Execution |
| `provider` | Which `ModelProvider` (fake, openai_compatible, …) |
| `model` | Which `Model` under that provider |
| `credential` | Which encrypted `Credential` to authenticate with |
| `temperature`, `max_tokens`, `context_limit` | Inference parameters |
| `token_budget`, `cost_budget` | Hard budgets enforced during execution |
| `capabilities` (M2M) | What this agent can do — used by the resolver |
| `tools` (M2M via ToolPermission) | Which tools it may call, and how |
| `permissions` | Non-tool authorizations |
| `status`, `enabled` | Lifecycle / availability |

### Per-agent independence (demo agents)

The `amin` company seeds specialized agents, each configured differently:

```text
Agent      Capability      Prompt        Model(provider)      Budget   Tools
────────   ────────────    ──────────    ─────────────────    ──────   ─────────────────────
PM         Research/Plan   pm@v1         fake:planner         $1.00    Search, FileWrite
Architect  Design          arch@v1       fake:designer        $1.00    FileRead, FileWrite
Engineer   Code            eng@v2        fake:coder           $2.00    FileRead, FileWrite, Code, Git
QA         Test            qa@v1         fake:tester          $1.00    TestRunner, FileRead
Reviewer   Review          rev@v1        fake:reviewer        $0.50    FileRead, Search
```

The point is architectural, not cosmetic: the resolver, gateway, and
budget enforcement all read these *per-agent* values, proving the
platform never assumes one model or one prompt for everyone.

## 3. Actor ↔ Agent binding

An `Actor` of `kind = ai_agent` references exactly one `Agent`; a `hybrid`
Actor references both a `User` and an `Agent` (human owner + AI copilot).
The workflow engine resolves an Actor for a Task; only if that Actor is
ai/hybrid does it dereference the Agent to run inference.

```text
Task ──requires──▶ Capability "Code"
                        │
                        ▼
                 Actor Resolver
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
   Actor(kind=human)       Actor(kind=ai_agent) ──▶ Agent(Engineer)
        → User                                     → provider/model/prompt/budget/tools
```

## 4. Capability-based assignment

Tasks declare a **required capability**, never a named actor (**Task ≠
Actor**, **Capability ≠ Role**). The resolver finds candidate Actors that
hold the capability and picks one by a simple, deterministic strategy.

### The resolver (demo strategy)

```python
# executions/services/resolver.py  (illustrative)
def resolve_actor(task, org) -> Actor:
    candidates = (
        Actor.objects
        .filter(organization=org, status="active")
        .filter(capabilities__capability=task.required_capability)
    )
    if task.required_skill:
        candidates = candidates.filter(
            capabilities__skills__name=task.required_skill
        )
    # Demo strategy: prefer an explicit role match, then availability,
    # then a stable ordering so runs are deterministic.
    candidates = candidates.order_by(
        _role_match(task),      # 0 if actor's role == node's role hint
        _presence_rank(),       # available < busy < offline
        "created_at",           # stable tiebreak → deterministic demo
    )
    actor = candidates.first()
    if actor is None:
        raise NoEligibleActor(task.required_capability)
    return actor
```

The strategy is intentionally simple for the Foundation stage. The seam
for a future **Routing Engine** (quality × cost × availability ×
experience × risk × SLA) is exactly this function — it can grow richer
without changing Tasks, Workflows, or Agents. See [ROADMAP.md](ROADMAP.md).

```text
Task
  │  required_capability (+ optional skill)
  ▼
Candidate Actors  (hold the capability)
  │
  ├─ Human A        ┐
  ├─ Agent(Engineer)├─ rank: role-match → presence → stable order
  └─ Hybrid Team    ┘
  ▼
Assignment → chosen Actor
```

## 5. Tool permissions

Tools are granted **per agent** through `ToolPermission`. An Agent can
only call a Tool it has been granted, within the granted scope, and every
call is logged as a `ToolCall` and a `TOOL_CALL_*` event.

| ToolPermission field | Purpose |
| -------------------- | ------- |
| `agent`, `tool` | The grant (unique together) |
| `allowed` | Enable/disable without deleting the grant |
| `scope` (JSON) | e.g. path prefixes for File tools, allowed hosts for HTTP |
| `constraints` (JSON) | e.g. max shell timeout, read-only git |

### Workspace isolation

File, Code, Shell, and TestRunner tools operate **only** inside the
project workspace:

```text
D:\easyES\data\workspaces\<project-id>\
```

Attempts to read or write outside the workspace are rejected by the tool
abstraction before the underlying operation runs. Shell/Code execution is
constrained (timeouts, no ambient network unless granted) — see
[SECURITY.md](SECURITY.md).

### Tool abstractions available

`FileRead`, `FileWrite`, `Code`, `Shell`, `TestRunner`, `Git`, `Search`,
`HTTP` — each a thin, auditable wrapper. **Tool ≠ Connector**: these are
in-runtime capabilities; external-system connectors (GitHub, Slack, …)
are a separate, roadmap concern.

## 6. Budgets and enforcement

Every Agent carries `token_budget` and `cost_budget`. During execution
the gateway estimates and then records cost per `ModelCall`; the engine
accumulates cost on the `WorkflowRun` and the Execution. If an Agent
would exceed its budget, the call is refused and the loop-safety
`max_cost` stop condition can fire (see
[WORKFLOW_ENGINE.md](WORKFLOW_ENGINE.md)). Budgets are also expressible at
Project, Workflow, and Task levels; the **most specific** budget wins,
consistent with the policy hierarchy in [DOMAIN_MODEL.md](DOMAIN_MODEL.md).

## 7. What an Agent is *not*

- Not a chatbot session — an Agent is a configured worker bound into org
  structure, not a conversation.
- Not equal to an LLM — a future Agent may compose several models and
  components (planner + coder + validator); the entity is designed to
  grow into that without schema upheaval.
- Not the owner of hidden reasoning — Agents record Decision/Action
  summaries, evidence, tool calls, inputs, and outputs. No private
  chain-of-thought is stored (see [DOMAIN_MODEL.md](DOMAIN_MODEL.md) §11).
