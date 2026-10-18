"""Requires a verified email on top of authentication.

Unverified access raises EmailNotVerified -> HTTP 403 with body
    {"code": "email_not_verified", "message": "..."}
(via accounts.exceptions.api_exception_handler) so the frontend can redirect
to the verify screen. Unauthenticated requests return False so the standard
401 path still applies.
"""

from django.conf import settings
from rest_framework.permissions import BasePermission

from .exceptions import EmailNotVerified, PhoneNotVerified


class RequireVerifiedEmail(BasePermission):
    message = "Verify your email address to continue."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return False
        if not getattr(user, "email_verified", False):
            raise EmailNotVerified(self.message)
        return True


class RequireVerifiedPhone(BasePermission):
    """403 phone_not_verified unless the user verified a phone number."""

    message = "Verify your phone number to continue."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return False
        if not getattr(user, "phone_verified", False):
            raise PhoneNotVerified(self.message)
        return True


class RequireFullyVerified(BasePermission):
    """Email AND phone. Email is checked first so a doubly-unverified user
    always sees email_not_verified (stable ordering for the frontend)."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return False
        if not getattr(user, "email_verified", False):
            raise EmailNotVerified(RequireVerifiedEmail.message)
        # Phone gating is phase-2. While PHONE_VERIFICATION_REQUIRED is off
        # the gate is email-only, so the app is fully usable without a phone.
        if not getattr(settings, "PHONE_VERIFICATION_REQUIRED", True):
            return True
        if not getattr(user, "phone_verified", False):
            raise PhoneNotVerified(RequireVerifiedPhone.message)
        return True


def email_not_verified_response():
    """Helper for function-style 403s with the same body contract."""
    from rest_framework.response import Response
    from rest_framework import status

    return Response(
        {"code": "email_not_verified", "message": RequireVerifiedEmail.message},
        status=status.HTTP_403_FORBIDDEN,
    )
