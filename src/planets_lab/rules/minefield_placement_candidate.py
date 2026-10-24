"""Pure source-bounded minefield site selection, NOT a Host placement phase.

Official sources:
  https://help.planets.nu/minefields
  https://help.planets.nu/minefields-examples
  https://help.planets.nu/star-clusters

Select the nearest center of the requested owner AND normal/web type.
A lowest-ID tie break precedes the point-inside-selected-field decision.
This module does not lay mines, create IDs, change field units, discard
excess units, touch the ship inventory or run a complete Host turn.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isqrt
from typing import Sequence

from .minelaying_conversion import MineLayingQuote

EVIDENCE = "DOCUMENTED_GEOMETRY_TESTED_CONDITIONAL_NOT_HOST_ACCEPTED"
MAX_COORD_ABS = 1_000_000
MAX_SNAPSHOT_FIELDS = 5000
STANDARD_RADII = frozenset((100, 150))


class MinefieldPlacementAbstain(ValueError):
    """Missing source provenance or unsupported actual spatial/Host context."""


@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class LocatedMinefield:
    field_id: int
    owner_id: int
    center: Point
    mine_units: int
    is_web: bool


@dataclass(frozen=True, slots=True)
class StarClusterCore:
    # This is the FULL core disc, not the radiation-halo radius.
    center: Point
    core_radius: int


@dataclass(frozen=True, slots=True)
class PlacementCandidate:
    decision: str  # NO_UNITS, NEW_CANDIDATE, EXPAND_CANDIDATE
    center: Point | None
    matching_nearest_field_id: int | None
    expansion_candidate_field_id: int | None
    distance_squared_to_nearest: int | None
    raw_unallocated_units: int
    prospective_units_if_uncontested: int
    prospective_radius_if_uncontested: int
    max_radius: int
    evidence: str = EVIDENCE
    created_field_id: None = None
    field_created_or_expanded: bool = False
    field_roster_mutated: bool = False
    host_order_accepted_verified: bool = False
    host_phase_order_verified: bool = False
    host_causal_verified: bool = False


def _int(value: object, minimum: int, maximum: int) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _point(value: object) -> bool:
    return (
        type(value) is Point
        and _int(value.x, -MAX_COORD_ABS, MAX_COORD_ABS)
        and _int(value.y, -MAX_COORD_ABS, MAX_COORD_ABS)
    )


def _distance2(a: Point, b: Point) -> int:
    return (a.x - b.x) ** 2 + (a.y - b.y) ** 2


def quote_minefield_placement_candidate(
    *,
    quote: MineLayingQuote,
    mine_layer_position: Point,
    target_owner_id: int,
    fields: Sequence[LocatedMinefield],
    cluster_cores: Sequence[StarClusterCore],
    max_radius: int,
    complete_current_field_roster_confirmed: bool,
    exact_position_and_radius_source_confirmed: bool,
    target_owner_and_quote_mission_consistent_confirmed: bool,
    full_star_cluster_core_geometry_confirmed: bool,
    isolated_pre_lay_snapshot_confirmed: bool,
) -> PlacementCandidate:
    """Classify one hypothetical lay site; entirely atomic on ABSTAIN.

    The snapshot must represent the appropriate pre-lay phase and have no
    preceding same-phase mine laying, sweeping, transfers, or custom rules
    hidden from the caller. Flags assert assumptions; they do not prove them.
    The projected footprint must fit capacity and avoid ALL core + 10 LY
    exclusion discs, or this calculator abstains instead of modeling loss.
    """
    if any(flag is not True for flag in (
        complete_current_field_roster_confirmed,
        exact_position_and_radius_source_confirmed,
        target_owner_and_quote_mission_consistent_confirmed,
        full_star_cluster_core_geometry_confirmed,
        isolated_pre_lay_snapshot_confirmed,
    )):
        raise MinefieldPlacementAbstain("required source/phase/owner provenance is unverified")
    if type(quote) is not MineLayingQuote or quote.evidence != (
        "DOCUMENTED_CONVERSION_AND_TESTED_CONDITIONAL_NOT_HOST_ACCEPTED"
    ):
        raise MinefieldPlacementAbstain("typed documented quote required")
    if quote.field_created_or_expanded or quote.minefield_allocation_verified or quote.host_causal_verified:
        raise MinefieldPlacementAbstain("cannot reuse already-executed or claimed Host result")
    if not _point(mine_layer_position) or not _int(target_owner_id, 1, 2_147_483_647):
        raise MinefieldPlacementAbstain("invalid geometry or target ownership")
    if type(max_radius) is not int or max_radius not in STANDARD_RADII or (
        quote.single_empty_standard_field_capacity != max_radius * max_radius
    ):
        raise MinefieldPlacementAbstain("inconsistent standard field radius")
    if not isinstance(fields, (tuple, list)) or len(fields) > MAX_SNAPSHOT_FIELDS:
        raise MinefieldPlacementAbstain("complete bounded field roster required")
    if not isinstance(cluster_cores, (tuple, list)):
        raise MinefieldPlacementAbstain("complete cluster core roster required")
    seen: set[int] = set()
    eligible: list[tuple[int, int, LocatedMinefield]] = []
    for field in fields:
        if type(field) is not LocatedMinefield or not (
            _int(field.field_id, 1, 2_147_483_647)
            and _int(field.owner_id, 1, 2_147_483_647)
            and _point(field.center)
            and _int(field.mine_units, 1, max_radius * max_radius)
            and type(field.is_web) is bool
        ):
            raise MinefieldPlacementAbstain("invalid current field record/density")
        if field.field_id in seen:
            raise MinefieldPlacementAbstain("duplicate field ID")
        seen.add(field.field_id)
        if field.owner_id == target_owner_id and field.is_web == quote.uses_web_mine_units:
            eligible.append((_distance2(mine_layer_position, field.center), field.field_id, field))
    checked_cores: list[StarClusterCore] = []
    for core in cluster_cores:
        if type(core) is not StarClusterCore or not (
            _point(core.center) and _int(core.core_radius, 0, MAX_COORD_ABS)
        ):
            raise MinefieldPlacementAbstain("incomplete star cluster core geometry")
        checked_cores.append(core)
    # Do not silently treat zero-stock as a new zero-unit minefield.
    if not _int(quote.unallocated_mine_units, 0, 5_000_000):
        raise MinefieldPlacementAbstain("unsupported unallocated unit quote")
    if quote.unallocated_mine_units == 0:
        return PlacementCandidate(
            "NO_UNITS", None, None, None, None, 0, 0, 0, max_radius,
        )
    nearest = min(eligible, key=lambda item: (item[0], item[1])) if eligible else None
    if nearest is None:
        center, base_units, decision, matched, target_id, dist2 = (
            mine_layer_position, 0, "NEW_CANDIDATE", None, None, None,
        )
    else:
        dist2, matched, field = nearest
        # Mine radius is integer floor(sqrt(units)). Boundary is inclusive.
        inside = dist2 <= isqrt(field.mine_units) ** 2
        center = field.center if inside else mine_layer_position
        base_units = field.mine_units if inside else 0
        decision = "EXPAND_CANDIDATE" if inside else "NEW_CANDIDATE"
        target_id = field.field_id if inside else None

    # Soft limit: new field may trigger next-turn eviction at 500+.
    if decision == "NEW_CANDIDATE" and len(fields) >= 500:
        raise MinefieldPlacementAbstain("soft field-limit side effects unresolved")
    proposed = base_units + quote.unallocated_mine_units
    if proposed > max_radius * max_radius:
        raise MinefieldPlacementAbstain("field overcapacity requires Host excess-unit rules")
    radius = isqrt(proposed)
    for core in checked_cores:
        forbidden_radius = core.core_radius + 10 + radius
        if _distance2(center, core.center) <= forbidden_radius ** 2:
            raise MinefieldPlacementAbstain("star cluster exclusion intersects prospective field")
    return PlacementCandidate(
        decision=decision,
        center=center,
        matching_nearest_field_id=matched,
        expansion_candidate_field_id=target_id,
        distance_squared_to_nearest=dist2,
        raw_unallocated_units=quote.unallocated_mine_units,
        prospective_units_if_uncontested=proposed,
        prospective_radius_if_uncontested=radius,
        max_radius=max_radius,
    )
