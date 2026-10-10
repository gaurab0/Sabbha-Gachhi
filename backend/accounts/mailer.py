"""Pluggable mailer for verification emails.

Provider abstraction: anything exposing ``send_mail(subject, text, html,
from_email, to)`` can be swapped in via settings.EMAIL_VERIFICATION_PROVIDER
(callable path or instance). New providers SHOULD also accept ``headers``
(dict) and ``reply_to`` (list); if they don't, we fall back to the legacy
call shape. Default uses Django's EmailMultiAlternatives (honours the
MAILERS setting — console backend in dev, SMTP in prod).

No-reply behaviour: every message carries Reply-To: noreply@…, plus the
Auto-Submitted / X-Auto-Response-Suppress / Precedence: bulk headers, and a
"do not reply" footer. Note no email system can technically BLOCK replies —
these headers plus an unmonitored (bounce or blackhole) noreply mailbox are
the standard way to discourage them. See README "Email deliverability".

Security notes:
- Only the raw token/code leaves the process via email; hashes stay in the DB.
- Provider failures are logged server-side; callers get True/False so the API
  never leaks SMTP details to clients.
- In DEBUG, the link/OTP is logged to console (dev convenience). In
  production (DEBUG=False) the raw secret is NEVER logged.
"""

import logging
import smtplib
import socket
from dataclasses import dataclass

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.module_loading import import_string

logger = logging.getLogger("accounts.mailer")
audit = logging.getLogger("accounts.audit")

APP_NAME = "Sabha Gachhi"

# Standard "don't reply to automated mail" headers (RFC 3834 / convention).
# Applied on the default path; forwarded to custom providers when accepted.
NOREPLY_HEADERS = {
    "Auto-Submitted": "auto-generated",
    "X-Auto-Response-Suppress": "All",
    "Precedence": "bulk",
}

FOOTER_TEXT = "\n\n--\nThis is an automated message. Please do not reply."
FOOTER_HTML = "<p style='color:#888;font-size:12px'>This is an automated message. Please do not reply.</p>"


@dataclass
class VerificationEmail:
    to_email: str
    subject: str
    text_body: str
    html_body: str


def build_link_email(to_email: str, link: str, expiry_minutes: int) -> VerificationEmail:
    subject = f"Verify your {APP_NAME} email"
    text_body = (
        f"Namaste,\n\nPlease verify your email address for {APP_NAME} by opening "
        f"this link (valid for {expiry_minutes} minutes):\n\n{link}\n\n"
        "If you didn't sign up, you can safely ignore this email.\n"
        + FOOTER_TEXT
    )
    html_body = (
        f"<p>Namaste,</p><p>Please verify your email address for {APP_NAME}.</p>"
        f'<p><a href="{link}">Verify my email</a> '
        f"(valid for {expiry_minutes} minutes)</p>"
        f"<p>If the button doesn't work, paste this link:<br><code>{link}</code></p>"
        "<p>If you didn't sign up, you can safely ignore this email.</p>"
        + FOOTER_HTML
    )
    return VerificationEmail(to_email, subject, text_body, html_body)


def build_otp_email(to_email: str, code: str, expiry_minutes: int) -> VerificationEmail:
    subject = f"Your {APP_NAME} verification code"
    text_body = (
        f"Namaste,\n\nYour {APP_NAME} verification code is: {code}\n\n"
        f"It expires in {expiry_minutes} minutes. "
        "If you didn't sign up, you can safely ignore this email.\n"
        + FOOTER_TEXT
    )
    html_body = (
        f"<p>Namaste,</p><p>Your {APP_NAME} verification code is:</p>"
        f"<p style='font-size:28px;letter-spacing:6px'><strong>{code}</strong></p>"
        f"<p>It expires in {expiry_minutes} minutes.</p>"
        "<p>If you didn't sign up, you can safely ignore this email.</p>"
        + FOOTER_HTML
    )
    return VerificationEmail(to_email, subject, text_body, html_body)


def _resolve_sender():
    """Return a send_mail-compatible callable from settings (provider swap)."""
    provider = getattr(settings, "EMAIL_VERIFICATION_PROVIDER", None)
    if provider is None:
        return None  # default: django.core.mail.send_mail
    return import_string(provider) if isinstance(provider, str) else provider


def noreply_headers() -> dict:
    """Headers discouraging replies to automated mail (see module docstring)."""
    return {
        "Reply-To": settings.DEFAULT_FROM_EMAIL,
        **NOREPLY_HEADERS,
    }


def send_verification_email(
    message: VerificationEmail,
    *,
    log_secret: str | None = None,
    user_id=None,
) -> bool:
    """Send one verification email. Never raises; returns success flag."""
    if settings.DEBUG and log_secret:
        # Dev convenience only — raw secrets are never logged in production.
        logger.info("DEV verification secret for %s: %s", message.to_email, log_secret)
    sender = _resolve_sender()
    try:
        if sender is None:
            email = EmailMultiAlternatives(
                subject=message.subject,
                body=message.text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[message.to_email],
                headers=noreply_headers(),
            )
            email.attach_alternative(message.html_body, "text/html")
            email.send(fail_silently=False)
        else:
            try:
                # Preferred: providers that accept no-reply metadata.
                sender(
                    subject=message.subject,
                    text_body=message.text_body,
                    html_body=message.html_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to_email=message.to_email,
                    headers=noreply_headers(),
                    reply_to=[settings.DEFAULT_FROM_EMAIL],
                )
            except TypeError:
                # Backward compat: legacy providers with the original
                # (subject, text_body, html_body, from_email, to_email) shape.
                sender(
                    subject=message.subject,
                    text_body=message.text_body,
                    html_body=message.html_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to_email=message.to_email,
                )
        # Logged ONLY here, after a confirmed send — never at dispatch time,
        # so "verification_sent" in the logs always means delivered to SMTP.
        audit.info("verification_sent to=%s", message.to_email)
        return True
    except smtplib.SMTPAuthenticationError as exc:
        # Wrong username/password (Gmail 535 = App Password required, not the
        # login password). Retrying never helps; fix EMAIL_PASS. The server
        # message carries no secrets, safe to log.
        logger.exception("Verification email auth failed user_id=%s", user_id or "-")
        return False
    except smtplib.SMTPServerDisconnected as exc:
        # Server dropped the connection (Gmail does this right AFTER a failed
        # login too — check for a preceding 535 before blaming the network).
        logger.exception("Verification email disconnected user_id=%s", user_id or "-")
        return False
    except smtplib.SMTPConnectError as exc:
        logger.exception("Verification email connection failed user_id=%s", user_id or "-")
        return False
    except (socket.timeout, TimeoutError) as exc:
        logger.exception("Verification email timed out user_id=%s", user_id or "-")
        return False
    except OSError as exc:
        # DNS, refused connection, firewall/antivirus blocks.
        logger.exception("Verification email network error user_id=%s", user_id or "-")
        return False
    except Exception as exc:  # provider failure: log, don't leak to client
        logger.exception("Verification email failed user_id=%s", user_id or "-")
        return False
