"""Email normalization, masking, and disposable-domain helpers.

Conventions: pure functions, no Django imports (testable in isolation).
Gmail rule (also applied to googlemail.com): lowercase + trim, remove dots
from the local part, strip everything from "+" onward — so a.b@gmail.com,
ab@gmail.com and ab+x@gmail.com all normalize to ab@gmail.com.
"""

from django.conf import settings

GMAIL_DOMAINS = {"gmail.com", "googlemail.com"}

# Minimal built-in blocklist. Extend via settings.DISPOSABLE_EMAIL_DOMAINS.
# (Node equivalent of the `disposable-email-domains` package; kept dependency-free.)
BUILTIN_DISPOSABLE_DOMAINS = frozenset({
    "mailinator.com",
    "tempmail.com",
    "10minutemail.com",
    "guerrillamail.com",
    "yopmail.com",
    "trashmail.com",
})


def normalize_email(raw: str) -> str:
    """Lowercase + trim; Gmail dot/plus canonicalization. Never raises."""
    email = (raw or "").strip().lower()
    if "@" not in email:
        return email
    local, _, domain = email.partition("@")
    if domain in GMAIL_DOMAINS:
        local = local.split("+", 1)[0].replace(".", "")
    return f"{local}@{domain}"


def mask_email(email: str) -> str:
    """Mask for UI display, e.g. a***@gmail.com. Safe for short/odd inputs."""
    email = (email or "").strip()
    if "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


def blocked_disposable_domains() -> set:
    extra = getattr(settings, "DISPOSABLE_EMAIL_DOMAINS", []) or []
    return set(BUILTIN_DISPOSABLE_DOMAINS) | {str(d).strip().lower() for d in extra}


def is_disposable(email: str) -> bool:
    """True if the domain is a known disposable domain (config-gated)."""
    if not getattr(settings, "BLOCK_DISPOSABLE_EMAILS", True):
        return False
    domain = normalize_email(email).partition("@")[2]
    return domain in blocked_disposable_domains()
