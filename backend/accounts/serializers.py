import logging

from django.contrib.auth import get_user_model
from django.core.validators import validate_email as django_validate_email
from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken

from .email_normalize import is_disposable, normalize_email

User = get_user_model()
audit = logging.getLogger("accounts.audit")

MAX_EMAIL_LENGTH = 254
MAX_PASSWORD_LENGTH = 128


def validate_email_value(value: str) -> str:
    """Shared email rules: format, max length, disposable block (config-gated)."""
    value = (value or "").strip()
    if len(value) > MAX_EMAIL_LENGTH:
        raise serializers.ValidationError("Email is too long.")
    try:
        django_validate_email(value)
    except Exception:
        raise serializers.ValidationError("Enter a valid email address.")
    if is_disposable(value):
        raise serializers.ValidationError(
            "Disposable email addresses are not allowed. Please use a permanent address."
        )
    return value


def tokens_for_user(user) -> dict:
    """Issue refresh+access with FRESH verification claims from the DB row."""
    refresh = RefreshToken.for_user(user)
    refresh["email_verified"] = bool(user.email_verified)
    refresh["phone_verified"] = bool(user.phone_verified)
    access = refresh.access_token
    access["email_verified"] = bool(user.email_verified)
    access["phone_verified"] = bool(user.phone_verified)
    return {"access": str(access), "refresh": str(refresh)}


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, min_length=8, max_length=MAX_PASSWORD_LENGTH
    )

    class Meta:
        model = User
        fields = ["email", "password"]

    def validate_email(self, value):
        value = validate_email_value(value)
        # Normalized uniqueness (Gmail dot/plus folding): a.b@gmail.com ==
        # ab@gmail.com == ab+x@gmail.com. Case-insensitive exact check kept
        # as a second net for races on non-Gmail domains.
        normalized = normalize_email(value)
        if User.objects.filter(normalized_email=normalized).exists() or User.objects.filter(
            email__iexact=value
        ).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )
        audit.info("signup user_id=%s email=%s", user.pk, user.email)
        return user


class VerifiedTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login serializer: adds fresh email_verified to claims AND response.

    Unverified users CAN log in (they need tokens to reach the verify
    screen); the RequireVerifiedEmail permission gates everything else.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email_verified"] = bool(user.email_verified)
        token["phone_verified"] = bool(user.phone_verified)
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["email_verified"] = bool(self.user.email_verified)
        data["phone_verified"] = bool(self.user.phone_verified)
        data["email"] = self.user.email
        data["is_staff"] = bool(self.user.is_staff)
        audit.info("login user_id=%s verified=%s", self.user.pk, self.user.email_verified)
        return data


class VerifiedTokenRefreshSerializer(TokenRefreshSerializer):
    """Refresh serializer: re-reads the DB row so a just-verified user gets
    the updated claim immediately without re-login."""

    def validate(self, attrs):
        data = super().validate(attrs)
        try:
            refresh = RefreshToken(attrs["refresh"])
            user = User.objects.filter(pk=refresh.get("user_id")).first()
            # Re-read the row so a revoked/changed number (or fresh verify)
            # takes effect on the next access token without re-login.
            data["email_verified"] = bool(user.email_verified) if user else False
            data["phone_verified"] = bool(user.phone_verified) if user else False
        except Exception:
            data["email_verified"] = False
            data["phone_verified"] = False
        return data


class VerifyEmailSerializer(serializers.Serializer):
    # OTP path (preferred): {"code": "123456"} — "otp" accepted as an alias
    # for frontends already sending that key. Codes are matched as strings so
    # leading zeros survive; DRF CharField also trims surrounding whitespace.
    # Legacy link path: {"token": "<64-hex>"} (kept while
    # EMAIL_VERIFICATION_METHOD=link is the default).
    token = serializers.CharField(max_length=128, required=False, allow_blank=True)
    code = serializers.CharField(max_length=12, required=False, allow_blank=True)
    otp = serializers.CharField(max_length=12, required=False, allow_blank=True)

    def validate(self, data):
        code = (data.get("code") or data.get("otp") or "").strip()
        token = (data.get("token") or "").strip()
        if code:
            import re

            if not re.fullmatch(r"\d{6}", code):
                raise serializers.ValidationError(
                    {"code": "Code must be exactly 6 digits."}
                )
            data["code"] = code
            return data
        if token:
            data["token"] = token
            return data
        raise serializers.ValidationError(
            "Provide a verification code or token."
        )


class ResendVerificationSerializer(serializers.Serializer):
    # Both endpoints require authentication, so the target is always the
    # caller's own address — unknown-account enumeration is structurally
    # impossible (no email parameter by design).
    channel = serializers.CharField(required=False, allow_blank=True, default="email")
    captcha_token = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        channel = (data.get("channel") or "email").strip().lower()
        if channel != "email":
            # Phone arrives later by registering a sender; see verification.py.
            raise serializers.ValidationError(
                {"channel": "Unsupported channel. Expected 'email'."}
            )
        data["channel"] = channel
        return data


PHONE_CHANNELS = ("sms", "whatsapp", "voice")


class StartPhoneSerializer(serializers.Serializer):
    """Accept E.164 directly, or country_code + national_number. The
    server re-parses everything — client formatting is never trusted."""

    e164 = serializers.CharField(max_length=32, required=False, allow_blank=True)
    country_code = serializers.CharField(max_length=8, required=False, allow_blank=True)
    national_number = serializers.CharField(max_length=32, required=False, allow_blank=True)
    channel = serializers.ChoiceField(choices=PHONE_CHANNELS, default="sms")
    captcha_token = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if not data.get("e164") and not data.get("national_number"):
            raise serializers.ValidationError(
                "Provide e164 or country_code + national_number."
            )
        if data.get("channel", "sms") not in PHONE_CHANNELS:
            raise serializers.ValidationError("Unsupported channel.")
        return data


class VerifyPhoneSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=4, max_length=12)

    def validate_code(self, value):
        value = (value or "").strip().replace(" ", "")
        if not value.isdigit():
            raise serializers.ValidationError("Code must be numeric.")
        return value


class ResendPhoneSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=PHONE_CHANNELS, default="sms")
    captcha_token = serializers.CharField(required=False, allow_blank=True)


class ChangePhoneSerializer(serializers.Serializer):
    e164 = serializers.CharField(max_length=32, required=False, allow_blank=True)
    country_code = serializers.CharField(max_length=8, required=False, allow_blank=True)
    national_number = serializers.CharField(max_length=32, required=False, allow_blank=True)
    current_password = serializers.CharField(write_only=True, max_length=MAX_PASSWORD_LENGTH)

    def validate(self, data):
        if not data.get("e164") and not data.get("national_number"):
            raise serializers.ValidationError(
                "Provide e164 or country_code + national_number."
            )
        return data


class ChangeEmailSerializer(serializers.Serializer):
    new_email = serializers.EmailField()
    current_password = serializers.CharField(write_only=True, max_length=MAX_PASSWORD_LENGTH)

    def validate_new_email(self, value):
        value = validate_email_value(value)
        normalized = normalize_email(value)
        if User.objects.filter(normalized_email=normalized).exists():
            # Generic message (same shape as other field errors) — the view
            # still returns 200-generic? No: for an AUTHENTICATED change
            # request the account is known, so a field error is fine.
            raise serializers.ValidationError("This email is already in use.")
        return value
