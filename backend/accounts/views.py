import logging
import smtplib
import socket
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .captcha import verify_captcha
from .email_normalize import mask_email, normalize_email
from .mailer import build_link_email, send_verification_email
from .models import EmailVerificationToken, VerificationSendLog
from .serializers import (
    ChangeEmailSerializer,
    ResendVerificationSerializer,
    SignupSerializer,
    VerifiedTokenObtainPairSerializer,
    VerifiedTokenRefreshSerializer,
    VerifyEmailSerializer,
    tokens_for_user,
)
from .verification import (
    hash_secret,
    issue_token,
    secrets_equal,
    verification_method,
)

audit = logging.getLogger("accounts.audit")
User = get_user_model()

# Shared 60s cooldown used by the phone flow's send limiter. (The email
# resend endpoint now uses OTP_RESEND_COOLDOWN_SECONDS + the service-layer
# last_sent_at instead, with explicit 429s rather than generic 200s.)
RESEND_COOLDOWN_SECONDS = 60


def _client_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _dispatch_email(message, raw_secret: str | None = None) -> None:
    """Non-blocking send: Celery first, synchronous fallback if broker is down.

    `retry=False` on publish is deliberate: kombu's default publish-retry
    loop would block the request for ~a minute when Redis is down. Fail
    fast here and send inline instead, so signup never hangs.
    """
    payload = {
        "to_email": message.to_email,
        "subject": message.subject,
        "text_body": message.text_body,
        "html_body": message.html_body,
    }
    try:
        from .tasks import send_verification_email_task

        send_verification_email_task.apply_async(args=[payload], retry=False)
    except Exception as exc:  # broker down: send inline so signup still works
        logging.getLogger("accounts.mailer").warning(
            "Celery unavailable, sending verification email inline: %s", exc
        )
        send_verification_email(message, log_secret=raw_secret)


def _acquire_resend_lock(user_id) -> bool:
    """Best-effort per-user resend mutex (atomic add-if-absent, 60s TTL).

    Closes the check-then-act race where two requests arriving in the same
    second both pass the cooldown check before either writes its send row.
    Uses the Django cache (locmem by default: per-process only — point CACHES
    at Redis for multi-process deploys; DRF throttling has the same limit).
    Callers must release via _release_resend_lock in a finally block; the
    TTL is the backstop if the process dies mid-request.
    """
    from django.core.cache import cache

    return cache.add(f"resend-email-lock:{user_id}", 1, timeout=60)


def _release_resend_lock(user_id) -> None:
    from django.core.cache import cache

    cache.delete(f"resend-email-lock:{user_id}")


def _issue_and_send(user, target_email: str, *, synchronous: bool = False):
    """Create + dispatch a verification message. Returns (method, sent).

    `sent` is True/False only when the outcome is known synchronously (OTP
    path, or link path with synchronous=True). Plain link dispatch stays
    async (fire-and-forget, correct for signup) and returns sent=None —
    outcome unknown. NOTE: no "verification_sent" audit here; the mailer
    logs it only after a confirmed send, so dispatch-time logging can't lie.
    """
    from .verification import issue_code

    method = verification_method()
    if method == "otp":
        return method, issue_code(user, "email", target_email)
    token_row, raw = issue_token(user, target_email)
    minutes = int(getattr(settings, "EMAIL_LINK_EXPIRY_MINUTES", 60))
    link = f"{settings.FRONTEND_URL.rstrip('/')}/verify-email?token={raw}"
    message = build_link_email(target_email, link, minutes)
    if synchronous:
        # Resend path: block for the verdict so failures map to 503.
        sent = send_verification_email(message, user_id=user.pk)
        if not sent:
            # Don't leave a valid token for a mail that never went out.
            token_row.mark_used()
        return method, sent
    _dispatch_email(message, raw_secret=raw if settings.DEBUG else None)
    return method, None


def _log_send(user, ip: str | None, kind: str = "email") -> None:
    VerificationSendLog.objects.create(user=user, ip_address=ip, kind=kind)


class SignupView(APIView):
    """POST /api/auth/signup/ — creates an unverified user and emails a token."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        if not verify_captcha(request.data.get("captcha_token"), _client_ip(request)):
            return Response(
                {"code": "CAPTCHA_REQUIRED", "message": "Captcha verification failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        method, _ = _issue_and_send(user, user.email)
        _log_send(user, _client_ip(request))
        tokens = tokens_for_user(user)
        return Response(
            {
                "message": "Account created. Please verify your email to continue.",
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "email": user.email,
                "email_verified": False,
                "is_staff": bool(user.is_staff),
                "verification_method": method,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ — works for unverified users; response + claims
    carry email_verified so the frontend can route to the verify screen."""

    serializer_class = VerifiedTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RefreshView(TokenRefreshView):
    """POST /api/auth/login/refresh/ — re-reads the DB so the fresh access
    token carries the current email_verified claim."""

    serializer_class = VerifiedTokenRefreshSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class MeView(APIView):
    """GET /api/auth/me/ — verification status for guards. Exempt from the
    verified-email gate by design."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .phone_normalize import mask_phone

        user = request.user
        return Response(
            {
                "email": user.email,
                "email_verified": bool(user.email_verified),
                "email_verified_at": user.email_verified_at,
                "is_staff": bool(user.is_staff),
                "has_pending_email": bool(getattr(user, "pending_email", None)),
                "phone_verified": bool(getattr(user, "phone_verified", False)),
                "phone_verified_at": getattr(user, "phone_verified_at", None),
                "phone_masked": mask_phone(user.phone) if user.phone else None,
                "phone_country": getattr(user, "phone_country", None),
            }
        )


class VerifyEmailView(APIView):
    """POST /api/auth/verify-email/ — OTP {"code"} (or "otp" alias), or legacy
    link {"token"} while EMAIL_VERIFICATION_METHOD=link.

    Requires authentication: a user can only ever verify their OWN address
    (the target is derived from request.user, never from the body), which
    makes account enumeration structurally impossible here.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "verify"

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data.get("code"):
            return self._verify_otp(request.user, data["code"])
        return self._verify_link(request.user, data.get("token", ""))

    def _verify_otp(self, user, code):
        from .verification import VerificationResult, verify_code

        target = (user.pending_email_normalized
                  or normalize_email(user.email or ""))
        if user.email_verified and not user.pending_email:
            # Idempotent success: nothing to prove, burn no attempts.
            audit.info("verify_ok user_id=%s already_verified", user.pk)
            return Response({"detail": "Email already verified"})
        try:
            result = verify_code(
                user, "email", target, code,
                on_verified=user.mark_email_verified,
            )
        except Exception:
            # verify_code only raises on infrastructure failure (e.g. the DB
            # save inside on_verified). The row is already consumed at that
            # point, so the user simply requests a new code — a clean 503,
            # never a silent 500 or a half-verified account.
            audit.exception("verify_failed user_id=%s reason=verify_error", user.pk)
            return Response(
                {
                    "code": "verification_failed",
                    "detail": "Could not verify right now. Please try again shortly.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if result is VerificationResult.OK:
            audit.info("verify_ok user_id=%s", user.pk)
            return Response({"detail": "Email verified"})
        mapping = {
            VerificationResult.INVALID: (
                "invalid", "That code is incorrect. Check and try again."
            ),
            VerificationResult.EXPIRED: (
                "expired", "That code has expired. Request a new one."
            ),
            VerificationResult.TOO_MANY_ATTEMPTS: (
                "too_many_attempts",
                "Too many wrong attempts. Request a new code.",
            ),
            VerificationResult.NOT_FOUND: (
                "not_found", "No active code found. Request a new code."
            ),
        }
        code_str, detail = mapping.get(
            result, ("invalid", "Invalid or expired code.")
        )
        # The failure REASON is logged server-side (never the code itself);
        # the client gets the explicit machine-readable code instead of the
        # old bare-400 mystery body.
        audit.info("verify_failed user_id=%s reason=%s", user.pk, result.value)
        return Response(
            {"code": code_str, "detail": detail},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _verify_link(self, user, raw: str):
        digest = hash_secret(raw or "")
        row = (
            EmailVerificationToken.objects.filter(
                user=user,
                type=EmailVerificationToken.TYPE_EMAIL_LINK,
                token_hash=digest,
                used_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )
        if row is None or not secrets_equal(row.token_hash, digest):
            audit.info("verify_failed reason=invalid")
            return Response(
                {"code": "INVALID_TOKEN", "message": "This verification link is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = row.user
        if row.expires_at <= timezone.now():
            row.mark_used()
            audit.info("verify_failed user_id=%s reason=expired", user.pk)
            return Response(
                {
                    "code": "EXPIRED_TOKEN",
                    "message": "This verification link has expired. Request a new one.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        problem = self._check_target(user, row)
        if problem:
            return problem
        row.mark_used()
        user.mark_email_verified()
        tokens = tokens_for_user(user)
        return Response(
            {
                "message": "Email verified.",
                "email_verified": True,
                "email": user.email,
                "access": tokens["access"],
                "refresh": tokens["refresh"],
            }
        )

    @staticmethod
    def _check_target(user, row):
        """Token must verify the current address OR a pending new address."""
        current = normalize_email(user.email or "")
        pending = (user.pending_email_normalized or "").strip().lower()
        target = (row.target_normalized or "").strip().lower()
        if target and target not in (current, pending):
            audit.info("verify_failed user_id=%s reason=target_mismatch", user.pk)
            row.mark_used()
            return Response(
                {"code": "INVALID_TOKEN", "message": "This verification link is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if getattr(user, "email_verified", False) and not user.pending_email and target == current:
            row.mark_used()  # idempotent re-click: consume, confirm state
            tokens = tokens_for_user(user)
            return Response(
                {
                    "message": "Email already verified.",
                    "email_verified": True,
                    "email": user.email,
                    "access": tokens["access"],
                    "refresh": tokens["refresh"],
                }
            )
        return None


def _email_cooldown_remaining(user, target: str) -> int:
    """Seconds until another send is allowed for (user, target); 0 = send now.

    Looks at the newest send evidence across both issuance paths (OTP code
    rows carry last_sent_at; link sends are tracked in VerificationSendLog).
    """
    from .models import VerificationCode

    cooldown = int(getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60))
    now = timezone.now()
    candidates = []
    last_code = (
        VerificationCode.objects.filter(user=user, channel="email", target=target)
        .exclude(last_sent_at__isnull=True)
        .order_by("-last_sent_at")
        .first()
    )
    if last_code and last_code.last_sent_at:
        candidates.append(last_code.last_sent_at)
    last_log = (
        VerificationSendLog.objects.filter(user=user, kind="email")
        .order_by("-created_at")
        .first()
    )
    if last_log:
        candidates.append(last_log.created_at)
    if not candidates:
        return 0
    elapsed = (now - max(candidates)).total_seconds()
    return max(0, int(cooldown - elapsed))


def _email_target_hourly_remaining(user, target: str) -> int:
    """Seconds until the per-target hourly send budget refills; 0 = budget left.

    Counts sends in the last hour across both issuance paths (OTP code rows
    + legacy link/OTP token rows for this target).
    """
    from .models import EmailVerificationToken, VerificationCode

    cap = int(getattr(settings, "OTP_MAX_SENDS_PER_HOUR_PER_TARGET", 5))
    hour_ago = timezone.now() - timedelta(hours=1)
    code_times = list(
        VerificationCode.objects.filter(
            user=user, channel="email", target=target, created_at__gte=hour_ago
        ).values_list("created_at", flat=True)
    )
    link_times = list(
        EmailVerificationToken.objects.filter(
            user=user,
            type__in=[
                EmailVerificationToken.TYPE_EMAIL_LINK,
                EmailVerificationToken.TYPE_EMAIL_OTP,
            ],
            target_normalized=target,
            created_at__gte=hour_ago,
        ).values_list("created_at", flat=True)
    )
    stamps = sorted(code_times + link_times)
    if len(stamps) < cap:
        return 0
    retry_at = stamps[0] + timedelta(hours=1)
    return max(0, int((retry_at - timezone.now()).total_seconds()))


def _email_daily_remaining(user, ip: str | None) -> int:
    """Seconds until the daily budgets refill; 0 = budget left.

    5/day per user, 10/day per IP. Counts confirmed sends only; failed SMTP
    sends return 503 and do not consume the user's daily budget.
    """
    day_ago = timezone.now() - timedelta(days=1)
    user_stamps = list(
        VerificationSendLog.objects.filter(
            user=user, kind="email", created_at__gte=day_ago
        ).values_list("created_at", flat=True)
    )
    if len(user_stamps) >= 5:
        retry_at = min(user_stamps) + timedelta(days=1)
        return max(0, int((retry_at - timezone.now()).total_seconds()))
    if ip:
        ip_stamps = list(
            VerificationSendLog.objects.filter(
                ip_address=ip, kind="email", created_at__gte=day_ago
            ).values_list("created_at", flat=True)
        )
        if len(ip_stamps) >= 10:
            retry_at = min(ip_stamps) + timedelta(days=1)
            return max(0, int((retry_at - timezone.now()).total_seconds()))
    return 0


class ResendVerificationView(APIView):
    """POST /api/auth/resend-verification/ — body {"channel": "email"}.

    Requires authentication: the target is always the caller's own address
    (pending new address if an email change is in flight), so there is no
    unknown-account case to enumerate.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "resend"

    def post(self, request):
        data = ResendVerificationSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        ip = _client_ip(request)
        if not verify_captcha(data.validated_data.get("captcha_token"), ip):
            return Response(
                {"code": "CAPTCHA_REQUIRED", "message": "Captcha verification failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        target = user.pending_email_normalized or normalize_email(user.email or "")

        # Race guard: two requests in the same second must not both pass the
        # checks below before either writes its send row (MongoDB backend has
        # no transactions/select_for_update — the lock is the guard).
        if not _acquire_resend_lock(user.pk):
            audit.info("resend_blocked user_id=%s reason=locked", user.pk)
            return Response(
                {"code": "cooldown", "retry_after_seconds": 5},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": "5"},
            )
        try:
            wait = _email_cooldown_remaining(user, target)
            if wait > 0:
                audit.info("resend_blocked user_id=%s reason=cooldown", user.pk)
                return Response(
                    {"code": "cooldown", "retry_after_seconds": wait},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={"Retry-After": str(wait)},
                )
            wait = _email_target_hourly_remaining(user, target)
            if wait > 0:
                audit.info("resend_blocked user_id=%s reason=target_hourly_cap", user.pk)
                return Response(
                    {"code": "rate_limited", "retry_after_seconds": wait},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={"Retry-After": str(wait)},
                )
            wait = _email_daily_remaining(user, ip)
            if wait > 0:
                audit.info("resend_blocked user_id=%s reason=daily_cap", user.pk)
                return Response(
                    {
                        "code": "resend_daily_limit",
                        "retry_after_seconds": wait,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={"Retry-After": str(wait)},
                )

            method = verification_method()
            try:
                if method == "otp":
                    # Synchronous by design: issue_code returns the sender
                    # verdict so a failed send maps to 503 instead of a false
                    # 200.
                    from .verification import issue_code

                    sent: bool | None = issue_code(user, "email", target)
                else:
                    # Link mode must also block for the verdict — an async
                    # dispatch can never produce an honest 503.
                    _, sent = _issue_and_send(
                        user, user.pending_email or user.email, synchronous=True
                    )
            except (smtplib.SMTPException, OSError, socket.timeout):
                logging.getLogger("accounts.mailer").exception(
                    "verification_email_failed user_id=%s", user.pk
                )
                sent = False
            if not sent:
                audit.warning("resend_failed user_id=%s reason=send_failed", user.pk)
                return Response(
                    {
                        "code": "email_service_unavailable",
                        "detail": "Could not send verification email. Please try again shortly.",
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            _log_send(user, ip)
            audit.info("verification_email_sent user_id=%s", user.pk)
            detail = (
                "Verification code sent"
                if method == "otp"
                else "Verification link sent"
            )
            return Response(
                {
                    "detail": detail,
                    "cooldown_seconds": int(
                        getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60)
                    ),
                }
            )
        finally:
            _release_resend_lock(user.pk)


class ChangeEmailView(APIView):
    """POST /api/auth/email/change/ — stage a new address; swap only after
    the NEW address is verified. Old address gets a heads-up email."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .models import VerificationCode

        serializer = ChangeEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            return Response(
                {"code": "INVALID_PASSWORD", "message": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        new_email = serializer.validated_data["new_email"].strip()
        if normalize_email(new_email) == normalize_email(user.email or ""):
            return Response(
                {"code": "SAME_EMAIL", "message": "This is already your email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.pending_email = new_email
        user.pending_email_normalized = normalize_email(new_email)
        # Verification is tied to the CURRENT email: changing it resets the
        # flag and kills every outstanding code/token, so a stale code for
        # the old address can never verify the account.
        user.email_verified = False
        user.email_verified_at = None
        user.save(
            update_fields=[
                "pending_email",
                "pending_email_normalized",
                "email_verified",
                "email_verified_at",
            ]
        )
        now = timezone.now()
        VerificationCode.objects.filter(
            user=user, channel="email", consumed_at__isnull=True
        ).update(consumed_at=now)
        EmailVerificationToken.objects.filter(
            user=user,
            type__in=[
                EmailVerificationToken.TYPE_EMAIL_LINK,
                EmailVerificationToken.TYPE_EMAIL_OTP,
            ],
            used_at__isnull=True,
        ).update(used_at=now)

        # Fire-and-forget: change-email confirmation happens on verify.
        _issue_and_send(user, new_email)
        _log_send(user, _client_ip(request))
        try:  # best-effort heads-up to the old address; never blocks
            send_mail(
                "Your Sabha Gachhi email change",
                f"A request was made to change your account email to {mask_email(new_email)}. "
                "If this wasn't you, please contact support.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception:
            pass
        audit.info("email_change_requested user_id=%s", user.pk)
        return Response(
            {
                "message": "Verification sent to your new address.",
                "pending_email_masked": mask_email(new_email),
                "email_verified": False,
            }
        )


# Generic phone response — identical whether or not the number is known
# elsewhere (no enumeration via start/resend).
_PHONE_GENERIC_RESPONSE = {
    "message": "If this number can receive SMS, a verification code has been sent."
}
_PHONE_GENERIC = _PHONE_GENERIC_RESPONSE


class _ProviderDown(Exception):
    """Provider failed after retry — view maps to generic 502."""


class _PhoneFlowMixin:
    """Shared guards/limits for the phone OTP endpoints."""

    def _require_email_first(self, user):
        """Verification order is email, then phone (configurable)."""
        if getattr(settings, "PHONE_REQUIRE_EMAIL_FIRST", True) and not user.email_verified:
            from .permissions import email_not_verified_response

            return email_not_verified_response()
        return None

    def _resolve_input(self, data):
        """Server-side parse of country_code+national_number or raw e164.
        Returns (e164|None, country|None)."""
        from .phone_normalize import parse_phone

        if data.get("e164"):
            e164, country, _ = parse_phone(data["e164"])
        else:
            e164, country, _ = parse_phone(
                data.get("national_number", ""), data.get("country_code") or None
            )
        return e164, country

    def _send_limits(self, user, ip, e164, country):
        """Coarse limits + abuse/cost guards. Returns (allowed, reason).

        Layers: per-user cooldown + daily cap, per-number daily cap, per-IP
        daily cap, per-country hourly circuit breaker, global daily cap, and
        sequential/multi-number burst detection. All denials are generic to
        the client; reasons go to the audit log only.
        """
        from .phone_normalize import mask_phone

        now = timezone.now()
        day_ago = now - timezone.timedelta(days=1)
        hour_ago = now - timezone.timedelta(hours=1)
        sends = VerificationSendLog.objects.filter(kind="phone")
        masked = mask_phone(e164)

        last = sends.filter(user=user).order_by("-created_at").first()
        if last and (now - last.created_at).total_seconds() < RESEND_COOLDOWN_SECONDS:
            return False, "cooldown"
        if sends.filter(user=user, created_at__gte=day_ago).count() >= int(
            getattr(settings, "PHONE_MAX_PER_USER_PER_DAY", 5)
        ):
            return False, "user_cap"
        if sends.filter(target=e164, created_at__gte=day_ago).count() >= int(
            getattr(settings, "PHONE_MAX_PER_NUMBER_PER_DAY", 3)
        ):
            return False, "number_cap"
        if ip and sends.filter(ip_address=ip, created_at__gte=day_ago).count() >= int(
            getattr(settings, "PHONE_MAX_PER_IP_PER_DAY", 10)
        ):
            return False, "ip_cap"
        country_cap = int(getattr(settings, "PHONE_COUNTRY_HOURLY_CAP", 50))
        if sends.filter(country=country, created_at__gte=hour_ago).count() >= country_cap:
            audit.warning(
                "phone_circuit_open country=%s user_id=%s", country, user.pk
            )
            return False, "circuit_open"
        if sends.filter(created_at__gte=day_ago).count() >= int(
            getattr(settings, "PHONE_GLOBAL_DAILY_CAP", 1000)
        ):
            audit.warning("phone_global_cap_hit user_id=%s", user.pk)
            return False, "global_cap"
        if ip:
            recent_targets = list(
                sends.filter(ip_address=ip, created_at__gte=hour_ago)
                .exclude(target__isnull=True)
                .values_list("target", flat=True)[:20]
            )
            if len(set(recent_targets)) >= int(
                getattr(settings, "PHONE_BURST_DISTINCT_NUMBERS", 8)
            ):
                audit.warning(
                    "phone_burst_block ip=%s distinct=%s user_id=%s",
                    ip,
                    len(set(recent_targets)),
                    user.pk,
                )
                return False, "burst"
        fail_ratio = self._country_fail_ratio(country)
        if fail_ratio is not None:
            audit.warning("phone_high_fail_ratio country=%s ratio=%.2f", country, fail_ratio)
        return True, ""

    @staticmethod
    def _country_fail_ratio(country):
        """Send-to-verify failure ratio watchdog (log-only signal)."""
        day_ago = timezone.now() - timezone.timedelta(days=1)
        sends = VerificationSendLog.objects.filter(
            kind="phone", country=country, created_at__gte=day_ago
        ).count()
        min_sends = int(getattr(settings, "PHONE_FAIL_RATIO_MIN_SENDS", 20))
        if sends < min_sends:
            return None
        verified = User.objects.filter(
            phone_country=country, phone_verified_at__gte=day_ago
        ).count()
        ratio = 1.0 - (verified / max(sends, 1))
        if ratio >= float(getattr(settings, "PHONE_FAIL_RATIO_ALERT", 0.9)):
            return ratio
        return None

    def _dispatch_sms(self, to_e164, code, channel="sms"):
        """Celery first (fail-fast publish), inline fallback if broker down."""
        try:
            from celery import current_app

            from .tasks import send_phone_otp_task

            result = send_phone_otp_task.apply_async(
                args=[to_e164, code, channel], retry=False
            )
            if current_app.conf.task_always_eager and result.state == "FAILURE":
                # Eager mode (dev/test) folds task Retry into a FAILURE
                # result instead of raising — surface it so a dead provider
                # still maps to 502 rather than a false "sent" 200.
                # Production (non-eager) is untouched: publish success means
                # accepted-for-delivery, state stays PENDING here.
                raise RuntimeError(f"sms task failed: {result.result!r}")
        except Exception as exc:
            logging.getLogger("accounts.mailer").warning(
                "Celery unavailable, sending SMS inline: %s", exc
            )
            from .sms_providers import get_provider_for_e164

            provider = get_provider_for_e164(to_e164)
            result = provider.send_otp(to_e164, code, channel=channel)
            if not result.ok:
                raise


class PhoneStartView(_PhoneFlowMixin, APIView):
    """POST /api/auth/phone/start/ — claim a number, run policy checks, send OTP.

    Authenticated. Generic response; never reveals whether the number belongs
    to another account. No SMS leaves for numbers failing validation,
    allow-list, or line-type checks (cost protection first layer).
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "phone"

    def post(self, request):
        from .phone_normalize import (
            LINE_LANDLINE,
            LINE_VOIP,
            check_country_allowed,
            lookup_line_type,
            mask_phone,
        )
        from .serializers import StartPhoneSerializer

        denied = self._require_email_first(request.user)
        if denied:
            return denied
        serializer = StartPhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user, ip = request.user, _client_ip(request)

        if not verify_captcha(data.get("captcha_token"), ip):
            return Response(
                {"code": "CAPTCHA_REQUIRED", "message": "Captcha verification failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        e164, country = self._resolve_input(data)
        if not e164:
            audit.info(
                "phone_blocked_invalid user_id=%s ip=%s", user.pk, ip
            )
            return Response(
                {"code": "INVALID_NUMBER", "message": "Enter a valid phone number."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not check_country_allowed(country):
            audit.info(
                "phone_blocked_country user_id=%s country=%s ip=%s",
                user.pk,
                country,
                ip,
            )
            return Response(
                {
                    "code": "COUNTRY_NOT_SUPPORTED",
                    "message": "Phone numbers from this country aren't supported yet.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        line_type, risk = lookup_line_type(e164)
        if line_type == LINE_LANDLINE:
            audit.info("phone_blocked_landline user_id=%s country=%s", user.pk, country)
            return Response(
                {"code": "LINE_TYPE_BLOCKED", "message": "Landline numbers can't receive SMS codes."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if line_type == LINE_VOIP and getattr(settings, "PHONE_BLOCK_VOIP", True):
            user.add_risk_flag("voip_number")
            audit.info(
                "phone_blocked_voip user_id=%s country=%s ip=%s", user.pk, country, ip
            )
            return Response(
                {
                    "code": "LINE_TYPE_BLOCKED",
                    "message": "Virtual/VoIP numbers aren't accepted. Use a mobile number.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if risk:
            user.add_risk_flag(risk)
        if risk == "lookup_failed_blocked":
            return Response(
                {"code": "LINE_TYPE_BLOCKED", "message": "Could not verify this number. Try again later."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed, reason = self._send_limits(user, ip, e164, country)
        if not allowed:
            audit.info(
                "phone_rate_limited user_id=%s to=%s reason=%s ip=%s",
                user.pk,
                mask_phone(e164),
                reason,
                ip,
            )
            status_code = (
                status.HTTP_429_TOO_MANY_REQUESTS
                if reason in ("circuit_open", "global_cap", "burst")
                else status.HTTP_200_OK
            )
            # Cooldown/user caps stay generic-200 (no limit probing);
            # circuit/burst states are 429s so clients back off.
            if status_code == 200:
                return Response(_PHONE_GENERIC)
            return Response(
                {"code": "RATE_LIMITED", "message": "Too many requests. Try again later."},
                status=status_code,
            )

        user.pending_phone = e164
        user.pending_phone_country = country
        user.phone_line_type = line_type if line_type != "unknown" else user.phone_line_type
        user.save(
            update_fields=["pending_phone", "pending_phone_country", "phone_line_type"]
        )

        channel = data.get("channel", "sms")
        try:
            self._send_otp(user, e164, channel, ip)
        except _ProviderDown:
            return Response(
                {"code": "PROVIDER_ERROR", "message": "Could not send right now. Try again shortly."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(_PHONE_GENERIC)

    def _send_otp(self, user, e164, channel, ip):
        from .phone_normalize import mask_phone
        from .phone_verification import issue_phone_code
        from .sms_providers import provider_mode

        row, secret = issue_phone_code(user, e164, channel)
        provider_name = getattr(settings, "PHONE_SMS_PROVIDER", "console")
        if provider_mode() == "managed":
            ok = row is not None
            if not ok:
                audit.warning(
                    "phone_provider_failed user_id=%s to=%s", user.pk, mask_phone(e164)
                )
        else:
            try:
                self._dispatch_sms(e164, secret, channel)
                ok = True
            except Exception:
                ok = False
                audit.warning(
                    "phone_provider_failed user_id=%s to=%s", user.pk, mask_phone(e164)
                )
        VerificationSendLog.objects.create(
            user=user, ip_address=ip, kind="phone", target=e164,
            country=user.pending_phone_country, provider=provider_name,
        )
        audit.info(
            "phone_otp_sent user_id=%s to=%s channel=%s ok=%s",
            user.pk,
            mask_phone(e164),
            channel,
            ok,
        )
        if not ok:
            raise _ProviderDown()


class PhoneVerifyView(_PhoneFlowMixin, APIView):
    """POST /api/auth/phone/verify/ — {code}. Single-use, expiry + attempts
    enforced; success swaps pending->verified (first-verified-wins) and
    returns fresh JWTs with the updated phone_verified claim."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "phone"

    def post(self, request):
        from .phone_normalize import mask_phone
        from .phone_verification import (
            check_managed_code,
            find_phone_token,
            latest_usable_phone_token,
            phone_otp_max_attempts,
        )
        from .serializers import VerifyPhoneSerializer
        from .sms_providers import provider_mode

        denied = self._require_email_first(request.user)
        if denied:
            return denied
        serializer = VerifyPhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, code = request.user, serializer.validated_data["code"]
        e164 = user.pending_phone
        if not e164:
            audit.info("phone_otp_failed user_id=%s reason=no_pending", user.pk)
            return Response(
                {"code": "INVALID_CODE", "message": "Invalid or expired code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if provider_mode() == "managed":
            if check_managed_code(user, e164, code):
                return self._success(user, e164, via="managed")
            audit.info(
                "phone_otp_failed user_id=%s to=%s reason=wrong_code",
                user.pk,
                mask_phone(e164),
            )
            return Response(
                {"code": "INVALID_CODE", "message": "Invalid or expired code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token, reason = find_phone_token(user, code)
        if token is None:
            if reason == "invalid":
                latest = latest_usable_phone_token(user)
                if latest is not None:
                    # Cap from settings (may differ from email OTP cap).
                    latest_attempts = (latest.attempts or 0) + 1
                    latest.attempts = latest_attempts
                    if latest_attempts >= phone_otp_max_attempts():
                        latest.used_at = timezone.now()
                        latest.save(update_fields=["attempts", "used_at"])
                        audit.info("phone_otp_failed user_id=%s reason=otp_locked", user.pk)
                        return Response(
                            {
                                "code": "OTP_LOCKED",
                                "message": "Too many wrong attempts. Request a new code.",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    latest.save(update_fields=["attempts"])
                audit.info(
                    "phone_otp_failed user_id=%s to=%s reason=wrong_code",
                    user.pk,
                    mask_phone(e164),
                )
            else:
                audit.info(
                    "phone_otp_failed user_id=%s to=%s reason=%s",
                    user.pk,
                    mask_phone(e164),
                    reason,
                )
            return Response(
                {
                    "code": "EXPIRED_CODE" if reason == "expired" else "INVALID_CODE",
                    "message": "Invalid or expired code.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Bind the code to the exact number it was sent to.
        if (token.target_normalized or "") != (e164 or ""):
            token.mark_used()
            audit.info("phone_otp_failed user_id=%s reason=number_changed", user.pk)
            return Response(
                {"code": "INVALID_CODE", "message": "Invalid or expired code."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        token.mark_used()
        return self._success(user, e164, via="custom")

    def _success(self, user, e164, via):
        from .phone_normalize import mask_phone

        # Another account already VERIFIED this number: fail closed (the
        # authenticated user just proved nothing about ownership vs them).
        User = get_user_model()
        holder = User.objects.filter(phone=e164, phone_verified=True).exclude(pk=user.pk).first()
        if holder is not None:
            audit.warning(
                "phone_taken user_id=%s to=%s", user.pk, mask_phone(e164)
            )
            return Response(
                {
                    "code": "NUMBER_TAKEN",
                    "message": "This number can't be verified on this account.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        country = user.pending_phone_country
        line_type = user.phone_line_type
        user.mark_phone_verified(e164, country, line_type)
        audit.info("phone_verified user_id=%s to=%s via=%s", user.pk, mask_phone(e164), via)
        tokens = tokens_for_user(user)
        return Response(
            {
                "message": "Phone verified.",
                "phone_verified": True,
                "phone_masked": mask_phone(e164),
                "phone_country": country,
                "access": tokens["access"],
                "refresh": tokens["refresh"],
            }
        )


class PhoneResendView(_PhoneFlowMixin, APIView):
    """POST /api/auth/phone/resend/ — {channel?}. Same caps as start, plus
    CAPTCHA is required again once the user passed 2 sends (when enabled)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "phone"

    def post(self, request):
        from .phone_normalize import mask_phone
        from .serializers import ResendPhoneSerializer

        denied = self._require_email_first(request.user)
        if denied:
            return denied
        serializer = ResendPhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, ip = request.user, _client_ip(request)
        e164 = user.pending_phone
        if not e164:
            # No pending number: identical generic response (no probing).
            return Response(_PHONE_GENERIC)

        sends_today = VerificationSendLog.objects.filter(
            user=user, kind="phone", created_at__gte=timezone.now() - timezone.timedelta(days=1)
        ).count()
        if getattr(settings, "CAPTCHA_REQUIRED", False) and sends_today >= 2:
            if not verify_captcha(
                serializer.validated_data.get("captcha_token"), ip
            ):
                return Response(
                    {"code": "CAPTCHA_REQUIRED", "message": "Captcha verification failed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        channel = serializer.validated_data.get("channel", "sms")
        allowed, reason = self._send_limits(user, ip, e164, user.pending_phone_country)
        if not allowed:
            audit.info(
                "phone_rate_limited user_id=%s to=%s reason=%s ip=%s",
                user.pk,
                mask_phone(e164),
                reason,
                ip,
            )
            if reason in ("circuit_open", "global_cap", "burst"):
                return Response(
                    {"code": "RATE_LIMITED", "message": "Too many requests. Try again later."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            return Response(_PHONE_GENERIC)
        try:
            starter = PhoneStartView()
            starter._send_otp(user, e164, channel, ip)
        except _ProviderDown:
            return Response(
                {"code": "PROVIDER_ERROR", "message": "Could not send right now. Try again shortly."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(_PHONE_GENERIC)


class PhoneChangeView(_PhoneFlowMixin, APIView):
    """POST /api/auth/phone/change/ — current password AND a verified OTP on
    the NEW number are both required; the old verified number's owner is
    notified by email. Only swaps after the new number verifies.

    NOTE (SIM-swap): SMS OTP alone must never gate password reset — email
    confirmation is also required there. This endpoint only moves a phone
    claim, never auth credentials.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "phone"

    def post(self, request):
        from .phone_normalize import (
            check_country_allowed,
            mask_phone,
        )
        from .serializers import ChangePhoneSerializer

        denied = self._require_email_first(request.user)
        if denied:
            return denied
        serializer = ChangePhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            return Response(
                {"code": "INVALID_PASSWORD", "message": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        e164, country = self._resolve_input(serializer.validated_data)
        if not e164 or not check_country_allowed(country):
            return Response(
                {"code": "INVALID_NUMBER", "message": "Enter a valid, supported phone number."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.phone_verified and e164 == user.phone:
            return Response(
                {"code": "SAME_NUMBER", "message": "This number is already verified on your account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        old_masked = mask_phone(user.phone) if user.phone else None
        user.pending_phone = e164
        user.pending_phone_country = country
        user.save(update_fields=["pending_phone", "pending_phone_country"])
        audit.info(
            "phone_change_requested user_id=%s old=%s new=%s",
            user.pk,
            old_masked or "-",
            mask_phone(e164),
        )
        # Notify the old address/number holder by email (best-effort).
        if user.phone_verified:
            try:
                send_mail(
                    "Your Sabha Gachhi phone number change",
                    f"A request was made to change your verified phone number to {mask_phone(e164)}. "
                    "If this wasn't you, please contact support at once.",
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            except Exception:
                pass
        try:
            starter = PhoneStartView()
            starter._send_otp(user, e164, "sms", _client_ip(request))
        except _ProviderDown:
            return Response(
                {"code": "PROVIDER_ERROR", "message": "Could not send right now. Try again shortly."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(
            {
                "message": "Verify the code sent to your new number to complete the change.",
                "pending_phone_masked": mask_phone(e164),
            }
        )


class PhoneWebhookView(APIView):
    """POST /api/auth/phone/webhook/ — delivery receipts (delivered/failed).

    Signature-checked when TWILIO_AUTH_TOKEN is set (Twilio X-Twilio-Signature
    HMAC scheme); without it the endpoint only accepts the dev console
    provider's receipts. Failures are logged and surface as voice/WhatsApp
    fallback hints on the next resend via provider fallback_hint.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "phone"

    def post(self, request):
        from .phone_normalize import mask_phone

        if not self._signature_ok(request):
            audit.warning("phone_webhook_bad_signature ip=%s", _client_ip(request))
            return Response({"ok": False}, status=status.HTTP_403_FORBIDDEN)
        to = str(request.data.get("To") or request.data.get("to") or "")
        event = str(request.data.get("Status") or request.data.get("status") or "unknown")
        sid = str(request.data.get("Sid") or request.data.get("sid") or "")
        audit.info(
            "phone_webhook to=%s status=%s sid=%s",
            mask_phone(to),
            event,
            sid[-8:] if sid else "-",
        )
        return Response({"ok": True})

    def _signature_ok(self, request) -> bool:
        import base64
        import hashlib
        import hmac as hmac_lib

        token = getattr(settings, "TWILIO_AUTH_TOKEN", "") or ""
        if not token:
            # No signing secret configured: accept only dev receipts.
            return getattr(settings, "PHONE_SMS_PROVIDER", "console") == "console"
        signature = request.META.get("HTTP_X_TWILIO_SIGNATURE", "")
        url = request.build_absolute_uri()
        params = dict(sorted((request.data or {}).items()))
        expected = base64.b64encode(
            hmac_lib.new(
                token.encode(), (url + "".join(k + str(v) for k, v in params.items())).encode(),
                hashlib.sha1,
            ).digest()
        ).decode()
        return hmac_lib.compare_digest(signature, expected)


class LogoutView(APIView):
    """POST /api/auth/logout/ — tokens are client-stored; server just logs."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        audit.info("logout user_id=%s", request.user.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

# Create your views here.
