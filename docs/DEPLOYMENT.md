# Deployment

How to run the easyES with Docker Compose: the services,
their health checks, environment configuration, seeding, and resetting.
For the no-Docker local path see [DEVELOPMENT.md](DEVELOPMENT.md).

## 1. Quick start

From the repository root (`D:\easyES`):

```bash
docker compose up --build
```

This builds and starts the full stack. On first boot the backend applies
migrations and seeds the `amin` demo automatically (controlled by
`AUTO_SEED`, see §5). When healthy:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000/api/v1/`
- Swagger UI: `http://localhost:8000/api/schema/swagger-ui/`

Log in as the seeded demo user `amin` / `123456` (dev/demo only).

## 2. Services

```text
                       ┌──────────────┐
                       │   frontend   │  Next.js 14 (prod build)  :3000
                       └──────┬───────┘
                              │  REST + SSE
                       ┌──────▼───────┐
                       │   backend    │  Django 5 + DRF + gunicorn :8000
                       │  (+ threaded │  runs migrations, seed, and the
                       │   execution) │  in-process workflow engine
                       └──┬────────┬──┘
                          │        │
                 ┌────────▼──┐  ┌──▼──────────────┐
                 │ postgres  │  │ redis (optional)│
                 │  :5432    │  │  :6379          │
                 └───────────┘  └──┬──────────────┘
                                   │ (only if a broker-based backend is enabled)
                              ┌────▼─────┐
                              │  worker  │  optional: Celery/other backend
                              │ (optional)│
                              └──────────┘
```

| Service | Image / build | Role | Required? |
| ------- | ------------- | ---- | --------- |
| `frontend` | `frontend/Dockerfile` | Next.js production server | Yes |
| `backend` | `backend/Dockerfile` | Django API + threaded workflow engine | Yes |
| `postgres` | `postgres:16` | Primary database | Yes |
| `redis` | `redis:7` | Broker/cache for a future broker-based execution backend | Optional |
| `worker` | `backend/Dockerfile` (different command) | Runs a Celery/other `ExecutionBackend` when enabled | Optional |

The **default execution backend is threaded and in-process** inside
`backend`, so `redis` and `worker` are **not needed** for the demo. They
are declared behind a Compose profile (`--profile workers`) so the
architecture's execution-backend seam is visible and swappable (see
[ARCHITECTURE.md](ARCHITECTURE.md) §6 and
[adr/0006-background-execution.md](adr/0006-background-execution.md)).

```bash
# default: frontend + backend + postgres (threaded engine)
docker compose up --build

# opt into redis + worker (future broker-based backend)
docker compose --profile workers up --build
```

## 3. Health checks

Each service exposes a health check so Compose can order startup and
report readiness:

| Service | Check | Notes |
| ------- | ----- | ----- |
| `postgres` | `pg_isready -U $POSTGRES_USER` | `backend` waits for this |
| `redis` | `redis-cli ping` | only in the `workers` profile |
| `backend` | `GET /api/v1/health/` returns 200 | verifies DB + model-gateway `health_check()` |
| `frontend` | `GET /` returns 200 | Next.js server ready |
| `worker` | process liveness / backend `status()` | only in the `workers` profile |

`depends_on` with `condition: service_healthy` gates the boot order:
`postgres` → `backend` (migrate + seed) → `frontend`.

## 4. Environment configuration

Configuration is via environment variables (Compose reads `.env` at the
repo root). Key variables for a containerized run:

| Variable | Example | Purpose |
| -------- | ------- | ------- |
| `DJANGO_ENV` | `demo` | `dev`/`demo`/`prod` behavior toggles |
| `DJANGO_DEBUG` | `False` | Debug off outside local dev |
| `DJANGO_SECRET_KEY` | (secret) | Signing key — set explicitly in prod |
| `DATABASE_URL` | `postgres://easyes:...@postgres:5432/easyes` | Points at the `postgres` service |
| `EXECUTION_BACKEND` | `threaded` | `threaded` (default) or a broker backend under the `workers` profile |
| `REDIS_URL` | `redis://redis:6379/0` | Only used by broker backends |
| `MODEL_PROVIDER_DEFAULT` | `fake` | Deterministic offline provider |
| `CREDENTIAL_ENCRYPTION_KEY` | (secret) | Encrypts stored credentials at rest |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | Frontend origin |
| `ALLOWED_HOSTS` | `backend,localhost` | Django allowed hosts |
| `AUTO_SEED` | `true` | Seed the demo on backend boot |
| `WORKSPACE_ROOT` | `/data/workspaces` | Per-project tool workspace (mounted volume) |

Secrets (`DJANGO_SECRET_KEY`, `CREDENTIAL_ENCRYPTION_KEY`, DB password)
must be provided via the environment / a secrets manager and never
committed (see [SECURITY.md](SECURITY.md)). The offline demo uses the
FakeModelProvider and therefore stores **no external provider secrets**.

## 5. Seeding

- On boot, if `AUTO_SEED=true`, the `backend` entrypoint runs:
  ```bash
  python manage.py migrate --noinput
  python manage.py seed_demo
  ```
- `seed_demo` is **idempotent**: it creates or refreshes the `amin`
  organization, its specialized agents, the Software Development workflow
  template, a project, and (in dev/demo) the `amin` user. Re-running does
  not duplicate.
- To seed manually:
  ```bash
  docker compose exec backend python manage.py seed_demo
  ```

## 6. Resetting

| Goal | Command |
| ---- | ------- |
| Reset demo *runs* only (keep definitions) | `docker compose exec backend python manage.py reset_demo` |
| Full wipe (drop DB + volumes) | `docker compose down -v` then `docker compose up --build` |
| Clear project workspaces | remove `WORKSPACE_ROOT/<project-id>` (or the mounted `data` volume) |

`reset_demo` deletes `WorkflowRun`, `NodeExecution`, `Execution`,
`ModelCall`/`ToolCall`, `Artifact`, `Message`, `Evaluation`, and `Event`
rows for the demo project while preserving the organization, agents, and
workflow definitions — so you can re-run the demo cleanly without
re-seeding.

## 7. Volumes and persistence

| Volume | Mounted at | Holds |
| ------ | ---------- | ----- |
| `pgdata` | postgres `/var/lib/postgresql/data` | Database |
| `workspaces` | backend/worker `WORKSPACE_ROOT` | Per-project tool workspaces |
| `static` | backend `/app/static` (served by frontend/proxy) | Collected static assets |

`docker compose down` keeps volumes; `down -v` removes them (full reset).

## 8. Logs and observability

```bash
docker compose logs -f backend     # engine + API logs (secrets scrubbed)
docker compose logs -f frontend
docker compose exec backend python manage.py shell
```

Live execution activity is best observed through the app's SSE feed (see
[REALTIME.md](REALTIME.md)); the append-only Event table is the durable
record behind it.

## 9. Production notes

- Set `DJANGO_DEBUG=False`, a real `DJANGO_SECRET_KEY` and
  `CREDENTIAL_ENCRYPTION_KEY`, explicit `ALLOWED_HOSTS`, HTTPS
  termination, and a restrictive `CORS_ALLOWED_ORIGINS` (see
  [SECURITY.md](SECURITY.md)).
- Do **not** enable demo-user seeding outside dev/demo (`DJANGO_ENV`
  gates it).
- For durable/at-scale execution, enable the `workers` profile and switch
  `EXECUTION_BACKEND` to the broker backend, or adopt Temporal per the
  [ROADMAP.md](ROADMAP.md) — no domain code changes are required.
