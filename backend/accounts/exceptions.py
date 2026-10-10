"""API exceptions with machine-readable `code` bodies for auth flows."""

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


class EmailNotVerified(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Verify your email address to continue."
    default_code = "email_not_verified"


class PhoneNotVerified(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Verify your phone number to continue."
    default_code = "phone_not_verified"


def api_exception_handler(exc, context):
    """Default DRF handler + `{"code", "message"}` shape for coded errors.

    Only the *Verified exceptions get coded bodies; everything else falls
    through to DRF's standard `{"detail": ...}` so existing error contracts
    don't change.
    """
    if isinstance(exc, EmailNotVerified):
        return Response(
            {"code": "email_not_verified", "message": str(exc.detail)},
            status=status.HTTP_403_FORBIDDEN,
        )
    if isinstance(exc, PhoneNotVerified):
        return Response(
            {"code": "phone_not_verified", "message": str(exc.detail)},
            status=status.HTTP_403_FORBIDDEN,
        )
    return exception_handler(exc, context)
