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
The first eligible candidate (in CANDIDATE_ORDERING order) is chosen.
"""

from dataclasses import dataclass
from datetime import date
from itertools import islice

from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db import transaction
from django.utils import timezone

from .models import Match, MatchAttemptLog, MatchProposal, Registration
from .sapinda import SAPINDA_RULES_VERSION


PATERNAL_GENERATIONS = 3
MATERNAL_GENERATIONS = 2

# Name of the moolgram / ancestral village field on Registration.
# Change this if your model uses a different name (e.g. "ancestral_village").
MOOLGRAM_FIELD = "moolgram"

# Deterministic order so the "first eligible" candidate is stable across runs.
# Use ("created_at", "pk") if you want the oldest registration to win.
CANDIDATE_ORDERING = ("pk",)

# Rows fetched per DB round-trip while streaming the pool.
POOL_CHUNK_SIZE = 500

DECISION_ACCEPTED = "accepted"
DECISION_REJECTED = "rejected"
ACCEPTED_REASON = "passed gotra, moolgram, sapinda, and age rules"


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
    paternal: frozenset[str]
    maternal: frozenset[str]
    dob: date | None
    gender: str


def _build_profile(reg: Registration) -> _Profile:
    gotra = _clean(reg.gotra)
    moolgram = _clean(getattr(reg, MOOLGRAM_FIELD, ""))
    return _Profile(
        gotra=gotra,
        gotra_key=gotra.casefold(),
        moolgram=moolgram,
        moolgram_key=moolgram.casefold(),
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

def _gotra_reason(me: _Profile, other: _Profile) -> str | None:
    if me.gotra_key and me.gotra_key == other.gotra_key:
        return f"same gotra: {other.gotra}"
    return None


def _moolgram_reason(me: _Profile, other: _Profile) -> str | None:
    if me.moolgram_key and me.moolgram_key == other.moolgram_key:
        return f"same moolgram: {other.moolgram}"
    return None


def _ancestor_reasons(me: _Profile, other: _Profile) -> list[str]:
    """Shared named ancestors across the paternal and maternal lines."""
    reasons = []
    for line_name, mine, theirs in (
        ("paternal", me.paternal, other.paternal),
        ("maternal", me.maternal, other.maternal),
        ("paternal/maternal", me.paternal, other.maternal),
        ("maternal/paternal", me.maternal, other.paternal),
    ):
        for name in sorted(mine & theirs):
            reasons.append(f"shared ancestor name '{name}' ({line_name})")
    return reasons


def _age_reason(me: _Profile, other: _Profile) -> str | None:
    """The groom must be at least as old as the bride (same day passes)."""
    if me.dob is None or other.dob is None:
        return "date of birth missing"

    if me.gender == Registration.Gender.BRIDE:
        groom_dob, bride_dob = other.dob, me.dob
    else:
        groom_dob, bride_dob = me.dob, other.dob

    return None if groom_dob <= bride_dob else "groom is younger than bride"


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

def run_matching_engine(registration: Registration):
    """Evaluate the verified opposite-gender pool and persist one Match.

    Candidates are streamed from the database and only the first eligible
    one is kept in memory. Every candidate still gets an audit entry in
    ``candidates_considered``.
    """
    _check_moolgram_field()
    me = _build_profile(registration)

    considered = []
    chosen = None
    pool_size = 0
    post_gotra_size = 0
    eligible_count = 0

    for candidate in _candidate_pool(registration).iterator(chunk_size=POOL_CHUNK_SIZE):
        pool_size += 1
        other = _build_profile(candidate)

        gotra_reason = _gotra_reason(me, other)
        if gotra_reason is None:
            post_gotra_size += 1

        reasons = [
            reason
            for reason in (
                gotra_reason,
                _moolgram_reason(me, other),
                *_ancestor_reasons(me, other),
                _age_reason(me, other),
            )
            if reason
        ]

        if reasons:
            considered.append({
                "candidate_reference": candidate.reference,
                "decision": DECISION_REJECTED,
                "reasons": reasons,
            })
            continue

        considered.append({
            "candidate_reference": candidate.reference,
            "decision": DECISION_ACCEPTED,
            "reasons": [ACCEPTED_REASON],
        })
        eligible_count += 1
        if chosen is None:
            chosen = candidate

    outcome = (
        MatchAttemptLog.Outcome.MATCHED
        if chosen is not None
        else MatchAttemptLog.Outcome.NO_ELIGIBLE_CANDIDATE
    )

    # Match and audit log are written together or not at all.
    with transaction.atomic():
        if chosen is not None:
            Match.objects.update_or_create(
                registration=registration,
                candidate=chosen,
                defaults={"score": 0.0, "status": Match.Status.PENDING},
            )
        MatchAttemptLog.objects.create(
            registration=registration,
            outcome=outcome,
            matched_registration=chosen,
            candidates_considered=considered,
            sapinda_rules_version=SAPINDA_RULES_VERSION,
        )

    return {
        "pool_size": pool_size,
        "post_gotra_size": post_gotra_size,
        "final_matches": [(chosen, 0.0)] if chosen is not None else [],
        "audit_log": {
            "outcome": outcome,
            "pool_size": pool_size,
            "final_count": eligible_count,
        },
    }


def create_automated_proposal(registration: Registration):
    """Create paired MatchProposal rows for the engine's selected Match.

    Idempotent: if this registration already has an active proposal we do
    nothing, so Celery retries or re-verifications don't pile up duplicates.
    Both proposals are created and linked in one transaction, so a failure
    can never leave an unpaired proposal behind.
    """
    with transaction.atomic():
        has_active_proposal = registration.match_proposals.exclude(
            your_response=MatchProposal.PartyResponse.DECLINED,
            other_response=MatchProposal.PartyResponse.DECLINED,
        ).exists()
        if has_active_proposal:
            return None

        result = run_matching_engine(registration)
        if not result["final_matches"]:
            return None

        top_candidate, _ = result["final_matches"][0]
        today = timezone.localdate()

        proposal_for_registration = MatchProposal.objects.create(
            registration=registration,
            shared_by_panjikar="Matched by Sabha Gachhi",
            shared_details=_build_shared_details(registration, top_candidate, today),
        )
        # Created already linked back, so only one extra write is needed below.
        proposal_for_match = MatchProposal.objects.create(
            registration=top_candidate,
            shared_by_panjikar="Matched by Sabha Gachhi",
            shared_details=_build_shared_details(top_candidate, registration, today),
            paired_proposal=proposal_for_registration,
        )
        proposal_for_registration.paired_proposal = proposal_for_match
        proposal_for_registration.save(update_fields=["paired_proposal"])
        return proposal_for_registration


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