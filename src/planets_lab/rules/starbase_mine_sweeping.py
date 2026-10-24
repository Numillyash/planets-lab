"""Source-bounded isolated Campaign starbase mine sweeping quote.

Official https://help.planets.nu/adv-starbase-mine-sweeping :
- Campaign advantage disabled by default; primary order Sweep Mines.
- Each defensive beam (planet + starbase) uses highest buildable starbase
  beam technology, NOT the underlying planet's own weapon type.
- Starbases sweep AFTER ship sweeps, BEFORE mine scooping.
- Starbase distance restrictions equal starship sweeping restrictions.

This models one selected starbase on a pinned hypothetical pre-starbase
post-ship field roster. It never resolves multiple-starbase order,
concurrent ship scooping, campaign/custom effects or Host accepted orders.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isqrt
from typing import Mapping, Sequence

from .minefield_placement_candidate import LocatedMinefield, Point
from .mine_beam_sweeping import (
    BeamMineSweepAbstain,
    STANDARD_BEAM_SWEEP_YIELDS,
    _beam_in_range,
    _validate_fields,
    _map_for_keys,
)

EVIDENCE = "DOCUMENTED_SINGLE_STARBASE_SWEEP_QUOTE_TESTED_CONDITIONAL_NOT_HOST_VERIFIED"
MAX_ID = 2_147_483_647
MAX_POSITION = 1_000_000
MAX_DEFENSE_BEAMS = 2000  # Local quote bound, NOT asserted to be NuHost limit.
STANDARD_RADII = frozenset((100, 150))
SWEEP_ORDER = "SWEEP_MINES"


class StarbaseMineSweepAbstain(ValueError):
    """Ambiguous base loadout, pre-base phase, web geometry or unsupported setting."""


@dataclass(frozen=True, slots=True)
class SweepingStarbase:
    starbase_id: int
    owner_id: int
    position: Point
    primary_order: str
    highest_buildable_beam_family: str
    planetary_defense_beams: int
    starbase_defense_beams: int


@dataclass(frozen=True, slots=True)
class StarbaseSweepFieldQuote:
    field_id: int
    classification: str
    mine_units_before: int
    mine_units_potentially_destroyed: int
    mine_units_after_if_executed: int
    radius_before: int
    radius_after_if_executed: int
    beam_yield_per_weapon: int
    total_defensive_beams: int


@dataclass(frozen=True, slots=True)
class IsolatedStarbaseMineSweepQuote:
    starbase_id: int
    defensive_beam_family: str
    planetary_defense_beams: int
    starbase_defense_beams: int
    total_defensive_beams: int
    field_quotes: tuple[StarbaseSweepFieldQuote, ...]
    fields_hypothetically_after: tuple[LocatedMinefield, ...]
    initial_mine_units: int
    hypothetical_remaining_mine_units: int
    hypothetical_destroyed_mine_units: int
    evidence: str = EVIDENCE
    real_host_advantage_activation_verified: bool = False
    actual_ship_sweeps_verified: bool = False
    real_host_order_accepted_verified: bool = False
    real_host_starbase_sweep_verified: bool = False
    host_phase_order_verified: bool = False
    actual_field_roster_mutated: bool = False
    host_diff_verified: bool = False


def _int(value: object, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def quote_isolated_campaign_starbase_mine_sweep(
    *,
    starbase: SweepingStarbase,
    fields_post_ship_sweeps: Sequence[LocatedMinefield],
    enemy_by_field_id: Mapping[int, bool],
    ion_storm_contains_field_center_by_id: Mapping[int, bool],
    standard_web_beam_yield_by_field_id: Mapping[int, bool],
    max_radius: int,
    campaign_and_advantage_enabled_confirmed: bool,
    exact_starbase_beam_tech_and_both_defense_counts_confirmed: bool,
    post_ship_pre_starbase_field_roster_complete_confirmed: bool,
    complete_enemy_diplomacy_and_ion_storm_context_confirmed: bool,
    exactly_one_starbase_and_no_concurrent_scooping_confirmed: bool,
    ordinary_sweeping_no_special_campaign_modifiers_confirmed: bool,
) -> IsolatedStarbaseMineSweepQuote:
    """Return immutable possible mine-unit changes, not actual Host state."""
    if any(flag is not True for flag in (
        campaign_and_advantage_enabled_confirmed,
        exact_starbase_beam_tech_and_both_defense_counts_confirmed,
        post_ship_pre_starbase_field_roster_complete_confirmed,
        complete_enemy_diplomacy_and_ion_storm_context_confirmed,
        exactly_one_starbase_and_no_concurrent_scooping_confirmed,
        ordinary_sweeping_no_special_campaign_modifiers_confirmed,
    )):
        raise StarbaseMineSweepAbstain("Campaign advantage/phase/inventory context not confirmed")
    if type(max_radius) is not int or max_radius not in STANDARD_RADII:
        raise StarbaseMineSweepAbstain("unknown custom minefield radius")
    if type(starbase) is not SweepingStarbase or not (
        _int(starbase.starbase_id, 1, MAX_ID)
        and _int(starbase.owner_id, 1, MAX_ID)
        and type(starbase.position) is Point
        and _int(starbase.position.x, -MAX_POSITION, MAX_POSITION)
        and _int(starbase.position.y, -MAX_POSITION, MAX_POSITION)
        and type(starbase.primary_order) is str
        and starbase.primary_order == SWEEP_ORDER
        and type(starbase.highest_buildable_beam_family) is str
        and starbase.highest_buildable_beam_family in STANDARD_BEAM_SWEEP_YIELDS
        and _int(starbase.planetary_defense_beams, 0, MAX_DEFENSE_BEAMS)
        and _int(starbase.starbase_defense_beams, 0, MAX_DEFENSE_BEAMS)
        and 1 <= starbase.planetary_defense_beams
            + starbase.starbase_defense_beams <= MAX_DEFENSE_BEAMS
    ):
        raise StarbaseMineSweepAbstain("invalid order, position, beam tech or defense loadout")
    try:
        roster = _validate_fields(fields_post_ship_sweeps, max_radius=max_radius)
        field_ids = {f.field_id for f in roster}
        enemy = _map_for_keys(enemy_by_field_id, field_ids, label="starbase enemy field")
        ion = _map_for_keys(
            ion_storm_contains_field_center_by_id, field_ids, label="starbase ion storm"
        )
        web_rates = _map_for_keys(
            standard_web_beam_yield_by_field_id,
            {f.field_id for f in roster if f.is_web},
            label="starbase standard web rate",
        )
    except BeamMineSweepAbstain as exc:
        raise StarbaseMineSweepAbstain(f"missing/invalid field provenance: {exc}") from exc
    if not all(web_rates.values()):
        raise StarbaseMineSweepAbstain("nonstandard web defense-beam sweep rate not proven")
    for f in roster:
        if f.owner_id == starbase.owner_id and enemy[f.field_id]:
            raise StarbaseMineSweepAbstain("same-owner field cannot be marked enemy")

    beam_count = starbase.planetary_defense_beams + starbase.starbase_defense_beams
    quotes: list[StarbaseSweepFieldQuote] = []
    hypothetical_fields: list[LocatedMinefield] = []
    total_destroyed = 0
    for f in roster:
        per_beam = STANDARD_BEAM_SWEEP_YIELDS[
            starbase.highest_buildable_beam_family
        ][int(f.is_web)]
        potential = per_beam * beam_count
        destroyed = 0
        status = "NOT_ENEMY"
        if enemy[f.field_id]:
            if ion[f.field_id]:
                status = "ION_BLOCKED"
            else:
                try:
                    in_range = _beam_in_range(
                        ship_center=starbase.position,
                        field_center=f.center, mine_units=f.mine_units, web=f.is_web,
                    )
                except BeamMineSweepAbstain as exc:
                    raise StarbaseMineSweepAbstain(f"starbase web edge ABSTAIN: {exc}") from exc
                if in_range:
                    destroyed = min(potential, f.mine_units)
                    status = "SWEEPED"
                else:
                    status = "OUT_OF_RANGE"
        remain = f.mine_units - destroyed
        total_destroyed += destroyed
        quotes.append(StarbaseSweepFieldQuote(
            field_id=f.field_id,
            classification=status,
            mine_units_before=f.mine_units,
            mine_units_potentially_destroyed=destroyed,
            mine_units_after_if_executed=remain,
            radius_before=isqrt(f.mine_units),
            radius_after_if_executed=isqrt(remain),
            beam_yield_per_weapon=per_beam,
            total_defensive_beams=beam_count,
        ))
        if remain:
            hypothetical_fields.append(LocatedMinefield(
                f.field_id, f.owner_id, f.center, remain, f.is_web,
            ))
    initially = sum(f.mine_units for f in roster)
    hypothetically_remaining = sum(f.mine_units for f in hypothetical_fields)
    if initially != hypothetically_remaining + total_destroyed:
        raise StarbaseMineSweepAbstain("conditional mine conservation failed")
    return IsolatedStarbaseMineSweepQuote(
        starbase_id=starbase.starbase_id,
        defensive_beam_family=starbase.highest_buildable_beam_family,
        planetary_defense_beams=starbase.planetary_defense_beams,
        starbase_defense_beams=starbase.starbase_defense_beams,
        total_defensive_beams=beam_count,
        field_quotes=tuple(quotes),
        fields_hypothetically_after=tuple(hypothetical_fields),
        initial_mine_units=initially,
        hypothetical_remaining_mine_units=hypothetically_remaining,
        hypothetical_destroyed_mine_units=total_destroyed,
    )
