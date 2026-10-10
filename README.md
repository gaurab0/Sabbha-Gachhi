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