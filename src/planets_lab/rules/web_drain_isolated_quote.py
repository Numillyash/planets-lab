"""Isolated Crystal web-drain quote, not a Host phase or web mine impact.

Official source https://help.planets.nu/minefields :
After decay, each qualifying enemy Crystal-owned web field consumes 25 KT
of Neutronium; when fuel becomes zero, missions other than Beam up Fuel
reset to Explore. Non-Crystal-owned web fields have no per-turn web drain.

Only unambiguous inside-integer-radius positive geometry and safely
distant negative geometry are supported. Near-edge 1-LY/raster unknown
=> ABSTAIN. No Host order, mine hit, movement fuel, other fuel phases,
clipping, field/ship mutation or original minefield sourcing is claimed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .minefield_placement_candidate import LocatedMinefield, Point
from .web_circle_phase_envelope import (
    classify_web_circle_envelope, PRE_DECAY, POST_DECAY,
    INSIDE_CONFIRMED, EDGE_ABSTAIN,
)

EVIDENCE = "DOCUMENTED_POST_DECAY_CRYSTAL_WEB_DRAIN_TESTED_CONDITIONAL_NOT_HOST_VERIFIED"
DRAIN_PER_QUALIFYING_WEB_FIELD_KT = 25
MAX_FIELDS = 128
MAX_COORD_ABS = 1_000_000
MAX_ID = 2_147_483_647
MAX_FUEL_KT = 1_000_000
MAX_RADII = frozenset((100, 150))
SUPPORTED_MISSIONS = frozenset(("EXPLORE", "BEAM_UP_FUEL", "MINE_SWEEP", "CLOAK"))


class WebDrainQuoteAbstain(ValueError):
    """Unknown enemy entitlement, near-edge raster or overlapping fuel phases."""


@dataclass(frozen=True, slots=True)
class IsolatedCrystalWebDrainQuote:
    ship_owner_id: int
    ship_position: Point
    qualifying_post_decay_web_field_ids: tuple[int, ...]
    web_fields_in_source_roster: int
    neutronium_before_kt: int
    requested_drain_neutronium_kt: int
    hypothetical_neutronium_after_kt: int
    mission_before: str
    hypothetical_mission_after: str
    mission_would_reset_if_executed: bool
    evidence: str = EVIDENCE
    ship_fuel_mutated: bool = False
    mission_actually_reset: bool = False
    web_mine_impact_calculated: bool = False
    field_roster_mutated: bool = False
    host_phase_order_verified: bool = False
    host_diff_verified: bool = False


def _integer(value: object, minimum: int, maximum: int) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _point(p: object) -> bool:
    return type(p) is Point and _integer(p.x, -MAX_COORD_ABS, MAX_COORD_ABS) and _integer(
        p.y, -MAX_COORD_ABS, MAX_COORD_ABS,
    )


def _exact_flags(
    source: object, required: set[int], *, name: str,
) -> dict[int, bool]:
    if not isinstance(source, Mapping):
        raise WebDrainQuoteAbstain(f"missing complete {name} map")
    try:
        mapping = dict(source)
    except (TypeError, ValueError) as exc:
        raise WebDrainQuoteAbstain(f"malformed {name} map") from exc
    if (
        set(mapping) != required
        or any(not _integer(k, 1, MAX_ID) or type(v) is not bool for k, v in mapping.items())
    ):
        raise WebDrainQuoteAbstain(f"untyped/incomplete {name} map")
    return mapping


def quote_isolated_crystal_web_drain(
    *,
    ship_owner_id: int,
    ship_position: Point,
    neutronium_before_kt: int,
    ship_mission: str,
    fields_post_decay: Sequence[LocatedMinefield],
    enemy_web_by_field_id: Mapping[int, bool],
    crystal_owner_by_owner_id: Mapping[int, bool],
    max_radius: int,
    complete_post_decay_field_roster_confirmed: bool,
    exact_post_decay_geometry_confirmed: bool,
    full_diplomacy_friendly_code_and_web_entitlement_confirmed: bool,
    no_other_prior_or_simultaneous_fuel_events_confirmed: bool,
    ordinary_no_custom_or_terrain_modifiers_confirmed: bool,
    exact_fuel_and_mission_before_drain_confirmed: bool,
) -> IsolatedCrystalWebDrainQuote:
    """Conditional one-ship, one-stage quote. Flags do NOT attest a Host receipt."""
    if any(flag is not True for flag in (
        complete_post_decay_field_roster_confirmed,
        exact_post_decay_geometry_confirmed,
        full_diplomacy_friendly_code_and_web_entitlement_confirmed,
        no_other_prior_or_simultaneous_fuel_events_confirmed,
        ordinary_no_custom_or_terrain_modifiers_confirmed,
        exact_fuel_and_mission_before_drain_confirmed,
    )):
        raise WebDrainQuoteAbstain("post-decay source, diplomacy or isolated phase unverified")
    if not (
        _integer(ship_owner_id, 1, MAX_ID)
        and _point(ship_position)
        and _integer(neutronium_before_kt, 0, MAX_FUEL_KT)
        and type(ship_mission) is str and ship_mission in SUPPORTED_MISSIONS
        and type(max_radius) is int and max_radius in MAX_RADII
    ):
        raise WebDrainQuoteAbstain("unsupported ship, fuel, mission or standard radius")
    if not isinstance(fields_post_decay, (list, tuple)) or len(fields_post_decay) > MAX_FIELDS:
        raise WebDrainQuoteAbstain("full bounded post-decay field roster required")
    seen: set[int] = set()
    roster: list[LocatedMinefield] = []
    for f in fields_post_decay:
        if type(f) is not LocatedMinefield or not (
            _integer(f.field_id, 1, MAX_ID)
            and _integer(f.owner_id, 1, MAX_ID)
            and _point(f.center)
            and _integer(f.mine_units, 1, max_radius * max_radius)
            and type(f.is_web) is bool
        ):
            raise WebDrainQuoteAbstain("invalid post-decay field record")
        if f.field_id in seen:
            raise WebDrainQuoteAbstain("duplicate minefield identity")
        seen.add(f.field_id)
        roster.append(f)
    web = tuple(sorted((f for f in roster if f.is_web), key=lambda f: f.field_id))
    enemy = _exact_flags(enemy_web_by_field_id, {f.field_id for f in web}, name="enemy web")
    crystal = _exact_flags(
        crystal_owner_by_owner_id, {f.owner_id for f in web}, name="Crystal owner",
    )
    qualifying: list[int] = []
    for f in web:
        if f.owner_id == ship_owner_id and enemy[f.field_id]:
            raise WebDrainQuoteAbstain("own web field cannot also be confirmed enemy")
        if not enemy[f.field_id] or not crystal[f.owner_id]:
            continue
        # Web DRAIN uses POST_DECAY, unlike PRE_DECAY web sweeping.
        envelope = classify_web_circle_envelope(
            ship_position=ship_position,
            field_center=f.center,
            field_mine_units=f.mine_units,
            phase=POST_DECAY,
            exact_integer_positions_and_phase_confirmed=True,
            standard_field_no_custom_geometry_confirmed=True,
        )
        if envelope.classification == INSIDE_CONFIRMED:
            qualifying.append(f.field_id)
        elif envelope.classification == EDGE_ABSTAIN:
            raise WebDrainQuoteAbstain("near-edge post-decay web drain geometry ambiguous")
    drain = len(qualifying) * DRAIN_PER_QUALIFYING_WEB_FIELD_KT
    if drain > neutronium_before_kt:
        raise WebDrainQuoteAbstain("insufficient fuel: partial web drain/clipping unknown")
    remaining = neutronium_before_kt - drain
    resetting = drain > 0 and remaining == 0 and ship_mission != "BEAM_UP_FUEL"
    mission_after = "EXPLORE" if resetting else ship_mission
    if remaining + drain != neutronium_before_kt:
        raise WebDrainQuoteAbstain("fuel conservation error")
    return IsolatedCrystalWebDrainQuote(
        ship_owner_id=ship_owner_id,
        ship_position=ship_position,
        qualifying_post_decay_web_field_ids=tuple(qualifying),
        web_fields_in_source_roster=len(web),
        neutronium_before_kt=neutronium_before_kt,
        requested_drain_neutronium_kt=drain,
        hypothetical_neutronium_after_kt=remaining,
        mission_before=ship_mission,
        hypothetical_mission_after=mission_after,
        mission_would_reset_if_executed=resetting,
    )
