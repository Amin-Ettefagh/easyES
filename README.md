# easyES

**easyES** is a universal Human + AI Organization & Execution Platform. It is
not a chatbot, not only an agent builder, and not a simple workflow automation
clone. It models an organization as a living system of units, roles,
capabilities, humans, AI agents, tools, workflows, projects, executions,
events, artifacts, evaluations, policies, budgets, and feedback loops.

The current repository is a full-stack foundation/demo: Django + DRF backend,
Next.js frontend, PostgreSQL, a deterministic offline model provider, seeded
organization data, a software-delivery workflow, live execution tracking, and a
real QA fix loop.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Django](https://img.shields.io/badge/Django-5.x-0C4B33)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)

## Project Idea

The core idea behind easyES is simple: future organizations will not be made of
only humans or only AI agents. They will be hybrid execution systems where each
piece of work can be done by a human, an AI, a human-supervised AI, a tool, a
service, or a team made of all of them.

easyES provides the operating layer for that world:

- **Model the organization**: companies, org units, roles, capabilities, teams,
  actors, agents, tools, policies, budgets, and permissions.
- **Design the work**: projects use workflow graphs made of typed nodes,
  conditional edges, loops, reviews, approvals, evaluations, and terminal states.
- **Run the work**: the execution engine walks the graph, records every node run,
  emits an append-only event stream, writes artifacts, and enforces stop rules.
- **Improve the work**: failed tests and evaluations feed back into earlier
  workflow stages, creating bounded improvement loops instead of one-shot output.
- **Stay vendor-neutral**: models go through a provider gateway; agents are not
  hard-coded to one model, API, runtime, or tool vendor.
- **Keep the domain clean**: roles, actors, agents, models, workflows, projects,
  executions, tools, connectors, knowledge, memory, and evaluations are separate
  concepts.

The demo proves the idea with one seeded company named `amin`. It runs:

```text
Idea -> Research -> Planning -> Development -> Testing
     -> QA feedback -> Fix -> Re-test -> Review -> Completion / Archive
```

The first test can intentionally fail, the failure is turned into feedback, the
developer agent receives that feedback, the workflow loops back, and the second
test passes. This is the heart of the project: easyES is built to execute,
observe, control, measure, and improve organizational work.

For the complete product concept, see [docs/PROJECT_IDEA.md](docs/PROJECT_IDEA.md)
and the original expanded notes in [Idea.md](Idea.md).

## Quick Start

Requires Docker and Docker Compose.

```bash
docker compose up --build
```

Open http://localhost:18121 and log in:

```text
username: amin
password: 123456
```

The demo credential is a development seed only. It is gated by
`EASYES_ALLOW_DEMO_SEED` and should be disabled outside local/demo use.

To run one workflow automatically at startup:

```bash
EASYES_RUN_DEMO=1 EASYES_DEMO_SCENARIO=fail_once docker compose up --build
```

Scenarios:

- `success`: the workflow passes on the first run.
- `fail_once`: QA fails once, loops back, fixes, and passes.
- `always_fail`: the workflow stops at the max-iteration safety limit.

## Services

| Service | Host port | Purpose |
| --- | ---: | --- |
| `db` | internal | PostgreSQL 16 |
| `backend` | `18120` | Django + DRF API at `/api/v1` |
| `frontend` | `18121` | Next.js control room |

## What You Can Do

After logging in, the UI lets you:

- inspect the organization, roles, capabilities, human actors, and AI actors;
- edit agents, providers, models, token budgets, temperatures, and prompts;
- create projects from an idea and requirements;
- run a project through the `software_delivery` workflow;
- watch live node states, events, artifacts, QA loop state, and terminal results;
- test provider/model routing through the provider gateway.

## Architecture

easyES is a modular monolith: one Django project with well-bounded apps and a
Next.js control room.

```text
Browser
  |
  | HTTP/JSON
  v
Next.js frontend  ----->  Django + DRF API  ----->  PostgreSQL
                               |
                               +-- core/workflow_engine
                               +-- core/model_gateway
                               +-- apps/organizations
                               +-- apps/actors
                               +-- apps/agents
                               +-- apps/workflows
                               +-- apps/executions
                               +-- apps/audit
```

Important boundaries:

| Separate concepts |
| --- |
| Role != Actor != Agent != Model |
| Workflow != Project != Execution |
| Task != Actor |
| Knowledge != Memory |
| Tool != Connector |
| Evaluation != Execution |
| Capability != Role |

The workflow loop lives in data, not hard-coded logic. A workflow graph can
express branches, retries, gates, approvals, and loop-back edges while the
engine stays generic.

## Repository Map

```text
backend/        Django apps, API, workflow engine, model gateway
frontend/       Next.js App Router frontend
docs/           GitHub-friendly documentation set
docs/adr/       Architecture decision records
data/           Runtime workspace data, created locally when needed
Idea.md         Original expanded product idea
DemoPrompt.md   Original build/demo specification
```

## Documentation

| Document | Purpose |
| --- | --- |
| [docs/PROJECT_IDEA.md](docs/PROJECT_IDEA.md) | Full project idea and product thesis |
| [docs/PRODUCT_VISION.md](docs/PRODUCT_VISION.md) | Product vision and north star |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture |
| [docs/PRODUCT_ARCHITECTURE.md](docs/PRODUCT_ARCHITECTURE.md) | Product hierarchy |
| [docs/DOMAIN_MODEL.md](docs/DOMAIN_MODEL.md) | Core domain model |
| [docs/DATABASE.md](docs/DATABASE.md) | Schema and ERD notes |
| [docs/API.md](docs/API.md) | REST API surface |
| [docs/WORKFLOW_ENGINE.md](docs/WORKFLOW_ENGINE.md) | Workflow engine and QA loop |
| [docs/AGENT_SYSTEM.md](docs/AGENT_SYSTEM.md) | Agent, prompt, tool, and memory model |
| [docs/MODEL_GATEWAY.md](docs/MODEL_GATEWAY.md) | Model provider abstraction |
| [docs/PROVIDER_GATEWAY.md](docs/PROVIDER_GATEWAY.md) | Provider catalog and routing |
| [docs/REALTIME.md](docs/REALTIME.md) | Events, SSE, and polling behavior |
| [docs/SECURITY.md](docs/SECURITY.md) | Tenant isolation, secrets, and safety |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Local development |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Deployment notes |
| [docs/TESTING.md](docs/TESTING.md) | Test strategy |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Roadmap |
| [docs/RND_REFERENCES.md](docs/RND_REFERENCES.md) | R&D references |
| [docs/adr/](docs/adr/) | Architecture decision records |

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py shell -c "from core.seed import seed_demo; seed_demo()"
python manage.py runserver 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Run the lifecycle from the CLI:

```bash
cd backend
python manage.py run_demo --scenario fail_once
```

## Testing

```bash
cd backend
pytest
```

The test suite covers the domain model, workflow loop, API, condition
evaluation, model gateway, catalog import, and end-to-end execution behavior.

## Configuration

Copy [.env.example](.env.example) to `.env` and adjust as needed. Every variable
has a local demo default.

Primary easyES environment variables:

| Variable | Purpose |
| --- | --- |
| `EASYES_ENCRYPTION_KEY` | Encrypt stored provider credentials |
| `EASYES_WORKSPACES_ROOT` | Isolated project workspace root |
| `EASYES_ALLOW_DEMO_SEED` | Allow demo user/company seed |
| `EASYES_SEED` | Seed demo data on container boot |
| `EASYES_RUN_DEMO` | Run one workflow on container boot |
| `EASYES_DEMO_SCENARIO` | `success`, `fail_once`, or `always_fail` |
| `EASYES_EXECUTION_BACKEND` | `thread` for app, `inline` for tests/CLI |
| `EASYES_DEFAULT_PROVIDER` | Default model provider, usually `fake` locally |

## Production Notes

The repository is production-shaped but still a foundation/demo. Before real
deployment, rotate secrets, disable demo seed credentials, use a real encryption
key, configure allowed hosts/origins, move JWT storage to httpOnly cookies,
attach durable execution infrastructure, and connect real provider credentials.

## License

No license has been declared yet.
