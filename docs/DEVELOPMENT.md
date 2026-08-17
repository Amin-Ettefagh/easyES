# Development

How to run the easyES locally **without Docker**, using a
Python virtualenv, SQLite, and the Next.js dev server. The whole
demo runs offline and deterministically — no external API keys required.

For the containerized path see [DEPLOYMENT.md](DEPLOYMENT.md).

## 1. Prerequisites

| Tool | Version |
| ---- | ------- |
| Python | 3.12 |
| Node.js | 20+ (for the Next.js 14 frontend) |
| Git | any recent |

No PostgreSQL is needed for local dev — SQLite is the default. No model
provider keys are needed — the FakeModelProvider is the default.

## 2. Backend setup (venv + SQLite)

From the repository root (`D:\easyES`):

```bash
# 1. Create and activate a virtualenv
cd backend
python -m venv .venv
# Windows (bash): source .venv/Scripts/activate
# Windows (PowerShell): .venv\Scripts\Activate.ps1
source .venv/Scripts/activate

# 2. Install dependencies
pip install -r requirements.txt          # or: pip install -e .[dev]

# 3. Configure environment (see §4); the defaults already target SQLite + Fake
cp .env.example .env

# 4. Apply migrations (creates db.sqlite3)
python manage.py migrate

# 5. Seed the demo (organization "amin", agents, workflow, project, user)
python manage.py seed_demo

# 6. Run the API
python manage.py runserver 0.0.0.0:8000
```

The backend is now at `http://localhost:8000`. Swagger UI is at
`http://localhost:8000/api/schema/swagger-ui/` (see [API.md](API.md)).

## 3. Frontend setup

```bash
cd frontend
npm install
cp .env.local.example .env.local     # set NEXT_PUBLIC_API_BASE=http://localhost:8000
npm run dev
```

The frontend is at `http://localhost:3000`. Log in with the seeded demo
user `amin` / `123456`.

## 4. Environment variables

Backend (`backend/.env`):

| Variable | Default (dev) | Purpose |
| -------- | ------------- | ------- |
| `DJANGO_ENV` | `dev` | Enables dev-only behavior (demo user seeding, DEBUG) |
| `DJANGO_DEBUG` | `True` | Django debug mode |
| `DJANGO_SECRET_KEY` | dev placeholder | Signing key (set a real one outside dev) |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | Swap to `postgres://…` to use Postgres locally |
| `EXECUTION_BACKEND` | `threaded` | In-process thread backend (default) |
| `MODEL_PROVIDER_DEFAULT` | `fake` | Deterministic offline provider |
| `CREDENTIAL_ENCRYPTION_KEY` | dev placeholder | Encrypts stored credentials at rest |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | Frontend origin |
| `WORKSPACE_ROOT` | `../data/workspaces` | Per-project tool workspace root |

Frontend (`frontend/.env.local`):

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000` | REST + SSE base URL |

Never commit real secrets; `.env` files are git-ignored (see
[SECURITY.md](SECURITY.md)).

## 5. Running the fake demo end-to-end

With backend and frontend running:

1. Log in as `amin` / `123456`.
2. Open the seeded **Software Development** project in the `amin`
   organization.
3. Click **Start**. The workflow run begins on the threaded backend.
4. Watch the live activity feed (SSE) and the React Flow canvas:
   - Research → Planning produce artifacts.
   - Development (iteration 1) → Testing **fails QA**.
   - Feedback → Fix → Development (iteration 2) → Testing **passes** the
     Quality Gate (loop exits with `PASS`).
   - Review (Approval) parks in `WAITING_FOR_APPROVAL`.
5. Click **Approve** on the review node → the project **Completes** and
   can be **Archived**.
6. Exercise controls at any time: Pause, Resume, Stop, Retry, Reject,
   Instruct (see [API.md](API.md) §5).

Because the FakeModelProvider is deterministic (keyed on
agent/node/iteration), the run tells the same story every time — ideal
for demos and tests (see [MODEL_GATEWAY.md](MODEL_GATEWAY.md)).

You can also drive it headlessly:

```bash
# Start the seeded project's run from the CLI (dev convenience)
python manage.py run_demo --project amin-software-dev
```

## 6. Useful management commands

| Command | Effect |
| ------- | ------ |
| `python manage.py migrate` | Apply migrations |
| `python manage.py seed_demo` | Seed/refresh the `amin` demo (idempotent) |
| `python manage.py reset_demo` | Drop demo runs/artifacts/events, keep definitions |
| `python manage.py run_demo --project <slug>` | Start a run without the UI |
| `python manage.py createsuperuser` | Admin user for Django admin |

## 7. Code style

- **Python:** Black (formatting), Ruff (lint/imports), type hints on
  public functions. `core/` stays framework-agnostic — no Django imports
  in `core/` (see [ARCHITECTURE.md](ARCHITECTURE.md) §3).
- **TypeScript:** ESLint + Prettier; strict TypeScript; React function
  components and hooks; React Flow for the canvas.
- **Commits/PRs:** small, layered changes; respect the dependency
  direction (Intelligence → Business → Foundation → core).
- **Tests:** add/extend tests with every change; see
  [TESTING.md](TESTING.md).

## 8. Switching to Postgres locally (optional)

If you want to develop against Postgres without full Docker:

```bash
# start just a postgres container
docker run --name easyes-pg -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=easyes -p 5432:5432 -d postgres:16

# point the backend at it
export DATABASE_URL=postgres://postgres:postgres@localhost:5432/easyes
python manage.py migrate && python manage.py seed_demo
```

Migrations are written to apply cleanly on both SQLite and PostgreSQL
(see [DATABASE.md](DATABASE.md)).

## 9. Project layout reminder

```text
backend/   config/ core/ apps/ manage.py requirements.txt .env
frontend/  app/ components/ lib/ package.json .env.local
data/      workspaces/<project-id>/     # created at runtime by tools
docs/      this documentation set
```

The read-only R&D reference tree at `D:\AgentPlayground` is **never**
modified — see [RND_REFERENCES.md](RND_REFERENCES.md).
