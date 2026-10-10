import logging

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from .email_normalize import normalize_email

logger = logging.getLogger("accounts.audit")


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        # Keep derived fields in one place so creates outside the signup
        # serializer (shell, admin, createsuperuser) stay consistent.
        user.normalized_email = normalize_email(email)
        if not user.pk and not user.email_verified:
            user.email_verified_at = None
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        # This is what makes `python manage.py createsuperuser` become
        # your admin login — same User model, just is_staff/is_superuser=True.
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    # --- Email verification (phase 1). Additive, non-breaking. ---
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    # Canonical identity for uniqueness: lowercase/trimmed (+ Gmail
    # dot/plus folding). Original `email` is kept for display/sending.
    normalized_email = models.CharField(max_length=254, unique=True, null=True, blank=True)
    # Email-change flow: new address waits here until verified via token.
    pending_email = models.EmailField(null=True, blank=True)
    pending_email_normalized = models.CharField(max_length=254, null=True, blank=True)

    # --- Phone verification (phase 2). ---
    # `phone` holds the VERIFIED E.164 number only (unique: one verified
    # owner per number). Unverified claims live in `pending_phone`, so a
    # second account claiming the same number never blocks the real owner —
    # first to verify wins and the loser's pending claim is cleared.
    phone = models.CharField(max_length=32, unique=True, null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    phone_country = models.CharField(max_length=8, null=True, blank=True)
    phone_line_type = models.CharField(max_length=16, null=True, blank=True)
    pending_phone = models.CharField(max_length=32, null=True, blank=True)
    pending_phone_country = models.CharField(max_length=8, null=True, blank=True)
    phone_changes_count = models.IntegerField(default=0)
    # Moderator-only fraud signals (never exposed to end users).
    risk_flags = models.JSONField(default=list, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def add_risk_flag(self, flag: str):
        """Append a moderator-only fraud signal (idempotent, capped)."""
        flags = list(self.risk_flags or [])
        if flag not in flags:
            flags.append(flag)
            self.risk_flags = flags[-20:]
            self.save(update_fields=["risk_flags"])
            logger.info("risk_flag user_id=%s flag=%s", self.pk, flag)

    def mark_phone_verified(self, e164: str, country: str | None = None,
                            line_type: str | None = None):
        """Verify a number with first-verified-wins duplicate handling.

        The verified E.164 moves to `phone` (unique). Any OTHER account still
        holding it as an unverified pending claim gets cleared so it can't
        squat or confuse moderation. Changing to a different country than the
        previously verified one sets a `country_changed` risk flag.
        """
        UserModel = self.__class__
        cleared = (
            UserModel.objects.filter(pending_phone=e164)
            .exclude(pk=self.pk)
            .update(pending_phone=None, pending_phone_country=None)
        )
        if cleared:
            # Never log the number itself — count only.
            logger.info("phone_claim_cleared count=%s winner_user_id=%s", cleared, self.pk)
        if self.phone and self.phone != e164:
            self.phone_changes_count = (self.phone_changes_count or 0) + 1
            if self.phone_changes_count >= 2:
                self.add_risk_flag("multiple_phone_changes")
        if country and self.phone_country and self.phone_country != country:
            self.add_risk_flag("country_changed")
        self.phone = e164
        self.phone_verified = True
        self.phone_verified_at = timezone.now()
        self.phone_country = country
        self.phone_line_type = line_type
        self.pending_phone = None
        self.pending_phone_country = None
        self.save(
            update_fields=[
                "phone",
                "phone_verified",
                "phone_verified_at",
                "phone_country",
                "phone_line_type",
                "pending_phone",
                "pending_phone_country",
                "phone_changes_count",
            ]
        )
        logger.info("phone_verified user_id=%s country=%s", self.pk, country)

    def mark_email_verified(self):
        """Idempotent verify; swaps a pending new address if one exists."""
        self.email_verified = True
        self.email_verified_at = timezone.now()
        if self.pending_email:
            old_email = self.email
            self.email = self.pending_email
            self.normalized_email = self.pending_email_normalized or normalize_email(
                self.pending_email
            )
            self.pending_email = None
            self.pending_email_normalized = None
            logger.info("email_changed user_id=%s old=%s new=%s", self.pk, old_email, self.email)
        self.save(
            update_fields=[
                "email_verified",
                "email_verified_at",
                "email",
                "normalized_email",
                "pending_email",
                "pending_email_normalized",
            ]
        )
        logger.info("email_verified user_id=%s email=%s", self.pk, self.email)


class EmailVerificationToken(models.Model):
    """Single-use verification tokens. Only SHA-256 hashes are stored.

    `type` is the extension point for phase 2: "email_link" | "email_otp"
    today, "phone_otp" later — same table, same lifecycle rules.
    """

    TYPE_EMAIL_LINK = "email_link"
    TYPE_EMAIL_OTP = "email_otp"
    TYPE_PHONE_OTP = "phone_otp"  # phase 2 (SMS), reserved
    TYPE_CHOICES = (
        (TYPE_EMAIL_LINK, "Email link"),
        (TYPE_EMAIL_OTP, "Email OTP"),
        (TYPE_PHONE_OTP, "Phone OTP"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="verification_tokens"
    )
    type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    # SHA-256 hex digest of the raw token/code. Raw value is emailed only.
    token_hash = models.CharField(max_length=64, db_index=True)
    # Address (or phone, phase 2) this token verifies. For email-change
    # flows this is the NEW address, not user.email.
    target = models.CharField(max_length=254)
    target_normalized = models.CharField(max_length=254, db_index=True)
    # Delivery channel for phone OTPs: sms | whatsapp | voice. Unused by email.
    channel = models.CharField(max_length=16, default="sms")
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    attempts = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["user", "used_at"]),
            models.Index(fields=["token_hash", "user"]),
        ]

    @property
    def is_usable(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])


class VerificationCode(models.Model):
    """Channel-agnostic one-time codes (email OTP today, phone later).

    Only ONE active (unconsumed, unexpired) code exists per
    (user, channel, target) — issuing a new code consumes the previous one.
    Only the HMAC-SHA256 hash is stored; the raw code lives only in the
    outbound message. See accounts/verification.py for the service layer.
    """

    CHANNEL_EMAIL = "email"
    CHANNEL_PHONE = "phone"  # reserved: added later by registering a sender
    CHANNEL_CHOICES = (
        (CHANNEL_EMAIL, "Email"),
        (CHANNEL_PHONE, "Phone"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="verification_codes"
    )
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES)
    # The address/number being verified, already normalized by the service
    # layer (lowercased email / E.164 phone) so lookups are exact matches.
    target = models.CharField(max_length=254, db_index=True)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "channel", "target", "consumed_at"]),
        ]

    @property
    def is_active(self) -> bool:
        return self.consumed_at is None and self.expires_at > timezone.now()

    def mark_consumed(self):
        self.consumed_at = timezone.now()
        self.save(update_fields=["consumed_at"])


class VerificationSendLog(models.Model):
    """Append-only log backing resend rate limits (per-user/day, per-IP/day).

    A model (not cache) is used so limits survive worker restarts and work
    across processes without extra infra.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="verification_sends",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    kind = models.CharField(max_length=16, default="email")  # "email" | "phone"
    # Full destination (E.164) + country for per-number caps, country hourly
    # caps, and sequential-number abuse detection. Operational data only —
    # mask it in every log line (see phone_normalize.mask_phone).
    target = models.CharField(max_length=254, null=True, blank=True)
    country = models.CharField(max_length=8, null=True, blank=True)
    provider = models.CharField(max_length=32, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["ip_address", "created_at"]),
            models.Index(fields=["target", "created_at"]),
            models.Index(fields=["country", "created_at"]),
        ]

# Create your models here.
