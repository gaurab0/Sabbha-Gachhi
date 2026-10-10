"""Standalone Gmail SMTP connectivity check (no Django needed).

Loads backend/.env with python-dotenv, prints the effective config WITHOUT
revealing the password, then connects with smtplib directly:
  - port 465 or EMAIL_SECURE=true  -> SMTP_SSL (implicit SSL)
  - otherwise                      -> SMTP + starttls() (port 587)

Usage (from backend/):
    python scripts/smtp_check.py

Exit code 0 on LOGIN OK, 1 otherwise. Never prints EMAIL_PASS (only whether
it is set and its length, so quoted/padded values are visible as wrong).
"""

import os
import smtplib
import socket
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv is not installed (pip install python-dotenv).")
    sys.exit(1)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)


def _get(*names, default=""):
    for name in names:
        value = os.environ.get(name, "")
        if value:
            return value
    return default


def _strip_quotes(value: str) -> str:
    value = (value or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return value


def main() -> int:
    host = _get("EMAIL_HOST", "EMAIL_SMTP_HOST", default="smtp.gmail.com")
    port_raw = _get("EMAIL_PORT", "EMAIL_SMTP_PORT", default="587")
    user = _get("EMAIL_USER", "EMAIL_SMTP_USER")
    password = _strip_quotes(_get("EMAIL_PASS", "EMAIL_SMTP_PASSWORD"))
    secure_raw = os.environ.get("EMAIL_SECURE", "").strip().lower()

    try:
        port = int((port_raw or "587").strip())
    except ValueError:
        print(f"CONFIG ERROR: EMAIL_PORT={port_raw!r} is not a number.")
        return 1

    # Pairing rule: 465 <-> implicit SSL, 587 <-> STARTTLS.
    use_ssl = secure_raw in ("1", "true", "yes") or (not secure_raw and port == 465)
    if secure_raw and secure_raw not in ("1", "true", "yes", "0", "false", "no", "starttls", ""):
        print(f"CONFIG ERROR: EMAIL_SECURE={secure_raw!r} is not understood.")
        return 1
    if port == 465 and not use_ssl:
        print("CONFIG ERROR: port 465 requires EMAIL_SECURE=true (implicit SSL).")
        return 1
    if port == 587 and use_ssl:
        print("CONFIG ERROR: port 587 requires EMAIL_SECURE=false (STARTTLS).")
        return 1

    print(f"host={host} port={port} EMAIL_SECURE={secure_raw or '(unset)'}")
    print(f"user={user or '(missing)'}")
    print(f"password: {'set' if password else 'MISSING'}"
          + (f" (length {len(password)})" if password else ""))
    if not user or not password:
        print("CONFIG ERROR: EMAIL_USER and EMAIL_PASS must both be set.")
        return 1

    mode = "SMTP_SSL (implicit SSL)" if use_ssl else "SMTP + starttls() (STARTTLS)"
    print(f"mode={mode} timeout=20")
    try:
        if use_ssl:
            conn = smtplib.SMTP_SSL(host, port, timeout=20)
        else:
            conn = smtplib.SMTP(host, port, timeout=20)
        conn.set_debuglevel(1)
        conn.ehlo()
        if not use_ssl:
            conn.starttls()
            conn.ehlo()
        # Single-shot AUTH PLAIN (initial response) instead of login():
        # login() falls back through every advertised mechanism, so a 535 on
        # the first attempt gets buried under a later disconnect. One shot
        # gives one clean verdict.
        import base64

        token = base64.b64encode(f"\0{user}\0{password}".encode()).decode()
        code, msg = conn.docmd("AUTH PLAIN", token)
        if code == 235:
            print("LOGIN OK")
            conn.quit()
            return 0
        if code == 535:
            print(f"RESULT: SMTP error code 535: {msg!r}.")
            print("CLASSIFICATION: wrong credentials — Gmail needs an App Password "
                  "(Google Account -> Security -> 2-Step Verification ON -> "
                  "App passwords -> Mail), not the login password. Also confirm "
                  "the password was pasted with no spaces/quotes (16 chars).")
            return 1
        print(f"RESULT: unexpected AUTH reply {code}: {msg!r}.")
        return 1
    except smtplib.SMTPServerDisconnected as exc:
        print(f"RESULT: disconnect before/during login ({exc}).")
        print("CLASSIFICATION: port/secure mismatch or network/firewall/antivirus "
              "block. Verify 587+STARTTLS vs 465+SSL pairing, then try another network. "
              "Note: Gmail also drops the connection right AFTER a failed login, "
              "so check the transcript above for a 535 reply first.")
        return 1
    except smtplib.SMTPAuthenticationError as exc:
        print(f"RESULT: SMTP error code {exc.smtp_code}: {exc.smtp_error!r}.")
        print("CLASSIFICATION: wrong credentials — Gmail needs an App Password "
              "(Google Account -> Security -> 2-Step Verification ON -> "
              "App passwords -> Mail), not the login password.")
        return 1
    except (socket.timeout, TimeoutError) as exc:
        print(f"RESULT: timeout ({exc}).")
        print("CLASSIFICATION: network blocking SMTP. Try another network/VPN.")
        return 1
    except (OSError, smtplib.SMTPException) as exc:
        print(f"RESULT: connection/send error: {type(exc).__name__}: {exc}.")
        print("CLASSIFICATION: likely DNS/firewall. Check host spelling, "
              "outbound port access, and antivirus mail shields.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
