"""OTP email smoke test against a running dev server (live HTTP, real SMTP).

Prerequisites (do these first, in order):
  1. flip EMAIL_VERIFICATION_METHOD=otp in backend/.env + FULL server restart
  2. dev server running (python manage.py runserver), MongoDB up
  3. use an UNVERIFIED account (sign up fresh in the app if needed)

Usage (PowerShell):
  $env:SABHA_BASE_URL = "http://127.0.0.1:8000"
  $env:SABHA_EMAIL = "you@gmail.com"
  $env:SABHA_PASSWORD = "your-password"
  .\\backend\\venv\\Scripts\\python.exe backend/scripts/smoke_otp.py

Security: credentials come only from the environment (never committed,
never printed). Tokens and OTP codes from responses are never printed —
only status codes and the safe fields below (detail/code/retry_after).

Exit code 0 = all steps PASS, 1 = anything failed.
"""

import os
import sys
import time

import requests

BASE = os.environ.get("SABHA_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
EMAIL = os.environ.get("SABHA_EMAIL", "")
PASSWORD = os.environ.get("SABHA_PASSWORD", "")
TIMEOUT = 15

results: list[tuple[str, bool, str]] = []


def report(step: str, ok: bool, note: str = "") -> None:
    """One PASS/FAIL line per step. `note` must never contain secrets/tokens."""
    results.append((step, ok, note))
    print(f"[{'PASS' if ok else 'FAIL'}] {step}" + (f" — {note}" if note else ""))


def api(method: str, path: str, token: str | None = None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.request(
        method, BASE + path, headers=headers, timeout=TIMEOUT, **kwargs
    )


def main() -> int:
    if not EMAIL or not PASSWORD:
        print("Set SABHA_EMAIL and SABHA_PASSWORD first (see docstring).")
        return 2

    # -- Step 1: login + method flag -------------------------------------
    try:
        r = api("POST", "/api/auth/login/", json={"email": EMAIL, "password": PASSWORD})
    except requests.RequestException as exc:
        report("1. login", False, f"no response (is the server running?): {exc}")
        return finish()
    body = safe_json(r)
    if r.status_code != 200 or "access" not in body:
        report("1. login", False, f"status={r.status_code}")
        return finish()
    token = body["access"]
    report("1. login", True, "got access token (not shown)")

    me = safe_json(api("GET", "/api/auth/me/", token=token))
    if me.get("verification_method") != "otp":
        report(
            "1. method is otp",
            False,
            f"server reports {me.get('verification_method')!r}; "
            "flip EMAIL_VERIFICATION_METHOD=otp + restart",
        )
        return finish()
    report("1. method is otp", True)
    if me.get("email_verified"):
        report(
            "prerequisite",
            False,
            "account already verified — sign up a fresh one and re-run",
        )
        return finish()

    # -- Step 2: resend 200, immediate resend 429 -------------------------
    # NOTE: if you hammered resend manually just before running this, the
    # first call below can itself 429 on the 60s cooldown — the helper
    # waits it out once, then proceeds.
    r = resend_expect_ok(token)
    if r is None:
        return finish()
    report("2. resend 200", True, f"detail={safe_json(r).get('detail')!r}")
    r = api("POST", "/api/auth/resend-verification/", token=token,
            json={"channel": "email"})
    body = safe_json(r)
    ok = r.status_code == 429
    report("2. immediate resend 429", ok,
           f"status={r.status_code} code={body.get('code')!r}")

    # -- Step 3: one wrong code (attempt 1 of 5) -------------------------
    r = api("POST", "/api/auth/verify-email/", token=token,
            json={"code": "000000"})
    report("3. wrong code 400 invalid",
           (r.status_code, safe_json(r).get("code")) == (400, "invalid"),
           f"status={r.status_code}")

    # -- Step 4: five more wrong codes (attempts 2-6): the 5th overall
    # locks the row (too_many_attempts), the 6th finds nothing left.
    seq = []
    for _ in range(5):
        rr = api("POST", "/api/auth/verify-email/", token=token,
                 json={"code": "000000"})
        seq.append((rr.status_code, safe_json(rr).get("code")))
    report("4. lockout sequence",
           [s for _, s in seq] == ["invalid", "invalid", "invalid",
                                   "too_many_attempts", "not_found"],
           f"codes={[s for _, s in seq]}")

    # -- Step 5: fresh resend (cooldown-sensitive) + real inbox code -------
    # NOTE: this resend needs the 60s cooldown from step 2 to have lapsed;
    # the helper below waits out a 429 automatically.
    r = resend_expect_ok(token)
    if r is None:
        return finish()
    try:
        real_code = input("Paste the 6-digit code from your inbox: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted at inbox prompt.")
        return finish()
    if len(real_code) != 6 or not real_code.isdigit():
        report("5. real code format", False, "expected 6 digits")
        return finish()
    r = api("POST", "/api/auth/verify-email/", token=token,
            json={"code": real_code})
    report("5. verify real code 200", r.status_code == 200,
           f"status={r.status_code} detail={safe_json(r).get('detail')!r}")
    me = safe_json(api("GET", "/api/auth/me/", token=token))
    report("5. /me/ shows verified", me.get("email_verified") is True,
           f"email_verified={me.get('email_verified')!r}")

    # -- Step 6: reuse ------------------------------------------------------
    r = api("POST", "/api/auth/verify-email/", token=token,
            json={"code": real_code})
    report("6. reuse is not_found",
           (r.status_code, safe_json(r).get("code")) == (400, "not_found"),
           f"status={r.status_code}")

    # -- Step 7: gating ------------------------------------------------------
    # Fresh signup is guaranteed unverified and needs no inbox access, so
    # any valid address works. NOTE: not a plus-address of the main email:
    # Gmail folding would normalize it onto the (verified) main account.
    fresh_email = f"smoketest{int(time.time())}@example.com"
    r = api("POST", "/api/auth/signup/",
            json={"email": fresh_email, "password": "SmokePass123!"})
    body = safe_json(r)
    if r.status_code != 201 or "access" not in body:
        report("7. second signup", False, f"status={r.status_code}")
        return finish()
    tok2 = body["access"]
    r = api("POST", "/api/registrations/", token=tok2, json={})
    report("7. unverified blocked 403",
           (r.status_code, safe_json(r).get("code")) == (403, "email_not_verified"),
           f"status={r.status_code}")
    r = api("POST", "/api/registrations/", token=token, json={})
    # Verified account passes the gate; empty body fails serializer
    # validation (400) — which is exactly the proof (a 403 would mean gated).
    report("7. verified passes gate", r.status_code == 400,
           f"status={r.status_code} (400 validation, not 403)")

    return finish()


def safe_json(response) -> dict:
    """Parse JSON defensively; never print it (may hold tokens)."""
    try:
        data = response.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def resend_expect_ok(token: str):
    """POST resend; on 429-cooldown, wait out retry_after once and retry.

    Returns the 200 response, or None (already reported FAIL).
    """
    r = api("POST", "/api/auth/resend-verification/", token=token,
            json={"channel": "email"})
    if r.status_code == 200:
        return r
    if r.status_code == 429:
        wait = safe_json(r).get("retry_after_seconds") or 60
        wait = min(int(wait) + 2, 120)
        print(f"  (cooldown active — waiting {wait}s, then one retry)")
        time.sleep(wait)
        r = api("POST", "/api/auth/resend-verification/", token=token,
                json={"channel": "email"})
        if r.status_code == 200:
            return r
    report("resend 200", False,
           f"status={r.status_code} code={safe_json(r).get('code')!r}")
    return None


def finish() -> int:
    failed = [name for name, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} steps passed.")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
