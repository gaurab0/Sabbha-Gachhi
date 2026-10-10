"""Verification-token issue/consume logic shared by the views.

- Raw secrets (link token / OTP code) are generated with `secrets` and only
  ever leave via email. The DB holds SHA-256 hex digests, compared with
  hmac.compare_digest (constant-time).
- Tokens are single-use (`used_at`). Issuing a new token marks all previous
  unused tokens for the same user+type as used (invalidated).
- OTP: 10-min expiry, max 5 wrong attempts, then invalidated.
- Link: 60-min expiry (both overridable via settings).
Never use JWT for verification tokens.
"""

import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .email_normalize import normalize_email
from .models import EmailVerificationToken

audit = logging.getLogger("accounts.audit")

LINK_TOKEN_BYTES = 32  # -> 64-char hex
OTP_LENGTH = 6
OTP_MAX_ATTEMPTS = 5


def verification_method() -> str:
    method = getattr(settings, "EMAIL_VERIFICATION_METHOD", "link")
    return method if method in ("link", "otp") else "link"


def link_expiry() -> timedelta:
    return timedelta(minutes=int(getattr(settings, "EMAIL_LINK_EXPIRY_MINUTES", 60)))


def otp_expiry() -> timedelta:
    return timedelta(minutes=int(getattr(settings, "EMAIL_OTP_EXPIRY_MINUTES", 10)))


def hash_secret(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def secrets_equal(a_hex: str, b_hex: str) -> bool:
    """Constant-time digest comparison (length-mismatch safe)."""
    try:
        return hmac.compare_digest(a_hex or "", b_hex or "")
    except TypeError:
        return False


def _token_type() -> str:
    return (
        EmailVerificationToken.TYPE_EMAIL_LINK
        if verification_method() == "link"
        else EmailVerificationToken.TYPE_EMAIL_OTP
    )


def issue_token(user, target_email: str) -> tuple[EmailVerificationToken, str]:
    """Create a fresh token, invalidate older unused ones, return (row, raw)."""
    token_type = _token_type()
    if token_type == EmailVerificationToken.TYPE_EMAIL_LINK:
        raw = secrets.token_hex(LINK_TOKEN_BYTES)
        expires_at = timezone.now() + link_expiry()
    else:
        raw = f"{secrets.randbelow(10 ** OTP_LENGTH):0{OTP_LENGTH}d}"
        expires_at = timezone.now() + otp_expiry()

    EmailVerificationToken.objects.filter(
        user=user, type=token_type, used_at__isnull=True
    ).update(used_at=timezone.now())

    row = EmailVerificationToken.objects.create(
        user=user,
        type=token_type,
        token_hash=hash_secret(raw),
        target=target_email,
        target_normalized=normalize_email(target_email),
        expires_at=expires_at,
    )
    return row, raw


def find_usable_token(user, raw: str, token_type: str):
    """Return the usable token row matching `raw`, else (None, reason)."""
    now = timezone.now()
    candidates = (
        EmailVerificationToken.objects.filter(user=user, type=token_type, used_at__isnull=True)
        .order_by("-created_at")
        .all()
    )
    digest = hash_secret(raw or "")
    for token in candidates:
        if secrets_equal(token.token_hash, digest):
            if token.expires_at <= now:
                token.mark_used()
                return None, "expired"
            return token, ""
    return None, "invalid"


def record_failed_attempt(token: EmailVerificationToken) -> bool:
    """Increment attempts; invalidate at the cap. Returns True if now locked."""
    token.attempts = (token.attempts or 0) + 1
    if token.attempts >= OTP_MAX_ATTEMPTS:
        token.used_at = timezone.now()
        token.save(update_fields=["attempts", "used_at"])
        return True
    token.save(update_fields=["attempts"])
    return False


# ---------------------------------------------------------------------------
# Channel-agnostic OTP service (email today, phone later).
#
# Phone is added later WITHOUT touching this logic: implement a BaseSender
# (see sms_providers.SmsProvider for the established shape), register it as
#   SENDERS["phone"] = SmsSender()
# and add a thin POST /api/auth/verify-phone/ view calling verify_code with
# channel="phone" (plus phonenumbers validation + provider settings).
# ---------------------------------------------------------------------------

import enum
from abc import ABC, abstractmethod

from django.db import transaction
from django.db.models import F


class VerificationResult(enum.Enum):
    OK = "ok"
    INVALID = "invalid"
    EXPIRED = "expired"
    TOO_MANY_ATTEMPTS = "too_many_attempts"
    NOT_FOUND = "not_found"
    ALREADY_VERIFIED = "already_verified"


class BaseSender(ABC):
    """Channel sender interface. Implementations must never raise: return
    True on accepted-for-delivery, False on failure (caller maps to 503)."""

    channel: str = ""

    @abstractmethod
    def send(self, *, user, target: str, code: str) -> bool:
        """Deliver `code` to `target`. Return True if accepted, False if not."""
        raise NotImplementedError


class EmailSender(BaseSender):
    """Email channel: builds the OTP message via mailer.py and dispatches it
    through the existing provider pattern (console in dev, SMTP in prod)."""

    channel = "email"

    def send(self, *, user, target: str, code: str) -> bool:
        from .mailer import build_otp_email, send_verification_email

        minutes = otp_expiry_minutes()
        message = build_otp_email(target, code, minutes)
        # Never raises (mailer contract); DEBUG-only secret logging inside.
        return send_verification_email(message, log_secret=code, user_id=user.pk)


SENDERS: dict[str, BaseSender] = {
    "email": EmailSender(),
    # TODO(phone): register SENDERS["phone"] = SmsSender() here. The sender
    # should wrap sms_providers.get_provider_for_e164(...).send_otp(...) and
    # return result.ok. No change to issue_code/verify_code is needed.
}


def register_sender(sender: BaseSender) -> None:
    """Add (or replace, e.g. in tests) the sender for sender.channel."""
    SENDERS[sender.channel] = sender


def otp_expiry_minutes() -> int:
    return int(getattr(settings, "OTP_EXPIRY_MINUTES", 10))


def otp_max_attempts() -> int:
    return int(getattr(settings, "OTP_MAX_ATTEMPTS", 5))


def otp_code_length() -> int:
    return 6


def hash_code(raw: str) -> str:
    """HMAC-SHA256 with SECRET_KEY. Keyed hashing means a DB read alone
    never lets an attacker verify guesses offline against a static digest."""
    key = settings.SECRET_KEY.encode("utf-8")
    return hmac.new(key, (raw or "").encode("utf-8"), hashlib.sha256).hexdigest()


def _active_code_qs(user, channel: str, target: str):
    from .models import VerificationCode

    return VerificationCode.objects.filter(
        user=user, channel=channel, target=target, consumed_at__isnull=True
    )


def issue_code(user, channel: str, target: str) -> bool:
    """Generate, hash, save, and dispatch an OTP. Returns True iff the
    sender accepted it. Exactly one active code per (user, channel, target):
    any previous active code is consumed first.

    `target` must already be normalized by the caller for email
    (normalize_email) / E.164 for phone — it is stored and matched exactly.
    The raw code is a zero-padded string and is NEVER converted to int, so
    leading zeros (e.g. "012345") survive end to end.
    """
    from .models import VerificationCode

    sender = SENDERS.get(channel)
    if sender is None:
        raise ValueError(f"No sender registered for channel {channel!r}")
    if channel == VerificationCode.CHANNEL_EMAIL:
        target = normalize_email(target)

    now = timezone.now()
    length = otp_code_length()
    raw = f"{secrets.randbelow(10 ** length):0{length}d}"

    with transaction.atomic():
        # Single atomic UPDATE invalidates any previous active code, so at
        # most one active code per (user, channel, target) can exist.
        # (atomic()/select_for_update() below are real on Postgres; on this
        # MongoDB backend they are documented no-ops, so the F()-based
        # counter increment is what actually protects attempts counting.)
        _active_code_qs(user, channel, target).update(consumed_at=now)
        row = VerificationCode.objects.create(
            user=user,
            channel=channel,
            target=target,
            code_hash=hash_code(raw),
            expires_at=now + timedelta(minutes=otp_expiry_minutes()),
        )
        sent = sender.send(user=user, target=target, code=raw)
        if sent:
            row.last_sent_at = now
            row.save(update_fields=["last_sent_at"])
        else:
            # Don't leave an unsent code active: it would burn the cooldown
            # window and confuse "request a new code" retries.
            row.mark_consumed()
        audit.info(
            "code_issued user_id=%s channel=%s sent=%s",
            getattr(user, "pk", None),
            channel,
            sent,
        )
        return sent


def verify_code(user, channel: str, target: str, code: str,
                on_verified=None) -> VerificationResult:
    """Check an OTP. Never raises for bad input; returns a VerificationResult.

    `on_verified` (optional) runs inside the same atomic block after a
    successful match — the view passes a closure that flips the verified
    flag, keeping lifecycle + domain effect together without the service
    knowing channel specifics.
    """
    from .models import VerificationCode

    if channel == VerificationCode.CHANNEL_EMAIL:
        target = normalize_email(target)

    with transaction.atomic():
        row = (
            _active_code_qs(user, channel, target)
            .select_for_update()
            .order_by("-created_at")
            .first()
        )
        if row is None:
            return VerificationResult.NOT_FOUND
        if row.expires_at <= timezone.now():
            row.mark_consumed()
            return VerificationResult.EXPIRED
        # Reserve one attempt with a SINGLE conditional UPDATE: the counter
        # moves only while it is still below the cap. Concurrent requests
        # race on this one statement instead of on a read value, so exactly
        # one of them can claim the last remaining slot — the losers match
        # zero rows. (select_for_update() above is real on Postgres and
        # ignored on this MongoDB backend; the UPDATE below is atomic on
        # both, which is what actually closes the race.)
        max_attempts = otp_max_attempts()
        reserved = (
            VerificationCode.objects.filter(
                pk=row.pk,
                consumed_at__isnull=True,
                attempts__lt=max_attempts,
            ).update(attempts=F("attempts") + 1)
        )
        if not reserved:
            # No slot left, or the row vanished concurrently (consumed by a
            # resend elsewhere, or a parallel success). Re-read to tell which.
            row.refresh_from_db()
            if row.consumed_at is not None:
                return VerificationResult.NOT_FOUND
            return VerificationResult.TOO_MANY_ATTEMPTS
        if secrets_equal(row.code_hash, hash_code(code or "")):
            # Consume conditionally too: a twin request may have consumed
            # this row first, and single-use means single-use.
            consumed = (
                VerificationCode.objects.filter(
                    pk=row.pk, consumed_at__isnull=True
                ).update(consumed_at=timezone.now())
            )
            if not consumed:
                return VerificationResult.NOT_FOUND
            row.refresh_from_db()
            if on_verified is not None:
                on_verified()
            return VerificationResult.OK
        # Wrong guess, but the attempt was already counted by the
        # reservation above. Re-read to see whether it filled the cap.
        row.refresh_from_db(fields=["attempts"])
        if (row.attempts or 0) >= max_attempts:
            row.mark_consumed()
            return VerificationResult.TOO_MANY_ATTEMPTS
        return VerificationResult.INVALID
