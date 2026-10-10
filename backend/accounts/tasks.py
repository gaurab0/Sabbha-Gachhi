"""Async verification-email delivery + expired-token cleanup.

Follows the existing registrations.tasks convention (shared_task, bind where
retry state matters). Views call ``.delay()`` and fall back to synchronous
send if the broker is down, so signup never hangs or 500s on Redis outage.
"""

import logging

from celery import shared_task

logger = logging.getLogger("accounts.mailer")


# ignore_result=True is load-bearing, not just tidy: with the result backend
# (Redis) down, apply_async would otherwise block ~2 min in the result-store
# reconnect loop even with retry=False (which only skips broker retries).
# Email delivery is fire-and-forget — no caller reads this result.
@shared_task(bind=True, max_retries=2, default_retry_delay=60, ignore_result=True)
def send_verification_email_task(self, payload: dict):
    """payload: {to_email, subject, text_body, html_body} (no secrets).

    At most 2 retries with exponential backoff (60s, 120s). Each attempt is
    logged exactly once by the mailer itself — nothing is logged here, so a
    failing send produces one ERROR line per attempt, not a cascade.
    (Note: Celery applies task-level `retry_backoff` only to autoretry, not
    to manual self.retry() calls, hence the explicit 60 * 2**retries here.)
    """
    from .mailer import VerificationEmail, send_verification_email

    message = VerificationEmail(**payload)
    ok = send_verification_email(message)
    if not ok:
        raise self.retry(countdown=60 * (2 ** self.request.retries))
    return {"sent": True, "to": message.to_email}


# Same load-bearing ignore_result=True as the email task: fire-and-forget,
# and a down Redis must fail the publish fast (views pass retry=False).
@shared_task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True)
def send_phone_otp_task(self, to_e164: str, code: str, channel: str = "sms"):
    """Custom-mode SMS dispatch. Payload holds the code only transiently in
    the broker; the DB never stores it (hash only)."""
    from .phone_normalize import mask_phone
    from .sms_providers import get_provider_for_e164

    provider = get_provider_for_e164(to_e164)
    if not provider.supports_channel(channel):
        channel = "sms"  # degrade to SMS rather than fail the verify flow
    result = provider.send_otp(to_e164, code, channel=channel)
    if not result.ok:
        # One retry on transient provider errors; then the view's generic
        # error path takes over (details stay server-side).
        raise self.retry(countdown=60)
    logger.info(
        "phone otp dispatched to=%s provider=%s channel=%s",
        mask_phone(to_e164),
        provider.name,
        channel,
    )
    return {"sent": True}


@shared_task
def cleanup_expired_verification_tokens():
    """Delete long-expired token/send-log rows. Wire to Celery beat daily.

    (django-mongodb-backend has no native TTL-index support, so expiry is
    enforced in queries via `expires_at` and old rows are pruned here.)
    """
    from datetime import timedelta

    from django.utils import timezone

    from .models import EmailVerificationToken, VerificationSendLog

    cutoff = timezone.now() - timedelta(days=30)
    tokens, _ = EmailVerificationToken.objects.filter(expires_at__lt=cutoff).delete()
    logs, _ = VerificationSendLog.objects.filter(created_at__lt=cutoff).delete()
    logger.info("verification cleanup: %s tokens, %s send-logs pruned", tokens, logs)
    return {"tokens": tokens, "send_logs": logs}
