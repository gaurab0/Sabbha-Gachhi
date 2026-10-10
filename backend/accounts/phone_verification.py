"""Phone-OTP issue/consume logic (phase 2), mirroring verification.py.

Two modes (PHONE_VERIFICATION_PROVIDER_MODE):
- "custom" (default): we generate a 6-digit code with secrets, store only its
  SHA-256 hash in the shared EmailVerificationToken table (type=phone_otp),
  and send it through the routed SMS gateway. Lifecycle (expiry 5 min,
  single-use, invalidate-previous, 5 wrong attempts -> lock) matches email OTP.
- "managed" (Twilio Verify style): the provider sends AND checks codes; we
  store no OTP material — only an audit marker row (empty hash, provider sid
  in `channel`... stored as channel="managed") so send/attempt accounting
  stays in one place. Attempt limits are then enforced provider-side.

OTP rows are bound to the exact E.164 in `target_normalized`; changing the
number strands old codes (they no longer match the pending number).
"""

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import EmailVerificationToken
from .phone_normalize import mask_phone
from .sms_providers import get_provider_for_e164, provider_mode
from .verification import hash_secret, record_failed_attempt, secrets_equal

audit = logging.getLogger("accounts.audit")

PHONE_TYPE = EmailVerificationToken.TYPE_PHONE_OTP
PHONE_OTP_LENGTH = 6


def phone_otp_expiry() -> timedelta:
    return timedelta(minutes=int(getattr(settings, "PHONE_OTP_EXPIRY_MINUTES", 5)))


def phone_otp_max_attempts() -> int:
    return int(getattr(settings, "PHONE_OTP_MAX_ATTEMPTS", 5))


def issue_phone_code(user, e164: str, channel: str = "sms"):
    """Create (+ send) a phone OTP. Returns (row|None, provider_result).

    In managed mode there is no local raw secret (returns None) — the
    provider owns the code. In custom mode the caller dispatches `raw`
    through _dispatch_sms (kept separate so tests can capture it).
    """
    EmailVerificationToken.objects.filter(
        user=user, type=PHONE_TYPE, used_at__isnull=True
    ).update(used_at=timezone.now())

    if provider_mode() == "managed":
        provider = get_provider_for_e164(e164)
        result = provider.send_otp(e164, None, channel=channel)
        row = None
        if result.ok:
            row = EmailVerificationToken.objects.create(
                user=user,
                type=PHONE_TYPE,
                token_hash="",  # managed: no secret material stored, ever
                target=e164,
                target_normalized=e164,
                expires_at=timezone.now() + phone_otp_expiry(),
                channel=f"managed:{provider.name}",
            )
        audit.info(
            "phone_otp_sent user_id=%s to=%s provider=%s channel=%s ok=%s",
            user.pk,
            mask_phone(e164),
            provider.name,
            channel,
            result.ok,
        )
        return row, result

    raw = f"{secrets.randbelow(10 ** PHONE_OTP_LENGTH):0{PHONE_OTP_LENGTH}d}"
    row = EmailVerificationToken.objects.create(
        user=user,
        type=PHONE_TYPE,
        token_hash=hash_secret(raw),
        target=e164,
        target_normalized=e164,
        expires_at=timezone.now() + phone_otp_expiry(),
        channel=channel,
    )
    return row, raw


def find_phone_token(user, code: str):
    """Match a custom-mode code. Returns (row|None, reason)."""
    now = timezone.now()
    candidates = (
        EmailVerificationToken.objects.filter(user=user, type=PHONE_TYPE, used_at__isnull=True)
        .exclude(token_hash="")
        .order_by("-created_at")
        .all()
    )
    digest = hash_secret(code or "")
    for token in candidates:
        if secrets_equal(token.token_hash, digest):
            if token.expires_at <= now:
                token.mark_used()
                return None, "expired"
            return token, ""
    return None, "invalid"


def latest_usable_phone_token(user):
    return (
        EmailVerificationToken.objects.filter(user=user, type=PHONE_TYPE, used_at__isnull=True)
        .exclude(token_hash="")
        .order_by("-created_at")
        .first()
    )


def check_managed_code(user, e164: str, code: str):
    """Provider-side verdict for managed mode. Returns True/False."""
    provider = get_provider_for_e164(e164)
    verdict = provider.check_otp(e164, code)
    audit.info(
        "phone_otp_checked user_id=%s to=%s provider=%s ok=%s",
        user.pk,
        mask_phone(e164),
        provider.name,
        verdict,
    )
    return bool(verdict)
