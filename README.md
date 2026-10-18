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

## Email deliverability (production)

Verification mail is sent from `DEFAULT_FROM_EMAIL` — full `EMAIL_FROM`
wins, otherwise `Sabha Gachhi <noreply@${NOREPLY_EMAIL_DOMAIN}>`. For the
sending domain you need, at your DNS registrar:

- **SPF** (TXT @): `v=spf1 include:<your-provider> ~all`
- **DKIM** (TXT `<selector>._domainkey`): provider-supplied key record
- **DMARC** (TXT `_dmarc`): `v=DMARC1; p=quarantine; rua=mailto:dmarc@<domain>`

The `noreply@` mailbox should either not exist (bounce) or be a
discard/blackhole address — nobody reads it. Note no email system can
technically *block* replies; the `Reply-To`/`Auto-Submitted`/
`X-Auto-Response-Suppress`/`Precedence: bulk` headers plus the unmonitored
address are the standard way to discourage them.

Use a transactional provider in production (SES, Postmark, SendGrid, Resend,
or Brevo) — via `EMAIL_SMTP_*` or a custom `EMAIL_VERIFICATION_PROVIDER` —
never a personal Gmail account. Console backend in dev.

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

## Running with Docker

Docker Compose **2.20.3 or newer** is required for the root file's `include:`
feature. Docker Desktop with the WSL2 engine is recommended on Windows. Keep
the checkout in the WSL filesystem (for example `~/src/SabhaGachi`) for much
faster bind mounts and file watching.

### First-time setup

From the repository root, create the shared networks and prepare `.env`:

```powershell
.\scripts\create-networks.ps1
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

```bash
sh ./scripts/create-networks.sh
test -f .env || cp .env.example .env
```

If you already have a real `.env`, keep it and copy the new Docker variables
from `.env.example` into it; don't overwrite your existing credentials. Set
unique random values for `MONGO_ROOT_PASSWORD`, `MONGO_APP_PASSWORD`,
`REDIS_PASSWORD`, and `DJANGO_SECRET_KEY`. Keep Mongo/Redis passwords
alphanumeric so Mongo's URI credentials don't need escaping. The Mongo app
account is created with `readWrite` on `MONGO_DATABASE`; Django does not use
the Mongo root account. Redis DB 0 is the Celery broker, DB 1 is the Celery
result backend, and DB 2 is Django's shared cache in Docker. Without
`DJANGO_CACHE_URL`, local Django keeps its per-process locmem cache.

### Development

The root `docker-compose.override.yml` is loaded automatically by
`docker compose` and selects Vite and Django development targets, source bind
mounts, and polling for Windows file watching.

```powershell
docker compose up --build
```

```bash
docker compose up --build
```

The frontend is at <http://localhost:5173>, the API at
<http://localhost:8000>, and the liveness endpoint at
<http://localhost:8000/healthz/>. MongoDB Compass can connect to
`mongodb://root:<MONGO_ROOT_PASSWORD>@localhost:27017/?authSource=admin`; Redis
is bound to `127.0.0.1:6379`. The browser-side API URL is
`http://localhost:8000/api`. Do not use `http://backend:8000` in browser code:
that service name is only resolvable between containers. If a Vite proxy is
added later, its target runs inside the frontend container and should use
`http://backend:8000`.

Migrations run once in the `migrate` service before the web and worker start.
The initial setup currently hits a pre-existing blocker: migration
`registrations.0005_registration_token_match` opens its own hard-coded,
unauthenticated `mongodb://localhost:27017/` PyMongo connection and drops a
collection. Inside the container `localhost` is the migrate container, and
the Mongo service requires authentication. I have not changed that migration
because the requested code-change boundary excludes migration changes. The
stack will not complete a clean first migration until that migration is made
configuration-aware and its collection-drop behavior is reviewed. It cannot
be repaired by changing Compose settings alone.

### Production-style deployment

Before starting, set `DJANGO_DEBUG=false`, a real `DJANGO_SECRET_KEY`, the
public domain in `DJANGO_ALLOWED_HOSTS`, the public origin in
`DJANGO_CSRF_TRUSTED_ORIGINS`, and production mail/SMS credentials in `.env`.
`VITE_API_BASE_URL` is compiled into the frontend image; changing it requires
a rebuild. By default, production uses `/api` on the frontend origin and Nginx
proxies `/api/` and `/admin/` to `backend:8000`. Set `BACKEND_UPSTREAM` to
change the proxy destination. Uploaded files persist in the backend media
volume. Production `/media/` access returns 404 because the current app has no
authenticated file-serving endpoint; directly mounting that directory in
Nginx would make private candidate photos public. Add an authorized endpoint
before enabling production photo delivery.

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

Only the frontend is published (port 80 by default, configurable with
`FRONTEND_PORT`). MongoDB and Redis have no host ports in production. The
containers use non-root users, read-only root filesystems where supported,
resource limits, log rotation, and `no-new-privileges`. Configure TLS at an
upstream load balancer or reverse proxy and set `DJANGO_CSRF_TRUSTED_ORIGINS`
for its HTTPS origin. The compose files do not run Celery beat: the repository
has no beat schedule (the token cleanup task is defined but unscheduled).
For optional local monitoring, set a strong `FLOWER_BASIC_AUTH` and start with
`docker compose --profile monitoring up --build`; Flower is bound to
`127.0.0.1:${FLOWER_PORT}`.

### Common commands

```powershell
docker compose run --rm migrate
docker compose exec backend python manage.py createsuperuser
docker compose logs -f backend worker
docker compose exec backend python manage.py check_celery_worker
docker compose exec backend python manage.py <command>
docker compose exec backend python manage.py test
```

```bash
docker compose run --rm migrate
docker compose exec backend python manage.py createsuperuser
docker compose logs -f backend worker
docker compose exec backend python manage.py check_celery_worker
docker compose exec backend python manage.py <command>
docker compose exec backend python manage.py test
```

Run a MongoDB backup or restore from the repo root while the `sabha_data`
network and Mongo container are running:

```powershell
.\scripts\backup.ps1
.\scripts\restore.ps1 <backup-file-name>
```

```bash
sh ./scripts/backup.sh
sh ./scripts/restore.sh <backup-file-name>
```

Archives are gzip-compressed and stored under `backups/` (git-ignored). Restore
merges documents into the target database; it does not drop collections.

### Running a tier on its own

Each tier compose can be used independently after creating the two external
networks and filling in `.env`. Start data before backend; start backend before
frontend:

```powershell
docker compose -f data/compose.yml up -d
docker compose -f backend/compose.yml up --build -d
docker compose -f frontend/compose.yml up --build -d
```

```bash
docker compose -f data/compose.yml up -d
docker compose -f backend/compose.yml up --build -d
docker compose -f frontend/compose.yml up --build -d
```

### Troubleshooting

- **`exec format error` or `not found` on a shell helper:** normalize scripts
  to LF; `.gitattributes` enforces this for `*.sh`.
- **Vite does not reload changes on Windows:** polling is enabled in dev. Keep
  the repository inside the WSL filesystem for better performance.
- **Mongo says the replica set is not initialized:** this compose setup uses a
  standalone Mongo server. Django's standard `transaction.atomic()` is a no-op
  with this backend; enabling real transactions requires converting code to
  `django_mongodb_backend.transaction.atomic()` and then deploying Mongo as a
  replica set. No replica set or keyfile is configured here.
- **Port already in use:** change `FRONTEND_DEV_PORT`, `API_PORT`,
  `MONGO_PORT`, or `REDIS_PORT` in `.env` (production uses `FRONTEND_PORT`).
- **Frontend API URL changed but old URL remains:** rebuild the frontend image;
  `VITE_*` variables are baked into production assets.
- **Compose reports a missing network:** run `scripts/create-networks.ps1`
  (PowerShell) or `sh scripts/create-networks.sh` (bash).
- **A clean database migration fails:** see the hard-coded `0005` migration
  limitation in the development section above.

### Inspection notes and code changes

- MongoDB access is through `django-mongodb-backend` 6.1.0 and PyMongo 4.18.1;
  dependencies are not fully pinned in the existing requirements file. The
  frontend uses npm with `package-lock.json`, `npm run build`, and
  `BrowserRouter`.
- The allowed code changes outside Docker files are configuration-only:
  Django settings now read Mongo URI/database, allowed hosts, CORS/CSRF origins,
  and Celery eager-mode from environment; Docker can use Redis DB 2 for a
  shared cache; static root and WhiteNoise are set;
  `/healthz/` was added; and Vite binds to all interfaces and supports the
  dev-only polling environment variable. `gunicorn==23.0.0` and
  `whitenoise==6.9.0` were added to requirements.
- Existing candidate-photo uploads write private files, but production has no
  authorized file-serving endpoint. Docker persists these files and does not
  expose them through Nginx; `/media/` returns 404 until a protected delivery
  route is added.
- Matching and verification currently use Django's transaction API, which the
  Mongo backend documents as a no-op. Existing `UniqueConstraint` is over
  regular fields, not an expression. No business logic or ORM code was changed.
- Existing local working-tree edits were preserved. No existing Docker files
  were present to overwrite.
