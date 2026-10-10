"""CAPTCHA hook (Cloudflare Turnstile / reCAPTCHA), behind a config flag.

Default OFF: `verify_captcha` returns True without network calls. When
`CAPTCHA_REQUIRED=True`, a verifier callable must be configured via
`CAPTCHA_VERIFIER` (dotted path) — otherwise verification fails closed.
"""

import logging

from django.conf import settings

logger = logging.getLogger("accounts.audit")


def captcha_required() -> bool:
    return bool(getattr(settings, "CAPTCHA_REQUIRED", False))


def verify_captcha(token: str | None, remote_ip: str | None = None) -> bool:
    if not captcha_required():
        return True
    if not token:
        return False
    verifier_path = getattr(settings, "CAPTCHA_VERIFIER", None)
    if not verifier_path:
        logger.error("CAPTCHA required but no CAPTCHA_VERIFIER configured")
        return False
    from django.utils.module_loading import import_string

    try:
        return bool(import_string(verifier_path)(token, remote_ip))
    except Exception as exc:
        logger.error("CAPTCHA verifier failed: %s", exc)
        return False
