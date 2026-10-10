"""Tests for email verification (phase 1 of stronger auth).

Covers: signup->verify->access flow (link), expired/reused/tampered tokens,
OTP contract (auth-required {code}, explicit error codes), attempt lockout,
resend-invalidates-old, cooldown 429, leading zeros, mailer 503, cross-user
isolation, change-email reset, Gmail alias folding, 403 gate, JWT refresh.

Throttle rates are raised under test (DRF anon/scope buckets are shared per
test-client IP, so defaults would flake the suite); the limits themselves are
exercised directly against the resend logic.
"""

import json
from datetime import timedelta
from unittest import mock

import jwt
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .email_normalize import normalize_email
from .models import EmailVerificationToken, VerificationCode, VerificationSendLog
from .verification import SENDERS, BaseSender, hash_code, hash_secret, issue_token

User = get_user_model()

HIGH_THROTTLES = {
    "REST_FRAMEWORK": {
        "EXCEPTION_HANDLER": "accounts.exceptions.api_exception_handler",
        "DEFAULT_AUTHENTICATION_CLASSES": (
            "rest_framework_simplejwt.authentication.JWTAuthentication",
        ),
        "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
        "DEFAULT_THROTTLE_CLASSES": [
            "rest_framework.throttling.AnonRateThrottle",
            "rest_framework.throttling.ScopedRateThrottle",
        ],
        "DEFAULT_THROTTLE_RATES": {
            "anon": "10000/hour",
            "status_check": "10000/hour",
            "auth": "10000/hour",
            "verify": "10000/hour",
            "resend": "10000/hour",
        },
    }
}


def _post(client, path, data, token=None):
    kwargs = {"content_type": "application/json"}
    if token:
        kwargs["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client.post(path, data=json.dumps(data), **kwargs)


_ip_counter = [100]


def _fresh_client():
    """Test client with a unique IP.

    DRF binds THROTTLE_RATES at import time, so override_settings cannot
    raise throttle rates in tests — shared-IP buckets would fill at the real
    20/hour across the suite (same pattern as tests_phone._fresh_client).
    """
    _ip_counter[0] += 1
    return APIClient(REMOTE_ADDR=f"10.200.1.{_ip_counter[0]}")


def _make_code(user, target, code="482916", minutes=10, channel="email"):
    """Seed an active OTP row directly (hash path is the real one)."""
    return VerificationCode.objects.create(
        user=user,
        channel=channel,
        target=target,
        code_hash=hash_code(code),
        expires_at=timezone.now() + timedelta(minutes=minutes),
    )


class _RecordingSender(BaseSender):
    """Captures codes instead of sending (resend-invalidates-old test)."""

    channel = "email"

    def __init__(self):
        self.sent = []

    def send(self, *, user, target, code):
        self.sent.append((target, code))
        return True


def _failing_sender(**kwargs):
    raise RuntimeError("smtp down")


@override_settings(**HIGH_THROTTLES)
class EmailVerificationTests(TestCase):
    def setUp(self):
        self.client = _fresh_client()

    def _signup(self, email="case.one@gmail.com", password="StrongPass123!"):
        res = self.client.post(
            "/api/auth/signup/", {"email": email, "password": password}, format="json"
        )
        self.assertEqual(res.status_code, 201, res.content[:300])
        return res.data

    def _authed(self, email, password="StrongPass123!"):
        """Fresh client (unique IP) authenticated as a newly signed-up user."""
        client = _fresh_client()
        res = client.post(
            "/api/auth/signup/", {"email": email, "password": password}, format="json"
        )
        self.assertEqual(res.status_code, 201, res.content[:300])
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return client, User.objects.get(email=email)

    # -- happy path (link flow, still supported) -------------------------
    def test_signup_verify_access_flow(self):
        body = self._signup()
        self.assertFalse(body["email_verified"])
        self.assertIn("access", body)

        # Unverified: /me works, protected app route is gated with the code.
        me = self.client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {body['access']}")
        self.assertEqual(me.status_code, 200)
        self.assertFalse(me.data["email_verified"])

        # Unverified users CAN read their own status (deliberate: the
        # frontend needs the payload to render the "verify your email"
        # screen). The gate is a 200 with email_verified=False, not a 403 —
        # RequireVerifiedEmail still guards create/withdraw.
        gated = self.client.get(
            "/api/registrations/me/status/",
            HTTP_AUTHORIZATION=f"Bearer {body['access']}",
        )
        self.assertEqual(gated.status_code, 200)
        self.assertFalse(gated.data["email_verified"])
        self.assertIsNone(gated.data["registration"])

        # Verify out-of-band (console backend in tests) with auth header.
        user = User.objects.get(email="case.one@gmail.com")
        _, raw = issue_token(user, user.email)
        res = _post(
            self.client, "/api/auth/verify-email/", {"token": raw}, token=body["access"]
        )
        self.assertEqual(res.status_code, 200, res.content[:300])
        self.assertTrue(res.data["email_verified"])
        claim = jwt.decode(res.data["access"], options={"verify_signature": False})
        self.assertTrue(claim.get("email_verified"))

        # Gate now passes (404 = no registration yet, NOT 403).
        gated2 = self.client.get(
            "/api/registrations/me/status/",
            HTTP_AUTHORIZATION=f"Bearer {res.data['access']}",
        )
        self.assertNotEqual(gated2.status_code, 403)

        # Login response carries the verified flag too.
        login = _post(
            self.client,
            "/api/auth/login/",
            {"email": "case.one@gmail.com", "password": "StrongPass123!"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.data["email_verified"])

    # -- gating: unverified is blocked from app writes, status stays open -
    def test_unverified_blocked_create_403(self):
        body = self._signup(email="gate.create@gmail.com")
        res = _post(
            self.client, "/api/registrations/", {}, token=body["access"]
        )
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.data["code"], "email_not_verified")

    def test_unverified_blocked_withdraw_403(self):
        body = self._signup(email="gate.withdraw@gmail.com")
        # Permission runs before the handler, so the missing registration
        # surfaces as 403 here, not the handler's 404.
        res = _post(
            self.client,
            "/api/registrations/me/withdraw/",
            {},
            token=body["access"],
        )
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.data["code"], "email_not_verified")

    def test_unverified_blocked_concern_403(self):
        body = self._signup(email="gate.concern@gmail.com")
        res = _post(
            self.client, "/api/concern-reports/", {}, token=body["access"]
        )
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.data["code"], "email_not_verified")

    def test_otp_verify_grants_access(self):
        client, user = self._authed("gate.otp@gmail.com")
        _make_code(user, normalize_email(user.email), code="482916")
        ok = client.post(
            "/api/auth/verify-email/", {"code": "482916"}, format="json"
        )
        self.assertEqual(ok.status_code, 200, ok.content[:300])
        # Gate now passes: empty body fails serializer validation (400),
        # which proves we got past the permission check (would be 403).
        res = client.post("/api/registrations/", {}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertNotEqual(res.data.get("code"), "email_not_verified")

    # -- token misuse (link flow) ----------------------------------------
    def test_expired_reused_tampered_tokens(self):
        body = self._signup(email="reuse.case@gmail.com")
        user = User.objects.get(email="reuse.case@gmail.com")
        auth = body["access"]

        expired, raw_expired = issue_token(user, user.email)
        expired.expires_at = timezone.now() - timedelta(minutes=1)
        expired.save(update_fields=["expires_at"])
        res = _post(
            self.client, "/api/auth/verify-email/", {"token": raw_expired}, token=auth
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "EXPIRED_TOKEN")

        _, raw = issue_token(user, user.email)
        ok = _post(self.client, "/api/auth/verify-email/", {"token": raw}, token=auth)
        self.assertEqual(ok.status_code, 200)
        reuse = _post(self.client, "/api/auth/verify-email/", {"token": raw}, token=auth)
        self.assertEqual(reuse.status_code, 400)
        self.assertEqual(reuse.data["code"], "INVALID_TOKEN")

        tampered = _post(
            self.client, "/api/auth/verify-email/", {"token": "0" * 64}, token=auth
        )
        self.assertEqual(tampered.status_code, 400)
        self.assertEqual(tampered.data["code"], "INVALID_TOKEN")

    def test_token_hash_stored_not_raw(self):
        self._signup(email="hash.case@gmail.com")
        user = User.objects.get(email="hash.case@gmail.com")
        row, raw = issue_token(user, user.email)
        self.assertEqual(row.token_hash, hash_secret(raw))
        self.assertNotIn(raw, row.token_hash)
        self.assertEqual(len(row.token_hash), 64)

    # -- OTP contract ----------------------------------------------------
    def test_otp_verify_success(self):
        client, user = self._authed("otp.ok@gmail.com")
        target = normalize_email(user.email)
        _make_code(user, target, code="482916")
        res = client.post("/api/auth/verify-email/", {"code": "482916"}, format="json")
        self.assertEqual(res.status_code, 200, res.content[:300])
        self.assertEqual(res.data, {"detail": "Email verified"})
        user.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertIsNotNone(user.email_verified_at)

    def test_otp_alias_accepted(self):
        client, user = self._authed("otp.alias@gmail.com")
        _make_code(user, normalize_email(user.email), code="112233")
        res = client.post("/api/auth/verify-email/", {"otp": "112233"}, format="json")
        self.assertEqual(res.status_code, 200, res.content[:300])

    def test_otp_wrong_code(self):
        client, user = self._authed("otp.wrong@gmail.com")
        _make_code(user, normalize_email(user.email), code="482916")
        res = client.post("/api/auth/verify-email/", {"code": "000000"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "invalid")
        self.assertIn("detail", res.data)
        user.refresh_from_db()
        self.assertFalse(user.email_verified)

    def test_otp_expired_code(self):
        client, user = self._authed("otp.exp@gmail.com")
        _make_code(user, normalize_email(user.email), code="482916", minutes=-1)
        res = client.post("/api/auth/verify-email/", {"code": "482916"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "expired")

    def test_otp_attempt_lockout(self):
        client, user = self._authed("otp.lock@gmail.com")
        _make_code(user, normalize_email(user.email), code="482916")
        for i in range(4):
            res = client.post(
                "/api/auth/verify-email/", {"code": "000000"}, format="json"
            )
            self.assertEqual(res.status_code, 400)
            self.assertEqual(res.data["code"], "invalid", i)
        locked = client.post(
            "/api/auth/verify-email/", {"code": "000000"}, format="json"
        )
        self.assertEqual(locked.status_code, 400)
        self.assertEqual(locked.data["code"], "too_many_attempts")
        # The locked row is consumed, so even the right code afterwards
        # finds no active code — either way, a new code must be requested.
        dead = client.post(
            "/api/auth/verify-email/", {"code": "482916"}, format="json"
        )
        self.assertEqual(dead.status_code, 400)
        self.assertEqual(dead.data["code"], "not_found")

    def test_concurrent_wrong_guesses_cap_attempts_exactly(self):
        import concurrent.futures

        from .verification import VerificationResult, verify_code

        _, user = self._authed("otp.race@gmail.com")
        target = normalize_email(user.email)
        row = _make_code(user, target, code="482916")
        row.attempts = 4
        row.save(update_fields=["attempts"])

        def attempt():
            # Fresh user object per thread: no shared in-memory state, so
            # the only coordination point is the database row itself.
            # Each thread closes its own connection afterwards — Django
            # opens one connection per thread and never closes ones it
            # didn't open, so without this 20 short-lived connections
            # would linger until process teardown.
            from django.db import connection

            try:
                u = User.objects.get(pk=user.pk)
                return verify_code(u, "email", target, "000000")
            finally:
                connection.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(lambda _: attempt(), range(20)))

        row.refresh_from_db()
        # Exactly one reservation could land (4 -> 5); the other 19 matched
        # zero rows, so the counter cannot overshoot no matter the timing.
        self.assertEqual(row.attempts, 5)
        # The winner locked the row; losers either saw the lock or found the
        # row already consumed — every answer still means "try a new code".
        self.assertIn(VerificationResult.TOO_MANY_ATTEMPTS, results)
        for result in results:
            self.assertIn(
                result,
                (VerificationResult.TOO_MANY_ATTEMPTS, VerificationResult.NOT_FOUND),
            )

    def test_verify_infra_failure_returns_503(self):
        # If the DB save inside on_verified blows up, the row is already
        # consumed — the view must answer 503 (ask for a new code), never
        # 500 and never a half-verified account.
        client, user = self._authed("otp.infra@gmail.com")
        _make_code(user, normalize_email(user.email), code="482916")
        with mock.patch.object(
            User, "mark_email_verified", side_effect=RuntimeError("db down")
        ):
            res = client.post(
                "/api/auth/verify-email/", {"code": "482916"}, format="json"
            )
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.data["code"], "verification_failed")
        user.refresh_from_db()
        self.assertFalse(user.email_verified)

    def test_otp_no_active_code(self):
        client, _ = self._authed("otp.none@gmail.com")
        res = client.post("/api/auth/verify-email/", {"code": "482916"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "not_found")

    def test_otp_already_verified(self):
        client, user = self._authed("otp.done@gmail.com")
        user.email_verified = True
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified", "email_verified_at"])
        res = client.post("/api/auth/verify-email/", {"code": "482916"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, {"detail": "Email already verified"})

    def test_otp_leading_zero_code(self):
        client, user = self._authed("otp.zero@gmail.com")
        _make_code(user, normalize_email(user.email), code="012345")
        res = client.post("/api/auth/verify-email/", {"code": "012345"}, format="json")
        self.assertEqual(res.status_code, 200, res.content[:300])
        self.assertEqual(res.data, {"detail": "Email verified"})

    def test_otp_generation_zero_pads(self):
        # Deterministic proof that issue_code zero-pads: force randbelow to
        # a 5-digit number and assert the issued (and verifiable) code keeps
        # its leading zero end to end. No luck involved.
        client, user = self._authed("otp.pad@gmail.com")
        VerificationSendLog.objects.filter(user=user).delete()
        fake, old_sender = _RecordingSender(), SENDERS["email"]
        SENDERS["email"] = fake
        try:
            with mock.patch(
                "accounts.verification.secrets.randbelow", return_value=12345
            ):
                with override_settings(EMAIL_VERIFICATION_METHOD="otp"):
                    res = client.post(
                        "/api/auth/resend-verification/",
                        {"channel": "email"},
                        format="json",
                    )
            self.assertEqual(res.status_code, 200, res.content[:300])
        finally:
            SENDERS["email"] = old_sender
        self.assertEqual(fake.sent[-1][1], "012345")
        ok = client.post(
            "/api/auth/verify-email/", {"code": "012345"}, format="json"
        )
        self.assertEqual(ok.status_code, 200, ok.content[:300])

    def test_otp_malformed_code_rejected(self):
        client, _ = self._authed("otp.bad@gmail.com")
        for bad in ("12345", "1234567", "abcdef", "12 34 56"):
            res = client.post(
                "/api/auth/verify-email/", {"code": bad}, format="json"
            )
            self.assertEqual(res.status_code, 400, bad)

    def test_otp_cannot_verify_other_users_email(self):
        client_a, user_a = self._authed("otp.a@gmail.com")
        client_b, _ = self._authed("otp.b@gmail.com")
        _make_code(user_a, normalize_email(user_a.email), code="482916")
        # B posts A's code: B has no active code of their own.
        res = client_b.post(
            "/api/auth/verify-email/", {"code": "482916"}, format="json"
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "not_found")
        # A's row is untouched and still usable by A.
        ok = client_a.post(
            "/api/auth/verify-email/", {"code": "482916"}, format="json"
        )
        self.assertEqual(ok.status_code, 200)

    # -- resend ----------------------------------------------------------
    def test_resend_cooldown_429(self):
        client, user = self._authed("otp.cool@gmail.com")
        # Signup itself sends a message; clear that evidence so the first
        # resend below is a clean send (cooldown must come from IT, not signup).
        VerificationSendLog.objects.filter(user=user).delete()
        with override_settings(EMAIL_VERIFICATION_METHOD="otp"):
            ok = client.post(
                "/api/auth/resend-verification/", {"channel": "email"}, format="json"
            )
            self.assertEqual(ok.status_code, 200, ok.content[:300])
            self.assertEqual(ok.data["detail"], "Verification code sent")
            self.assertEqual(ok.data["cooldown_seconds"], 60)
            again = client.post(
                "/api/auth/resend-verification/", {"channel": "email"}, format="json"
            )
            self.assertEqual(again.status_code, 429)
            self.assertEqual(again.data["code"], "cooldown")
            self.assertGreater(again.data["retry_after_seconds"], 0)
            self.assertEqual(again["Retry-After"], str(again.data["retry_after_seconds"]))
            self.assertEqual(VerificationSendLog.objects.filter(user=user).count(), 1)

    def test_resend_lock_contention_429(self):
        from django.core.cache import cache

        client, user = self._authed("otp.locked@gmail.com")
        VerificationSendLog.objects.filter(user=user).delete()
        # Simulate a concurrent resend holding the per-user lock.
        self.assertTrue(
            cache.add(f"resend-email-lock:{user.pk}", 1, timeout=60)
        )
        try:
            with override_settings(EMAIL_VERIFICATION_METHOD="otp"):
                res = client.post(
                    "/api/auth/resend-verification/",
                    {"channel": "email"},
                    format="json",
                )
        finally:
            cache.delete(f"resend-email-lock:{user.pk}")
        self.assertEqual(res.status_code, 429)
        self.assertEqual(res["Retry-After"], "5")

    def test_resend_daily_user_cap_429(self):
        from django.utils import timezone as tz

        client, user = self._authed("otp.daily@gmail.com")
        VerificationSendLog.objects.filter(user=user).delete()
        # Seed 5 sends in the last day (backdated past cooldown/hourly).
        for _ in range(5):
            VerificationSendLog.objects.create(
                user=user,
                ip_address="10.200.1.250",
                kind="email",
                created_at=tz.now() - timedelta(hours=2),
            )
        with override_settings(
            EMAIL_VERIFICATION_METHOD="otp", OTP_MAX_SENDS_PER_HOUR_PER_TARGET=100
        ):
            res = client.post(
                "/api/auth/resend-verification/", {"channel": "email"}, format="json"
            )
        self.assertEqual(res.status_code, 429)
        self.assertEqual(res.data["code"], "resend_daily_limit")
        self.assertGreater(res.data["retry_after_seconds"], 0)
        self.assertEqual(res["Retry-After"], str(res.data["retry_after_seconds"]))

    def test_resend_daily_ip_cap_429(self):
        from django.utils import timezone as tz

        client, user = self._authed("otp.ipcap@gmail.com")
        VerificationSendLog.objects.filter(user=user).delete()
        ip = client.defaults.get("REMOTE_ADDR", "127.0.0.1")
        others = [User.objects.create_user(email=f"seed{i}@example.com", password="x" * 12) for i in range(3)]
        for i in range(10):
            VerificationSendLog.objects.create(
                user=others[i % 3],
                ip_address=ip,
                kind="email",
                created_at=tz.now() - timedelta(hours=2),
            )
        with override_settings(
            EMAIL_VERIFICATION_METHOD="otp",
            OTP_MAX_SENDS_PER_HOUR_PER_TARGET=100,
            # Pin a low IP cap so the test needs 10 seeded rows, not 100.
            RESEND_MAX_PER_IP_PER_DAY=10,
        ):
            res = client.post(
                "/api/auth/resend-verification/", {"channel": "email"}, format="json"
            )
        self.assertEqual(res.status_code, 429)
        self.assertEqual(res.data["code"], "resend_daily_limit")
        self.assertGreater(res.data["retry_after_seconds"], 0)
        self.assertEqual(res["Retry-After"], str(res.data["retry_after_seconds"]))

    def test_resend_invalidates_old_code(self):
        client, user = self._authed("otp.inv@gmail.com")
        VerificationSendLog.objects.filter(user=user).delete()
        fake, old_sender = _RecordingSender(), SENDERS["email"]
        SENDERS["email"] = fake
        try:
            with override_settings(EMAIL_VERIFICATION_METHOD="otp"):
                first = client.post(
                    "/api/auth/resend-verification/", {"channel": "email"}, format="json"
                )
                self.assertEqual(first.status_code, 200, first.content[:300])
                # Bypass the 60s cooldown: backdate send evidence.
                VerificationCode.objects.filter(user=user).update(
                    last_sent_at=timezone.now() - timedelta(seconds=61)
                )
                VerificationSendLog.objects.filter(user=user).delete()
                second = client.post(
                    "/api/auth/resend-verification/", {"channel": "email"}, format="json"
                )
                self.assertEqual(second.status_code, 200, second.content[:300])
        finally:
            SENDERS["email"] = old_sender
        self.assertEqual(len(fake.sent), 2)
        old_code, new_code = fake.sent[0][1], fake.sent[1][1]
        stale = client.post(
            "/api/auth/verify-email/", {"code": old_code}, format="json"
        )
        self.assertEqual(stale.status_code, 400)
        self.assertIn(stale.data["code"], ("invalid", "not_found"))
        fresh = client.post(
            "/api/auth/verify-email/", {"code": new_code}, format="json"
        )
        self.assertEqual(fresh.status_code, 200)

    def test_resend_mailer_failure_503(self):
        client, user = self._authed("otp.fail@gmail.com")
        VerificationSendLog.objects.filter(user=user).delete()
        with override_settings(
            EMAIL_VERIFICATION_METHOD="otp", EMAIL_VERIFICATION_PROVIDER=_failing_sender
        ):
            res = client.post(
                "/api/auth/resend-verification/", {"channel": "email"}, format="json"
            )
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.data["code"], "email_service_unavailable")
        self.assertEqual(VerificationSendLog.objects.filter(user=user).count(), 0)

    def test_resend_link_failure_503_and_token_invalidated(self):
        from unittest import mock

        client, user = self._authed("link.fail@gmail.com")
        VerificationSendLog.objects.filter(user=user).delete()
        with override_settings(EMAIL_VERIFICATION_METHOD="link"):
            with mock.patch(
                "accounts.views.send_verification_email", return_value=False
            ) as mock_send:
                res = client.post(
                    "/api/auth/resend-verification/",
                    {"channel": "email"},
                    format="json",
                )
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.data["code"], "email_service_unavailable")
        self.assertEqual(VerificationSendLog.objects.filter(user=user).count(), 0)
        # Exactly one send attempt for one request.
        self.assertEqual(mock_send.call_count, 1)
        # The token minted for the failed send must not stay valid.
        self.assertFalse(
            EmailVerificationToken.objects.filter(
                user=user, used_at__isnull=True
            ).exists()
        )

    def test_resend_bad_channel(self):
        client, _ = self._authed("otp.chan@gmail.com")
        res = client.post(
            "/api/auth/resend-verification/", {"channel": "sms"}, format="json"
        )
        self.assertEqual(res.status_code, 400)

    # -- change email resets verification --------------------------------
    def test_change_email_resets_verification(self):
        client, user = self._authed("otp.old@gmail.com")
        target = normalize_email(user.email)
        _make_code(user, target, code="482916")
        res = client.post(
            "/api/auth/email/change/",
            {"new_email": "otp.new@gmail.com", "current_password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content[:300])
        user.refresh_from_db()
        self.assertFalse(user.email_verified)
        self.assertIsNone(user.email_verified_at)
        self.assertEqual(user.pending_email, "otp.new@gmail.com")
        # The pre-change code is dead.
        stale = client.post(
            "/api/auth/verify-email/", {"code": "482916"}, format="json"
        )
        self.assertEqual(stale.status_code, 400)

    def test_change_email_otp_end_to_end(self):
        # Full journey in OTP mode: verify old address, request a change,
        # verify the NEW address with the NEW code, end verified-as-new.
        client, user = self._authed("otp.move@gmail.com")
        _make_code(user, normalize_email(user.email), code="111111")
        first = client.post(
            "/api/auth/verify-email/", {"code": "111111"}, format="json"
        )
        self.assertEqual(first.status_code, 200, first.content[:300])
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

        fake, old_sender = _RecordingSender(), SENDERS["email"]
        SENDERS["email"] = fake
        try:
            with override_settings(EMAIL_VERIFICATION_METHOD="otp"):
                chg = client.post(
                    "/api/auth/email/change/",
                    {
                        "new_email": "otp.moved@gmail.com",
                        "current_password": "StrongPass123!",
                    },
                    format="json",
                )
            self.assertEqual(chg.status_code, 200, chg.content[:300])
        finally:
            SENDERS["email"] = old_sender
        user.refresh_from_db()
        # While the change is pending the account is unverified...
        self.assertFalse(user.email_verified)
        self.assertEqual(user.pending_email, "otp.moved@gmail.com")
        # ...and the code went to the NEW address (normalized: Gmail
        # dots are folded, so otp.moved@ becomes otpmoved@), not the old one.
        self.assertEqual(fake.sent[-1][0], "otpmoved@gmail.com")
        done = client.post(
            "/api/auth/verify-email/",
            {"code": fake.sent[-1][1]},
            format="json",
        )
        self.assertEqual(done.status_code, 200, done.content[:300])
        user.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertEqual(user.email, "otp.moved@gmail.com")
        self.assertIsNone(user.pending_email)

    # -- Gmail aliases ---------------------------------------------------
    def test_gmail_alias_duplicates_rejected(self):
        self._signup(email="a.b@gmail.com")
        for alias in ("ab@gmail.com", "ab+x@gmail.com", "A.B@gmail.com"):
            res = self.client.post(
                "/api/auth/signup/",
                {"email": alias, "password": "StrongPass123!"},
                format="json",
            )
            self.assertEqual(res.status_code, 400, alias)
        user = User.objects.get(email="a.b@gmail.com")
        self.assertEqual(user.normalized_email, "ab@gmail.com")


class ClientIpTests(TestCase):
    def _request(self, remote, xff=None):
        extra = {"REMOTE_ADDR": remote}
        if xff is not None:
            extra["HTTP_X_FORWARDED_FOR"] = xff
        return RequestFactory().get("/", **extra)

    def test_spoofed_forwarded_header_ignored_by_default(self):
        from .views import _client_ip

        # Default TRUSTED_PROXY_COUNT=0: a client-supplied XFF must never
        # override the direct peer, or throttles and IP caps evade trivially.
        req = self._request("5.6.7.8", xff="1.2.3.4")
        self.assertEqual(_client_ip(req), "5.6.7.8")

    def test_forwarded_header_honored_behind_trusted_proxy(self):
        from django.conf import settings as dj_settings

        from .views import _client_ip

        # With one trusted proxy, DRF trusts the last XFF entry (the peer
        # our proxy received from) and ignores spoofed entries to its left.
        # NOTE: NUM_PROXIES is read per-request (unlike THROTTLE_RATES, which
        # binds at import), so overriding the REST_FRAMEWORK dict works here.
        rest = dict(dj_settings.REST_FRAMEWORK)
        rest["NUM_PROXIES"] = 1
        with override_settings(REST_FRAMEWORK=rest):
            req = self._request("9.9.9.9", xff="spoofed, 9.9.8.8")
            self.assertEqual(_client_ip(req), "9.9.8.8")

    def test_client_ip_matches_drf_ident(self):
        """_client_ip and DRF throttling must key on the same machine.

        _client_ip delegates to SimpleRateThrottle.get_ident, so this is
        structural — the matrix below pins the agreed behavior against
        literal values in case a DRF upgrade changes the formula.
        """
        from django.conf import settings as dj_settings

        from .views import _client_ip

        cases = [
            # (remote, xff, num_proxies, expected)
            ("5.6.7.8", None, 0, "5.6.7.8"),
            ("5.6.7.8", "1.2.3.4", 0, "5.6.7.8"),
            ("9.9.9.9", "1.2.3.4", 1, "1.2.3.4"),
            ("9.9.9.9", "spoofed, 9.9.8.8", 1, "9.9.8.8"),
            ("9.9.9.9", "a, b, c", 2, "b"),
        ]
        for remote, xff, proxies, expected in cases:
            rest = dict(dj_settings.REST_FRAMEWORK)
            rest["NUM_PROXIES"] = proxies
            with override_settings(REST_FRAMEWORK=rest):
                self.assertEqual(
                    _client_ip(self._request(remote, xff=xff)),
                    expected,
                    f"remote={remote} xff={xff} proxies={proxies}",
                )

    def test_num_proxies_mirrors_trusted_proxy_count(self):
        """The single-knob contract: DRF's NUM_PROXIES must equal our
        TRUSTED_PROXY_COUNT, or throttles and caps would key differently."""
        from django.conf import settings as dj_settings

        self.assertEqual(
            dj_settings.REST_FRAMEWORK["NUM_PROXIES"],
            dj_settings.TRUSTED_PROXY_COUNT,
        )
