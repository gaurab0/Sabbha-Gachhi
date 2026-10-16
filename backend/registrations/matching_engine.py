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
Multiple matches per registration are allowed and ranked deterministically by
internal preference score (as tie-breaker only) and primary key.
Duplicate pairs (A,B) and (B,A) are prevented by unique DB constraints and pre-checks.
"""

from dataclasses import dataclass
from datetime import date
from itertools import islice

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db import IntegrityError, models, transaction
from django.utils import timezone

from .models import Match, MatchAttemptLog, MatchProposal, Registration
from .sapinda import SAPINDA_RULES_VERSION


PATERNAL_GENERATIONS = 3
MATERNAL_GENERATIONS = 2

# Name of the moolgram / ancestral village field on Registration.
MOOLGRAM_FIELD = "mool_gram"

# Deterministic order so candidate pool streaming is stable across runs.
CANDIDATE_ORDERING = ("pk",)

# Rows fetched per DB round-trip while streaming the pool.
POOL_CHUNK_SIZE = 500

DECISION_ACCEPTED = "accepted"
DECISION_REJECTED = "rejected"
DECISION_ELIGIBLE_NOT_SELECTED = "eligible_not_selected"

ACCEPTED_REASON = "passed gotra, moolgram, sapinda, and age rules"

# Reason codes for structured logging / UI tooltips
REASON_SAME_GOTRA = "SAME_GOTRA"
REASON_SAME_MOOLGRAM = "SAME_MOOLGRAM"
REASON_SHARED_ANCESTOR = "SHARED_ANCESTOR"
REASON_AGE = "GROOM_YOUNGER"
REASON_MOOLGRAM_MISSING = "MOOLGRAM_MISSING"
REASON_ALREADY_MATCHED = "ALREADY_MATCHED_WITH_PROPOSAL"
REASON_DECLINED_PAIR = "DECLINED_PAIR"
REASON_CAP_REACHED = "CAP_REACHED"
REASON_PROPOSAL_HEALED = "PROPOSAL_HEALED"

# Configurable match cap per registration (None = unlimited)
MAX_MATCHES_PER_REGISTRATION = getattr(settings, "MAX_MATCHES_PER_REGISTRATION", None)
# Optional candidate incoming proposal cap (None = unlimited)
# TODO: Implement MAX_INCOMING_PROPOSALS_PER_REGISTRATION cap if candidate proposal intake throttling is needed in future.
MAX_INCOMING_PROPOSALS_PER_REGISTRATION = getattr(
    settings, "MAX_INCOMING_PROPOSALS_PER_REGISTRATION", None
)


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
    """Fail loudly if the moolgram field is misnamed."""
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
    the caller notes 'needs review' in the audit log.
    """
    if me.moolgram_missing or other.moolgram_missing:
        return None
    if me.moolgram_key == other.moolgram_key:
        return (REASON_SAME_MOOLGRAM, f"same moolgram: {other.moolgram}")
    return None


def _ancestor_reasons(me: _Profile, other: _Profile) -> list[tuple[str, str]]:
    """Shared named ancestors across the paternal and maternal lines."""
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
    """The groom must be at least as old as the bride (same day passes)."""
    if me.dob is None or other.dob is None:
        return (REASON_AGE, "date of birth missing")

    if me.gender == Registration.Gender.BRIDE:
        groom_dob, bride_dob = other.dob, me.dob
    else:
        groom_dob, bride_dob = me.dob, other.dob

    return None if groom_dob <= bride_dob else (REASON_AGE, "groom is younger than bride")


# --------------------------------------------------------------------------
# Candidate pool & Helpers
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


def _age_years(dob: date, today: date | None = None) -> int:
    today = today or timezone.localdate()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _normalize_pair(id_a, id_b) -> tuple[str, str]:
    """Return deterministically sorted string pair IDs."""
    return tuple(sorted([str(id_a), str(id_b)]))


def _preference_score(
    registration: Registration,
    candidate: Registration,
    candidate_age: int | None = None,
    today: date | None = None,
) -> int:
    """
    Lower is better. Used ONLY to rank among candidates that already passed
    every hard filter — never to exclude anyone, per the tie-breaker design.
    This score is internal only; it must never be exposed to end users.
    """
    score = 0

    if candidate_age is None and candidate.candidate_dob is not None:
        candidate_age = _age_years(candidate.candidate_dob, today)

    pref_age_min = getattr(registration, "preferred_age_min", None)
    pref_age_max = getattr(registration, "preferred_age_max", None)
    if candidate_age is not None:
        if pref_age_min and candidate_age < pref_age_min:
            score += (pref_age_min - candidate_age)
        if pref_age_max and candidate_age > pref_age_max:
            score += (candidate_age - pref_age_max)

    pref_location = getattr(registration, "preferred_location", None)
    cand_city = getattr(candidate, "candidate_current_city", "") or ""
    if (
        pref_location
        and cand_city.strip().lower()
        != pref_location.strip().lower()
    ):
        score += 5

    pref_education = getattr(registration, "preferred_education", None)
    cand_edu = getattr(candidate, "candidate_education", "") or ""
    if (
        pref_education
        and cand_edu.strip().lower()
        != pref_education.strip().lower()
    ):
        score += 3

    return score


def _build_shared_details(from_reg, to_reg, today: date | None = None) -> list[str]:
    """Build shared details for proposals.

    Plain facts only: city, age, occupation, education.
    Safe when candidate_dob is None (omits the age line instead of raising).
    """
    today = today or timezone.localdate()
    details = []
    if to_reg.candidate_current_city:
        details.append(f"From {to_reg.candidate_current_city}")
    if to_reg.candidate_dob is not None:
        details.append(f"Age {_age_years(to_reg.candidate_dob, today)}")
    if to_reg.candidate_occupation:
        details.append(f"Works as {to_reg.candidate_occupation}")
    if to_reg.candidate_education:
        details.append(f"Educated: {to_reg.candidate_education}")
    return details


def _match_exists(registration: Registration, candidate: Registration) -> bool:
    """Check if a Match already exists between these two registrations in either direction."""
    low_id, high_id = _normalize_pair(registration.pk, candidate.pk)
    return Match.objects.filter(pair_low_id=low_id, pair_high_id=high_id).exists()


# --------------------------------------------------------------------------
# Matching Engine Core
# --------------------------------------------------------------------------

def run_matching_engine(registration: Registration) -> dict:
    """Evaluate the verified opposite-gender pool, rank by preference, and persist Matches & Proposals.

    Candidates are streamed from the database. Every eligible candidate creates
    or heals a Match and paired MatchProposal in an atomic, idempotent, and
    self-healing transaction per pair.
    """
    _check_moolgram_field()
    me = _build_profile(registration)
    today = timezone.localdate()

    considered = []
    eligible_items = []
    pool_size = 0
    post_gotra_size = 0

    # Bug 6a: Pre-fetch existing matches and proposals in bulk to prevent N+1 queries.
    existing_matches = Match.objects.filter(
        models.Q(registration=registration) | models.Q(candidate=registration)
    ).values_list("registration_id", "candidate_id")

    matched_counterpart_ids = set()
    for r_id, c_id in existing_matches:
        matched_counterpart_ids.add(c_id if r_id == registration.pk else r_id)

    # Fetch proposal pairs involving this registration in both directions
    existing_proposals = MatchProposal.objects.filter(
        models.Q(registration=registration) | models.Q(paired_proposal__registration=registration)
    ).values_list(
        "registration_id",
        "paired_proposal__registration_id",
        "your_response",
        "other_response",
    )

    counterparts_with_proposal = set()
    declined_counterpart_ids = set()

    for r_id, p_r_id, yr, opr in existing_proposals:
        other_id = None
        if r_id == registration.pk and p_r_id:
            other_id = p_r_id
        elif p_r_id == registration.pk and r_id:
            other_id = r_id

        if other_id is not None:
            counterparts_with_proposal.add(other_id)
            if (
                yr == MatchProposal.PartyResponse.DECLINED
                or opr == MatchProposal.PartyResponse.DECLINED
            ):
                declined_counterpart_ids.add(other_id)

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

        if reason_tuples:
            reasons_detail = [{"code": code, "detail": detail} for code, detail in reason_tuples]
            considered.append({
                "candidate_reference": candidate.reference,
                "decision": DECISION_REJECTED,
                "reasons": reasons_detail,
            })
            continue

        # Do NOT re-propose pairs where either side declined. The matching engine strictly
        # preserves past decline decisions. Note: matching.py differs here (it checked only
        # active proposals and allowed re-proposal after a decline), but engine policy is
        # to never re-propose a declined pair.
        if candidate.pk in declined_counterpart_ids:
            considered.append({
                "candidate_reference": candidate.reference,
                "decision": DECISION_REJECTED,
                "reasons": [
                    {
                        "code": REASON_DECLINED_PAIR,
                        "detail": "pair was previously declined and will not be re-proposed",
                    }
                ],
            })
            continue

        # Only skip a pair when BOTH the Match and the paired proposals already exist.
        has_match = candidate.pk in matched_counterpart_ids
        has_proposal = candidate.pk in counterparts_with_proposal

        if has_match and has_proposal:
            considered.append({
                "candidate_reference": candidate.reference,
                "decision": DECISION_REJECTED,
                "reasons": [
                    {
                        "code": REASON_ALREADY_MATCHED,
                        "detail": "match and proposal pair already exist",
                    }
                ],
            })
            continue

        # Candidate is eligible (either new pair or self-healing incomplete pair)
        is_healing = has_match and not has_proposal
        cand_age = (
            _age_years(candidate.candidate_dob, today)
            if candidate.candidate_dob is not None
            else None
        )
        score = _preference_score(registration, candidate, candidate_age=cand_age, today=today)

        eligible_items.append({
            "candidate": candidate,
            "score": score,
            "is_healing": is_healing,
            "moolgram_missing": moolgram_missing,
        })

    # Sort eligible candidates deterministically by (preference_score, pk).
    # Lower preference_score = better match. Ties break deterministically by pk.
    eligible_items.sort(key=lambda item: (item["score"], str(item["candidate"].pk)))

    # Apply match cap per registration (Bug 4)
    max_matches = getattr(settings, "MAX_MATCHES_PER_REGISTRATION", None)
    if max_matches is not None:
        # Existing active matches (excluding declined ones) count toward the cap
        existing_active_count = len(matched_counterpart_ids - declined_counterpart_ids)
        slots_available = max(0, max_matches - existing_active_count)
    else:
        slots_available = len(eligible_items)

    selected_items = eligible_items[:slots_available]
    capped_items = eligible_items[slots_available:]

    rank = 1
    for item in selected_items:
        accepted_reasons = [{"code": "ACCEPTED", "detail": ACCEPTED_REASON}]
        if item["moolgram_missing"]:
            accepted_reasons.append({
                "code": "NEEDS_REVIEW",
                "detail": "moolgram missing - manual review recommended",
            })
        if item["is_healing"]:
            accepted_reasons.append({
                "code": REASON_PROPOSAL_HEALED,
                "detail": "proposal recreated after incomplete earlier run",
            })
        considered.append({
            "candidate_reference": item["candidate"].reference,
            "decision": DECISION_ACCEPTED,
            "rank": rank,
            "preference_score": item["score"],
            "reasons": accepted_reasons,
        })
        rank += 1

    for item in capped_items:
        considered.append({
            "candidate_reference": item["candidate"].reference,
            "decision": DECISION_ELIGIBLE_NOT_SELECTED,
            "rank": rank,
            "preference_score": item["score"],
            "reasons": [
                {
                    "code": REASON_CAP_REACHED,
                    "detail": f"Reached maximum match cap of {max_matches}",
                }
            ],
        })
        rank += 1

    first_proposal = None
    final_matches = []

    for item in selected_items:
        cand = item["candidate"]
        score = item["score"]
        low_id, high_id = _normalize_pair(registration.pk, cand.pk)

        # Bug 1 & Bug 2: Ensure Match and MatchProposal exist in ONE atomic block per candidate.
        # Create Match inside its own savepoint catching IntegrityError to tolerate concurrent workers.
        with transaction.atomic():
            match_obj = None
            try:
                with transaction.atomic():
                    match_obj, created = Match.objects.get_or_create(
                        pair_low_id=low_id,
                        pair_high_id=high_id,
                        defaults={
                            "registration": registration,
                            "candidate": cand,
                            "score": float(score),
                            "status": Match.Status.PENDING,
                        },
                    )
            except IntegrityError:
                # Another worker created the Match row first; fetch the existing row
                match_obj = Match.objects.filter(pair_low_id=low_id, pair_high_id=high_id).first()

            # Ensure paired MatchProposal rows exist (healing if missing)
            existing_proposal = MatchProposal.objects.filter(
                models.Q(registration=registration, paired_proposal__registration=cand) |
                models.Q(registration=cand, paired_proposal__registration=registration)
            ).first()

            if not existing_proposal:
                proposal_for_registration = MatchProposal.objects.create(
                    registration=registration,
                    shared_by_panjikar="Matched by Sabha Gachhi",
                    shared_details=_build_shared_details(registration, cand, today),
                )
                proposal_for_match = MatchProposal.objects.create(
                    registration=cand,
                    shared_by_panjikar="Matched by Sabha Gachhi",
                    shared_details=_build_shared_details(cand, registration, today),
                    paired_proposal=proposal_for_registration,
                )
                proposal_for_registration.paired_proposal = proposal_for_match
                proposal_for_registration.save(update_fields=["paired_proposal"])

                if first_proposal is None:
                    first_proposal = proposal_for_registration
            elif first_proposal is None:
                if existing_proposal.registration_id == registration.pk:
                    first_proposal = existing_proposal
                else:
                    first_proposal = existing_proposal.paired_proposal

            final_matches.append((cand, float(score)))

    outcome = (
        MatchAttemptLog.Outcome.MATCHED
        if selected_items
        else MatchAttemptLog.Outcome.NO_ELIGIBLE_CANDIDATE
    )

    # Bug 1 & 5: MatchAttemptLog is written to record the audit trail for this run.
    # matched_registration is the top-ranked match; the complete audit trail of all
    # accepted, capped, and rejected candidates lives in candidates_considered.
    # Writing the log here reflects the persisted state of this run (including healed pairs).
    top_match = selected_items[0]["candidate"] if selected_items else None
    MatchAttemptLog.objects.create(
        registration=registration,
        outcome=outcome,
        matched_registration=top_match,
        candidates_considered=considered,
        sapinda_rules_version=SAPINDA_RULES_VERSION,
    )

    if first_proposal is None and selected_items:
        top_cand = selected_items[0]["candidate"]
        first_proposal = MatchProposal.objects.filter(
            registration=registration,
            paired_proposal__registration=top_cand,
        ).first()

    return {
        "pool_size": pool_size,
        "post_gotra_size": post_gotra_size,
        "final_matches": final_matches,
        "audit_log": {
            "outcome": outcome,
            "pool_size": pool_size,
            "final_count": len(final_matches),
        },
        "_first_proposal": first_proposal,
    }


def create_automated_proposal(registration: Registration) -> MatchProposal | None:
    """Create paired MatchProposal rows for ALL eligible matches from the engine.

    Single entry point that evaluates candidates and persists both Match and
    paired MatchProposal records idempotently. Returns the first (top-ranked)
    proposal, or None if no candidate was eligible.
    """
    result = run_matching_engine(registration)
    return result.get("_first_proposal")