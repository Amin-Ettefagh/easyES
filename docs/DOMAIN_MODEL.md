# Domain Model

This is the canonical reference for the core entities of the AI-Native
easyES, their key fields, their relationships, and — most
importantly — the **decoupling rules** that keep the domains independent.
Everything else in the codebase (database, API, engine) is a projection
of this model.

The spine of the model is a single containment/execution chain:

```text
Platform → Organization → (Space) → Project → Goal → Workflow
   → WorkflowRun → NodeExecution → Task → Assignment
      → Execution/Run → (ModelCall, ToolCall) → Events
         → Artifacts → Evaluation
```

## 1. The decoupling rules (read this first)

These rules are the reason the platform can run a software team today and
a trading arena tomorrow without a rewrite. Each rule says *two things
are separate domains*, and each has a concrete payoff.

| Rule | Why it exists |
| ---- | ------------- |
| **Role ≠ Actor** | A Role ("Backend Engineer") is a slot in the org; an Actor is a concrete worker. The same Role can be filled by a human, an AI, or a hybrid — and the filler can change without redefining the Role. |
| **Actor ≠ Agent** | An Actor is the unit of work-doing (human/ai/hybrid). An Agent is the AI *implementation* behind an ai-kind Actor. Keeping them apart lets a human and an AI be assigned the same Task through the same Assignment path. |
| **Agent ≠ Model** | An Agent is a configured worker (persona, prompt, tools, budget, permissions). A Model is a raw inference endpoint. One Agent may swap models; one Model backs many Agents. |
| **Capability ≠ Role** | Capability = *what an actor can do* ("Code", "Review"). Role = *the org position*. Tasks require Capabilities, not named actors, so assignment stays flexible. |
| **Task ≠ Actor** | A Task is defined by its goal, inputs, required capability, and output contract — with no actor baked in. The Actor Resolver binds an Actor at Assignment time. |
| **Tool ≠ Connector** | A Tool is an in-runtime capability (FileWrite, TestRunner). A Connector is *how you reach an external system* (GitHub, Slack). A Tool may be backed by a Connector, but the abstractions differ. |
| **Knowledge ≠ Memory** | Knowledge = what the org *knows* (docs, SOPs, code). Memory = what an actor/system *experienced* (conversation, episodic, decisions). Different lifecycle, access, and retrieval. |
| **Workflow ≠ Project** | A Workflow is a reusable *graph of how work flows*. A Project is a *container for a goal* that runs a workflow. One workflow → many projects; a project can change workflow versions. |
| **Execution ≠ Task** | A Task is the *definition* of work. An Execution is one concrete *attempt*. A Task may be executed many times (retries, model comparisons). |
| **Evaluation ≠ Execution** | Producing a result and judging it are separate. The same Execution can be evaluated by rules, an AI judge, or a human — independently and repeatedly. |

## 2. Foundation entities

### Organization (tenant)
The tenant container. Every business object hangs off exactly one
Organization; queries are always org-scoped.
- Fields: `id`, `name`, `slug`, `description`, `settings (JSON)`,
  `created_at`, `archived_at`.
- Relations: has many `Membership`, `OrgUnit`, `Role`, `Project`,
  `Agent`, `Actor`, `Tool`, `Policy`.

### Membership
Links a `User` to an `Organization` with a role in that org (owner /
admin / member). This is the tenant-access join.
- Fields: `id`, `organization`, `user`, `org_role`, `created_at`.

### User (accounts)
A human identity for authentication. Distinct from **Actor** — a User is
who logs in; an Actor is who does work. A human Actor references a User.
- Fields: standard Django user + `email`, `is_active`, timestamps.

### Space *(conceptual; Organization is the only concrete Space in the demo)*
A contextual, controllable environment holding actors, resources,
policies, processes, and knowledge. Organization, Project, Department,
Experiment, Arena, and Meeting are all *kinds of Space*. The demo
realizes Organization (and Project as a scoped context); other Spaces are
roadmap.

## 3. Structure

### OrgUnit
Self-referential tree modeling Departments, Teams, Squads, etc.
- Fields: `id`, `organization`, `parent (self, nullable)`, `name`,
  `unit_type` (department|team|group|…), `metadata (JSON)`.
- Relation: `parent`/`children` form the org tree.

### Role
An org position, independent of who fills it (**Role ≠ Actor**).
- Fields: `id`, `organization`, `name`, `description`,
  `default_capabilities (M2M Capability)`.

### Position
A binding of a Role within an OrgUnit (e.g. "Backend Engineer in the
Platform Team"), optionally reporting to another Position.
- Fields: `id`, `role`, `org_unit`, `reports_to (self, nullable)`.

### Capability
*What can be done* (**Capability ≠ Role**). Tasks require capabilities;
actors hold capabilities.
- Fields: `id`, `organization (nullable = platform-global)`, `key`,
  `name`, `description`.

### Skill
Domain specialization that qualifies a Capability ("Programming" +
"Python").
- Fields: `id`, `capability`, `name`, `level`.

## 4. Actors and Agents

### Actor
Any entity that can do work. The Assignment/Execution machinery is
**Actor-aware**, not user-or-agent-aware.
- Fields: `id`, `organization`, `kind` (`human` | `ai_agent` |
  `hybrid`), `display_name`, `status`, `presence`
  (available|busy|working|waiting|offline|blocked|paused), `user
  (nullable — set when kind=human/hybrid)`, `agent (nullable — set when
  kind=ai_agent/hybrid)`.
- Relations: holds `ActorRoleAssignment` (Role slots) and
  `ActorCapability` (what it can do).

```text
        Actor.kind
   ┌────────┼─────────┐
 human   ai_agent   hybrid
   │        │          │
 User     Agent    User + Agent
```

### Agent
The independent AI implementation entity. **Agent ≠ Actor** and **Agent ≠
Model**. Each Agent may use a *different* provider, model, credential,
prompt, budget, tool set, and permission set — this per-agent
configurability is a core requirement.
- Fields: `id`, `organization`, `name`, `description`, `role (nullable)`,
  `persona`, `system_prompt` (via **PromptVersion**, not an inline
  string), `provider`, `model`, `credential`, `temperature`,
  `max_tokens`, `context_limit`, `token_budget`, `cost_budget`,
  `status`, `enabled`.
- Relations: M2M `capabilities`, M2M `tools` (through `ToolPermission`),
  `permissions`, `AgentPromptAssignment`.

See [AGENT_SYSTEM.md](AGENT_SYSTEM.md) for the full agent story.

## 5. Model registry

### ModelProvider
A provider record (fake, openai_compatible, …) resolved to an adapter by
the gateway.
- Fields: `id`, `organization (nullable = shared)`, `kind`, `name`,
  `base_url (nullable)`, `enabled`.

### Model
A specific model exposed by a provider.
- Fields: `id`, `provider`, `name`, `context_window`,
  `input_cost_per_1k`, `output_cost_per_1k`, `capabilities (JSON)`.

### Credential
Encrypted-at-rest secret for a provider (**never logged**, never
serialized in API responses).
- Fields: `id`, `organization`, `provider`, `label`,
  `secret_encrypted`, `created_at`, `last_used_at`.

**Agent ≠ Model** is enforced here: an Agent points at a Provider + Model
+ Credential, and can be repointed without changing the Agent's identity.

## 6. Prompts

### Prompt / PromptVersion / AgentPromptAssignment
Prompts are a first-class, **versioned** domain — not a string column on
Agent.
- `Prompt`: `id`, `organization`, `name`, `purpose`.
- `PromptVersion`: `id`, `prompt`, `version`, `content`, `variables
  (JSON)`, `created_at`, `is_active`.
- `AgentPromptAssignment`: binds an Agent to a specific PromptVersion for
  a role/context.
- **Every Execution records which PromptVersion it used** so runs are
  reproducible and comparable.

## 7. Tools

### Tool
An in-runtime capability abstraction. **Tool ≠ Connector.**
- Kinds: `FileRead`, `FileWrite`, `Code`, `Shell`, `TestRunner`, `Git`,
  `Search`, `HTTP`.
- Fields: `id`, `organization`, `key`, `name`, `kind`, `config (JSON)`.

### ToolPermission
Per-agent grant of a Tool, with scoping. Every tool call is logged.
- Fields: `id`, `agent`, `tool`, `allowed`, `scope (JSON)`,
  `constraints (JSON)`.
- Workspace isolation: file/code/shell tools operate only within
  `D:\easyES\data\workspaces\<project-id>\`.

## 8. Projects and Goals

### Project
Belongs to an Organization; a container for a goal that runs a Workflow.
**Workflow ≠ Project.**
- Fields: `id`, `organization`, `name`, `description`, `objective`,
  `status`, `owner (User)`, `start_date`, `budget`, `workflow (FK)`,
  `created_at`, `updated_at`, `archived_at`.
- Statuses: `Draft, Planning, Running, Blocked, Review, Completed,
  Failed, Archived`.

### Goal
What must be achieved; can be nested (org/team/project/task goals).
- Fields: `id`, `project (nullable)`, `parent (self, nullable)`, `name`,
  `description`, `target_metric`.

## 9. Workflow graph

### Workflow
A reusable graph of how work flows. Versioned; instantiated by Projects.
- Fields: `id`, `organization`, `name`, `version`, `description`,
  `is_template`, `metadata (JSON)`.

### WorkflowNode
- Fields: `id`, `workflow`, `type`, `name`, `configuration (JSON)`,
  `inputs (JSON)`, `outputs (JSON)`, `position (JSON: x,y)`, `metadata
  (JSON)`.
- Node types: `Start, Task, AgentTask, HumanTask, Tool, Condition,
  Decision, Parallel, Join, Loop, Review, Approval, Evaluation, Wait,
  Event, Subworkflow, End, Archive`.

### WorkflowEdge
- Fields: `id`, `workflow`, `source (Node)`, `target (Node)`, `condition
  (expr, nullable)`, `priority`, `metadata (JSON)`.

### WorkflowTemplate
The seeded Software Development workflow that intentionally fails QA on
the first pass and loops fix→retest until it passes. See
[WORKFLOW_ENGINE.md](WORKFLOW_ENGINE.md).

## 10. Execution domain

### WorkflowRun
One execution of a Workflow for a Project.
- Fields: `id`, `project`, `workflow`, `state`, `started_at`,
  `ended_at`, `iteration_counters (JSON)`, `stop_condition`,
  `cost_accum`, `token_accum`.

### NodeExecution
One execution of one node within a run (a node may execute multiple times
under a loop).
- Fields: `id`, `workflow_run`, `node`, `iteration`, `state`,
  `started_at`, `ended_at`, `inputs (JSON)`, `outputs (JSON)`, `error`.

### Task
The definition of a unit of assignable work — **no actor baked in**
(**Task ≠ Actor**).
- Fields: `id`, `node_execution (nullable)`, `project`, `goal`, `name`,
  `required_capability`, `required_skill (nullable)`, `context (JSON)`,
  `constraints (JSON)`, `output_contract (JSON)`, `budget`, `sla`.

### Assignment
Binds a Task to a resolved Actor (the output of the Actor Resolver).
- Fields: `id`, `task`, `actor`, `assigned_at`, `strategy` (capability
  match), `status`.

### Execution / Run
An Execution is one concrete attempt at a Task by an Actor (**Execution ≠
Task**). It may contain multiple Runs (e.g. the same task tried on
different models).
- `Execution`: `id`, `task`, `actor`, `state`, `runtime`, `started_at`,
  `ended_at`, `cost`, `result`, `prompt_version (FK — recorded)`.
- `Run`: `id`, `execution`, `attempt`, `model (FK)`, `outcome`.

### ModelCall / ToolCall
Fine-grained records under an Execution/Run.
- `ModelCall`: `id`, `run`, `provider`, `model`, `prompt_version`,
  `input_tokens`, `output_tokens`, `cost`, `latency_ms`, `status`.
- `ToolCall`: `id`, `run`, `tool`, `input (JSON)`, `output (JSON)`,
  `status`, `duration_ms`.

## 11. Communication

### Conversation / Message
Actors communicate through structured messages — not free-form
chat-of-thought.
- `Conversation`: `id`, `organization`, `project (nullable)`, `task
  (nullable)`, `execution (nullable)`, `created_at`.
- `Message`: `id`, `conversation`, `sender_actor`, `receiver_actor
  (nullable)`, `project`, `task`, `execution`, `message_type`,
  `timestamp`, plus structured body fields.
- Message types: `Request, Response, Feedback, Review, Question, Answer,
  Delegation, Report, Decision, System`.
- **No private chain-of-thought is stored.** A Message body holds
  *Decision Summary / Action Summary / Evidence / Tool Calls / Inputs /
  Outputs / Result* — the auditable substance of what an actor did and
  why, never hidden reasoning traces.

## 12. Artifacts

### Artifact
A produced output, versioned.
- Fields: `id`, `project`, `task (nullable)`, `execution (nullable)`,
  `created_by (Actor)`, `type` (code|document|report|design|dataset|
  plan|build|…), `name`, `content` or `file_ref`, `version`, `metadata
  (JSON)`.

## 13. Evaluation

### Evaluation
Judges a target (**Evaluation ≠ Execution**); can be automatic, rule,
AI-judge, or human.
- Fields: `id`, `target` (execution/artifact/run), `evaluator (Actor or
  rule)`, `metrics (JSON)`, `score`, `result` (pass|fail),
  `feedback`, `timestamp`.
- Demo metrics: **Product Completeness, Code Quality, Test Result,
  Requirement Coverage**.
- **Quality Gate:** `tests_passed AND requirement_coverage >= threshold
  AND critical_errors == 0` — the condition the QA loop must satisfy to
  exit.

## 14. Policies and Rules

Policies form a hierarchy that resolves from broad to narrow, with the
most specific winning:

```text
Platform → Organization → Project → Workflow → Agent → Task
```

- `Policy/Rule`: `id`, `scope_level`, `scope_id`, `name`, `effect`
  (allow|deny|require_approval), `condition (JSON)`, `priority`.
- Resolution is intentionally simple and deterministic (see
  `core/rules`): collect applicable rules along the chain, order by
  specificity then priority, first decisive rule wins.

## 15. Audit / Events

### Event (append-only)
The backbone of both audit and realtime. Only ever inserted.
- Fields: `id (monotonic)`, `organization`, `project`, `task`,
  `execution`, `type`, `actor (nullable)`, `agent (nullable)`, `model
  (nullable)`, `prompt_version (nullable)`, `tool (nullable)`, `cost`,
  `tokens`, `result`, `payload (JSON)`, `created_at`.
- Event types: `PROJECT_CREATED, PROJECT_STARTED, WORKFLOW_STARTED,
  NODE_STARTED, NODE_COMPLETED, NODE_FAILED, TASK_CREATED, TASK_ASSIGNED,
  TASK_STARTED, TASK_COMPLETED, AGENT_STARTED, AGENT_MESSAGE,
  MODEL_CALL_STARTED, MODEL_CALL_COMPLETED, TOOL_CALL_STARTED,
  TOOL_CALL_COMPLETED, ARTIFACT_CREATED, EVALUATION_STARTED,
  EVALUATION_COMPLETED, LOOP_STARTED, LOOP_ITERATION, LOOP_EXITED,
  USER_INTERVENTION, PROJECT_COMPLETED, PROJECT_FAILED,
  PROJECT_ARCHIVED`.

Every important action records **WHO / WHAT / WHEN / PROJECT / TASK /
EXECUTION / RESULT**, and for AI actions additionally **Agent / Model /
PromptVersion / Tool / Cost / Tokens** — the raw material for
observability, evaluation, and the future Experience/Learning loop.

## 16. Relationship map (text ERD)

```text
Organization 1───* Membership *───1 User
Organization 1───* OrgUnit (tree)
Organization 1───* Role 1───* Position *───1 OrgUnit
Organization 1───* Capability 1───* Skill
Organization 1───* Actor
   Actor *───1 User? ;  Actor *───1 Agent?
   Actor 1───* ActorRoleAssignment *───1 Role
   Actor 1───* ActorCapability *───1 Capability
Organization 1───* Agent
   Agent *───1 Provider ; Agent *───1 Model ; Agent *───1 Credential
   Agent 1───* AgentPromptAssignment *───1 PromptVersion
   Agent 1───* ToolPermission *───1 Tool
Provider 1───* Model ; Provider 1───* Credential
Prompt 1───* PromptVersion
Organization 1───* Project *───1 Workflow ; Project 1───* Goal
Workflow 1───* WorkflowNode ; Workflow 1───* WorkflowEdge
Project 1───* WorkflowRun 1───* NodeExecution *───1 WorkflowNode
NodeExecution 1───* Task 1───* Assignment *───1 Actor
Task 1───* Execution 1───* Run 1───* ModelCall
                                Run 1───* ToolCall
Execution *───1 PromptVersion
Project 1───* Conversation 1───* Message *───1 Actor(sender/receiver)
Project 1───* Artifact ; Execution 1───* Artifact
Execution 1───* Evaluation ; Artifact 1───* Evaluation
Organization 1───* Policy
Organization 1───* Event  (append-only; FKs to project/task/execution)
```

This model is intentionally larger in *concept* than the demo wires up:
the decoupling rules and the entity boundaries are all present so that
Spaces, Arenas, Memory, Knowledge, and richer authorization can be added
later as new domains rather than as rewrites of existing ones.
