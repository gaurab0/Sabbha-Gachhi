"""
Notification service for match events.

Pluggable — swap the backend implementation for email, push,
in-app, or any other channel without touching the matching engine.
"""

from __future__ import annotations

import logging

from django.core.mail import send_mail
from django.conf import settings

from .models import Registration

logger = logging.getLogger(__name__)


def send_match_notification(from_registration, to_registration):
    """
    Trigger a notification to the user of `to_registration` that
    they have a new match from `from_registration`.

    Currently uses the console email backend (configurable via
    MAILERS in settings.py). Swap to SendGrid / Firebase / etc.
    by replacing this function's body.
    """
    to_email = to_registration.owner.email
    from_name = from_registration.candidate_full_name
    ref = from_registration.reference

    subject = f"New match: {from_name} (ref: {ref})"
    message = (
        f"A new match has been proposed for your registration.\n\n"
        f"Candidate: {from_name}\n"
        f"Reference: {ref}\n\n"
        f"Log in to review this match."
    )

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            fail_silently=False,
        )
        logger.info(
            "Match notification sent to %s for registration %s",
            to_email, ref,
        )
    except Exception as e:
        logger.error(
            "Failed to send match notification to %s: %s", to_email, e,
        )


def notify_both_users(registration_a, registration_b, match_score: float):
    """
    Notify both users of a new match. Called by the matching engine
    or Celery task after a match is persisted.
    """
    send_match_notification(registration_a, registration_b)
    send_match_notification(registration_b, registration_a)


def notify_admin_verification(registration: Registration):
    """
    Notify admin staff when a registration is verified and the
    matching engine has been triggered.
    """
    logger.info(
        "Matching engine triggered for verified registration %s (%s)",
        registration.reference, registration.candidate_full_name,
    )