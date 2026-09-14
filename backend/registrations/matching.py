"""
Automated matching pipeline.

Flow, per the earlier design discussion:
  1. Pool filter (hard, non-negotiable): opposite gender, both verified,
     neither withdrawn, neither already in an active proposal.
  2. Sapinda gate (hard, non-negotiable): registrations.sapinda.check_sapinda_conflict.
  3. If exactly one candidate survives steps 1-2 -> propose them.
  4. If multiple survive -> use preferences (age range, location, education)
     as TIE-BREAKERS to rank, not to exclude.
  5. If none survive -> no proposal is created; the registration remains
     unmatched until the pipeline runs again (e.g. when a new registration
     is verified).

Every call to find_match_for() writes a MatchAttemptLog entry, regardless
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


def _has_active_proposal(registration: Registration) -> bool:
    """
    'Active' = not fully resolved. A proposal is resolved once either side
    has declined. Anything still pending/accepted-waiting counts as active,
    since we don't want to double-propose someone mid-conversation.
    """
    return MatchProposal.objects.filter(
        registration=registration
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
    if registration.preferred_age_min and candidate_age < registration.preferred_age_min:
        score += (registration.preferred_age_min - candidate_age)
    if registration.preferred_age_max and candidate_age > registration.preferred_age_max:
        score += (candidate_age - registration.preferred_age_max)

    if (
        registration.preferred_location
        and candidate.candidate_current_city.strip().lower()
        != registration.preferred_location.strip().lower()
    ):
        score += 5

    if (
        registration.preferred_education
        and candidate.candidate_education.strip().lower()
        != registration.preferred_education.strip().lower()
    ):
        score += 3

    return score


def find_match_for(registration: Registration):
    """
    Runs the full pipeline for a single registration. Returns the matched
    Registration, or None if nobody currently qualifies. Always writes a
    MatchAttemptLog entry, regardless of outcome, so every automated
    decision is traceable after the fact.
    """
    if _has_active_proposal(registration):
        return None

    considered = []
    eligible = []

    for candidate in _candidate_pool(registration):
        if _has_active_proposal(candidate):
            considered.append({
                "candidate_reference": candidate.reference,
                "skipped_reason": "candidate already has an active proposal",
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
        return None

    eligible.sort(key=lambda c: _preference_score(registration, c))
    chosen = eligible[0]

    MatchAttemptLog.objects.create(
        registration=registration,
        outcome=MatchAttemptLog.Outcome.MATCHED,
        matched_registration=chosen,
        candidates_considered=considered,
        sapinda_rules_version=SAPINDA_RULES_VERSION,
    )

    return chosen


def create_automated_proposal(registration: Registration) -> MatchProposal | None:
    """
    Finds a match and creates the MatchProposal record. Returns None (and
    creates nothing) if no eligible candidate currently exists.
    """
    match = find_match_for(registration)
    if match is None:
        return None

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

    return proposal_for_registration