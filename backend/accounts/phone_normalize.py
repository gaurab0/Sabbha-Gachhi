"""Phone normalization + policy checks (server-side, never trust the client).

Uses `phonenumbers` (Python port of libphonenumber) with `is_valid()`
(full validation, not just `is_possible()`). All helpers are pure apart
from settings reads so they stay unit-testable.
"""

import phonenumbers
from django.conf import settings

# Line types we refuse outright or conditionally.
LINE_MOBILE = "mobile"
LINE_LANDLINE = "landline"
LINE_VOIP = "voip"
LINE_UNKNOWN = "unknown"


def allowed_countries() -> list:
    """ISO codes allowed to receive OTPs. Config-only change, no deploy."""
    raw = getattr(settings, "PHONE_ALLOWED_COUNTRIES", ["NP", "IN"])
    if isinstance(raw, str):
        raw = [c.strip().upper() for c in raw.split(",") if c.strip()]
    return [str(c).strip().upper() for c in (raw or [])]


def parse_phone(raw: str, default_country: str | None = None):
    """Parse + validate. Returns (e164, country_iso, line_hint) or (None, reason, None).

    `default_country` only interprets numbers given without a country prefix;
    the user's explicit dropdown choice is what counts (IP guess may only
    preselect the dropdown client-side).
    """
    text = (raw or "").strip().replace(" ", "").replace("-", "")
    if not text:
        return None, "invalid_number", None
    try:
        if text.startswith("+"):
            number = phonenumbers.parse(text, None)
        elif text.startswith("00"):
            number = phonenumbers.parse("+" + text[2:], None)
        elif default_country:
            number = phonenumbers.parse(text, default_country.upper())
        else:
            return None, "country_required", None
    except Exception:
        return None, "invalid_number", None
    # Full validation — is_possible() alone lets through unassigned ranges.
    if not phonenumbers.is_valid_number(number):
        return None, "invalid_number", None
    e164 = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
    country = phonenumbers.region_code_for_number(number)
    return e164, (country or "UNKNOWN"), None


def check_country_allowed(country_iso: str) -> bool:
    return (country_iso or "").upper() in allowed_countries()


def mask_phone(e164: str) -> str:
    """Mask for UI/logs, e.g. +9779812345678 -> +977 98****5678."""
    digits = "".join(c for c in (e164 or "") if c.isdigit())
    if len(digits) < 7:
        return "+**"
    cc_len = len(digits) - 10 if len(digits) > 10 else 0
    cc = f"+{digits[:cc_len]} " if cc_len else "+"
    rest = digits[cc_len:]
    return f"{cc}{rest[:2]}****{rest[-4:]}"


def lookup_line_type(e164: str) -> tuple[str, str | None]:
    """Best-effort line-type lookup. Returns (line_type, risk_flag|None).

    Layer 1 (offline, always): libphonenumber metadata via number_type().
    FIXED_LINE and premium/toll ranges are definitive blocks; VOIP metadata
    is flagged. FIXED_LINE_OR_MOBILE and MOBILE fall through to layer 2.
    Layer 2 (Twilio Lookup, only if credentials configured): can reclassify
    mobile-looking ranges as VoIP. Lookup failures follow
    PHONE_LOOKUP_FAIL_MODE ("allow" + `lookup_failed` risk flag, or "block").
    """
    try:
        number = phonenumbers.parse(e164, None)
        local = phonenumbers.number_type(number)
    except Exception:
        local = None
    if local == phonenumbers.PhoneNumberType.FIXED_LINE:
        return LINE_LANDLINE, None
    if local in (
        phonenumbers.PhoneNumberType.TOLL_FREE,
        phonenumbers.PhoneNumberType.PREMIUM_RATE,
        phonenumbers.PhoneNumberType.SHARED_COST,
    ):
        return LINE_LANDLINE, "non_mobile_range"
    if local == phonenumbers.PhoneNumberType.VOIP:
        return LINE_VOIP, "voip_number"

    provider = _lookup_provider()
    if provider is None:
        return LINE_UNKNOWN, None
    try:
        return provider(e164)
    except Exception as exc:
        import logging

        logging.getLogger("accounts.audit").warning(
            "phone lookup failed for %s: %s", mask_phone(e164), exc
        )
        if (getattr(settings, "PHONE_LOOKUP_FAIL_MODE", "allow") or "allow") == "block":
            return LINE_UNKNOWN, "lookup_failed_blocked"
        return LINE_UNKNOWN, "lookup_failed"


def _lookup_provider():
    """Twilio Lookup hook (urllib only, no new deps). None = not configured."""
    account = getattr(settings, "TWILIO_ACCOUNT_SID", "") or ""
    token = getattr(settings, "TWILIO_AUTH_TOKEN", "") or ""
    if not (account and token):
        return None

    import base64
    import json
    import urllib.parse
    import urllib.request

    def _lookup(e164: str) -> tuple[str, str | None]:
        url = (
            "https://lookups.twilio.com/v2/PhoneNumbers/"
            + urllib.parse.quote(e164, safe="")
            + "?Fields=line_type_intelligence"
        )
        creds = base64.b64encode(f"{account}:{token}".encode()).decode()
        req = urllib.request.Request(url, headers={"Authorization": f"Basic {creds}"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode())
        line_type = (
            (payload.get("line_type_intelligence") or {}).get("type") or "unknown"
        ).lower()
        if "voip" in line_type:
            return LINE_VOIP, "voip_number"
        if "landline" in line_type:
            return LINE_LANDLINE, None
        if "mobile" in line_type:
            return LINE_MOBILE, None
        return LINE_UNKNOWN, None

    return _lookup
