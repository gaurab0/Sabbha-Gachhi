# Sabha Gachhi

A matrimony/matching platform. Monorepo with a Django (+ MongoDB) backend in
`backend/` and a React + TypeScript frontend in `frontend/`.

## Running the async worker

The automated matching engine runs as an **asynchronous Celery task**. On
Windows the default `prefork` pool is not supported, so a solo pool is used.

Start the worker from the repo root:

```sh
# Windows (native PowerShell) — uses --pool=solo
.\scripts\run_worker.ps1

# Linux / WSL / production — uses the default prefork pool
./scripts/run_worker.sh
```

Or run it directly from `backend/`:

```sh
celery -A core.celery worker --pool=solo -l info    # Windows
celery -A core.celery worker -l info                # Linux / WSL / prod
```

The worker consumes from `redis://localhost:6379/0` (override via
`CELERY_BROKER_URL`). **Redis must be running** before the worker starts.

> ⚠️ **Registrations silently no-op without the worker.** Verification emits
> `run_matching_engine_task.delay(...)` from `registrations/signals.py`; if no
> worker is consuming the broker, the task is never executed and no
> `Match`, `MatchProposal`, or `MatchAttemptLog` rows are created — no error is
> raised anywhere. Always check worker health:

```sh
cd backend
python manage.py check_celery_worker
```

This pings the worker (`celery control ping`) and **fails loudly with exit
code 1** if no worker responds or the broker is unreachable, so a dead worker
is visible in dev/staging instead of silently swallowing match tasks.

## Quick start

Backend (MongoDB + Redis must be running):

```sh
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Frontend:

```sh
cd frontend
npm install
npm run dev
```