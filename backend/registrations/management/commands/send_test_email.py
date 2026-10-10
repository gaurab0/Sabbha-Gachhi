"""
Send a test email through the configured mailer to verify SMTP setup.

Usage (from backend/):
    python manage.py send_test_email --to you@example.com
    python manage.py send_test_email --to you@example.com --subject "Hi" --body "Hello"

What it shows BEFORE sending: the active backend class plus host, port and
username. The password is never printed or logged. Exit code 0 on success,
1 with a specific hint on failure (bad app password vs unreachable host).
"""

import logging
import smtplib
import socket

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send a test email via the configured mailer (verifies Gmail SMTP wiring)."

    def add_arguments(self, parser):
        parser.add_argument("--to", required=True, help="Recipient address.")
        parser.add_argument(
            "--subject",
            default="Sabha Gachhi test email",
            help="Subject line.",
        )
        parser.add_argument(
            "--body",
            default=(
                "If you received this, the Gmail SMTP wiring works "
                "(Sabha Gachhi mailer test)."
            ),
            help="Plain-text body.",
        )

    def handle(self, *args, **options):
        mailers = getattr(settings, "MAILERS", {})
        entry = mailers.get("default", {})
        backend = entry.get("BACKEND", "(legacy EMAIL_BACKEND path)")
        opts = entry.get("OPTIONS", {})

        self.stdout.write(f"Backend : {backend}")
        if opts:
            # Password deliberately omitted — never print secrets.
            self.stdout.write(
                f"SMTP    : host={opts.get('host')} port={opts.get('port')} "
                f"user={opts.get('username')} "
                f"{'(implicit SSL)' if opts.get('use_ssl') else '(STARTTLS)'}"
            )
        else:
            self.stdout.write(
                "SMTP    : not configured — console backend active, "
                "mail will only be printed, nothing is sent."
            )
        self.stdout.write(f"From    : {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"To      : {options['to']}")

        try:
            send_mail(
                options["subject"],
                options["body"],
                settings.DEFAULT_FROM_EMAIL,
                [options["to"]],
                fail_silently=False,
            )
        except smtplib.SMTPAuthenticationError as exc:
            raise CommandError(
                "SMTP authentication failed. For Gmail this almost always "
                f"means EMAIL_PASS is wrong (code {exc.smtp_code!r}). Use a "
                "Google App Password (Account -> Security -> 2-Step "
                "Verification ON -> App passwords -> Mail), not your login "
                "password, and paste it without spaces."
            ) from exc
        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected,
                socket.gaierror, socket.timeout, OSError) as exc:
            raise CommandError(
                "Could not reach the SMTP server. Check EMAIL_HOST/EMAIL_PORT "
                f"and your network/firewall. Underlying error: {exc}"
            ) from exc
        except smtplib.SMTPException as exc:
            raise CommandError(f"SMTP send failed: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("Test email sent successfully."))
