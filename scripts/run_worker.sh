#!/usr/bin/env bash
#
# Starts the Celery worker for local development on Linux/WSL and for
# production-like environments, using the default prefork pool.
#
# On native Windows this prefork pool does not work — use
# scripts/run_worker.ps1 instead (it pins --pool=solo).
#
# Prereqs: Redis running on localhost:6379 (see README "Running the async
# worker" section).
#
# Usage:
#     ./scripts/run_worker.sh
#     ./scripts/run_worker.sh --loglevel=debug
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"

if [[ -x "$BACKEND/venv/bin/python" ]]; then
    PYTHON="$BACKEND/venv/bin/python"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
    PYTHON="$ROOT/.venv/bin/python"
else
    PYTHON="python"
fi

LOGLEVEL="${1:-info}"

echo "Starting Celery worker (default/prefork pool) ... press Ctrl+C to stop."
cd "$BACKEND"
exec "$PYTHON" -m celery -A core.celery worker -l "$LOGLEVEL"