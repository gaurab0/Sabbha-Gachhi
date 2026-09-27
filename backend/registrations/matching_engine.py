"""Hard-rule matching for verified registrations."""

from datetime import date as _date

from django.utils import timezone

from .models import Match, MatchAttemptLog, MatchProposal, Registration
from .sapinda import SAPINDA_RULES_VERSION


PATERNAL_GENERATIONS = 3
MATERNAL_GENERATIONS = 2


def _opposite_gender(gender: str) -> str:
    return (
        Registration.Gender.GROOM
        if gender == Registration.Gender.BRIDE
        else Registration.Gender.BRIDE
    )


def _candidate_pool(registration: Registration):
    return Registration.objects.filter(
        withdrawn=False,
        verification_status=Registration.VerificationStatus.VERIFIED,
        candidate_gender=_opposite_gender(registration.candidate_gender),
    ).exclude(pk=registration.pk)


def _age_years(dob) -> int:
    today = timezone.now().date()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _lineage_names(entries, limit: int) -> set[str]:
    names = set()
    for entry in list(entries or [])[:limit]:
        name = entry.get("name", "") if isinstance(entry, dict) else entry.name
        if name:
            names.add(name.strip().casefold())
    return names


def _sapinda_reasons(registration: Registration, candidate: Registration) -> list[str]:
    """Reject same gotra or any shared named ancestor in the defined lines.

    The fixed rule checks the first three paternal and first two maternal
    entries, including paternal-to-maternal cross-line comparisons.
    """
    reasons = []
    if registration.gotra and candidate.gotra:
        if registration.gotra.strip().casefold() == candidate.gotra.strip().casefold():
            reasons.append(f"same gotra: {candidate.gotra}")

    registration_paternal = _lineage_names(
        registration.paternal_line, PATERNAL_GENERATIONS
    )
    registration_maternal = _lineage_names(
        registration.maternal_line, MATERNAL_GENERATIONS
    )
    candidate_paternal = _lineage_names(candidate.paternal_line, PATERNAL_GENERATIONS)
    candidate_maternal = _lineage_names(candidate.maternal_line, MATERNAL_GENERATIONS)

    for line_name, shared_names in (
        ("paternal", registration_paternal & candidate_paternal),
        ("maternal", registration_maternal & candidate_maternal),
        ("paternal/maternal", registration_paternal & candidate_maternal),
        ("maternal/paternal", registration_maternal & candidate_paternal),
    ):
        for name in sorted(shared_names):
            reasons.append(f"shared ancestor name '{name}' ({line_name})")
    return reasons


def _age_rule_reason(registration: Registration, candidate: Registration) -> str | None:
    """Enforce the fixed rule that the groom is at least as old as the bride."""
    if registration.candidate_gender == Registration.Gender.BRIDE:
        groom_dob, bride_dob = candidate.candidate_dob, registration.candidate_dob
    else:
        groom_dob, bride_dob = registration.candidate_dob, candidate.candidate_dob

    if groom_dob <= bride_dob:
        return None
    return "groom is younger than bride"


def run_matching_engine(registration: Registration):
    """Evaluate the verified opposite-gender pool and persist one Match.

    Every pool candidate is recorded in ``candidates_considered``. The
    engine's fixed rules are same-gotra rejection, the lineage rule above,
    and the rule that the groom must be at least as old as the bride.
    """
    pool = list(_candidate_pool(registration))
    considered = []
    eligible = []

    for candidate in pool:
        sapinda_reasons = _sapinda_reasons(registration, candidate)
        age_reason = _age_rule_reason(registration, candidate)
        reasons = sapinda_reasons + ([age_reason] if age_reason else [])
        if reasons:
            considered.append({
                "candidate_reference": candidate.reference,
                "decision": "rejected",
                "reasons": reasons,
            })
            continue

        considered.append({
            "candidate_reference": candidate.reference,
            "decision": "accepted",
            "reasons": ["passed gotra, sapinda, and age rules"],
        })
        eligible.append(candidate)

    chosen = eligible[0] if eligible else None
    if chosen is not None:
        Match.objects.update_or_create(
            registration=registration,
            candidate=chosen,
            defaults={"score": 0.0, "status": Match.Status.PENDING},
        )

    outcome = (
        MatchAttemptLog.Outcome.MATCHED
        if chosen is not None
        else MatchAttemptLog.Outcome.NO_ELIGIBLE_CANDIDATE
    )
    MatchAttemptLog.objects.create(
        registration=registration,
        outcome=outcome,
        matched_registration=chosen,
        candidates_considered=considered,
        sapinda_rules_version=SAPINDA_RULES_VERSION,
    )

    final_matches = [(chosen, 0.0)] if chosen is not None else []
    return {
        "pool_size": len(pool),
        "post_gotra_size": len(pool),
        "final_matches": final_matches,
        "audit_log": {
            "outcome": outcome,
            "pool_size": len(pool),
            "final_count": len(eligible),
        },
    }


def create_automated_proposal(registration: Registration):
    """Create paired MatchProposal rows for the engine's selected Match.

    Idempotent: if this registration already has an active proposal we do
    nothing, so Celery retries or re-verifications don't pile up duplicates.
    """
    if registration.match_proposals.exclude(
        your_response=MatchProposal.PartyResponse.DECLINED,
        other_response=MatchProposal.PartyResponse.DECLINED,
    ).exists():
        return None

    result = run_matching_engine(registration)
    if not result["final_matches"]:
        return None

    top_candidate, _ = result["final_matches"][0]
    proposal_for_registration = MatchProposal.objects.create(
        registration=registration,
        shared_by_panjikar="Matched by Sabha Gachhi",
        shared_details=_build_shared_details(registration, top_candidate),
    )
    proposal_for_match = MatchProposal.objects.create(
        registration=top_candidate,
        shared_by_panjikar="Matched by Sabha Gachhi",
        shared_details=_build_shared_details(top_candidate, registration),
    )

    proposal_for_registration.paired_proposal = proposal_for_match
    proposal_for_registration.save(update_fields=["paired_proposal"])
    proposal_for_match.paired_proposal = proposal_for_registration
    proposal_for_match.save(update_fields=["paired_proposal"])
    return proposal_for_registration


def _build_shared_details(from_reg, to_reg) -> list:
    age = _age_years(to_reg.candidate_dob)
    details = []
    if to_reg.candidate_current_city:
        details.append(f"From {to_reg.candidate_current_city}")
    details.append(f"Age {age}")
    if to_reg.candidate_occupation:
        details.append(f"Works as {to_reg.candidate_occupation}")
    if to_reg.candidate_education:
        details.append(f"Educated: {to_reg.candidate_education}")
    return details
