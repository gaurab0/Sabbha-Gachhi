"""
Sapinda / gotra conflict-checking rule engine.

IMPORTANT: The default parameters below (which generations are checked,
whether mool gram alone counts as a conflict, etc.) are provisional. This
module exists specifically so someone with real authority on the Panji
Prabandh tradition can review and adjust these rules without touching the
matching pipeline itself. Do not treat these defaults as authoritative.
"""

from dataclasses import dataclass, field
from typing import List


SAPINDA_RULES_VERSION = "v0.1-provisional"


@dataclass
class SapindaRuleConfig:
    check_gotra: bool = True
    check_mool_gram: bool = True
    check_shared_ancestors: bool = True
    # How many generations back to compare named ancestors. Defaults to
    # "all generations RegistrationFlow currently collects" (3 paternal,
    # 2 maternal) — raise these if the lineage step ever captures more.
    paternal_generations: int = 3
    maternal_generations: int = 2
    # Whether to also cross-check family A's paternal line against family
    # B's maternal line (and vice versa), not just same-line-against-same-line.
    cross_line_check: bool = True


DEFAULT_CONFIG = SapindaRuleConfig()


@dataclass
class SapindaResult:
    has_conflict: bool
    reasons: List[str] = field(default_factory=list)
    rules_version: str = SAPINDA_RULES_VERSION


def _normalize(value: str) -> str:
    return (value or "").strip().lower()


def _ancestor_names(entries, limit):
    names = []
    for entry in entries[:limit]:
        name = _normalize(entry.name)
        if name:
            names.append(name)
    return names


def check_sapinda_conflict(
    registration_a,
    registration_b,
    config: SapindaRuleConfig = DEFAULT_CONFIG,
) -> SapindaResult:
    """
    Conservative, name-based sapinda/gotra check between two Registration
    instances. Returns has_conflict=True on ANY match — deliberately biased
    toward blocking, since this is a hard gate with no human review after it.
    """
    reasons: List[str] = []

    gotra_a, gotra_b = _normalize(registration_a.gotra), _normalize(registration_b.gotra)
    if config.check_gotra and gotra_a and gotra_b and gotra_a == gotra_b:
        reasons.append(f"Same gotra: '{registration_a.gotra}'")

    mool_a, mool_b = _normalize(registration_a.mool_gram), _normalize(registration_b.mool_gram)
    if config.check_mool_gram and mool_a and mool_b and mool_a == mool_b:
        reasons.append(f"Same ancestral village (mool gram): '{registration_a.mool_gram}'")

    if config.check_shared_ancestors:
        a_paternal = _ancestor_names(registration_a.paternal_line, config.paternal_generations)
        a_maternal = _ancestor_names(registration_a.maternal_line, config.maternal_generations)
        b_paternal = _ancestor_names(registration_b.paternal_line, config.paternal_generations)
        b_maternal = _ancestor_names(registration_b.maternal_line, config.maternal_generations)

        pairs_to_check = [
            (a_paternal, b_paternal, "paternal", "paternal"),
            (a_maternal, b_maternal, "maternal", "maternal"),
        ]
        if config.cross_line_check:
            pairs_to_check += [
                (a_paternal, b_maternal, "paternal", "maternal"),
                (a_maternal, b_paternal, "maternal", "paternal"),
            ]

        for names_a, names_b, line_a, line_b in pairs_to_check:
            for shared_name in set(names_a) & set(names_b):
                reasons.append(
                    f"Possible shared ancestor '{shared_name}' "
                    f"({line_a} line vs {line_b} line)"
                )

    return SapindaResult(has_conflict=bool(reasons), reasons=reasons)