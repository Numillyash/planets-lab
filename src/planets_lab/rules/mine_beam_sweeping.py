"""Conditional standard beam-only mine sweeping; never a whole NuHost phase.

DOCUMENTED sources:
https://help.planets.nu/minefields (Mine Sweeping)
https://help.planets.nu/weapon-destruction-power (Beam Weapon swept per turn)
https://help.planets.nu/minefields-examples (pre-decay web circle and square)

The roster is explicitly pinned to a hypothetical pre-sweep snapshot. No
starbases, Colonial fighter sweep, MSC scooping, external layout, terrain/
host phases or custom web reductions are assumed or simulated.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isqrt
from typing import Mapping, Sequence

from .minefield_placement_candidate import LocatedMinefield, Point
from .web_circle_phase_envelope import (
    classify_web_circle_envelope, PRE_DECAY, POST_DECAY,
    INSIDE_CONFIRMED, EDGE_ABSTAIN,
)

EVIDENCE = "DOCUMENTED_BEAM_SWEEP_TESTED_CONDITIONAL_NOT_HOST_DIFF_VERIFIED"
MAX_SHIPS = 100
MAX_FIELDS = 5000
MAX_COORD_ABS = 1_000_000
MAX_BEAMS = 20
MAX_ID = 2_147_483_647
STANDARD_MAX_RADII = frozenset((100, 150))

# Documented standard beam family names; these are NOT dynamic game weapon IDs.
# Values are units destroyed per individual beam, normal/web respectively.
STANDARD_BEAM_SWEEP_YIELDS: dict[str, tuple[int, int]] = {
    "laser": (4, 3),
    "x_ray_laser": (16, 12),
    "plasma_bolt": (36, 27),
    "blaster": (64, 48),
    "positron_beam": (100, 75),
    "disruptor": (144, 108),
    "heavy_blaster": (196, 147),
    "phaser": (256, 192),
    "heavy_disruptor": (324, 243),
    "heavy_phaser": (400, 300),
}


class BeamMineSweepAbstain(ValueError):
    """Ambiguous source, phase, geometry, custom mechanics, or snapshot."""


@dataclass(frozen=True, slots=True)
class SweepingShip:
    ship_id: int
    owner_id: int
    center: Point
    beam_family: str
    beam_count: int
    mission: str
    has_msc_scoop_friendly_code: bool


@dataclass(frozen=True, slots=True)
class BeamSweepEvent:
    ship_id: int
    field_id: int
    status: str
    mine_units_before: int
    mine_units_destroyed: int
    mine_units_after: int
    radius_before: int
    radius_after: int
    beam_yield_per_weapon: int
    mine_units_potentially_swept: int


@dataclass(frozen=True, slots=True)
class BeamSweepStep:
    ship_id: int
    fields_before: tuple[LocatedMinefield, ...]
    fields_after: tuple[LocatedMinefield, ...]
    events: tuple[BeamSweepEvent, ...]
    units_before: int
    units_after: int
    units_swept: int


@dataclass(frozen=True, slots=True)
class BeamSweepSequence:
    steps: tuple[BeamSweepStep, ...]
    fields_final: tuple[LocatedMinefield, ...]
    initial_units: int
    final_units: int
    total_units_swept: int
    evidence: str = EVIDENCE
    host_orders_accepted_verified: bool = False
    host_phase_order_verified: bool = False
    whole_host_mine_lifecycle_verified: bool = False
    host_diff_verified: bool = False


def _int(value: object, lo: int, hi: int) -> bool:
    return type(value) is int and lo <= value <= hi


def _point(value: object) -> bool:
    return type(value) is Point and _int(value.x, -MAX_COORD_ABS, MAX_COORD_ABS) and _int(
        value.y, -MAX_COORD_ABS, MAX_COORD_ABS,
    )


def _dist2(a: Point, b: Point) -> int:
    return (a.x - b.x) ** 2 + (a.y - b.y) ** 2


def _validate_fields(fields: object, *, max_radius: int) -> tuple[LocatedMinefield, ...]:
    if not isinstance(fields, (list, tuple)) or len(fields) > MAX_FIELDS:
        raise BeamMineSweepAbstain("complete bounded typed field roster required")
    seen: set[int] = set()
    result: list[LocatedMinefield] = []
    for f in fields:
        if type(f) is not LocatedMinefield or not (
            _int(f.field_id, 1, MAX_ID)
            and _int(f.owner_id, 1, MAX_ID)
            and _point(f.center)
            and _int(f.mine_units, 1, max_radius * max_radius)
            and type(f.is_web) is bool
        ):
            raise BeamMineSweepAbstain("invalid field state, ID, center or density")
        if f.field_id in seen:
            raise BeamMineSweepAbstain("duplicate field ID")
        seen.add(f.field_id)
        result.append(f)
    return tuple(sorted(result, key=lambda f: f.field_id))


def _validate_ships(ships: object) -> tuple[SweepingShip, ...]:
    if not isinstance(ships, (list, tuple)) or len(ships) > MAX_SHIPS:
        raise BeamMineSweepAbstain("complete bounded ship sweep roster required")
    seen: set[int] = set()
    result: list[SweepingShip] = []
    for ship in ships:
        if type(ship) is not SweepingShip or not (
            _int(ship.ship_id, 1, MAX_ID)
            and _int(ship.owner_id, 1, MAX_ID)
            and _point(ship.center)
            and type(ship.beam_family) is str
            and ship.beam_family in STANDARD_BEAM_SWEEP_YIELDS
            and _int(ship.beam_count, 1, MAX_BEAMS)
            and type(ship.mission) is str
            and ship.mission == "MINE_SWEEP"
            and type(ship.has_msc_scoop_friendly_code) is bool
            and ship.has_msc_scoop_friendly_code is False
        ):
            raise BeamMineSweepAbstain("unsupported mission, beam, vessel or MSC scoop")
        if ship.ship_id in seen:
            raise BeamMineSweepAbstain("duplicate ship ID")
        seen.add(ship.ship_id)
        result.append(ship)
    return tuple(sorted(result, key=lambda ship: ship.ship_id))


def _map_for_keys(values: object, keys: set, *, label: str, pair_keys: bool = False) -> dict:
    if not isinstance(values, Mapping):
        raise BeamMineSweepAbstain(f"missing {label} context")
    try:
        material = dict(values)
    except (TypeError, ValueError) as exc:
        raise BeamMineSweepAbstain(f"invalid {label} context") from exc
    def typed_key(key: object) -> bool:
        if pair_keys:
            return (
                type(key) is tuple and len(key) == 2
                and all(_int(part, 1, MAX_ID) for part in key)
            )
        return _int(key, 1, MAX_ID)

    if (
        any(not typed_key(key) for key in material)
        or set(material) != keys
        or any(type(v) is not bool for v in material.values())
    ):
        raise BeamMineSweepAbstain(f"incomplete or untyped {label} context")
    return material


def _beam_in_range(*, ship_center: Point, field_center: Point,
                   mine_units: int, web: bool) -> bool:
    radius = isqrt(mine_units)
    distance_squared = _dist2(ship_center, field_center)
    if not web:
        # Normal mines: inside the field OR strictly LESS than 5 LY
        # from its documented integer-radius edge.
        return distance_squared < (radius + 5) ** 2
    # Web sweeping deliberately uses the PRE_DECAY envelope. Exact cell
    # raster geometry is unresolved, so the guarded ring still abstains.
    envelope = classify_web_circle_envelope(
        ship_position=ship_center,
        field_center=field_center,
        field_mine_units=mine_units,
        phase=PRE_DECAY,
        exact_integer_positions_and_phase_confirmed=True,
        standard_field_no_custom_geometry_confirmed=True,
    )
    if envelope.classification == EDGE_ABSTAIN:
        raise BeamMineSweepAbstain("web mine sweep near-edge square/circle geometry unresolved")
    return envelope.classification == INSIDE_CONFIRMED


def simulate_isolated_standard_beam_sweeps(
    *,
    fields: Sequence[LocatedMinefield],
    ships: Sequence[SweepingShip],
    confirmed_enemy_by_ship_field: Mapping[tuple[int, int], bool],
    ion_storm_contains_field_center_by_id: Mapping[int, bool],
    standard_web_beam_yield_confirmed_by_field_id: Mapping[int, bool],
    max_radius: int,
    complete_pre_sweep_field_and_ship_rosters_confirmed: bool,
    exact_beam_loadouts_and_positions_confirmed: bool,
    complete_diplomacy_and_ion_context_confirmed: bool,
    isolated_beam_sweep_only_confirmed: bool,
    standard_no_custom_modifiers_confirmed: bool,
) -> BeamSweepSequence:
    """Atomic, deterministic hypothetical sweep steps, one per ascending ship ID.

    Trusted flags are caller assertions, NOT independent real Host receipts.
    Every ship/field pair has an explicit enemy Boolean, including friendly
    fields; every source field has an ion storm Boolean; every web field has
    an explicit affirmative standard-table eligibility Boolean.
    """
    if any(flag is not True for flag in (
        complete_pre_sweep_field_and_ship_rosters_confirmed,
        exact_beam_loadouts_and_positions_confirmed,
        complete_diplomacy_and_ion_context_confirmed,
        isolated_beam_sweep_only_confirmed,
        standard_no_custom_modifiers_confirmed,
    )):
        raise BeamMineSweepAbstain("unverified source, mission or Host interaction isolation")
    if type(max_radius) is not int or max_radius not in STANDARD_MAX_RADII:
        raise BeamMineSweepAbstain("custom or untyped max radius")
    roster = _validate_fields(fields, max_radius=max_radius)
    sweepers = _validate_ships(ships)
    field_ids = {f.field_id for f in roster}
    ship_ids = {s.ship_id for s in sweepers}
    enemy = _map_for_keys(
        confirmed_enemy_by_ship_field,
        {(s, f) for s in ship_ids for f in field_ids},
        label="enemy-by-ship-field", pair_keys=True,
    )
    for s in sweepers:
        for f in roster:
            if s.owner_id == f.owner_id and enemy[(s.ship_id, f.field_id)]:
                raise BeamMineSweepAbstain("same-owner minefield cannot be confirmed enemy")
    ion = _map_for_keys(
        ion_storm_contains_field_center_by_id,
        field_ids, label="ion-storm-center",
    )
    web_rate = _map_for_keys(
        standard_web_beam_yield_confirmed_by_field_id,
        {f.field_id for f in roster if f.is_web},
        label="standard-web-yield",
    )
    if not all(web_rate.values()):
        # For example, non-Crystal web mines placed in another identity
        # may have different sweep strength. No speculative multiplier.
        raise BeamMineSweepAbstain("nonstandard web field sweep rate unresolved")

    current = roster
    steps: list[BeamSweepStep] = []
    initial = sum(f.mine_units for f in current)
    for ship in sweepers:
        before = current
        after: list[LocatedMinefield] = []
        events: list[BeamSweepEvent] = []
        swept = 0
        for f in before:
            per_beam = STANDARD_BEAM_SWEEP_YIELDS[ship.beam_family][int(f.is_web)]
            potential = ship.beam_count * per_beam
            status = "NOT_ENEMY"
            destruction = 0
            if enemy[(ship.ship_id, f.field_id)]:
                if ion[f.field_id]:
                    status = "ION_BLOCKED"
                elif _beam_in_range(
                    ship_center=ship.center, field_center=f.center,
                    mine_units=f.mine_units, web=f.is_web,
                ):
                    status = "SWEEPED"
                    destruction = min(f.mine_units, potential)
                else:
                    status = "OUT_OF_RANGE"
            remaining = f.mine_units - destruction
            swept += destruction
            events.append(BeamSweepEvent(
                ship_id=ship.ship_id,
                field_id=f.field_id,
                status=status,
                mine_units_before=f.mine_units,
                mine_units_destroyed=destruction,
                mine_units_after=remaining,
                radius_before=isqrt(f.mine_units),
                radius_after=isqrt(remaining),
                beam_yield_per_weapon=per_beam,
                mine_units_potentially_swept=potential,
            ))
            if remaining:
                after.append(LocatedMinefield(
                    f.field_id, f.owner_id, f.center, remaining, f.is_web,
                ))
        current = tuple(after)
        before_units = sum(f.mine_units for f in before)
        after_units = sum(f.mine_units for f in current)
        if before_units != after_units + swept:
            raise BeamMineSweepAbstain("per-ship mine-unit conservation failure")
        steps.append(BeamSweepStep(
            ship.ship_id, before, current, tuple(events),
            before_units, after_units, swept,
        ))
    final = sum(f.mine_units for f in current)
    total = sum(step.units_swept for step in steps)
    if initial != final + total:
        raise BeamMineSweepAbstain("whole-sequence mine-unit conservation failure")
    return BeamSweepSequence(tuple(steps), current, initial, final, total)
