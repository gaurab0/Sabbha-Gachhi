from django.urls import path

from . import views

urlpatterns = [
    path("registrations/", views.RegistrationCreateView.as_view()),
    path("registrations/me/status/", views.MyRegistrationStatusView.as_view()),
    path("registrations/me/withdraw/", views.MyRegistrationWithdrawView.as_view()),
    path("status/check/", views.StatusCheckView.as_view()),
    path("match-proposals/<int:pk>/", views.MatchProposalDetailView.as_view()),
    path("match-proposals/<int:pk>/respond/", views.MatchProposalRespondView.as_view()),
    path("concern-reports/", views.ConcernReportCreateView.as_view()),
]