"""
Backward-compatible shim for legacy matching module.

Deprecated: Use ``registrations.matching_engine`` instead.
"""

import warnings
from datetime import date

from django.db import models, transaction

from .models import MatchAttemptLog, MatchProposal, Registration
from .matching_engine import (
    create_automated_proposal,
    run_matching_engine,
    _candidate_pool,
    _opposite_gender,
    _age_years,
    _preference_score,
    _build_shared_details,
)
from .sapinda import SAPINDA_RULES_VERSION, check_sapinda_conflict

warnings.warn(
    "registrations.matching is deprecated; use registrations.matching_engine instead.",
    DeprecationWarning,
    stacklevel=2,
)


def _has_active_proposal_for_pair(registration: Registration, candidate: Registration) -> bool:
    """Check if an active proposal already exists for this specific pair.

    Note: This legacy helper excluded declined proposals (allowing re-proposal
    after decline). The authoritative matching_engine policy does NOT re-propose
    declined pairs.
    """
    return MatchProposal.objects.filter(
        models.Q(registration=registration, paired_proposal__registration=candidate) |
        models.Q(registration=candidate, paired_proposal__registration=registration)
    ).exclude(
        models.Q(your_response=MatchProposal.PartyResponse.DECLINED)
        | models.Q(other_response=MatchProposal.PartyResponse.DECLINED)
    ).exists()


def find_matches_for(registration: Registration) -> list[Registration]:
    """Legacy helper: runs matching engine and returns eligible Registrations."""
    result = run_matching_engine(registration)
    return [candidate for candidate, _ in result["final_matches"]]