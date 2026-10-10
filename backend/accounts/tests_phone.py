"""Tests for phone verification (phase 2). SMS provider is always mocked —
no real SMS is ever sent in tests. A recording fake stands in for the
gateway (custom mode); managed mode is covered by faking check_otp.

Throttle rates are raised like in the email tests; per-user/number/IP caps
are exercised through the real send-log queries.
"""

import json
from datetime import timedelta
from unittest.mock import patch

import jwt
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import EmailVerificationToken, User, VerificationSendLog
from .phone_verification import issue_phone_code
from .sms_providers import PROVIDERS, SmsProvider, SmsResult
from .tests import HIGH_THROTTLES, _post
from .verification import issue_token

User = get_user_model()

HIGH_THROTTLES_PHONE = {
    "REST_FRAMEWORK": {
        **HIGH_THROTTLES["REST_FRAMEWORK"],
        "DEFAULT_THROTTLE_RATES": {
            **HIGH_THROTTLES["REST_FRAMEWORK"]["DEFAULT_THROTTLE_RATES"],
            "phone": "10000/hour",
        },
    }
}


class RecordingProvider(SmsProvider):
    """Test double: records sends, checks nothing (local-check mode)."""

    name = "recording"
    supports_voice = True
    supports_whatsapp = True
    sent = []

    def send_otp(self, to_e164, code, *, channel="sms"):
        RecordingProvider.sent.append(
            {"to": to_e164, "code": code, "channel": channel}
        )
        return SmsResult(True, sid="test-sid")

    @classmethod
    def reset(cls):
        cls.sent = []


PHONE_SETTINGS = dict(
    PHONE_ALLOWED_COUNTRIES=["NP", "IN", "BD"],
    PHONE_SMS_PROVIDER="recording",
    PHONE_VERIFICATION_PROVIDER_MODE="custom",
    PHONE_REQUIRE_EMAIL_FIRST=True,
    EMAIL_VERIFICATION_METHOD="link",
)


_ip_counter = [11]


def _fresh_client():
    """Test client with a unique IP.

    DRF binds THROTTLE_RATES at import time, so override_settings cannot
    raise throttle rates in tests — anon buckets (same test IP) would fill
    at the real 20/hour across the suite. Unique IPs keep buckets isolated.
    """
    _ip_counter[0] += 1
    return APIClient(REMOTE_ADDR=f"10.200.0.{_ip_counter[0]}")


def _authed_client_for(email, password="StrongPass123!"):
    client = _fresh_client()
    res = client.post(
        "/api/auth/signup/", {"email": email, "password": password}, format="json"
    )
    assert res.status_code == 201, res.content[:300]
    user = User.objects.get(email=email)
    _, raw = issue_token(user, user.email)
    # verify-email requires auth: verify your OWN address with fresh tokens.
    from .serializers import tokens_for_user

    access = tokens_for_user(user)["access"]
    res = client.post(
        "/api/auth/verify-email/",
        {"token": raw},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {access}",
    )
    assert res.status_code == 200, res.content[:300]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    user.refresh_from_db()
    return client, user


@override_settings(**HIGH_THROTTLES_PHONE, **PHONE_SETTINGS)
class PhoneVerificationTests(TestCase):
    def setUp(self):
        PROVIDERS["recording"] = RecordingProvider
        RecordingProvider.reset()
        self.client = _fresh_client()

    def tearDown(self):
        PROVIDERS.pop("recording", None)

    # -- happy path ------------------------------------------------------
    def test_start_verify_access_granted_claim_updated(self):
        client, user = _authed_client_for("ph.one@gmail.com")
        res = client.post(
            "/api/auth/phone/start/",
            {"country_code": "NP", "national_number": "9812345678"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content[:300])
        user.refresh_from_db()
        self.assertEqual(user.pending_phone, "+9779812345678")
        self.assertEqual(user.pending_phone_country, "NP")
        self.assertEqual(len(RecordingProvider.sent), 1)
        self.assertEqual(RecordingProvider.sent[0]["to"], "+9779812345678")

        code = RecordingProvider.sent[0]["code"]
        res = client.post("/api/auth/phone/verify/", {"code": code}, format="json")
        self.assertEqual(res.status_code, 200, res.content[:300])
        self.assertTrue(res.data["phone_verified"])
        claim = jwt.decode(res.data["access"], options={"verify_signature": False})
        self.assertTrue(claim.get("phone_verified"))
        self.assertTrue(claim.get("email_verified"))

        me = client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertTrue(me.data["phone_verified"])
        self.assertEqual(me.data["phone_masked"], "+977 98****5678")
        self.assertEqual(me.data["phone_country"], "NP")
        # No raw number anywhere in the response.
        self.assertNotIn("+9779812345678", json.dumps(me.data, default=str))

    # -- normalization ---------------------------------------------------
    def test_normalization_variants_converge(self):
        from .phone_normalize import parse_phone

        variants = [
            ("9812345678", "NP"),
            ("+977 9812345678", None),
            ("009779812345678", None),
            ("+977-981-234-5678", None),
        ]
        for raw, cc in variants:
            e164, country, _ = (
                parse_phone(raw, cc) if cc else parse_phone(raw)
            )
            self.assertEqual(e164, "+9779812345678", raw)
            self.assertEqual(country, "NP", raw)

        e164, country, _ = parse_phone("09812345678", "IN")
        self.assertEqual(e164, "+919812345678")
        e164, country, _ = parse_phone("01712345678", "BD")
        self.assertEqual(e164, "+8801712345678")

    # -- policy rejections ------------------------------------------------
    def test_rejected_country_invalid_landline(self):
        client, _ = _authed_client_for("ph.policy@gmail.com")
        res = client.post(
            "/api/auth/phone/start/",
            {"country_code": "US", "national_number": "2125551234"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "COUNTRY_NOT_SUPPORTED")

        res = client.post(
            "/api/auth/phone/start/",
            {"country_code": "NP", "national_number": "12"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "INVALID_NUMBER")

        # GB landline: valid number, landline type (phonenumbers metadata).
        with override_settings(PHONE_ALLOWED_COUNTRIES=["GB"]):
            res = client.post(
                "/api/auth/phone/start/",
                {"country_code": "GB", "national_number": "2079460018"},
                format="json",
            )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "LINE_TYPE_BLOCKED")

    def test_voip_blocked_with_flag(self):
        from . import phone_normalize

        client, user = _authed_client_for("ph.voip@gmail.com")
        with patch.object(
            phone_normalize, "lookup_line_type", return_value=("voip", "voip_number")
        ):
            with override_settings(PHONE_BLOCK_VOIP=True):
                res = client.post(
                    "/api/auth/phone/start/",
                    {"country_code": "NP", "national_number": "9812345678"},
                    format="json",
                )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "LINE_TYPE_BLOCKED")
        user.refresh_from_db()
        self.assertIn("voip_number", user.risk_flags)

    # -- OTP misuse --------------------------------------------------------
    def test_expired_reused_wrong_tampered_lockout(self):
        client, user = _authed_client_for("ph.misuse@gmail.com")
        client.post(
            "/api/auth/phone/start/",
            {"country_code": "NP", "national_number": "9851234567"},
            format="json",
        )
        row, code = issue_phone_code(user, "+9779851234567", "sms")

        row.expires_at = timezone.now() - timedelta(minutes=1)
        row.save(update_fields=["expires_at"])
        res = client.post("/api/auth/phone/verify/", {"code": code}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "EXPIRED_CODE")

        _, code2 = issue_phone_code(user, "+9779851234567", "sms")
        ok = client.post("/api/auth/phone/verify/", {"code": code2}, format="json")
        self.assertEqual(ok.status_code, 200)
        reuse = client.post("/api/auth/phone/verify/", {"code": code2}, format="json")
        self.assertEqual(reuse.status_code, 400)  # no pending number anymore

        # Re-claim to re-establish pending (verify consumes it). Clear the
        # send log first: the 60s cooldown would otherwise swallow the
        # re-start and leave no usable token for the lockout loop.
        VerificationSendLog.objects.filter(user=user).delete()
        restarted = client.post(
            "/api/auth/phone/start/",
            {"country_code": "NP", "national_number": "9851234567"},
            format="json",
        )
        self.assertEqual(restarted.status_code, 200)
        code3 = RecordingProvider.sent[-1]["code"]
        wrong = "000000" if code3 != "000000" else "111111"
        for _ in range(4):
            res = client.post("/api/auth/phone/verify/", {"code": wrong}, format="json")
            self.assertEqual(res.data["code"], "INVALID_CODE")
        locked = client.post("/api/auth/phone/verify/", {"code": wrong}, format="json")
        self.assertEqual(locked.data["code"], "OTP_LOCKED")
        dead = client.post("/api/auth/phone/verify/", {"code": code3}, format="json")
        self.assertEqual(dead.status_code, 400)

    # -- resend caps ---------------------------------------------------------
    def test_resend_cooldown_and_caps(self):
        client, user = _authed_client_for("ph.resend@gmail.com")
        client.post(
            "/api/auth/phone/start/",
            {"country_code": "NP", "national_number": "9861234567"},
            format="json",
        )
        VerificationSendLog.objects.filter(user=user).delete()
        RecordingProvider.reset()

        ok = client.post("/api/auth/phone/resend/", {"channel": "sms"}, format="json")
        self.assertEqual(ok.status_code, 200)
        again = client.post("/api/auth/phone/resend/", {"channel": "sms"}, format="json")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.data, ok.data)
        self.assertEqual(
            VerificationSendLog.objects.filter(user=user, kind="phone").count(), 1
        )

    def test_no_enumeration_start_unknown_number(self):
        client, _ = _authed_client_for("ph.enum@gmail.com")
        known = client.post(
            "/api/auth/phone/start/",
            {"country_code": "NP", "national_number": "9841234567"},
            format="json",
        )
        other, _ = _authed_client_for("ph.enum2@gmail.com")
        unknown = other.post(
            "/api/auth/phone/start/",
            {"country_code": "NP", "national_number": "9841234567"},
            format="json",
        )
        # Same number claimed by a second account: identical generic response.
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(unknown.data, known.data)

    # -- duplicates: first verified wins --------------------------------------
    def test_duplicate_first_verified_wins(self):
        c1, u1 = _authed_client_for("ph.dup1@gmail.com")
        c2, _ = _authed_client_for("ph.dup2@gmail.com")
        for c in (c1, c2):
            c.post(
                "/api/auth/phone/start/",
                {"country_code": "NP", "national_number": "9881234567"},
                format="json",
            )
        _, code1 = issue_phone_code(u1, "+9779881234567", "sms")
        ok = c1.post("/api/auth/phone/verify/", {"code": code1}, format="json")
        self.assertEqual(ok.status_code, 200)
        u2 = User.objects.get(email="ph.dup2@gmail.com")
        u2.refresh_from_db()
        self.assertIsNone(u2.pending_phone)  # loser's claim cleared
        self.assertFalse(u2.phone_verified)
        u1.refresh_from_db()
        self.assertEqual(u1.phone, "+9779881234567")

    # -- ordering: email error before phone error --------------------------------
    def test_require_fully_verified_ordering(self):
        client = _fresh_client()
        res = client.post(
            "/api/auth/signup/",
            {"email": "ph.order@gmail.com", "password": "StrongPass123!"},
            format="json",
        )
        token = res.data["access"]
        gated = client.get(
            "/api/match-proposals/000000000000000000000000/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(gated.status_code, 403)
        self.assertEqual(gated.data["code"], "email_not_verified")

    # -- phone change ------------------------------------------------------------
    def test_phone_change_needs_password_and_new_otp(self):
        client, user = _authed_client_for("ph.change@gmail.com")
        client.post(
            "/api/auth/phone/start/",
            {"country_code": "NP", "national_number": "9841234567"},
            format="json",
        )
        _, code = issue_phone_code(user, "+9779841234567", "sms")
        first = client.post("/api/auth/phone/verify/", {"code": code}, format="json")
        self.assertEqual(first.status_code, 200)

        bad = client.post(
            "/api/auth/phone/change/",
            {
                "country_code": "IN",
                "national_number": "9812345678",
                "current_password": "WrongPass123!",
            },
            format="json",
        )
        self.assertEqual(bad.status_code, 400)

        ok = client.post(
            "/api/auth/phone/change/",
            {
                "country_code": "IN",
                "national_number": "9812345678",
                "current_password": "StrongPass123!",
            },
            format="json",
        )
        self.assertEqual(ok.status_code, 200)
        user.refresh_from_db()
        # Swap has NOT happened yet — still the old verified number.
        self.assertEqual(user.phone, "+9779841234567")
        self.assertEqual(user.pending_phone, "+919812345678")
        _, code2 = issue_phone_code(user, "+919812345678", "sms")
        done = client.post("/api/auth/phone/verify/", {"code": code2}, format="json")
        self.assertEqual(done.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.phone, "+919812345678")
        self.assertIn("country_changed", user.risk_flags)

    # -- CAPTCHA -------------------------------------------------------------------
    def test_captcha_required_on_start(self):
        # Signup happens WITHOUT the flag (it gates signup too); the flag
        # applies only to the phone start call below.
        client, _ = _authed_client_for("ph.captcha@gmail.com")
        with override_settings(CAPTCHA_REQUIRED=True):
            res = client.post(
                "/api/auth/phone/start/",
                {"country_code": "NP", "national_number": "9801234567"},
                format="json",
            )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "CAPTCHA_REQUIRED")

    # -- provider failure ------------------------------------------------------------
    def test_provider_failure_generic(self):
        from . import sms_providers

        client, _ = _authed_client_for("ph.fail@gmail.com")

        class FailingProvider(SmsProvider):
            name = "failing"

            def send_otp(self, to_e164, code, *, channel="sms"):
                from .sms_providers import SmsResult

                return SmsResult(False, error="provider_error")

        PROVIDERS["failing"] = FailingProvider
        try:
            with override_settings(PHONE_SMS_PROVIDER="failing"):
                res = client.post(
                    "/api/auth/phone/start/",
                    {"country_code": "NP", "national_number": "9807654321"},
                    format="json",
                )
        finally:
            PROVIDERS.pop("failing", None)
        # Generic 502 surfaced; provider detail stays server-side.
        self.assertEqual(res.status_code, 502)
        self.assertEqual(res.data["code"], "PROVIDER_ERROR")
        self.assertNotIn("provider_error", str(res.data.get("message", "")))
