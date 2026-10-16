"""Hard-rule matching for verified registrations.

A candidate is eligible only if it passes every rule below. Any single
failure rejects it, and every reason is recorded in the audit log.

  1. Different gotra
  2. Different moolgram (ancestral village)
  3. No shared ancestor name within the first PATERNAL_GENERATIONS paternal
     and MATERNAL_GENERATIONS maternal entries (paternal/paternal,
     maternal/maternal and both cross-line combinations)
  4. Groom is at least as old as the bride

Every pool candidate is recorded in ``MatchAttemptLog.candidates_considered``.
ALL eligible candidates are chosen (multiple matches per registration allowed).
Duplicate pairs (A,B) and (B,A) are prevented by checking existing Matches.
"""

from dataclasses import dataclass
from datetime import date
from itertools import islice

from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db import models, transaction
from django.utils import timezone

from .models import Match, MatchAttemptLog, MatchProposal, Registration
from .sapinda import SAPINDA_RULES_VERSION


PATERNAL_GENERATIONS = 3
MATERNAL_GENERATIONS = 2

# Name of the moolgram / ancestral village field on Registration.
# Change this if your model uses a different name (e.g. "ancestral_village").
MOOLGRAM_FIELD = "mool_gram"

# Deterministic order so results are stable across runs.
# Use ("created_at", "pk") if you want the oldest registration to win.
CANDIDATE_ORDERING = ("pk",)

# Rows fetched per DB round-trip while streaming the pool.
POOL_CHUNK_SIZE = 500

DECISION_ACCEPTED = "accepted"
DECISION_REJECTED = "rejected"
ACCEPTED_REASON = "passed gotra, moolgram, sapinda, and age rules"

# Rejection reason codes for structured logging / UI tooltips
REASON_SAME_GOTRA = "SAME_GOTRA"
REASON_SAME_MOOLGRAM = "SAME_MOOLGRAM"
REASON_SHARED_ANCESTOR = "SHARED_ANCESTOR"
REASON_AGE = "GROOM_YOUNGER"
REASON_MOOLGRAM_MISSING = "MOOLGRAM_MISSING"


# --------------------------------------------------------------------------
# Normalisation and profiles
# --------------------------------------------------------------------------

def _clean(value) -> str:
    """Trim and collapse inner whitespace: '  Ban   Gaun ' -> 'Ban Gaun'."""
    return " ".join(str(value or "").split())


def _lineage_names(entries, limit: int) -> frozenset[str]:
    """Normalised ancestor names from the first ``limit`` lineage entries."""
    names = set()
    for entry in islice(entries or (), limit):
        raw = entry.get("name", "") if isinstance(entry, dict) else getattr(entry, "name", "")
        key = _clean(raw).casefold()
        if key:
            names.add(key)
    return frozenset(names)


@dataclass(frozen=True, slots=True)
class _Profile:
    """Normalised, comparison-ready view of a registration.

    Built once per registration, so the searching registration is processed a
    single time instead of once per candidate.
    """

    gotra: str
    gotra_key: str
    moolgram: str
    moolgram_key: str
    moolgram_missing: bool
    paternal: frozenset[str]
    maternal: frozenset[str]
    dob: date | None
    gender: str


def _build_profile(reg: Registration) -> _Profile:
    gotra = _clean(reg.gotra)
    moolgram_raw = _clean(getattr(reg, MOOLGRAM_FIELD, ""))
    moolgram_missing = not moolgram_raw
    return _Profile(
        gotra=gotra,
        gotra_key=gotra.casefold(),
        moolgram=moolgram_raw,
        moolgram_key=moolgram_raw.casefold(),
        moolgram_missing=moolgram_missing,
        paternal=_lineage_names(reg.paternal_line, PATERNAL_GENERATIONS),
        maternal=_lineage_names(reg.maternal_line, MATERNAL_GENERATIONS),
        dob=reg.candidate_dob,
        gender=reg.candidate_gender,
    )


def _check_moolgram_field() -> None:
    """Fail loudly if the moolgram field is misnamed.

    Without this, a wrong field name would silently disable the rule and let
    same-village candidates through.
    """
    try:
        Registration._meta.get_field(MOOLGRAM_FIELD)
    except FieldDoesNotExist:
        raise ImproperlyConfigured(
            f"Registration has no field '{MOOLGRAM_FIELD}'. Set MOOLGRAM_FIELD "
            "in matching_engine.py to the correct field name."
        ) from None


# --------------------------------------------------------------------------
# Rules (each returns a rejection reason, or None / empty list when it passes)
# --------------------------------------------------------------------------

def _gotra_reason(me: _Profile, other: _Profile) -> tuple[str, str] | None:
    """Returns (reason_code, reason_detail) or None if passes."""
    if me.gotra_key and me.gotra_key == other.gotra_key:
        return (REASON_SAME_GOTRA, f"same gotra: {other.gotra}")
    return None


def _moolgram_reason(me: _Profile, other: _Profile) -> tuple[str, str] | None:
    """Returns (reason_code, reason_detail) or None if passes.
    
    If either moolgram is missing, the check is SKIPPED (returns None) but
    the caller should note "needs review" in the audit log.
    """
    if me.moolgram_missing or other.moolgram_missing:
        return None  # Skip check - caller handles "needs review" logging
    if me.moolgram_key == other.moolgram_key:
        return (REASON_SAME_MOOLGRAM, f"same moolgram: {other.moolgram}")
    return None


def _ancestor_reasons(me: _Profile, other: _Profile) -> list[tuple[str, str]]:
    """Shared named ancestors across the paternal and maternal lines.
    
    Returns list of (reason_code, reason_detail) tuples.
    """
    reasons = []
    for line_name, mine, theirs in (
        ("paternal", me.paternal, other.paternal),
        ("maternal", me.maternal, other.maternal),
        ("paternal/maternal", me.paternal, other.maternal),
        ("maternal/paternal", me.maternal, other.paternal),
    ):
        for name in sorted(mine & theirs):
            reasons.append((REASON_SHARED_ANCESTOR, f"shared ancestor name '{name}' ({line_name})"))
    return reasons


def _age_reason(me: _Profile, other: _Profile) -> tuple[str, str] | None:
    """The groom must be at least as old as the bride (same day passes).
    
    Returns (reason_code, reason_detail) or None if passes.
    """
    if me.dob is None or other.dob is None:
        return (REASON_AGE, "date of birth missing")

    if me.gender == Registration.Gender.BRIDE:
        groom_dob, bride_dob = other.dob, me.dob
    else:
        groom_dob, bride_dob = me.dob, other.dob

    return None if groom_dob <= bride_dob else (REASON_AGE, "groom is younger than bride")


# --------------------------------------------------------------------------
# Candidate pool
# --------------------------------------------------------------------------

def _opposite_gender(gender: str) -> str:
    return (
        Registration.Gender.GROOM
        if gender == Registration.Gender.BRIDE
        else Registration.Gender.BRIDE
    )


def _candidate_pool(registration: Registration):
    return (
        Registration.objects.filter(
            withdrawn=False,
            verification_status=Registration.VerificationStatus.VERIFIED,
            candidate_gender=_opposite_gender(registration.candidate_gender),
        )
        .exclude(pk=registration.pk)
        .order_by(*CANDIDATE_ORDERING)
    )


def _age_years(dob, today: date | None = None) -> int:
    today = today or timezone.localdate()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


# --------------------------------------------------------------------------
# Engine
# --------------------------------------------------------------------------

def _match_exists(registration: Registration, candidate: Registration) -> bool:
    """Check if a Match already exists between these two registrations in either direction."""
    return Match.objects.filter(
        models.Q(registration=registration, candidate=candidate) |
        models.Q(registration=candidate, candidate=registration)
    ).exists()


def run_matching_engine(registration: Registration):
    """Evaluate the verified opposite-gender pool and persist ALL eligible Matches.

    Candidates are streamed from the database. Every eligible candidate creates
    a Match record. Duplicate pairs (A,B) and (B,A) are prevented by checking
    existing Matches. Every candidate gets an audit entry in
    ``candidates_considered``.
    """
    from django.db import models
    _check_moolgram_field()
    me = _build_profile(registration)

    considered = []
    eligible_candidates = []
    pool_size = 0
    post_gotra_size = 0

    for candidate in _candidate_pool(registration).iterator(chunk_size=POOL_CHUNK_SIZE):
        pool_size += 1
        other = _build_profile(candidate)

        gotra_reason = _gotra_reason(me, other)
        if gotra_reason is None:
            post_gotra_size += 1

        moolgram_reason = _moolgram_reason(me, other)
        moolgram_missing = me.moolgram_missing or other.moolgram_missing

        reason_tuples = [
            reason
            for reason in (
                gotra_reason,
                moolgram_reason,
                *_ancestor_reasons(me, other),
                _age_reason(me, other),
            )
            if reason
        ]

        # Convert reason tuples to dict format for audit log
        reasons_detail = [{"code": code, "detail": detail} for code, detail in reason_tuples]

        if reason_tuples:
            considered.append({
                "candidate_reference": candidate.reference,
                "decision": DECISION_REJECTED,
                "reasons": reasons_detail,
            })
            continue

        # Eligible candidate - check for duplicate pair before adding
        if _match_exists(registration, candidate):
            considered.append({
                "candidate_reference": candidate.reference,
                "decision": DECISION_REJECTED,
                "reasons": [{"code": "DUPLICATE_PAIR", "detail": "match already exists"}],
            })
            continue

        # Include any "needs review" notes in the accepted reasons
        accepted_reasons = [{"code": "ACCEPTED", "detail": ACCEPTED_REASON}]
        if moolgram_missing:
            accepted_reasons.append({
                "code": "NEEDS_REVIEW",
                "detail": "moolgram missing - manual review recommended"
            })

        considered.append({
            "candidate_reference": candidate.reference,
            "decision": DECISION_ACCEPTED,
            "reasons": accepted_reasons,
        })
        eligible_candidates.append(candidate)

    outcome = (
        MatchAttemptLog.Outcome.MATCHED
        if eligible_candidates
        else MatchAttemptLog.Outcome.NO_ELIGIBLE_CANDIDATE
    )

    # Match and audit log are written together or not at all.
    with transaction.atomic():
        for candidate in eligible_candidates:
            Match.objects.create(
                registration=registration,
                candidate=candidate,
                score=0.0,
                status=Match.Status.PENDING,
            )
        MatchAttemptLog.objects.create(
            registration=registration,
            outcome=outcome,
            matched_registration=eligible_candidates[0] if eligible_candidates else None,
            candidates_considered=considered,
            sapinda_rules_version=SAPINDA_RULES_VERSION,
        )

    return {
        "pool_size": pool_size,
        "post_gotra_size": post_gotra_size,
        "final_matches": [(c, 0.0) for c in eligible_candidates],
        "audit_log": {
            "outcome": outcome,
            "pool_size": pool_size,
            "final_count": len(eligible_candidates),
        },
    }


def create_automated_proposal(registration: Registration):
    """Create paired MatchProposal rows for ALL eligible matches from the engine.

    Idempotent per pair: if a proposal already exists for a specific pair
    (in either direction) we skip that pair, so Celery retries or
    re-verifications don't pile up duplicates.
    Returns the first created proposal (for backward compatibility) or None.
    """
    result = run_matching_engine(registration)
    if not result["final_matches"]:
        return None

    today = timezone.localdate()
    first_proposal = None

    for candidate, _ in result["final_matches"]:
        with transaction.atomic():
            # Check if a proposal already exists for this specific pair
            has_proposal_for_pair = MatchProposal.objects.filter(
                models.Q(registration=registration, paired_proposal__registration=candidate) |
                models.Q(registration=candidate, paired_proposal__registration=registration)
            ).exists()
            if has_proposal_for_pair:
                continue

            proposal_for_registration = MatchProposal.objects.create(
                registration=registration,
                shared_by_panjikar="Matched by Sabha Gachhi",
                shared_details=_build_shared_details(registration, candidate, today),
            )
            proposal_for_match = MatchProposal.objects.create(
                registration=candidate,
                shared_by_panjikar="Matched by Sabha Gachhi",
                shared_details=_build_shared_details(candidate, registration, today),
                paired_proposal=proposal_for_registration,
            )
            proposal_for_registration.paired_proposal = proposal_for_match
            proposal_for_registration.save(update_fields=["paired_proposal"])

            if first_proposal is None:
                first_proposal = proposal_for_registration

    return first_proposal


def _build_shared_details(from_reg, to_reg, today: date | None = None) -> list:
    details = []
    if to_reg.candidate_current_city:
        details.append(f"From {to_reg.candidate_current_city}")
    details.append(f"Age {_age_years(to_reg.candidate_dob, today)}")
    if to_reg.candidate_occupation:
        details.append(f"Works as {to_reg.candidate_occupation}")
    if to_reg.candidate_education:
        details.append(f"Educated: {to_reg.candidate_education}")
    return details