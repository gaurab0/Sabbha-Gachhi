from django.urls import path

from . import views

urlpatterns = [
    path("registrations/", views.RegistrationCreateView.as_view()),
    path("registrations/<str:reference>/status/", views.RegistrationStatusView.as_view()),
    path("registrations/<str:reference>/withdraw/", views.RegistrationWithdrawView.as_view()),
    path("match-proposals/<int:pk>/", views.MatchProposalDetailView.as_view()),
    path("match-proposals/<int:pk>/respond/", views.MatchProposalRespondView.as_view()),
    path("concern-reports/", views.ConcernReportCreateView.as_view()),
]