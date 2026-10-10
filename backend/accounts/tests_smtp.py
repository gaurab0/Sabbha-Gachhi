"""Unit tests for SMTP configuration and the mailer (no network, no Django DB).

_smtp_options() reads os.environ on every call, so tests isolate it with a
wiped environment. The mailer is exercised with a mocked EmailMultiAlternatives
so each smtplib failure mode is covered without touching the network.
"""

import os
import smtplib
import socket
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from accounts.mailer import VerificationEmail, send_verification_email
from core.settings import _clean_password, _smtp_options


def _env(**overrides):
    """Copies of the process env minus any EMAIL_* keys, plus overrides."""
    base = {k: v for k, v in os.environ.items() if not k.startswith("EMAIL_")}
    base.update(overrides)
    return base


def _msg():
    return VerificationEmail(
        to_email="case@example.com",
        subject="Subject",
        text_body="Body",
        html_body="<p>Body</p>",
    )


class SmtpOptionsTests(SimpleTestCase):
    def _options(self, debug=False, **env):
        # debug=False exercises the production path: missing credentials
        # raise instead of silently falling back to console. (Passing
        # debug=True would take the dev early-return.) Explicit parameter
        # rather than override_settings, because _smtp_options reads the
        # module-global DEBUG, which Django's override cannot reach.
        with mock.patch.dict(os.environ, _env(**env), clear=True):
            return _smtp_options(debug=debug)

    def test_valid_starttls_pair(self):
        opts = self._options(
            EMAIL_HOST="smtp.gmail.com",
            EMAIL_PORT="587",
            EMAIL_USE_TLS="true",
            EMAIL_USE_SSL="false",
            EMAIL_HOST_USER="a@gmail.com",
            EMAIL_HOST_PASSWORD="x" * 16,
        )
        self.assertEqual(
            opts,
            {
                "host": "smtp.gmail.com",
                "port": 587,
                "username": "a@gmail.com",
                "password": "x" * 16,
                "use_tls": True,
                "use_ssl": False,
                "timeout": 10,
            },
        )

    def test_valid_implicit_ssl_pair(self):
        opts = self._options(
            EMAIL_HOST="smtp.gmail.com",
            EMAIL_PORT="465",
            EMAIL_USE_TLS="false",
            EMAIL_USE_SSL="true",
            EMAIL_HOST_USER="a@gmail.com",
            EMAIL_HOST_PASSWORD="x" * 16,
        )
        self.assertTrue(opts["use_ssl"])
        self.assertFalse(opts["use_tls"])
        self.assertEqual(opts["port"], 465)

    def test_invalid_pairs_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self._options(
                EMAIL_HOST="smtp.gmail.com",
                EMAIL_PORT="587",
                EMAIL_USE_TLS="false",
                EMAIL_USE_SSL="true",
                EMAIL_HOST_USER="a@gmail.com",
                EMAIL_HOST_PASSWORD="x" * 16,
            )
        with self.assertRaises(ImproperlyConfigured):
            self._options(
                EMAIL_HOST="smtp.gmail.com",
                EMAIL_PORT="465",
                EMAIL_USE_TLS="true",
                EMAIL_USE_SSL="false",
                EMAIL_HOST_USER="a@gmail.com",
                EMAIL_HOST_PASSWORD="x" * 16,
            )

    def test_missing_user_or_password(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self._options(EMAIL_HOST="smtp.gmail.com", EMAIL_HOST_PASSWORD="x" * 16)
        self.assertIn("EMAIL_HOST_USER", str(ctx.exception))
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self._options(EMAIL_HOST="smtp.gmail.com", EMAIL_HOST_USER="a@gmail.com")
        self.assertIn("EMAIL_HOST_PASSWORD", str(ctx.exception))
        # The secret value itself must never appear in error messages.
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self._options(
                EMAIL_HOST="h",
                EMAIL_HOST_USER="u",
                EMAIL_HOST_PASSWORD="s3cr3t!",
                EMAIL_PORT="notaport",
            )
        self.assertNotIn("s3cr3t!", str(ctx.exception))

    def test_no_host_means_console_fallback(self):
        self.assertEqual(self._options(), {})

    def test_password_cleaning(self):
        self.assertEqual(_clean_password('"abcd 1234 efgh 5678"'), "abcd1234efgh5678")
        self.assertEqual(_clean_password("  abcd1234efgh5678  "), "abcd1234efgh5678")
        self.assertEqual(_clean_password("'abcd1234efgh5678'"), "abcd1234efgh5678")
        # Already-clean values pass through untouched.
        self.assertEqual(_clean_password("abcd1234efgh5678"), "abcd1234efgh5678")
        opts = self._options(
            EMAIL_HOST="smtp.gmail.com",
            EMAIL_HOST_USER="a@gmail.com",
            EMAIL_HOST_PASSWORD='"abcd 1234 efgh 5678"',
        )
        self.assertEqual(opts["password"], "abcd1234efgh5678")

    def test_timeout_setting(self):
        opts = self._options(
            EMAIL_HOST="h", EMAIL_HOST_USER="u", EMAIL_HOST_PASSWORD="p", EMAIL_TIMEOUT="5"
        )
        self.assertEqual(opts["timeout"], 5)
        with self.assertRaises(ImproperlyConfigured):
            self._options(
                EMAIL_HOST="h", EMAIL_HOST_USER="u", EMAIL_HOST_PASSWORD="p", EMAIL_TIMEOUT="soon"
            )

    def test_legacy_fallback_names(self):
        opts = self._options(
            EMAIL_SMTP_HOST="smtp.gmail.com",
            EMAIL_SMTP_PORT="587",
            EMAIL_SMTP_USER="a@gmail.com",
            EMAIL_SMTP_PASSWORD="p",
        )
        self.assertEqual(opts["host"], "smtp.gmail.com")
        self.assertTrue(opts["use_tls"])


class MailerTests(SimpleTestCase):
    def _send(self, mock_ema):
        # Failure paths log to accounts.mailer (ERROR) and nothing to
        # accounts.audit — assertNoLogs verifies the "no false sent-log" rule.
        with self.assertNoLogs("accounts.audit", level="INFO"), \
                self.assertLogs("accounts.mailer", level="ERROR") as mailer_logs:
            ok = send_verification_email(_msg())
        return ok, mailer_logs.output

    def test_success_logs_sent_once(self):
        with mock.patch("accounts.mailer.EmailMultiAlternatives") as mock_ema:
            mock_ema.return_value.send.return_value = 1
            with self.assertLogs("accounts.audit", level="INFO") as audit_logs:
                ok = send_verification_email(_msg())
        self.assertTrue(ok)
        sent = [line for line in audit_logs.output if "verification_sent" in line]
        self.assertEqual(len(sent), 1)
        mock_ema.return_value.send.assert_called_once()

    def test_disconnect_returns_false_without_sent_log(self):
        with mock.patch("accounts.mailer.EmailMultiAlternatives") as mock_ema:
            mock_ema.return_value.send.side_effect = smtplib.SMTPServerDisconnected(
                "Connection unexpectedly closed"
            )
            ok, mailer_logs = self._send(mock_ema)
        self.assertFalse(ok)
        self.assertTrue(any("disconnected" in line for line in mailer_logs))

    def test_auth_error_logged_distinctly(self):
        with mock.patch("accounts.mailer.EmailMultiAlternatives") as mock_ema:
            mock_ema.return_value.send.side_effect = smtplib.SMTPAuthenticationError(
                535, b"Username and Password not accepted"
            )
            ok, mailer_logs = self._send(mock_ema)
        self.assertFalse(ok)
        self.assertTrue(any("auth failed" in line for line in mailer_logs))

    def test_connect_and_timeout_errors(self):
        for exc in (
            smtplib.SMTPConnectError(421, b"cannot connect"),
            socket.timeout("timed out"),
            OSError("network unreachable"),
        ):
            with mock.patch("accounts.mailer.EmailMultiAlternatives") as mock_ema:
                mock_ema.return_value.send.side_effect = exc
                ok, _ = self._send(mock_ema)
            self.assertFalse(ok, exc)
