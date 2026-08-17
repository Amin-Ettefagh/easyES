#!/usr/bin/env sh
set -e

# ---------------------------------------------------------------------------
# Backend container entrypoint.
#
#   1. Wait for the database to accept connections (compose starts pg alongside).
#   2. Apply the migrations committed with the application image.
#   3. Collect static files (admin + DRF UI assets) for WhiteNoise.
#   4. Optionally seed + run the demo end-to-end (EASYES_RUN_DEMO=1).
#   5. Launch Gunicorn with threaded workers so the SSE stream endpoint (a
#      long-lived streaming response) doesn't starve request handling.
# ---------------------------------------------------------------------------

echo "[entrypoint] waiting for database..."
python - <<'PY'
import os, time, sys
url = os.environ.get("DATABASE_URL", "")
if not url:
    print("[entrypoint] no DATABASE_URL; using SQLite, no wait needed.")
    sys.exit(0)
import dj_database_url
cfg = dj_database_url.parse(url)
import psycopg
dsn = (
    f"host={cfg.get('HOST')} port={cfg.get('PORT') or 5432} "
    f"dbname={cfg.get('NAME')} user={cfg.get('USER')} password={cfg.get('PASSWORD')}"
)
for attempt in range(60):
    try:
        psycopg.connect(dsn, connect_timeout=2).close()
        print("[entrypoint] database is ready.")
        break
    except Exception as exc:  # noqa: BLE001
        print(f"[entrypoint] db not ready ({attempt+1}/60): {exc}")
        time.sleep(1)
else:
    print("[entrypoint] database never became ready; exiting.")
    sys.exit(1)
PY

echo "[entrypoint] migrate..."
python manage.py migrate --noinput

# Older demo images generated their initial migrations inside the container.  The
# database may therefore record 0001 while missing additive fields introduced by
# a newer image.  Reconcile those fields without dropping or rewriting user data.
echo "[entrypoint] reconciling additive gateway schema..."
python manage.py ensure_gateway_schema

echo "[entrypoint] collectstatic..."
python manage.py collectstatic --noinput || true

EASYES_RUN_DEMO_VALUE="${EASYES_RUN_DEMO:-${COMPANYOS_RUN_DEMO:-0}}"
EASYES_SEED_VALUE="${EASYES_SEED:-${COMPANYOS_SEED:-1}}"
EASYES_DEMO_SCENARIO_VALUE="${EASYES_DEMO_SCENARIO:-${COMPANYOS_DEMO_SCENARIO:-fail_once}}"
EASYES_IMPORT_ROLE_CATALOG_VALUE="${EASYES_IMPORT_ROLE_CATALOG:-${COMPANYOS_IMPORT_ROLE_CATALOG:-1}}"
EASYES_CATALOG_ORG_VALUE="${EASYES_CATALOG_ORG:-${COMPANYOS_CATALOG_ORG:-amin}}"

if [ "$EASYES_RUN_DEMO_VALUE" = "1" ]; then
  echo "[entrypoint] seeding + running demo (scenario=${EASYES_DEMO_SCENARIO_VALUE})..."
  python manage.py run_demo --scenario "$EASYES_DEMO_SCENARIO_VALUE" || \
    echo "[entrypoint] run_demo failed (continuing to boot server)."
elif [ "$EASYES_SEED_VALUE" = "1" ]; then
  # Seed the company + demo user (no run) so the UI has data + login on boot.
  echo "[entrypoint] seeding demo company (no run)..."
  python manage.py shell -c "from core.seed import seed_demo; seed_demo()" || \
    echo "[entrypoint] seed failed (continuing)."
fi

if [ "$EASYES_IMPORT_ROLE_CATALOG_VALUE" = "1" ]; then
  echo "[entrypoint] importing role taxonomy + one editable agent per unique role..."
  python manage.py import_role_catalog --organization "$EASYES_CATALOG_ORG_VALUE" || \
    echo "[entrypoint] role catalogue import failed (continuing to boot server)."
fi

echo "[entrypoint] starting gunicorn on :8000..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-8}" \
  --worker-class gthread \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
