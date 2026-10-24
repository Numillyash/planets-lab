"""One Colonial carrier: simultaneous beam + fighter mine-sweep *quote*.

Official:
 https://help.planets.nu/adv-fighter-mine-sweep
 https://help.planets.nu/minefields

One Colonial carrier with Mine Sweep may use BOTH its beam weapons and
fighters in the SAME ship-ID step. We compute each channel's independent
potential from the SAME pre-step field radius, then cap their combined
potential at the number of mines present. When oversaturated, no exact
beam-vs-fighter attribution/order is claimed.

Beam sweep: normal <5 LY from integer radius; web uses conservative
PRE_DECAY guard and ABSTAINS near its unresolved raster edge. Beam sweep
blocked by an ion storm at field center; Colonial fighters can sweep
normal (not web) fields even there, up to 100 LY from the edge.

No ship movement, inventory mutation, MSC, starbase, phase execution,
other ships, dynamic weapons, custom campaign or actual Host proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isqrt
from typing import Mapping, Sequence

from .minefield_placement_candidate import LocatedMinefield, Point
from .mine_beam_sweeping import (
    BeamMineSweepAbstain, STANDARD_BEAM_SWEEP_YIELDS,
    _beam_in_range, _map_for_keys, _validate_fields,
)
from .mine_fighter_sweeping import (
    FIGHTER_EDGE_REACH_LY, MAX_FIGHTERS_PER_SHIP, MINES_PER_FIGHTER,
)

EVIDENCE = "DOCUMENTED_COLONIAL_MIXED_BEAM_FIGHTER_SINGLE_STEP_TESTED_CONDITIONAL"
MAX_ID = 2_147_483_647
MAX_POSITION = 1_000_000
MAX_BEAMS = 20
STANDARD_RADII = frozenset((100, 150))


class ColonialMixedSweepAbstain(ValueError):
    """Unverified mixed loadout, phase, range, racial entitlement or source."""


@dataclass(frozen=True, slots=True)
class MixedColonialCarrier:
    ship_id: int
    owner_id: int
    position: Point
    mission: str
    beam_family: str
    beam_count: int
    fighter_count: int
    has_msc_scoop_friendly_code: bool


@dataclass(frozen=True, slots=True)
class MixedColonialFieldQuote:
    field_id: int
    is_web: bool
    mine_units_before: int
    pre_step_integer_radius: int
    beam_channel_status: str
    fighter_channel_status: str
    beam_potential_mine_units: int
    fighter_potential_mine_units: int
    combined_potential_mine_units: int
    total_hypothetical_mines_destroyed: int
    hypothetical_mines_remaining: int
    # No split of destruction when potential > present mines.
    channel_attribution_verified: bool = False


@dataclass(frozen=True, slots=True)
class MixedColonialSweepQuote:
    carrier_id: int
    field_quotes: tuple[MixedColonialFieldQuote, ...]
    fields_hypothetically_after: tuple[LocatedMinefield, ...]
    initially_present_mine_units: int
    hypothetically_destroyed_mine_units: int
    hypothetically_remaining_mine_units: int
    evidence: str = EVIDENCE
    actual_mission_accepted_verified: bool = False
    actual_beam_fighter_host_simultaneity_verified: bool = False
    actual_minefield_state_mutated: bool = False
    host_phase_order_verified: bool = False
    host_diff_verified: bool = False


def _integer(value: object, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def quote_isolated_colonial_mixed_sweep(
    *,
    carrier: MixedColonialCarrier,
    fields_before_carrier_sweep: Sequence[LocatedMinefield],
    enemy_by_field_id: Mapping[int, bool],
    ion_storm_contains_field_center_by_id: Mapping[int, bool],
    standard_web_beam_yield_by_field_id: Mapping[int, bool],
    max_radius: int,
    missing_colonies_race_and_fighter_advantage_confirmed: bool,
    exact_beams_fighters_mission_and_position_confirmed: bool,
    complete_pre_carrier_field_roster_confirmed: bool,
    complete_diplomacy_ion_and_web_rate_context_confirmed: bool,
    isolated_single_carrier_no_msc_or_starbase_confirmed: bool,
    standard_no_custom_modifiers_confirmed: bool,
) -> MixedColonialSweepQuote:
    """Source-conditional single-ship mixed potential, never Host outcome."""
    if any(x is not True for x in (
        missing_colonies_race_and_fighter_advantage_confirmed,
        exact_beams_fighters_mission_and_position_confirmed,
        complete_pre_carrier_field_roster_confirmed,
        complete_diplomacy_ion_and_web_rate_context_confirmed,
        isolated_single_carrier_no_msc_or_starbase_confirmed,
        standard_no_custom_modifiers_confirmed,
    )):
        raise ColonialMixedSweepAbstain("source or isolated mixed-step premise unconfirmed")
    if type(max_radius) is not int or max_radius not in STANDARD_RADII:
        raise ColonialMixedSweepAbstain("unsupported radius or custom game")
    if type(carrier) is not MixedColonialCarrier or not (
        _integer(carrier.ship_id, 1, MAX_ID)
        and _integer(carrier.owner_id, 1, MAX_ID)
        and type(carrier.position) is Point
        and _integer(carrier.position.x, -MAX_POSITION, MAX_POSITION)
        and _integer(carrier.position.y, -MAX_POSITION, MAX_POSITION)
        and type(carrier.mission) is str and carrier.mission == "MINE_SWEEP"
        and type(carrier.beam_family) is str
        and carrier.beam_family in STANDARD_BEAM_SWEEP_YIELDS
        and _integer(carrier.beam_count, 1, MAX_BEAMS)
        and _integer(carrier.fighter_count, 1, MAX_FIGHTERS_PER_SHIP)
        and type(carrier.has_msc_scoop_friendly_code) is bool
        and carrier.has_msc_scoop_friendly_code is False
    ):
        raise ColonialMixedSweepAbstain("invalid exact mixed carrier loadout or mission")
    try:
        roster = _validate_fields(fields_before_carrier_sweep, max_radius=max_radius)
        ids = {f.field_id for f in roster}
        enemy = _map_for_keys(enemy_by_field_id, ids, label="mixed carrier enemy roster")
        ion = _map_for_keys(
            ion_storm_contains_field_center_by_id, ids, label="mixed carrier ion roster"
        )
        web_rate = _map_for_keys(
            standard_web_beam_yield_by_field_id,
            {f.field_id for f in roster if f.is_web},
            label="mixed carrier web rate",
        )
    except BeamMineSweepAbstain as exc:
        raise ColonialMixedSweepAbstain(f"invalid complete field context: {exc}") from exc
    if not all(web_rate.values()):
        raise ColonialMixedSweepAbstain("nonstandard web beam yields unsupported")
    if any(f.owner_id == carrier.owner_id and enemy[f.field_id] for f in roster):
        raise ColonialMixedSweepAbstain("own field cannot be a confirmed enemy")

    quotes: list[MixedColonialFieldQuote] = []
    remaining_fields: list[LocatedMinefield] = []
    total_destroyed = 0
    for f in roster:
        radius = isqrt(f.mine_units)
        beam_potential = fighter_potential = 0
        beam_status = fighter_status = "NOT_ENEMY"
        if enemy[f.field_id]:
            # For a mixed carrier, fighters do not care about ion storms
            # and cannot destroy web mines at all.
            if f.is_web:
                fighter_status = "WEB_IMMUNE_TO_FIGHTERS"
            else:
                dist2 = (
                    (carrier.position.x - f.center.x) ** 2
                    + (carrier.position.y - f.center.y) ** 2
                )
                if dist2 <= (radius + FIGHTER_EDGE_REACH_LY) ** 2:
                    fighter_status = "FIGHTERS_IN_RANGE"
                    fighter_potential = carrier.fighter_count * MINES_PER_FIGHTER
                else:
                    fighter_status = "FIGHTERS_OUT_OF_RANGE"

            if ion[f.field_id]:
                beam_status = "ION_BLOCKED"
            else:
                try:
                    in_range = _beam_in_range(
                        ship_center=carrier.position,
                        field_center=f.center,
                        mine_units=f.mine_units,
                        web=f.is_web,
                    )
                except BeamMineSweepAbstain as exc:
                    raise ColonialMixedSweepAbstain(
                        f"web beam near-edge requires raster evidence: {exc}"
                    ) from exc
                if in_range:
                    beam_status = "BEAMS_IN_RANGE"
                    beam_potential = carrier.beam_count * (
                        STANDARD_BEAM_SWEEP_YIELDS[carrier.beam_family][int(f.is_web)]
                    )
                else:
                    beam_status = "BEAMS_OUT_OF_RANGE"

        combined_potential = beam_potential + fighter_potential
        destroyed = min(f.mine_units, combined_potential)
        remaining = f.mine_units - destroyed
        total_destroyed += destroyed
        quotes.append(MixedColonialFieldQuote(
            field_id=f.field_id,
            is_web=f.is_web,
            mine_units_before=f.mine_units,
            pre_step_integer_radius=radius,
            beam_channel_status=beam_status,
            fighter_channel_status=fighter_status,
            beam_potential_mine_units=beam_potential,
            fighter_potential_mine_units=fighter_potential,
            combined_potential_mine_units=combined_potential,
            total_hypothetical_mines_destroyed=destroyed,
            hypothetical_mines_remaining=remaining,
        ))
        if remaining:
            remaining_fields.append(LocatedMinefield(
                f.field_id, f.owner_id, f.center, remaining, f.is_web
            ))

    original = sum(f.mine_units for f in roster)
    final = sum(f.mine_units for f in remaining_fields)
    if original != final + total_destroyed:
        raise ColonialMixedSweepAbstain("mixed single-step mine conservation violation")
    return MixedColonialSweepQuote(
        carrier_id=carrier.ship_id,
        field_quotes=tuple(quotes),
        fields_hypothetically_after=tuple(remaining_fields),
        initially_present_mine_units=original,
        hypothetically_destroyed_mine_units=total_destroyed,
        hypothetically_remaining_mine_units=final,
    )
