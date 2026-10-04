#!/usr/bin/env python3
"""Pure candidate selectors for post-capture occurrence-round research.

These are discovery research candidates, not canonical NuHost mechanics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


PAIR_MAX_OCCURRENCES = 2


@dataclass(frozen=True, slots=True)
class Candidate:
    ship_id: int
    priority: tuple[int, int, int]
    pair_occurrences: int
    attacker_appearances: int

    def __post_init__(self) -> None:
        if isinstance(self.ship_id, bool) or not isinstance(self.ship_id, int) or self.ship_id <= 0:
            raise ValueError("ship_id must be a positive integer")
        if (
            not isinstance(self.priority, tuple)
            or len(self.priority) != 3
            or any(isinstance(v, bool) or not isinstance(v, int) for v in self.priority)
        ):
            raise ValueError("priority must be a 3-integer tuple")
        if (
            isinstance(self.pair_occurrences, bool)
            or not isinstance(self.pair_occurrences, int)
            or self.pair_occurrences < 0
        ):
            raise ValueError("pair_occurrences must be a non-negative integer")
        if (
            isinstance(self.attacker_appearances, bool)
            or not isinstance(self.attacker_appearances, int)
            or self.attacker_appearances < 0
        ):
            raise ValueError("attacker_appearances must be a non-negative integer")


def _fresh_pairs(candidates: Iterable[Candidate]) -> list[Candidate]:
    return [
        row
        for row in candidates
        if row.pair_occurrences < PAIR_MAX_OCCURRENCES
    ]


def select_static_priority(candidates: Iterable[Candidate]) -> Candidate | None:
    """Current static requester baseline; deliberately ignores pair history."""

    rows = list(candidates)
    return min(rows, key=lambda row: row.priority) if rows else None


def select_static_cap2(candidates: Iterable[Candidate]) -> Candidate | None:
    """Static priority after applying only the already-supported pair cap."""

    rows = _fresh_pairs(candidates)
    return min(rows, key=lambda row: row.priority) if rows else None


def select_pair_occurrence_round(
    candidates: Iterable[Candidate],
) -> Candidate | None:
    """Prefer first-occurrence pairs over second-occurrence pairs.

    The key is (prior pair occurrence count, static priority).  Pairs already
    seen twice are exhausted and excluded.
    """

    rows = _fresh_pairs(candidates)
    return (
        min(rows, key=lambda row: (row.pair_occurrences, row.priority))
        if rows
        else None
    )


def select_fresh_attacker_boolean(
    candidates: Iterable[Candidate],
) -> Candidate | None:
    """Prefer attackers with no earlier VCR appearance, then static priority."""

    rows = _fresh_pairs(candidates)
    return (
        min(
            rows,
            key=lambda row: (
                0 if row.attacker_appearances == 0 else 1,
                row.priority,
            ),
        )
        if rows
        else None
    )


def select_attacker_appearance_count(
    candidates: Iterable[Candidate],
) -> Candidate | None:
    """Prefer fewer prior attacker appearances, then static priority."""

    rows = _fresh_pairs(candidates)
    return (
        min(rows, key=lambda row: (row.attacker_appearances, row.priority))
        if rows
        else None
    )
