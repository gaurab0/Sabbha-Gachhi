from django.urls import path

from . import views

urlpatterns = [
    path("registrations/", views.RegistrationCreateView.as_view()),
    path("registrations/photo/", views.CandidatePhotoUploadView.as_view()),
    path("registrations/me/status/", views.MyRegistrationStatusView.as_view()),
    path("registrations/me/withdraw/", views.MyRegistrationWithdrawView.as_view()),
    path("status/check/", views.StatusCheckView.as_view()),
    # <str:pk> (not <int:pk>) on all three: ids are ObjectIds on the MongoDB
    # backend, so an int converter 404s before the view ever runs.
    path("match-proposals/<str:pk>/", views.MatchProposalDetailView.as_view()),
    path("match-proposals/<str:pk>/contact/", views.MatchProposalContactView.as_view()),
    path("match-proposals/<str:pk>/respond/", views.MatchProposalRespondView.as_view()),
    path("concern-reports/", views.ConcernReportCreateView.as_view()),
]