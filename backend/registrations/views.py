from django.shortcuts import render

# Create your views here.
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ConcernReport, MatchProposal, Registration
from .serializers import (
    ConcernReportSerializer,
    MatchProposalSerializer,
    RegistrationCreatedSerializer,
    RegistrationCreateSerializer,
    RegistrationStatusSerializer,
)


class RegistrationCreateView(APIView):
    """POST /api/registrations/ — called from RegistrationFlow.tsx's handleFinalSubmit."""

    def post(self, request):
        serializer = RegistrationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = serializer.save()
        return Response(
            RegistrationCreatedSerializer(registration).data,
            status=status.HTTP_201_CREATED,
        )


class RegistrationStatusView(APIView):
    """GET /api/registrations/<reference>/status/ — powers StatusPage.tsx."""

    def get(self, request, reference):
        registration = get_object_or_404(
            Registration, reference=reference, withdrawn=False
        )
        return Response(RegistrationStatusSerializer(registration).data)


class RegistrationWithdrawView(APIView):
    """
    POST /api/registrations/<reference>/withdraw/
    Called from StatusPage.tsx's handleWithdrawConfirmed — unconditional,
    no reason required, matching the frontend's plain confirm flow.
    """

    def post(self, request, reference):
        registration = get_object_or_404(
            Registration, reference=reference, withdrawn=False
        )
        registration.withdrawn = True
        from django.utils import timezone
        registration.withdrawn_at = timezone.now()
        registration.save(update_fields=["withdrawn", "withdrawn_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class MatchProposalDetailView(APIView):
    """GET /api/match-proposals/<id>/ — powers MatchProposalScreen.tsx on load."""

    def get(self, request, pk):
        proposal = get_object_or_404(MatchProposal, pk=pk)
        return Response(MatchProposalSerializer(proposal).data)


class MatchProposalRespondView(APIView):
    """
    POST /api/match-proposals/<id>/respond/
    Body: {"action": "accept"} or {"action": "decline"}
    """

    def post(self, request, pk):
        proposal = get_object_or_404(MatchProposal, pk=pk)
        action = request.data.get("action")

        if action not in ("accept", "decline"):
            return Response(
                {"detail": "action must be 'accept' or 'decline'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_value = (
            MatchProposal.PartyResponse.ACCEPTED
            if action == "accept"
            else MatchProposal.PartyResponse.DECLINED
        )
        proposal.your_response = new_value
        proposal.save(update_fields=["your_response"])

        # Automated matches create two linked rows (one per family) — mirror
        # this response onto the other family's row so both sides' `state`
        # stay in sync. Manually created proposals may not have a pair yet.
        if proposal.paired_proposal_id:
            paired = proposal.paired_proposal
            paired.other_response = new_value
            paired.save(update_fields=["other_response"])

        return Response(MatchProposalSerializer(proposal).data)

class ConcernReportCreateView(APIView):
    """POST /api/concern-reports/ — called from ReportConcernForm.tsx's handleSubmit."""

    def post(self, request):
        serializer = ConcernReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        registration_ref = serializer.validated_data.get(
            "registration_reference_text", ""
        )
        registration = Registration.objects.filter(
            reference=registration_ref
        ).first()

        report = ConcernReport.objects.create(
            registration=registration,
            **serializer.validated_data,
        )
        return Response({"received": True}, status=status.HTTP_201_CREATED)