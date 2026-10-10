# Deploy Checklist — email/phone verification hardening

Status quo (verified 2026-10-10): dev runs with `DEBUG=True`,
hardcoded dev `SECRET_KEY` fallback, locmem cache, console-friendly
SMTP config, link+OTP duality. **Implement nothing below until the
corresponding item is approved — each item lists its change, its test,
and its risk.**

Conventions used below: `backend/.env` holds secrets (gitignored, never
committed); `backend/.env.example` holds placeholders only.

---

## 1. `SECRET_KEY` from the environment, newly generated, never in git

**Change:** generate one fresh key (`python -c
"import secrets; print(secrets.token_urlsafe(64))"`), store it as
`DJANGO_SECRET_KEY` in production env only. Settings already fail fast
when it is missing and `DEBUG` is false — no code change needed for the
lookup itself.

**Test:** staging boot without the variable must raise
`ImproperlyConfigured` naming `DJANGO_SECRET_KEY` (proves fail-fast);
boot with it set must succeed; `manage.py check` green.

**Risk — read before rotating:** everything below logs out or breaks
on rotation, because all of it is keyed by `SECRET_KEY`:
- all outstanding JWT access/refresh tokens become invalid → **every
  user is logged out** (re-login required, no migration path);
- outstanding OTP hashes (`hash_code`) stop matching → pending codes
  return `not_found`, users must resend (graceful, by design);
- Django sessions, CSRF tokens, password-reset tokens all invalidate.
Rotate in a quiet window and announce re-login. Never print the key,
never put it in `.env.example`, docs, tests, or shell history
(use `read -s` / env-file injection, not `-c` echo).

## 2. `ALLOWED_HOSTS`, CORS, HTTPS-only cookies, `SECURE_PROXY_SSL_HEADER`, `DEBUG` off

**Change** (`backend/core/settings.py`, production only):
- `DEBUG=False` (already the default when `DJANGO_DEBUG` is unset).
- `ALLOWED_HOSTS=["<prod-domain>"]` (today: `[]` — rejects everything
  once `DEBUG` is off).
- `CORS_ALLOWED_ORIGINS=["https://<prod-frontend>"]` (today: localhost
  Vite origins only).
- `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`
  (cookies never travel over plain HTTP).
- `SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https")`
  **only** with `TRUSTED_PROXY_COUNT >= 1`, so Django knows when the
  outer request was HTTPS.

**Test:** with `DEBUG=False` locally: `/api/auth/me/` over plain HTTP
shows `Secure` cookies absent... (positive check) `curl -sI` shows no
`Set-Cookie` without `Secure`; request to an unlisted Host returns
400; CORS preflight from an unlisted origin is rejected.

**Risk:** setting `SECURE_PROXY_SSL_HEADER` without a real trusted
proxy lets a client spoof `https` (secure-cookie bypass). Couple it to
the same `TRUSTED_PROXY_COUNT` gate as item 4. Flipping `DEBUG` off
also silences the console email backend and DEV-code logging — verify
SMTP delivers before announcing.

## 3. `CACHES` pointed at Redis (resend lock, throttles)

**Change:** `CACHES = {"default": {"BACKEND":
"django_redis.cache.RedisCache", "LOCATION": env REDIS_CACHE_URL}}`.
Covers the resend `cache.add` lock and DRF throttle buckets
(`NUM_PROXIES`-keyed idents included).

**Test:** with Redis stopped, resend still answers (lock calls fall
through to live checks); with Redis up, two same-second resends yield
one 200 + one 429-`cooldown`.

**Risk — fail direction:** today the lock is fail-**open**: if Redis
is down, `cache.add` raises → we must catch and proceed to the
(normally sufficient) DB checks, otherwise a cache outage becomes a
total resend outage. Alternatives: fail-**closed** (deny resends when
the cache is unreachable — safer against bursts, but turns every Redis
blip into user-visible 503s). Recommendation: fail-open + alert (item
9), because the DB cooldown/caps remain as the backstop. Never let a
cache exception bubble as a 500.

## 4. `TRUSTED_PROXY_COUNT` and `NUM_PROXIES` equal the real proxy count

**Change:** set both to the actual number of proxies in front of
Django (they are already wired to a single setting), and firewall the
app server so it is reachable **only** through that proxy.

**Test:** the two spoof tests (`ClientIpTests`) plus an end-to-end
check with `X-Forwarded-For` spoofing through the real deployment —
expect the proxy's peer IP, never the spoofed value.

**Risk:** wrong count in either direction hurts: too low trusts
attacker headers (throttle/cap evasion); too high trusts the proxy's
own address (everyone shares one identity → mass false throttling).
Count every hop, including CDN → LB → app.

## 5. Move `sender.send()` out of `transaction.atomic()` in `issue_code()`

**Change:** create row → commit → send → on success stamp
`last_sent_at` in a second write; on failure consume the row. The
at-least-once edge (crash between send and stamp) resolves to a
harmless duplicate send on next resend, never to a phantom code.

**Test:** new test with a failing sender asserting: no row left
active, response path maps to 503, and a later successful send still
issues exactly one active row.

**Risk:** two writes instead of one (tiny perf cost); brief window
where a row exists unsent — verify path must keep treating
never-sent rows as consumable-then-`not_found`, which it already does
(no `last_sent_at` ≠ usable without a matching code).

## 6. Transactional email provider + SPF/DKIM

**Change:** implement `EMAIL_VERIFICATION_PROVIDER` (SES/Postmark/
SendGrid/Resend/Brevo) behind the existing mailer abstraction; no view
changes. Publish SPF (`v=spf1 ...`), DKIM (provider selector), DMARC
(`p=quarantine` → `reject`) for the sending domain; keep Gmail SMTP
for dev only.

**Test:** `send_test_email` to a real inbox (check headers show
SPF/DKIM `pass`); provider dashboard shows delivery, not just API
acceptance; failure still maps to 503 via the existing contract.

**Risk:** DNS propagation delay (verify with `dig` before switching);
per-message cost and sandbox limits on new accounts (warm up or request
limit raises); keep the Gmail path as a documented fallback, not the
default.

## 7. Retire the link path after old links expire

**Change (only after `EMAIL_LINK_EXPIRY_MINUTES` has elapsed since the
switch to OTP):** delete the `"token"` branch (`_verify_link`,
`issue_token` link mode, `EMAIL_VERIFICATION_METHOD` flag,
`EmailVerificationToken` email types) with its tests.

**Test:** suite green with link tests removed; grep for
`verify-email.*token`, `issue_token`, `TYPE_EMAIL_LINK` returns
nothing outside git history.

**Risk:** any unexpired emailed link dies instantly — hence the wait.
Also: frontend `?token=` handling and the toggle become dead code;
remove together or the page offers a flow the server rejects.

## 8. Prune `VerificationCode` rows older than 7 days

**Change:** extend the existing `cleanup_expired_verification_tokens`
beat task (or a sibling) to delete `VerificationCode` rows with
`created_at` older than 7 days.

**Test:** seed a 10-day-old consumed row + a fresh active row, run the
task, assert only the fresh row remains.

**Risk:** near-zero (rows are single-use and short-lived by design);
keeps the table small so the per-target/per-user scans stay cheap.
Schedule daily, same beat as the existing cleanup.

## 9. Monitoring: alert on verification anomalies

**What:** alert (not just log) on: `too_many_attempts` rate spike per
10 min (credential-stuffing/OTP-guessing signal), 503 rate from
verify/resend (provider down), `verification_send_failed` count
(SMTP/auth breakage — the exact failure mode from the Gmail outage).

**Test:** synthetic check that each counter increments on the
corresponding forced failure (reuse the 503/lockout tests with a
metrics assertion or a staging dry-run).

**Risk:** alert fatigue — set thresholds from a week of baseline
first (the audit log already emits all three events; start with
log-based alerts before adding counters).
