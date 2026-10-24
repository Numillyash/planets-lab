"""DOCUMENTED conditional Colonial FIGHTER-ONLY normal-mine sweeping.

https://help.planets.nu/adv-fighter-mine-sweep
https://help.planets.nu/minefields

Standalone source-scoped calculation. Does not combine beam sweeping (#293),
scooping, starbase advantages, accepted orders or global Host phases.
Ion storm centers intentionally DO NOT block Colonial fighter sweeping.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isqrt
from typing import Mapping, Sequence

from .minefield_placement_candidate import LocatedMinefield, Point

EVIDENCE = "DOCUMENTED_COLONIAL_FIGHTER_SWEEP_TESTED_CONDITIONAL_NOT_HOST_VERIFIED"
MINES_PER_FIGHTER = 20
FIGHTER_EDGE_REACH_LY = 100
MAX_RADIUS_OPTIONS = frozenset((100, 150))
MAX_SHIPS = 100
MAX_FIELDS = 5000
MAX_FIGHTERS_PER_SHIP = 1000
MAX_ID = 2_147_483_647
MAX_COORD_ABS = 1_000_000


class ColonialFighterSweepAbstain(ValueError):
    """Missing or untrustworthy source, unsupported phase or race modifiers."""


@dataclass(frozen=True, slots=True)
class ColonialFighterSweeper:
    ship_id: int
    owner_id: int
    position: Point
    fighter_count: int
    beam_count: int
    mission: str


@dataclass(frozen=True, slots=True)
class FighterSweepEvent:
    ship_id: int
    field_id: int
    status: str
    mine_units_before: int
    mine_units_destroyed: int
    mine_units_after: int
    radius_before: int
    radius_after: int
    fighter_count: int
    maximum_per_field_units: int


@dataclass(frozen=True, slots=True)
class FighterSweepStep:
    ship_id: int
    fields_before: tuple[LocatedMinefield, ...]
    fields_after: tuple[LocatedMinefield, ...]
    events: tuple[FighterSweepEvent, ...]
    units_before: int
    units_after: int
    units_destroyed: int


@dataclass(frozen=True, slots=True)
class FighterSweepSequence:
    steps: tuple[FighterSweepStep, ...]
    fields_final: tuple[LocatedMinefield, ...]
    initial_units: int
    final_units: int
    total_units_destroyed: int
    evidence: str = EVIDENCE
    host_mission_accepted_verified: bool = False
    host_phase_order_verified: bool = False
    full_host_mine_sweeping_verified: bool = False
    host_diff_verified: bool = False


def _int(x: object, lower: int, upper: int) -> bool:
    return type(x) is int and lower <= x <= upper


def _point(p: object) -> bool:
    return type(p) is Point and _int(p.x, -MAX_COORD_ABS, MAX_COORD_ABS) and _int(
        p.y, -MAX_COORD_ABS, MAX_COORD_ABS,
    )


def _distance_squared(a: Point, b: Point) -> int:
    return (a.x - b.x) ** 2 + (a.y - b.y) ** 2


def _typed_fields(fields: object, cap: int) -> tuple[LocatedMinefield, ...]:
    if not isinstance(fields, (tuple, list)) or len(fields) > MAX_FIELDS:
        raise ColonialFighterSweepAbstain("full bounded field roster required")
    seen: set[int] = set()
    typed: list[LocatedMinefield] = []
    for f in fields:
        if type(f) is not LocatedMinefield or not (
            _int(f.field_id, 1, MAX_ID)
            and _int(f.owner_id, 1, MAX_ID)
            and _point(f.center)
            and _int(f.mine_units, 1, cap * cap)
            and type(f.is_web) is bool
        ):
            raise ColonialFighterSweepAbstain("unsupported field source")
        if f.field_id in seen:
            raise ColonialFighterSweepAbstain("duplicate field identity")
        seen.add(f.field_id)
        typed.append(f)
    return tuple(sorted(typed, key=lambda f: f.field_id))


def _typed_ships(ships: object) -> tuple[ColonialFighterSweeper, ...]:
    if not isinstance(ships, (tuple, list)) or len(ships) > MAX_SHIPS:
        raise ColonialFighterSweepAbstain("full bounded sweeper roster required")
    seen: set[int] = set()
    typed: list[ColonialFighterSweeper] = []
    for ship in ships:
        if type(ship) is not ColonialFighterSweeper or not (
            _int(ship.ship_id, 1, MAX_ID)
            and _int(ship.owner_id, 1, MAX_ID)
            and _point(ship.position)
            and _int(ship.fighter_count, 1, MAX_FIGHTERS_PER_SHIP)
            and type(ship.beam_count) is int and ship.beam_count == 0
            and type(ship.mission) is str and ship.mission == "MINE_SWEEP"
        ):
            raise ColonialFighterSweepAbstain("invalid or mixed beam/fighter sweeper")
        if ship.ship_id in seen:
            raise ColonialFighterSweepAbstain("duplicate ship identity")
        seen.add(ship.ship_id)
        typed.append(ship)
    return tuple(sorted(typed, key=lambda ship: ship.ship_id))


def _typed_enemy_map(values: object, keys: set[tuple[int, int]]) -> dict:
    if not isinstance(values, Mapping):
        raise ColonialFighterSweepAbstain("complete explicit enemy matrix required")
    try:
        source = dict(values)
    except (TypeError, ValueError) as exc:
        raise ColonialFighterSweepAbstain("malformed enemy matrix") from exc
    if (
        any(type(key) is not tuple or len(key) != 2 or
            not all(_int(k, 1, MAX_ID) for k in key) for key in source)
        or set(source) != keys
        or any(type(value) is not bool for value in source.values())
    ):
        raise ColonialFighterSweepAbstain("untyped or incomplete enemy matrix")
    return source


def simulate_isolated_colonial_fighter_sweeping(
    *,
    fields: Sequence[LocatedMinefield],
    ships: Sequence[ColonialFighterSweeper],
    confirmed_enemy_by_ship_field: Mapping[tuple[int, int], bool],
    max_radius: int,
    full_presweep_field_ship_rosters_confirmed: bool,
    colonial_race_and_advantage_confirmed: bool,
    exact_fighters_positions_and_mission_confirmed: bool,
    fighter_only_no_beams_scoop_or_starbase_confirmed: bool,
    ordinary_unmodified_minefields_confirmed: bool,
    independent_host_phase_not_claimed: bool,
) -> FighterSweepSequence:
    """Hypothetical sweeps. The source flags are NOT actual Host evidence.

    Source documents 20 mines per Colonial fighter PER eligible normal
    minefield, with 100 LY reach from nearest edge, including ion storms.
    The only supported ship configuration is pure fighter sweeping with
    zero beams, not mixed simultaneous fighter+beam application.
    """
    if any(flag is not True for flag in (
        full_presweep_field_ship_rosters_confirmed,
        colonial_race_and_advantage_confirmed,
        exact_fighters_positions_and_mission_confirmed,
        fighter_only_no_beams_scoop_or_starbase_confirmed,
        ordinary_unmodified_minefields_confirmed,
        independent_host_phase_not_claimed,
    )):
        raise ColonialFighterSweepAbstain("pre-sweep source and isolation not independently supplied")
    if type(max_radius) is not int or max_radius not in MAX_RADIUS_OPTIONS:
        raise ColonialFighterSweepAbstain("nonstandard field radius")
    roster = _typed_fields(fields, max_radius)
    carriers = _typed_ships(ships)
    enemies = _typed_enemy_map(
        confirmed_enemy_by_ship_field,
        {(s.ship_id, f.field_id) for s in carriers for f in roster},
    )
    for ship in carriers:
        for f in roster:
            if ship.owner_id == f.owner_id and enemies[(ship.ship_id, f.field_id)]:
                raise ColonialFighterSweepAbstain("own field cannot be confirmed enemy")
    current = roster
    initial = sum(f.mine_units for f in current)
    steps: list[FighterSweepStep] = []
    for ship in carriers:
        before = current
        afterwards: list[LocatedMinefield] = []
        events: list[FighterSweepEvent] = []
        destroyed_total = 0
        for f in before:
            potential = ship.fighter_count * MINES_PER_FIGHTER
            status = "NOT_ENEMY"
            destroyed = 0
            if enemies[(ship.ship_id, f.field_id)]:
                if f.is_web:
                    status = "WEB_IMMUNE_TO_FIGHTERS"
                elif _distance_squared(ship.position, f.center) <= (
                    isqrt(f.mine_units) + FIGHTER_EDGE_REACH_LY
                ) ** 2:
                    status = "FIGHTERS_SWEPT"
                    destroyed = min(f.mine_units, potential)
                else:
                    status = "OUT_OF_RANGE"
            remaining = f.mine_units - destroyed
            destroyed_total += destroyed
            events.append(FighterSweepEvent(
                ship.ship_id, f.field_id, status, f.mine_units,
                destroyed, remaining, isqrt(f.mine_units),
                isqrt(remaining), ship.fighter_count, potential,
            ))
            if remaining > 0:
                afterwards.append(LocatedMinefield(
                    f.field_id, f.owner_id, f.center, remaining, f.is_web,
                ))
        current = tuple(afterwards)
        before_total = sum(f.mine_units for f in before)
        after_total = sum(f.mine_units for f in current)
        if before_total != after_total + destroyed_total:
            raise ColonialFighterSweepAbstain("intermediate mine-unit conservation failure")
        steps.append(FighterSweepStep(
            ship.ship_id, before, current, tuple(events),
            before_total, after_total, destroyed_total,
        ))
    final = sum(f.mine_units for f in current)
    total = sum(step.units_destroyed for step in steps)
    if initial != final + total:
        raise ColonialFighterSweepAbstain("whole-sequence mine-unit conservation failure")
    return FighterSweepSequence(tuple(steps), current, initial, final, total)
