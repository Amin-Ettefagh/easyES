# easyES — Frontend

Next.js 14 (App Router) + TypeScript control room for easyES.
It talks to the Django REST backend at `/api/v1` and renders:

- **Login** (`/login`) — JWT sign-in (demo: `amin` / `123456`).
- **Dashboard** (`/`) — org summary, projects, recent runs, and a "New Project" form.
- **Company** (`/company`) — org units, roles (with capabilities), and actors (human + AI).
- **Agents** (`/agents`) — per-agent config editor: model, temperature, budgets, and a
  prominent **system-prompt editor** (each save creates a new immutable prompt version).
- **Workflow** (`/workflow`) — the `software_delivery` graph rendered with React Flow.
- **Project Control Room** (`/projects/[uuid]`) — start a run (success / fail_once /
  always_fail), watch nodes light up live, see the QA loop iterate, and a live event log.

## Requirements

- Node.js 20+

## Local development

```bash
cd frontend
cp .env.local.example .env.local   # point NEXT_PUBLIC_API_BASE at your backend
npm install
npm run dev
```

Open http://localhost:3000. The backend must be running (default
`http://localhost:8000/api/v1`) with the demo seeded (`EASYES_ALLOW_DEMO_SEED=1` +
`python manage.py run_demo` — see the backend README).

## Configuration

| Variable                | Default                          | Notes                                            |
| ----------------------- | -------------------------------- | ------------------------------------------------ |
| `NEXT_PUBLIC_API_BASE`  | `http://localhost:8000/api/v1`   | Inlined into the browser bundle **at build time**. |

Because `NEXT_PUBLIC_*` is baked at build time, the Docker image takes it as a
build arg (see `docker-compose.yml` at the repo root).

## How live updates work

The backend exposes an SSE stream at `/executions/<uuid>/stream/`, but `EventSource`
can't attach the `Authorization: Bearer` header the API requires. So the Control
Room instead **polls** `GET /events/?execution=<uuid>` every 1.5 s and dedupes by
the monotonic `seq`, and polls the execution detail to update node statuses and the
loop panel. Polling stops as soon as the run reaches a terminal state
(`succeeded` / `failed` / `cancelled`).

## Docker

Built as part of the root `docker compose up --build`. To build standalone:

```bash
docker build -t easyes-frontend \
  --build-arg NEXT_PUBLIC_API_BASE=http://localhost:8000/api/v1 \
  frontend
docker run -p 3000:3000 easyes-frontend
```

## Notes / assumptions

- JWTs are stored in `localStorage` — simple and fine for a single-origin demo. For
  production you'd move to httpOnly cookies and add refresh-token rotation.
- The `model` field on an agent is patched by numeric PK; the models list endpoint
  exposes `id` for that purpose.
- The workflow graph is read-only on the canvas (nodes are draggable for layout but
  edits are not persisted) — the demo's focus is *observing* the real execution loop.
