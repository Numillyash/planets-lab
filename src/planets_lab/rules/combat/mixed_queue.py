"""Cross-phase Host combat queue primitives.

This module owns only the boundary between the already reconstructed ship-combat
queue and ship-vs-planet/base combat.

Evidence boundary:

- Host Order documents that all ship-vs-ship combat completes before
  ship-vs-planet/base combat;
- an explicit repair/MKT phase exists between those combat phases;
- ordinary ship-vs-planet attacker ordering uses the same documented Combat
  Priority key as ordinary ship-vs-ship ordering;
- factual ordinary mixed-site VCRs place the ship on LEFT and planet/base on
  RIGHT.

Capture-generated target/order lists remain separate.  A post-capture candidate
therefore fails closed here until its capture-generated priority/order semantics
are independently reconstructed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from .order import standard_battle_priority_key


class HostCombatQueuePhase(str, Enum):
    SHIP = "ship"
    INTERPHASE_REPAIR_MKT = "interphase_repair_mkt"
    PLANET = "planet"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class PlanetAttackCandidate:
    """One independently composed ship-vs-planet/base candidate."""

    ship_id: int
    mission: int | None
    primary_enemy: int | None
    friendly_code: str | None
    engagement_eligible: bool | None
    post_capture_generated_order: bool = False


@dataclass(frozen=True, slots=True)
class PlanetAttackSelection:
    """Fail-closed ordinary ship-vs-planet attacker selection."""

    engagement_available: bool | None
    eligible_candidate_count: int
    ship_id: int | None = None
    priority: tuple[int, int, int] | None = None
    unresolved_reasons: tuple[str, ...] = ()


def host_combat_phase(
    *,
    ship_queue_exhausted: bool,
    interphase_repair_mkt_applied: bool,
    planet_queue_exhausted: bool,
) -> HostCombatQueuePhase:
    """Return the current coarse Host combat phase.

    This is a phase-order state machine only.  It does not perform repair/MKT,
    rebuild candidates, or mutate participants.
    """

    for name, value in (
        ("ship_queue_exhausted", ship_queue_exhausted),
        ("interphase_repair_mkt_applied", interphase_repair_mkt_applied),
        ("planet_queue_exhausted", planet_queue_exhausted),
    ):
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be boolean")

    if not ship_queue_exhausted:
        return HostCombatQueuePhase.SHIP
    if not interphase_repair_mkt_applied:
        return HostCombatQueuePhase.INTERPHASE_REPAIR_MKT
    if not planet_queue_exhausted:
        return HostCombatQueuePhase.PLANET
    return HostCombatQueuePhase.COMPLETE


def ship_planet_sides(
    *,
    ship_id: int,
    planet_id: int,
) -> tuple[int, int]:
    """Return the evidence-backed ordinary VCR orientation: ship LEFT, planet RIGHT."""

    for name, value in (("ship_id", ship_id), ("planet_id", planet_id)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    return ship_id, planet_id


def select_initial_plain_planet_attacker(
    candidates: Sequence[PlanetAttackCandidate],
) -> PlanetAttackSelection:
    """Select the highest-priority ordinary planet attacker.

    Pair/planet eligibility must be composed upstream.  Known-ineligible rows are
    ignored.  Unknown eligibility, duplicate ship inputs, unsupported Friendly
    Code priority, or an eligible post-capture generated-order candidate makes
    the selection unresolved rather than silently changing queue order.
    """

    if not candidates:
        return PlanetAttackSelection(
            engagement_available=False,
            eligible_candidate_count=0,
            unresolved_reasons=("no_planet_attack_candidates",),
        )

    resolved: list[tuple[tuple[int, int, int], int]] = []
    unresolved: list[str] = []
    seen: set[int] = set()

    for candidate in candidates:
        ship_id = candidate.ship_id
        if isinstance(ship_id, bool) or not isinstance(ship_id, int) or ship_id <= 0:
            raise ValueError("candidate ship_id must be a positive integer")
        if ship_id in seen:
            unresolved.append(f"duplicate_ship_candidate:{ship_id}")
            continue
        seen.add(ship_id)

        if candidate.engagement_eligible is None:
            unresolved.append(f"{ship_id}:planet_engagement_unresolved")
            continue
        if candidate.engagement_eligible is False:
            continue
        if candidate.post_capture_generated_order:
            unresolved.append(f"{ship_id}:post_capture_generated_order_unresolved")
            continue

        priority = standard_battle_priority_key(
            ship_id=ship_id,
            mission=candidate.mission,
            primary_enemy=candidate.primary_enemy,
            friendly_code=candidate.friendly_code,
        )
        if priority is None:
            unresolved.append(f"{ship_id}:planet_priority_unresolved")
            continue
        resolved.append((priority, ship_id))

    if unresolved:
        return PlanetAttackSelection(
            engagement_available=None,
            eligible_candidate_count=len(resolved),
            unresolved_reasons=tuple(unresolved),
        )

    if not resolved:
        return PlanetAttackSelection(
            engagement_available=False,
            eligible_candidate_count=0,
            unresolved_reasons=("no_eligible_plain_planet_attacker",),
        )

    priority, ship_id = min(resolved)
    return PlanetAttackSelection(
        engagement_available=True,
        eligible_candidate_count=len(resolved),
        ship_id=ship_id,
        priority=priority,
    )
