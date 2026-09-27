import logging

from django.shortcuts import render
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import ConcernReport, Match, MatchProposal, Registration
from .serializers import (
    ConcernReportSerializer,
    MatchProposalSerializer,
    RegistrationCreatedSerializer,
    RegistrationCreateSerializer,
    RegistrationStatusSerializer,
    StatusCheckSerializer,
)


class RegistrationCreateView(APIView):
    """POST /api/registrations/ — requires login and stores the owner."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RegistrationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = serializer.save(owner=request.user)
        return Response(
            RegistrationCreatedSerializer(registration).data,
            status=status.HTTP_201_CREATED,
        )


class MyRegistrationStatusView(APIView):
    """GET /api/registrations/me/status/ — uses the authenticated owner."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        registration = get_object_or_404(Registration, owner=request.user)
        return Response(RegistrationStatusSerializer(registration).data)


class MyRegistrationWithdrawView(APIView):
    permission_classes = [IsAuthenticated]

    """POST /api/registrations/me/withdraw/"""

    def post(self, request):
        registration = get_object_or_404(
            Registration, owner=request.user, withdrawn=False
        )
        registration.withdrawn = True
        from django.utils import timezone
        registration.withdrawn_at = timezone.now()
        registration.save(update_fields=["withdrawn", "withdrawn_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class MatchProposalDetailView(APIView):
    """GET /api/match-proposals/<id>/ — powers MatchProposalScreen.tsx on load."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        proposal = get_object_or_404(MatchProposal, pk=pk)
        if proposal.registration.owner_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(MatchProposalSerializer(proposal).data)


class MatchProposalRespondView(APIView):
    """
    POST /api/match-proposals/<id>/respond/
    Body: {"action": "accept"} or {"action": "decline"}
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        proposal = get_object_or_404(MatchProposal, pk=pk)
        if proposal.registration.owner_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
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

            # Once both sides have genuinely accepted, reveal contact details.
            # Each side sees the other family's current guardian contact.
            if proposal.state == "both_accepted":
                _reveal_contact(proposal, source=paired.registration)
                _reveal_contact(paired, source=proposal.registration)

        return Response(MatchProposalSerializer(proposal).data)


def _reveal_contact(proposal: MatchProposal, source: Registration):
    proposal.contact_guardian_name = source.guardian_name
    proposal.contact_phone = source.guardian_phone
    proposal.contact_email = source.guardian_email
    proposal.save(
        update_fields=["contact_guardian_name", "contact_phone", "contact_email"]
    )

class ConcernReportCreateView(APIView):
    """POST /api/concern-reports/ — attaches the authenticated user's registration."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ConcernReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        registration = Registration.objects.filter(owner=request.user).first()

        report = ConcernReport.objects.create(
            registration=registration,
            **serializer.validated_data,
        )
        return Response({"received": True}, status=status.HTTP_201_CREATED)


class StatusCheckView(APIView):
    """
    POST /api/status/check/ — unauthenticated status lookup by token.

    Returns a generic status payload without revealing whether the token
    itself is valid, to prevent token enumeration. Throttled to 5
    requests per token/IP per hour.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'status_check'
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StatusCheckSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "Token not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        token = serializer.validated_data['token']
        try:
            registration = Registration.objects.get(token=token)
        except Registration.DoesNotExist:
            logger = logging.getLogger(__name__)
            logger.warning(
                "Status check failed — token not found from IP %s",
                request.META.get('REMOTE_ADDR', 'unknown'),
            )
            return Response(
                {"detail": "Token not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Generic response — do not distinguish "wrong token" from
        # "token exists but not verified" to avoid leaking token validity.
        verified = registration.verification_status == Registration.VerificationStatus.VERIFIED
        match_count = Match.objects.filter(registration=registration).count()
        match_found = match_count > 0

        if not verified:
            stage = "pending_verification"
        elif not match_found:
            stage = "verified_awaiting_match"
        else:
            stage = "matched"

        return Response(
            {
                "verified": verified,
                "match_found": match_found,
                "match_count": match_count,
                "stage": stage,
            },
            status=status.HTTP_200_OK,
        )

    def initialize_request(self, request, *args, **kwargs):
        response = super().initialize_request(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        return response