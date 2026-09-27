import re
import uuid

from rest_framework import serializers

from .models import ConcernReport, LineageEntry, MatchProposal, Registration


TOKEN_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


class StatusCheckSerializer(serializers.Serializer):
    """Validates the token payload for the status-check endpoint."""
    token = serializers.CharField(max_length=36, min_length=36)

    def validate_token(self, value):
        value = value.strip()
        if not TOKEN_RE.match(value):
            raise serializers.ValidationError("Invalid token format.")
        return value


class LineageEntrySerializer(serializers.Serializer):
    """
    Matches the LineageEntry interface from RegistrationFlow.tsx:
    { label: string, name: string }
    """
    label = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=150, allow_blank=True, required=False)


class RegistrationCreateSerializer(serializers.ModelSerializer):
    """
    Used for POST /api/registrations/ — accepts the full payload assembled
    across RegistrationFlow.tsx's guardian / candidate / lineage / consent steps.
    """
    paternal_line = LineageEntrySerializer(many=True, required=False)
    maternal_line = LineageEntrySerializer(many=True, required=False)

    class Meta:
        model = Registration
        fields = [
            "language",
            "guardian_name",
            "guardian_relation_to_candidate",
            "guardian_village",
            "guardian_district",
            "guardian_phone",
            "guardian_email",
            "candidate_full_name",
            "candidate_gender",
            "candidate_dob",
            "candidate_education",
            "candidate_occupation",
            "candidate_current_city",
            "gotra",
            "mool_gram",
            "paternal_line",
            "maternal_line",
            "consent_choice",
            "consent_own_words",
        ]

    def validate(self, data):
        # Mirrors the frontend's canSubmitConsent check in RegistrationFlow.tsx:
        # consent.choice === "agree" && consent.ownWords.trim().length > 0
        if data.get("consent_choice") != Registration.ConsentChoice.AGREE:
            raise serializers.ValidationError(
                "Registration cannot be submitted without explicit consent."
            )
        if not data.get("consent_own_words", "").strip():
            raise serializers.ValidationError(
                "Consent must be given in the candidate's own words."
            )
        return data

    def create(self, validated_data):
        paternal_data = validated_data.pop("paternal_line", [])
        maternal_data = validated_data.pop("maternal_line", [])
        owner = validated_data.pop("owner")

        registration = Registration.objects.create(
            owner=owner,
            paternal_line=[LineageEntry(**entry) for entry in paternal_data],
            maternal_line=[LineageEntry(**entry) for entry in maternal_data],
            **validated_data,
        )
        return registration


class RegistrationCreatedSerializer(serializers.ModelSerializer):
    """Response shape after a successful POST — matches ConfirmationStep's needs."""

    class Meta:
        model = Registration
        fields = ["reference", "created_at"]


class MatchProposalSerializer(serializers.ModelSerializer):
    """
    Matches the ProposedMatch interface from StatusPage.tsx and the
    MatchProposal interface from MatchProposalScreen.tsx.
    Contact fields are only ever populated by the view once state == "both_accepted".
    """
    id = serializers.CharField(read_only=True)
    state = serializers.CharField(read_only=True)
    shared_details = serializers.ListField(
        child=serializers.CharField(read_only=True),
        read_only=True,
    )

    class Meta:
        model = MatchProposal
        fields = [
            "id",
            "shared_by_panjikar",
            "proposed_on",
            "shared_details",
            "your_response",
            "other_response",
            "state",
            "contact_guardian_name",
            "contact_phone",
            "contact_email",
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Enforce "nothing shown before both accept" even if the DB happens
        # to have stale contact data from a prior accepted-then-reset state.
        if instance.state != "both_accepted":
            data["contact_guardian_name"] = ""
            data["contact_phone"] = ""
            data["contact_email"] = ""
        return data


class RegistrationStatusSerializer(serializers.ModelSerializer):
    """
    Matches the RegistrationStatus interface from StatusPage.tsx.
    Surfaces only the most recent non-declined match proposal, if any.
    """
    candidate_name = serializers.CharField(source="candidate_full_name")
    match = serializers.SerializerMethodField()

    class Meta:
        model = Registration
        fields = [
            "reference",
            "candidate_name",
            "guardian_name",
            "verification_status",
            "match",
            "withdrawn",
            "withdrawn_at",
        ]

    def get_match(self, obj):
        proposal = obj.match_proposals.exclude(
            your_response=MatchProposal.PartyResponse.DECLINED
        ).exclude(
            other_response=MatchProposal.PartyResponse.DECLINED
        ).first()
        if not proposal:
            return None
        return MatchProposalSerializer(proposal).data


class ConcernReportSerializer(serializers.ModelSerializer):
    """Matches ConcernSubmission from ReportConcernForm.tsx."""

    class Meta:
        model = ConcernReport
        fields = [
            "registration_reference_text",
            "topic",
            "description",
            "contact_back",
        ]

    def validate_description(self, value):
        if not value.strip():
            raise serializers.ValidationError("Please describe what's going on.")
        return value