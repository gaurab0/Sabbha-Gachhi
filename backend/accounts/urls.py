from django.urls import path

from .views import (
    ChangeEmailView,
    LoginView,
    LogoutView,
    MeView,
    PhoneChangeView,
    PhoneResendView,
    PhoneStartView,
    PhoneVerifyView,
    PhoneWebhookView,
    RefreshView,
    ResendVerificationView,
    SignupView,
    VerifyEmailView,
)

urlpatterns = [
    path("signup/", SignupView.as_view()),
    path("login/", LoginView.as_view()),  # body: {"email": ..., "password": ...}
    path("login/refresh/", RefreshView.as_view()),  # body: {"refresh": "..."}
    path("verify-email/", VerifyEmailView.as_view()),  # {token} or {email, otp}
    path("resend-verification/", ResendVerificationView.as_view()),
    path("email/change/", ChangeEmailView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("me/", MeView.as_view()),
    path("phone/start/", PhoneStartView.as_view()),
    path("phone/verify/", PhoneVerifyView.as_view()),
    path("phone/resend/", PhoneResendView.as_view()),
    path("phone/change/", PhoneChangeView.as_view()),
    path("phone/webhook/", PhoneWebhookView.as_view()),
]
