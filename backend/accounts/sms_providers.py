"""Pluggable SMS providers + config-driven country routing.

Interface (add providers by subclassing — routing table needs no code change):

    class SmsProvider:
        name = "..."
        def send_otp(self, to_e164, code, *, channel="sms") -> SmsResult
        def check_otp(self, to_e164, code) -> bool | None  # None = local check
        def supports_channel(self, channel) -> bool

Modes (PHONE_VERIFICATION_PROVIDER_MODE):
- "custom"  (default): we generate + hash the OTP locally and send it through
  a gateway provider (Console in dev, TwilioSms/MSG91-style in prod).
- "managed": Twilio Verify / Firebase-style — the provider sends AND checks
  codes; we never see or store OTP material, only audit marker rows.

Routing (PHONE_SMS_ROUTES, e.g. {"+977": "local_np", "+91": "india_dlt"}):
longest-prefix match on the E.164 number, else PHONE_SMS_PROVIDER default.
"""

import logging

from django.conf import settings

from .phone_normalize import mask_phone

logger = logging.getLogger("accounts.mailer")
audit = logging.getLogger("accounts.audit")


class SmsResult:
    def __init__(self, ok, sid="", error="", fallback_hint=""):
        self.ok = ok
        self.sid = sid
        self.error = error
        self.fallback_hint = fallback_hint  # e.g. "undelivered" -> offer voice


class SmsProvider:
    name = "base"
    supports_voice = False
    supports_whatsapp = False

    def send_otp(self, to_e164, code, *, channel="sms"):
        raise NotImplementedError

    def check_otp(self, to_e164, code):
        """Provider-side check (managed mode). None = check locally."""
        return None

    def supports_channel(self, channel):
        if channel == "sms":
            return True
        if channel == "voice":
            return self.supports_voice
        if channel == "whatsapp":
            return self.supports_whatsapp
        return False


class ConsoleSmsProvider(SmsProvider):
    """Dev default: prints to console, sends nothing real.

    Mirrors the email console backend. In DEBUG the code is included (dev
    convenience, same rule as the mailer); in production only metadata.
    """

    name = "console"
    supports_voice = True
    supports_whatsapp = True

    def send_otp(self, to_e164, code, *, channel="sms"):
        if settings.DEBUG:
            logger.info(
                "DEV SMS [%s] to %s code=%s (no real SMS sent)",
                channel,
                mask_phone(to_e164),
                code,
            )
        else:
            logger.info("SMS [%s] queued to %s", channel, mask_phone(to_e164))
        return SmsResult(True, sid="dev-console")


class TwilioSmsProvider(SmsProvider):
    """Custom-mode gateway via Twilio Programmable SMS (urllib, no new deps).

    India (+91): pass MessagingService SID with a DLT-registered sender;
    DLT_ENTITY_ID / DLT_TEMPLATE_ID are applied as parameters for providers
    that need them explicitly (documented in provider notes).
    """

    name = "twilio_sms"
    supports_voice = True
    supports_whatsapp = True

    def __init__(self):
        self.account = getattr(settings, "TWILIO_ACCOUNT_SID", "") or ""
        self.token = getattr(settings, "TWILIO_AUTH_TOKEN", "") or ""
        self.sender = getattr(settings, "TWILIO_SENDER_ID", "") or ""
        self.service_sid = getattr(settings, "TWILIO_MESSAGING_SERVICE_SID", "") or ""

    def _post(self, url, data):
        import base64
        import urllib.parse
        import urllib.request

        body = urllib.parse.urlencode(data).encode()
        creds = base64.b64encode(f"{self.account}:{self.token}".encode()).decode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Authorization": f"Basic {creds}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            import json

            return json.loads(resp.read().decode())

    def send_otp(self, to_e164, code, *, channel="sms"):
        from .phone_normalize import mask_phone as _mask

        body = sms_body(code)
        data = {"To": to_e164, "Body": body}
        if self.service_sid:
            data["MessagingServiceSid"] = self.service_sid
        elif self.sender:
            data["From"] = self.sender
        if to_e164.startswith("+91"):
            # DLT placeholders — harmless if the upstream ignores them.
            if getattr(settings, "DLT_ENTITY_ID", ""):
                data["EntityId"] = settings.DLT_ENTITY_ID
            if getattr(settings, "DLT_TEMPLATE_ID", ""):
                data["TemplateId"] = settings.DLT_TEMPLATE_ID
        try:
            if channel != "sms":
                return SmsResult(False, error=f"channel {channel} needs Verify API")
            payload = self._post(
                f"https://api.twilio.com/2010-04-01/Accounts/{self.account}/Messages.json",
                data,
            )
            return SmsResult(True, sid=payload.get("sid", ""))
        except Exception as exc:
            logger.error("SMS send failed to %s: %s", _mask(to_e164), exc)
            return SmsResult(False, error="provider_error", fallback_hint="retry_or_voice")


class TwilioVerifyProvider(SmsProvider):
    """Managed mode: Twilio Verify sends AND checks codes server-side.

    We never generate, see, or store OTP digits — check_otp returns a real
    verdict. Channels sms/voice/whatsapp are native to Verify.
    """

    name = "twilio_verify"
    supports_voice = True
    supports_whatsapp = True

    def __init__(self):
        self.account = getattr(settings, "TWILIO_ACCOUNT_SID", "") or ""
        self.token = getattr(settings, "TWILIO_AUTH_TOKEN", "") or ""
        self.service_sid = getattr(settings, "TWILIO_VERIFY_SERVICE_SID", "") or ""

    def _post(self, path, data):
        import base64
        import json
        import urllib.parse
        import urllib.request

        body = urllib.parse.urlencode(data).encode()
        creds = base64.b64encode(f"{self.account}:{self.token}".encode()).decode()
        req = urllib.request.Request(
            f"https://verify.twilio.com{path}",
            data=body,
            headers={"Authorization": f"Basic {creds}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())

    def send_otp(self, to_e164, code=None, *, channel="sms"):
        try:
            payload = self._post(
                f"/v2/Services/{self.service_sid}/Verifications",
                {"To": to_e164, "Channel": channel},
            )
            return SmsResult(True, sid=payload.get("sid", ""))
        except Exception as exc:
            logger.error(
                "Verify send failed to %s: %s",
                mask_phone(to_e164),
                exc,
            )
            return SmsResult(False, error="provider_error", fallback_hint="retry")

    def check_otp(self, to_e164, code):
        try:
            payload = self._post(
                f"/v2/Services/{self.service_sid}/VerificationCheck",
                {"To": to_e164, "Code": code},
            )
            return payload.get("status") == "approved"
        except Exception as exc:
            logger.error("Verify check failed for %s: %s", mask_phone(to_e164), exc)
            return False


def sms_body(code: str) -> str:
    """Short body: app name + code + expiry + never-share warning.

    Kept short for single-segment delivery. For Android web autofill, append
    the origin-bound `<#> ... <app-hash>` format (needs the release key
    hash — see provider notes).
    """
    minutes = int(getattr(settings, "PHONE_OTP_EXPIRY_MINUTES", 5))
    return (
        f"Sabha Gachhi code: {code}. Expires in {minutes} min. "
        "Never share this code with anyone."
    )


PROVIDERS = {
    "console": ConsoleSmsProvider,
    "twilio_sms": TwilioSmsProvider,
    "twilio_verify": TwilioVerifyProvider,
}


def provider_mode() -> str:
    mode = getattr(settings, "PHONE_VERIFICATION_PROVIDER_MODE", "custom")
    return mode if mode in ("custom", "managed") else "custom"


def default_provider_name() -> str:
    if provider_mode() == "managed":
        return getattr(settings, "PHONE_SMS_PROVIDER", "twilio_verify")
    return getattr(settings, "PHONE_SMS_PROVIDER", "console")


def get_provider_for_e164(to_e164: str) -> SmsProvider:
    """Longest-prefix routing table (PHONE_SMS_ROUTES), else the default."""
    routes = getattr(settings, "PHONE_SMS_ROUTES", {}) or {}
    best, best_len = None, -1
    for prefix, name in routes.items():
        if to_e164.startswith(prefix) and len(prefix) > best_len:
            best, best_len = name, len(prefix)
    name = best or default_provider_name()
    cls = PROVIDERS.get(name, ConsoleSmsProvider)
    try:
        return cls()
    except Exception as exc:
        logger.error("SMS provider %s init failed: %s", name, exc)
        return ConsoleSmsProvider()
