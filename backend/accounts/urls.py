from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import SignupView

urlpatterns = [
    path("signup/", SignupView.as_view()),
    path("login/", TokenObtainPairView.as_view()),        # body: {"email": ..., "password": ...}
    path("login/refresh/", TokenRefreshView.as_view()),   # body: {"refresh": "..."}
]