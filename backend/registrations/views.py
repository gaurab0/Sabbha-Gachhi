import logging

from django.shortcuts import render
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.permissions import (
    RequireFullyVerified,
    RequireVerifiedEmail,
    email_not_verified_response,
)

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

    permission_classes = [IsAuthenticated, RequireVerifiedEmail]

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
        registration = Registration.objects.filter(owner=request.user).first()
        if not request.user.email_verified:
            payload = {
                "email_verified": False,
                "registration": None,
            }
            if registration is not None:
                payload.update(RegistrationStatusSerializer(registration).data)
            return Response(payload)
        if registration is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        data = RegistrationStatusSerializer(registration).data
        data["email_verified"] = True
        return Response(data)


class MyRegistrationWithdrawView(APIView):
    permission_classes = [IsAuthenticated, RequireVerifiedEmail]

    """POST /api/registrations/me/withdraw/ — optional body {"reason": "..."}.

    Idempotent: withdrawing an already-withdrawn registration succeeds
    (updating the stored reason when one is supplied) instead of 404ing,
    so retries and double-clicks are safe.
    """

    def post(self, request):
        registration = get_object_or_404(Registration, owner=request.user)
        reason = (request.data.get("reason") or "").strip()[:200]
        if registration.withdrawn:
            if reason and reason != registration.withdrawn_reason:
                registration.withdrawn_reason = reason
                registration.save(update_fields=["withdrawn_reason"])
            return Response(status=status.HTTP_204_NO_CONTENT)
        registration.withdrawn = True
        from django.utils import timezone
        registration.withdrawn_at = timezone.now()
        registration.withdrawn_reason = reason
        registration.save(
            update_fields=["withdrawn", "withdrawn_at", "withdrawn_reason"]
        )
        _cancel_active_proposals(registration)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _cancel_active_proposals(registration: Registration) -> None:
    """Decline every proposal that isn't fully resolved, mirroring the
    decline onto the paired row so the other family's card disappears too.
    Engine Match rows are history/logs and are left intact."""
    proposals = MatchProposal.objects.filter(registration=registration).exclude(
        your_response=MatchProposal.PartyResponse.DECLINED
    ).exclude(
        other_response=MatchProposal.PartyResponse.DECLINED
    )
    for proposal in proposals:
        proposal.your_response = MatchProposal.PartyResponse.DECLINED
        proposal.save(update_fields=["your_response"])
        if proposal.paired_proposal_id:
            paired = proposal.paired_proposal
            paired.other_response = MatchProposal.PartyResponse.DECLINED
            paired.save(update_fields=["other_response"])


class MatchProposalDetailView(APIView):
    """GET /api/match-proposals/<id>/ — powers MatchProposalScreen.tsx on load."""

    # Full gate: this is where contact details (incl. phone) get revealed.
    permission_classes = [IsAuthenticated, RequireFullyVerified]

    def get(self, request, pk):
        proposal = get_object_or_404(MatchProposal, pk=pk)
        if proposal.registration.owner_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(MatchProposalSerializer(proposal).data)


class MatchProposalContactView(APIView):
    """GET /api/match-proposals/<id>/contact/ — minimal contact payload.

    Returns {"photo_url", "email", "phone"} for the matched candidate, only
    when (a) the caller is authenticated, (b) the caller's own registration
    is Verified, and (c) the proposal was made to them. Otherwise 403/404.

    Like the proposal serializer, contact details are empty strings until
    both families have accepted — the view never invents them.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        proposal = get_object_or_404(MatchProposal, pk=pk)
        if proposal.registration.owner_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if (
            proposal.registration.verification_status
            != Registration.VerificationStatus.VERIFIED
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        candidate = None
        if proposal.paired_proposal_id:
            candidate = proposal.paired_proposal.registration
        return Response(
            {
                "photo_url": (candidate.candidate_photo if candidate else "") or "",
                "email": proposal.contact_email or "",
                "phone": proposal.contact_phone or "",
            }
        )


class MatchProposalRespondView(APIView):
    """
    POST /api/match-proposals/<id>/respond/
    Body: {"action": "accept"} or {"action": "decline"}
    """

    # Full gate: accepting can reveal contact details on both_accepted.
    permission_classes = [IsAuthenticated, RequireFullyVerified]

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

    permission_classes = [IsAuthenticated, RequireVerifiedEmail]

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
        matches = registration.match_proposals.exclude(
            your_response=MatchProposal.PartyResponse.DECLINED
        ).exclude(
            other_response=MatchProposal.PartyResponse.DECLINED
        )
        match_count = matches.count()
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
