"""
Automated matching pipeline.

Flow:
  1. Pool filter (hard, non-negotiable): opposite gender, both verified,
     neither withdrawn.
  2. Sapinda gate (hard, non-negotiable): check_sapinda_conflict.
  3. ALL candidates that pass steps 1-2 become matches (multiple matches allowed).
  4. Preferences (age range, location, education) used as TIE-BREAKERS to rank.
  5. If none survive -> no proposal is created; the registration remains
     unmatched until the pipeline runs again.

Every call to find_matches_for() writes a MatchAttemptLog entry, regardless
of outcome — this is the accountability trail for a system that runs with
no human review step before a proposal is sent.
"""

from datetime import date

from django.db.models import Q

from .models import MatchAttemptLog, MatchProposal, Registration
from .sapinda import SAPINDA_RULES_VERSION, check_sapinda_conflict


def _opposite_gender(gender: str) -> str:
    return (
        Registration.Gender.GROOM
        if gender == Registration.Gender.BRIDE
        else Registration.Gender.BRIDE
    )


def _has_active_proposal_for_pair(registration: Registration, candidate: Registration) -> bool:
    """Check if an active proposal already exists for this specific pair."""
    return MatchProposal.objects.filter(
        Q(registration=registration, paired_proposal__registration=candidate) |
        Q(registration=candidate, paired_proposal__registration=registration)
    ).exclude(
        Q(your_response=MatchProposal.PartyResponse.DECLINED)
        | Q(other_response=MatchProposal.PartyResponse.DECLINED)
    ).exists()


def _candidate_pool(registration: Registration):
    return Registration.objects.filter(
        candidate_gender=_opposite_gender(registration.candidate_gender),
        verification_status=Registration.VerificationStatus.VERIFIED,
        withdrawn=False,
    ).exclude(pk=registration.pk)


def _age_years(dob) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _preference_score(registration: Registration, candidate: Registration) -> int:
    """
    Lower is better. Used ONLY to rank among candidates that already passed
    every hard filter — never to exclude anyone, per the tie-breaker design.
    This score is internal only; it must never be exposed to end users.
    """
    score = 0

    candidate_age = _age_years(candidate.candidate_dob)
    pref_age_min = getattr(registration, 'preferred_age_min', None)
    pref_age_max = getattr(registration, 'preferred_age_max', None)
    if pref_age_min and candidate_age < pref_age_min:
        score += (pref_age_min - candidate_age)
    if pref_age_max and candidate_age > pref_age_max:
        score += (candidate_age - pref_age_max)

    pref_location = getattr(registration, 'preferred_location', None)
    if (
        pref_location
        and candidate.candidate_current_city.strip().lower()
        != pref_location.strip().lower()
    ):
        score += 5

    pref_education = getattr(registration, 'preferred_education', None)
    if (
        pref_education
        and candidate.candidate_education.strip().lower()
        != pref_education.strip().lower()
    ):
        score += 3

    return score


def find_matches_for(registration: Registration):
    """
    Runs the full pipeline for a single registration. Returns a list of
    matched Registrations (may be empty). Always writes a MatchAttemptLog
    entry, regardless of outcome, so every automated decision is traceable.
    """
    considered = []
    eligible = []

    for candidate in _candidate_pool(registration):
        if _has_active_proposal_for_pair(registration, candidate):
            considered.append({
                "candidate_reference": candidate.reference,
                "skipped_reason": "candidate already has an active proposal with this registration",
            })
            continue

        result = check_sapinda_conflict(registration, candidate)
        entry = {
            "candidate_reference": candidate.reference,
            "sapinda_conflict": result.has_conflict,
            "sapinda_reasons": result.reasons,
        }

        if result.has_conflict:
            considered.append(entry)
            continue

        entry["preference_score"] = _preference_score(registration, candidate)
        considered.append(entry)
        eligible.append(candidate)

    if not eligible:
        MatchAttemptLog.objects.create(
            registration=registration,
            outcome=MatchAttemptLog.Outcome.NO_ELIGIBLE_CANDIDATE,
            candidates_considered=considered,
            sapinda_rules_version=SAPINDA_RULES_VERSION,
        )
        return []

    # Sort by preference score (lower is better) but keep all eligible
    eligible.sort(key=lambda c: _preference_score(registration, c))

    MatchAttemptLog.objects.create(
        registration=registration,
        outcome=MatchAttemptLog.Outcome.MATCHED,
        matched_registration=eligible[0],
        candidates_considered=considered,
        sapinda_rules_version=SAPINDA_RULES_VERSION,
    )

    return eligible


def create_automated_proposal(registration: Registration) -> MatchProposal | None:
    """
    Finds all eligible matches and creates MatchProposal records for each.
    Returns the first created proposal (for backward compatibility) or None.
    Idempotent per pair: skips pairs that already have an active proposal.
    """
    from django.db import transaction, models

    matches = find_matches_for(registration)
    if not matches:
        return None

    first_proposal = None

    for match in matches:
        with transaction.atomic():
            # Check if proposal already exists for this pair
            has_proposal_for_pair = MatchProposal.objects.filter(
                models.Q(registration=registration, paired_proposal__registration=match) |
                models.Q(registration=match, paired_proposal__registration=registration)
            ).exclude(
                models.Q(your_response=MatchProposal.PartyResponse.DECLINED)
                | models.Q(other_response=MatchProposal.PartyResponse.DECLINED)
            ).exists()
            if has_proposal_for_pair:
                continue

            shared_details = [
                f"From {match.candidate_current_city}" if match.candidate_current_city else None,
                f"Age {_age_years(match.candidate_dob)}",
                f"Works as {match.candidate_occupation}" if match.candidate_occupation else None,
                f"Educated: {match.candidate_education}" if match.candidate_education else None,
            ]
            shared_details = [d for d in shared_details if d]

            proposal_for_registration = MatchProposal.objects.create(
                registration=registration,
                shared_by_panjikar="Matched by Sabha Gachhi",
                shared_details=shared_details,
            )

            proposal_for_match = MatchProposal.objects.create(
                registration=match,
                shared_by_panjikar="Matched by Sabha Gachhi",
                shared_details=[
                    f"From {registration.candidate_current_city}" if registration.candidate_current_city else None,
                    f"Age {_age_years(registration.candidate_dob)}",
                    f"Works as {registration.candidate_occupation}" if registration.candidate_occupation else None,
                ],
            )

            # Link the two rows so accept/decline on one side can mirror onto the other.
            proposal_for_registration.paired_proposal = proposal_for_match
            proposal_for_registration.save(update_fields=["paired_proposal"])
            proposal_for_match.paired_proposal = proposal_for_registration
            proposal_for_match.save(update_fields=["paired_proposal"])

            if first_proposal is None:
                first_proposal = proposal_for_registration

    return first_proposal