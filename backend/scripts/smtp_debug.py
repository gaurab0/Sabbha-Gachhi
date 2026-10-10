"""Standalone SMTP debug check using the same env vars as Django settings.

Run from the repo root:
    backend\\venv\\Scripts\\python.exe backend\\scripts\\smtp_debug.py

The SMTP transcript is printed with smtplib debug output, but the password is
never printed. Gmail requires a 16-character App Password with spaces removed.
"""

from __future__ import annotations

import os
import smtplib
import socket
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv is not installed.")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env", override=False)


def env_string(*names: str, default: str = "") -> str:
    for name in names:
        if name in os.environ:
            value = (os.environ.get(name) or "").strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1].strip()
            return value
    return default


def env_bool(name: str, default: bool | None = None) -> bool | None:
    if name not in os.environ:
        return default
    value = (os.environ.get(name) or "").strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off", "", "starttls"):
        return False
    raise ValueError(f"{name}={value!r} is not understood")


def clean_password(raw: str) -> str:
    value = (raw or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return "".join(value.split())


def main() -> int:
    host = env_string("EMAIL_HOST", "EMAIL_SMTP_HOST", default="smtp.gmail.com")
    user = env_string("EMAIL_HOST_USER", "EMAIL_USER", "EMAIL_SMTP_USER")
    password = clean_password(
        os.environ.get("EMAIL_HOST_PASSWORD")
        or os.environ.get("EMAIL_PASS")
        or os.environ.get("EMAIL_SMTP_PASSWORD", "")
    )
    use_tls = env_bool("EMAIL_USE_TLS", None)
    use_ssl = env_bool("EMAIL_USE_SSL", None)
    if use_tls is None and use_ssl is None and "EMAIL_SECURE" in os.environ:
        secure = env_bool("EMAIL_SECURE", False)
        use_ssl = bool(secure)
        use_tls = not use_ssl
    elif use_tls is None and use_ssl is None:
        use_tls = env_bool("EMAIL_SMTP_TLS", True)
        use_ssl = False
    else:
        use_tls = bool(use_tls)
        use_ssl = bool(use_ssl)

    if use_tls and use_ssl:
        print("CONFIG ERROR: EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be true.")
        return 1

    default_port = 465 if use_ssl else 587
    try:
        port = int(env_string("EMAIL_PORT", "EMAIL_SMTP_PORT", default=str(default_port)))
        timeout = int(env_string("EMAIL_TIMEOUT", default="10"))
    except ValueError as exc:
        print(f"CONFIG ERROR: {exc}")
        return 1

    print(f"host={host} port={port} use_tls={use_tls} use_ssl={use_ssl} timeout={timeout}")
    print(f"user={user!r}")
    print(f"password=set length={len(password)}" if password else "password=MISSING")
    if not user or not password:
        print("CONFIG ERROR: EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are required.")
        return 1
    if port == 587 and use_ssl:
        print("CONFIG ERROR: port 587 requires STARTTLS, not implicit SSL.")
        return 1
    if port == 465 and not use_ssl:
        print("CONFIG ERROR: port 465 requires implicit SSL.")
        return 1

    try:
        if use_ssl:
            conn = smtplib.SMTP_SSL(host, port, timeout=timeout)
        else:
            conn = smtplib.SMTP(host, port, timeout=timeout)
        conn.set_debuglevel(1)
        conn.ehlo()
        if use_tls:
            conn.starttls()
            conn.ehlo()
        conn.login(user, password)
        print("LOGIN OK")
        conn.quit()
        return 0
    except smtplib.SMTPAuthenticationError as exc:
        print(f"RESULT: SMTP auth error {exc.smtp_code}: {exc.smtp_error!r}")
        print("CLASSIFICATION: wrong username/password; Gmail needs an App Password.")
        return 1
    except smtplib.SMTPServerDisconnected as exc:
        print(f"RESULT: server disconnected during SMTP exchange: {exc}")
        print(
            "CLASSIFICATION: if this happens right after AUTH, the provider is "
            "rejecting or blocking the login. For Gmail, generate a new App "
            "Password and remove spaces."
        )
        return 1
    except (socket.timeout, TimeoutError) as exc:
        print(f"RESULT: timeout: {exc}")
        print("CLASSIFICATION: network/firewall/antivirus may be blocking SMTP.")
        return 1
    except (OSError, smtplib.SMTPException) as exc:
        print(f"RESULT: SMTP/network error: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
