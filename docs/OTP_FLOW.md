# OTP Email Verification — Flow Guide

How a user goes from signup to verified, which files run each step, and
how to test it. Backend is Django + DRF (`backend/accounts/`), frontend
is React (`frontend/src/`).

## The flow (happy path)

1. **Signup** — `POST /api/auth/signup/` with `{"email", "password"}`.
   Creates the user (`email_verified=False`) and immediately issues a
   verification message. Response includes `access`/`refresh` JWTs plus
   `verification_method` (`"link"` or `"otp"`), so the frontend knows
   which UI to show. Code: `SignupView` in `backend/accounts/views.py`.
2. **Resend** — `POST /api/auth/resend-verification/` with
   `{"channel": "email"}` (requires login). Enforces, in order: per-user
   mutex lock → 60s cooldown → 5/hour per target → 5/day per user →
   100/day per IP. Violations return **429** with `code` +
   `retry_after_seconds` **and** a `Retry-After` header. A failed send
   returns **503** and consumes no quota. Code:
   `ResendVerificationView` in `views.py`, limits in `_email_*` helpers.
3. **Verify** — `POST /api/auth/verify-email/` with `{"code": "482916"}`
   (`"otp"` accepted as an alias) or legacy `{"token": "..."}` for links.
   Explicit error codes: `invalid`, `expired`, `too_many_attempts` (5
   wrong tries lock the code), `not_found`. Success marks the user
   verified and returns fresh JWTs carrying the updated claim. Code:
   `VerifyEmailView` → `verify_code()` in `verification.py`.
4. **Afterwards** — `GET /api/auth/me/` reports `email_verified` and
   `verification_method`. App routes requiring verification return
   **403 `email_not_verified`** otherwise (`RequireVerifiedEmail`;
   the status page itself stays readable so it can show the verify UI).

## Files involved

| Area | File | Role |
|---|---|---|
| Service | `backend/accounts/verification.py` | `issue_code` / `verify_code`, `VerificationResult`, `BaseSender` + `SENDERS` registry (phone plugs in here) |
| Models | `backend/accounts/models.py` | `VerificationCode` (hash only, never raw), `EmailVerificationToken` (legacy links), `VerificationSendLog` (quota accounting) |
| HTTP | `backend/accounts/views.py`, `serializers.py`, `urls.py` | Endpoints, input validation, permissions (`permissions.py`), coded errors (`exceptions.py`) |
| Delivery | `backend/accounts/mailer.py`, `tasks.py` | No-reply headers, pluggable provider, Celery dispatch with ≤2 backed-off retries |
| Identity | `backend/accounts/email_normalize.py` | Lowercase/trim + Gmail dot/plus folding, so aliases map to one account |
| Frontend | `frontend/src/components/VerifyEmailPage.tsx`, `frontend/src/api/auth.ts` | Code boxes with paste support, resend countdown, 429/503 messages, `?token=` link mode |
| Scripts | `backend/scripts/smtp_check.py`, `backend/scripts/smoke_otp.py` | SMTP diagnosis; end-to-end live smoke test |

## Settings (all env-driven, see `backend/.env.example`)

`EMAIL_VERIFICATION_METHOD` (`link`|`otp`), `OTP_EXPIRY_MINUTES` (10),
`OTP_MAX_ATTEMPTS` (5), `OTP_RESEND_COOLDOWN_SECONDS` (60),
`OTP_MAX_SENDS_PER_HOUR_PER_TARGET` (5), `RESEND_MAX_PER_USER_PER_DAY`
(5), `RESEND_MAX_PER_IP_PER_DAY` (100), `TRUSTED_PROXY_COUNT` (0) mirrored
to DRF `NUM_PROXIES`, `DJANGO_SECRET_KEY` (required outside DEBUG),
`DJANGO_DEBUG`, Gmail `EMAIL_HOST/PORT/USER/PASS` + `EMAIL_TIMEOUT`.

## Test commands

```powershell
cd backend
# Full accounts suite (54+ tests: contract, lockout, concurrency, resend
# limits, hostile inputs, SMTP config)
.\venv\Scripts\python.exe manage.py test accounts
# Single test:
.\venv\Scripts\python.exe manage.py test accounts.tests.EmailVerificationTests.test_otp_attempt_lockout
# Live end-to-end against a running server (needs an unverified account):
.\venv\Scripts\python.exe scripts/smoke_otp.py   # reads SABHA_* env vars
```

```powershell
cd frontend
npx tsc --noEmit   # typecheck (must exit 0)
```

## Key contracts to preserve

- Only hashes are stored (`code_hash`), compared with
  `hmac.compare_digest`; raw codes never touch DB, logs, or responses
  (DEBUG console email excepted — dev only).
- Codes are single-use and bound to the exact target address; a resend
  invalidates the previous code.
- Changing email resets `email_verified` and kills outstanding codes;
  the new code verifies the *new* address before the swap happens.
- JWTs carry `email_verified`/`phone_verified` claims, refreshed from
  the DB on every token refresh.
