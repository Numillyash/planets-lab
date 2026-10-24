"""Bounded, isolated MSC full-field *quote*, not an executed Host scoop.

Official documented sources:
  https://help.planets.nu/minefields  (Mine Scooping)
  https://help.planets.nu/friendly-codes (MSC)
  https://help.planets.nu/minefields-examples

Only calculate the reversible whole-field integer case for a SINGLE
unambiguously reachable owner-current standard field with enough declared
torpedo capacity. Do not guess fractional rounding, partial scoops,
near-edge raster, overlapping owned field selection, same-phase beam
sweeping, torpedo inventory movement or actual Host phase order.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isqrt
from typing import Sequence

from .minefield_placement_candidate import LocatedMinefield, Point
from .minelaying_conversion import (
    STANDARD_MAX_RADII,
    STANDARD_TORPEDO_MINE_YIELDS,
    MAX_QUOTED_TORPEDOES,
)

EVIDENCE = "DOCUMENTED_EXACT_FULL_FIELD_MSC_TESTED_CONDITIONAL_NOT_HOST_EXECUTED"
MAX_FIELDS = 5000
MAX_ID = 2_147_483_647
MAX_COORD_ABS = 1_000_000


class MineScoopQuoteAbstain(ValueError):
    """Unsupported/incompletely witnessed MSC geometry or exact division."""


@dataclass(frozen=True, slots=True)
class FullFieldScoopQuote:
    ship_id: int
    owner_id: int
    target_field_id: int
    torpedo_family: str
    is_web: bool
    field_mine_units_before: int
    base_mine_units_per_torpedo: int
    inverted_laying_multiplier: int
    exact_mine_units_per_recovered_torpedo: int
    torpedoes_before: int
    torpedo_capacity: int
    proposed_torpedoes_recovered: int
    proposed_torpedoes_after: int
    whole_field_units_mathematically_accounted: int
    proposed_units_left_if_entire_field_recovered: int
    would_exhaust_field_if_executed: bool
    evidence: str = EVIDENCE
    actual_torpedoes_transferred: bool = False
    actual_field_removed: bool = False
    field_roster_mutated: bool = False
    host_scoop_accepted_verified: bool = False
    host_phase_order_verified: bool = False
    host_diff_verified: bool = False


def _typed_int(value: object, minimum: int, maximum: int) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _point(value: object) -> bool:
    return (
        type(value) is Point
        and _typed_int(value.x, -MAX_COORD_ABS, MAX_COORD_ABS)
        and _typed_int(value.y, -MAX_COORD_ABS, MAX_COORD_ABS)
    )


def _distance_squared(a: Point, b: Point) -> int:
    return (a.x - b.x) ** 2 + (a.y - b.y) ** 2


def quote_exact_whole_field_msc(
    *,
    ship_id: int,
    owner_id: int,
    position: Point,
    mission: str,
    friendly_code: str,
    beams_present: bool,
    torpedo_tubes_present: bool,
    torpedo_family: str,
    torpedoes_before: int,
    torpedo_capacity: int,
    target_field_id: int,
    fields: Sequence[LocatedMinefield],
    max_radius: int,
    robot_normal_mine_bonus_confirmed: bool,
    crystal_standard_web_permission_confirmed: bool,
    complete_prescoop_field_roster_confirmed: bool,
    exact_ship_and_field_geometry_confirmed: bool,
    exact_torpedo_inventory_and_capacity_confirmed: bool,
    standard_racial_multiplier_and_catalog_confirmed: bool,
    isolated_scoop_without_beam_or_fighter_sweeps_confirmed: bool,
    no_custom_dense_or_phase_interactions_confirmed: bool,
) -> FullFieldScoopQuote:
    """Exact algebraic full-field quote with atomic fail-closed input checks.

    All *_confirmed flags are explicit hypothetical source preconditions,
    never authenticated server-accepted orders. The only geometric positive
    case is ship position inside the known integer-radius circle.
    """
    if any(flag is not True for flag in (
        complete_prescoop_field_roster_confirmed,
        exact_ship_and_field_geometry_confirmed,
        exact_torpedo_inventory_and_capacity_confirmed,
        standard_racial_multiplier_and_catalog_confirmed,
        isolated_scoop_without_beam_or_fighter_sweeps_confirmed,
        no_custom_dense_or_phase_interactions_confirmed,
    )):
        raise MineScoopQuoteAbstain("MSC source and phase preconditions unverified")
    if not (
        _typed_int(ship_id, 1, MAX_ID)
        and _typed_int(owner_id, 1, MAX_ID)
        and _typed_int(target_field_id, 1, MAX_ID)
        and _point(position)
    ):
        raise MineScoopQuoteAbstain("unsupported ship, owner, target or coordinates")
    if (
        type(mission) is not str or mission != "MINE_SWEEP"
        or type(friendly_code) is not str
        or friendly_code.upper() != "MSC"
        or beams_present is not True
        or torpedo_tubes_present is not True
    ):
        raise MineScoopQuoteAbstain("MSC mission/FC/beams/tubes not eligible")
    if (
        type(torpedo_family) is not str
        or torpedo_family not in STANDARD_TORPEDO_MINE_YIELDS
    ):
        raise MineScoopQuoteAbstain("standard torpedo family not independently resolved")
    if (
        not _typed_int(torpedoes_before, 0, MAX_QUOTED_TORPEDOES)
        or not _typed_int(torpedo_capacity, 1, MAX_QUOTED_TORPEDOES)
        or torpedoes_before > torpedo_capacity
    ):
        raise MineScoopQuoteAbstain("invalid or unknown torpedo inventory/capacity")
    if type(max_radius) is not int or max_radius not in STANDARD_MAX_RADII:
        raise MineScoopQuoteAbstain("custom or untyped field radius")
    if (
        type(robot_normal_mine_bonus_confirmed) is not bool
        or type(crystal_standard_web_permission_confirmed) is not bool
    ):
        raise MineScoopQuoteAbstain("unknown racial conversion and web context")
    if not isinstance(fields, (list, tuple)) or not 1 <= len(fields) <= MAX_FIELDS:
        raise MineScoopQuoteAbstain("complete non-empty bounded field roster required")
    seen: set[int] = set()
    target: LocatedMinefield | None = None
    for f in fields:
        if type(f) is not LocatedMinefield or not (
            _typed_int(f.field_id, 1, MAX_ID)
            and _typed_int(f.owner_id, 1, MAX_ID)
            and _point(f.center)
            and _typed_int(f.mine_units, 1, max_radius * max_radius)
            and type(f.is_web) is bool
        ):
            raise MineScoopQuoteAbstain("untyped or nonstandard field context")
        if f.field_id in seen:
            raise MineScoopQuoteAbstain("duplicate field ID")
        seen.add(f.field_id)
        if f.field_id == target_field_id:
            target = f
    if target is None or target.owner_id != owner_id:
        raise MineScoopQuoteAbstain("field is not uniquely confirmed as ship-owned")
    if target.is_web and not crystal_standard_web_permission_confirmed:
        raise MineScoopQuoteAbstain("standard owner-current web entitlement missing")
    if robot_normal_mine_bonus_confirmed and target.is_web:
        raise MineScoopQuoteAbstain("Robot 4x must not be applied to web fields")
    if _distance_squared(position, target.center) > isqrt(target.mine_units) ** 2:
        raise MineScoopQuoteAbstain(
            "near-edge/outside MSC geometry requires separately proven raster semantics"
        )
    # A second own field touching the ship's cell could alter the selection,
    # even if its minefield type differs. Refuse the entire operation.
    for f in fields:
        if f.field_id == target_field_id or f.owner_id != owner_id:
            continue
        if _distance_squared(position, f.center) < (isqrt(f.mine_units) + 2) ** 2:
            raise MineScoopQuoteAbstain("ambiguous multiple owner-current fields near MSC ship")
    multiplier = 4 if robot_normal_mine_bonus_confirmed else 1
    base_yield = STANDARD_TORPEDO_MINE_YIELDS[torpedo_family]
    effective = base_yield * multiplier
    units = target.mine_units
    recovered, remainder = divmod(units, effective)
    if remainder:
        raise MineScoopQuoteAbstain(
            "undocumented partial-torpedo rounding and remainder cannot be assumed"
        )
    if recovered <= 0:
        raise MineScoopQuoteAbstain("no whole torpedo could be recovered")
    if recovered > torpedo_capacity - torpedoes_before:
        raise MineScoopQuoteAbstain("partial scoop/cargo saturation not modeled")
    after = torpedoes_before + recovered
    if effective * recovered != units or after > torpedo_capacity:
        raise MineScoopQuoteAbstain("exact whole-field conversion invariant failure")
    return FullFieldScoopQuote(
        ship_id=ship_id,
        owner_id=owner_id,
        target_field_id=target.field_id,
        torpedo_family=torpedo_family,
        is_web=target.is_web,
        field_mine_units_before=units,
        base_mine_units_per_torpedo=base_yield,
        inverted_laying_multiplier=multiplier,
        exact_mine_units_per_recovered_torpedo=effective,
        torpedoes_before=torpedoes_before,
        torpedo_capacity=torpedo_capacity,
        proposed_torpedoes_recovered=recovered,
        proposed_torpedoes_after=after,
        whole_field_units_mathematically_accounted=effective * recovered,
        proposed_units_left_if_entire_field_recovered=0,
        would_exhaust_field_if_executed=True,
    )
