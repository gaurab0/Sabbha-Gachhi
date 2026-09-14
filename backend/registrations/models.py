from django.db import models

# Create your models here.
from django.db import models

from django_mongodb_backend.fields import ArrayField, EmbeddedModelArrayField
from django_mongodb_backend.models import EmbeddedModel


# ---------------------------------------------------------------------------
# Embedded documents (live inside a Registration document, not their own
# collection) — mirrors the LineageEntry interface from RegistrationFlow.tsx
# ---------------------------------------------------------------------------

class LineageEntry(EmbeddedModel):
    """
    One ancestor row in the family tree, e.g. {label: "Father", name: "..."}.
    Stored as a list of these inside Registration.paternal_line / maternal_line.
    """
    label = models.CharField(max_length=100)
    name = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f"{self.label}: {self.name or '—'}"


# ---------------------------------------------------------------------------
# Registration — combines GuardianDetails + CandidateDetails + Lineage +
# ConsentState from the frontend into a single document, since they're all
# submitted together as one registration.
# ---------------------------------------------------------------------------

class Registration(models.Model):

    class Gender(models.TextChoices):
        BRIDE = "Bride", "Bride"
        GROOM = "Groom", "Groom"

    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"

    class ConsentChoice(models.TextChoices):
        AGREE = "agree", "Agree"
        NOT_YET = "not-yet", "Not yet"

    class Language(models.TextChoices):
        ENGLISH = "en", "English"
        HINDI = "hi", "Hindi"
        MAITHILI = "mai", "Maithili"

    # ---- Meta / lifecycle -------------------------------------------------
    reference = models.CharField(max_length=20, unique=True, editable=False)
    language = models.CharField(
        max_length=5, choices=Language.choices, default=Language.ENGLISH
    )
    verification_status = models.CharField(
        max_length=10,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    withdrawn = models.BooleanField(default=False)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    # ---- Guardian details (GuardianDetails) --------------------------------
    guardian_name = models.CharField(max_length=150)
    guardian_relation_to_candidate = models.CharField(max_length=100)
    guardian_village = models.CharField(max_length=150, blank=True)
    guardian_district = models.CharField(max_length=150, blank=True)
    guardian_phone = models.CharField(max_length=20)
    guardian_email = models.EmailField(blank=True)

    # ---- Candidate details (CandidateDetails) ------------------------------
    candidate_full_name = models.CharField(max_length=150)
    candidate_gender = models.CharField(max_length=5, choices=Gender.choices)
    candidate_dob = models.DateField()
    candidate_education = models.CharField(max_length=200, blank=True)
    candidate_occupation = models.CharField(max_length=200, blank=True)
    candidate_current_city = models.CharField(max_length=150, blank=True)

    # ---- Lineage (Lineage / LineageEntry) — embedded, not a separate table
    gotra = models.CharField(max_length=150, blank=True)
    mool_gram = models.CharField(max_length=150, blank=True)
    paternal_line = EmbeddedModelArrayField(LineageEntry, blank=True, default=list)
    maternal_line = EmbeddedModelArrayField(LineageEntry, blank=True, default=list)

    # ---- Consent (ConsentState) --------------------------------------------
    consent_choice = models.CharField(
        max_length=10, choices=ConsentChoice.choices, blank=True
    )
    consent_own_words = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} — {self.candidate_full_name}"

    def save(self, *args, **kwargs):
        # MOCK-style reference generation, matching the frontend's
        # "SG-XXXXXX" format from RegistrationFlow.tsx. Replace with a more
        # robust generator (e.g. checked against collisions) before production.
        if not self.reference:
            import random
            self.reference = f"SG-{random.randint(100000, 999999)}"
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# MatchProposal — mirrors MatchProposal / PartyResponse from
# MatchProposalScreen.tsx. Lives in its own collection since it has its own
# lifecycle independent of the registration itself.
# ---------------------------------------------------------------------------

class MatchProposal(models.Model):

    class PartyResponse(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    registration = models.ForeignKey(
        Registration, on_delete=models.CASCADE, related_name="match_proposals"
    )
    paired_proposal = models.ForeignKey(
    "self",
     null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name="+",
    )

    shared_by_panjikar = models.CharField(max_length=150)
    proposed_on = models.DateField(auto_now_add=True)

    # Only what the panjikar chose to share — plain facts, no photo, no score.
    shared_details = ArrayField(
        models.CharField(max_length=300), blank=True, default=list
    )

    your_response = models.CharField(
        max_length=10, choices=PartyResponse.choices, default=PartyResponse.PENDING
    )
    other_response = models.CharField(
        max_length=10, choices=PartyResponse.choices, default=PartyResponse.PENDING
    )

    # Populated only once both sides have accepted — never before.
    contact_guardian_name = models.CharField(max_length=150, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)

    

    class Meta:
        ordering = ["-proposed_on"]

    def __str__(self):
        return f"Proposal {self.pk} for {self.registration.reference}"

    @property
    def state(self):
        """
        Derives the same four-state value the frontend computes in
        MatchProposalScreen.tsx's deriveState(): waiting_you / waiting_other /
        both_accepted / declined.
        """
        if (
            self.your_response == self.PartyResponse.DECLINED
            or self.other_response == self.PartyResponse.DECLINED
        ):
            return "declined"
        if (
            self.your_response == self.PartyResponse.ACCEPTED
            and self.other_response == self.PartyResponse.ACCEPTED
        ):
            return "both_accepted"
        if self.your_response == self.PartyResponse.ACCEPTED:
            return "waiting_other"
        return "waiting_you"

# ---------------------------------------------------------------------------
# MatchAttemptLog — records every matching decision the automated engine
# makes, whether or not it resulted in a proposal. This is the accountability
# trail for a system that runs with no human review step.
# ---------------------------------------------------------------------------

class MatchAttemptLog(models.Model):

    class Outcome(models.TextChoices):
        MATCHED = "matched", "Matched"
        NO_ELIGIBLE_CANDIDATE = "no_eligible_candidate", "No eligible candidate"

    registration = models.ForeignKey(
        Registration, on_delete=models.CASCADE, related_name="match_attempts"
    )
    ran_at = models.DateTimeField(auto_now_add=True)
    outcome = models.CharField(max_length=30, choices=Outcome.choices)

    # The registration that was ultimately chosen, if any.
    matched_registration = models.ForeignKey(
        Registration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    # Every candidate considered, and why each one was accepted or rejected —
    # this is what makes a "why did the system propose/not propose this"
    # question actually answerable later.
    candidates_considered = models.JSONField(default=list, blank=True)

    sapinda_rules_version = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["-ran_at"]

    def __str__(self):
        return f"Match attempt for {self.registration.reference} — {self.outcome} ({self.ran_at:%Y-%m-%d %H:%M})"


# ---------------------------------------------------------------------------
# ConcernReport — mirrors ConcernSubmission from ReportConcernForm.tsx.
# ---------------------------------------------------------------------------

class ConcernReport(models.Model):

    class Topic(models.TextChoices):
        DETAIL_FEELS_WRONG = "detail_feels_wrong", "A detail feels wrong"
        UNWANTED_CONTACT = "unwanted_contact", "Unwanted contact"
        UNSURE_ABOUT_MATCH = "unsure_about_match", "Unsure about a match"
        SOMETHING_ELSE = "something_else", "Something else"

    # Optional link — the frontend form allows submitting without a
    # registration reference on hand, so this isn't required.
    registration = models.ForeignKey(
        Registration,
        on_delete=models.SET_NULL,
        related_name="concern_reports",
        null=True,
        blank=True,
    )
    registration_reference_text = models.CharField(
        max_length=20,
        blank=True,
        help_text="Raw reference as typed by the user, kept even if it doesn't match a real Registration.",
    )

    topic = models.CharField(max_length=30, choices=Topic.choices, blank=True)
    description = models.TextField()
    contact_back = models.CharField(max_length=200, blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Concern #{self.pk} ({self.submitted_at:%Y-%m-%d})"