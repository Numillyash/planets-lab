"""Conditional ship-beam -> single Campaign starbase mine-sweep sequence.

This combines two *existing tested conditional* ledgers on ONE shared full
roster. The official documentation states starbases sweep after ships,
but this is NOT a real Host turn, Host-phase replay or confirmation that
ships, base and orders were accepted by the server.

Only pure beam-sweeping ships and ONE enabled starbase Sweep Mines order
are supported. No MSC, Colonial fighters, multiple bases, nonstandard
beam/web rates or interleaved Host actions. Unsupported => atomic ABSTAIN.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .minefield_placement_candidate import LocatedMinefield
from .mine_beam_sweeping import (
    SweepingShip, BeamSweepSequence, BeamMineSweepAbstain,
    simulate_isolated_standard_beam_sweeps,
    _map_for_keys, _validate_fields,
)
from .starbase_mine_sweeping import (
    SweepingStarbase, IsolatedStarbaseMineSweepQuote,
    StarbaseMineSweepAbstain, quote_isolated_campaign_starbase_mine_sweep,
)

EVIDENCE = "DOCUMENTED_CONDITIONAL_SHIP_TO_ONE_STARBASE_SWEEP_LEDGER_NOT_HOST_DIFF_VERIFIED"
MAX_ID = 2_147_483_647


class ShipStarbaseMineSweepAbstain(ValueError):
    """Unproven phase ordering, mismatched source maps or unsupported mechanics."""


@dataclass(frozen=True, slots=True)
class ConditionalShipStarbaseSweepLedger:
    ship_sequence: BeamSweepSequence
    starbase_quote: IsolatedStarbaseMineSweepQuote
    initial_fields: tuple[LocatedMinefield, ...]
    after_ship_fields: tuple[LocatedMinefield, ...]
    final_hypothetical_fields: tuple[LocatedMinefield, ...]
    initial_mine_units: int
    after_ship_mine_units: int
    final_hypothetical_mine_units: int
    ship_mine_units_swept: int
    starbase_mine_units_swept: int
    total_hypothetical_mine_units_swept: int
    evidence: str = EVIDENCE
    real_host_orders_accepted_verified: bool = False
    real_ship_phase_verified: bool = False
    real_starbase_phase_verified: bool = False
    real_host_phase_order_verified: bool = False
    actual_minefield_state_mutated: bool = False
    host_diff_verified: bool = False


def quote_conditional_ship_then_starbase_mine_sweeps(
    *,
    fields_before_ship_sweeps: Sequence[LocatedMinefield],
    beam_sweep_ships: Sequence[SweepingShip],
    starbase: SweepingStarbase,
    ship_enemy_by_ship_field: Mapping[tuple[int, int], bool],
    starbase_enemy_by_field_id: Mapping[int, bool],
    ion_storm_at_field_center_by_id: Mapping[int, bool],
    standard_web_beam_rate_by_field_id: Mapping[int, bool],
    max_radius: int,
    full_pre_ship_roster_and_all_ships_confirmed: bool,
    complete_diplomacy_ion_and_standard_web_rate_confirmed: bool,
    exact_ships_positions_missions_and_beams_confirmed: bool,
    campaign_starbase_advantage_and_order_confirmed: bool,
    exact_starbase_defenses_and_highest_buildable_beam_confirmed: bool,
    exactly_one_sweeping_starbase_confirmed: bool,
    no_msc_fighter_or_concurrent_field_mutations_confirmed: bool,
    standard_no_custom_mechanics_confirmed: bool,
) -> ConditionalShipStarbaseSweepLedger:
    """Immutable staged quote; the only bridge is the prior conditional result."""
    if any(x is not True for x in (
        full_pre_ship_roster_and_all_ships_confirmed,
        complete_diplomacy_ion_and_standard_web_rate_confirmed,
        exact_ships_positions_missions_and_beams_confirmed,
        campaign_starbase_advantage_and_order_confirmed,
        exact_starbase_defenses_and_highest_buildable_beam_confirmed,
        exactly_one_sweeping_starbase_confirmed,
        no_msc_fighter_or_concurrent_field_mutations_confirmed,
        standard_no_custom_mechanics_confirmed,
    )):
        raise ShipStarbaseMineSweepAbstain("full staged provenance and exclusions required")
    if type(max_radius) is not int or max_radius not in (100, 150):
        raise ShipStarbaseMineSweepAbstain("unsupported field radius")

    # Strictly validate source fields and ALL field-based maps BEFORE filtering
    # to the surviving roster. This prevents unknown omitted/misidentified
    # destroyed fields from silently disappearing in the phase transition.
    try:
        before = _validate_fields(fields_before_ship_sweeps, max_radius=max_radius)
        field_ids = {f.field_id for f in before}
        base_enemy = _map_for_keys(
            starbase_enemy_by_field_id, field_ids, label="initial base enemy",
        )
        ion = _map_for_keys(
            ion_storm_at_field_center_by_id, field_ids, label="initial ion",
        )
        web = _map_for_keys(
            standard_web_beam_rate_by_field_id,
            {f.field_id for f in before if f.is_web}, label="initial web rate",
        )
    except BeamMineSweepAbstain as exc:
        raise ShipStarbaseMineSweepAbstain(f"initial source ABSTAIN: {exc}") from exc

    if not isinstance(beam_sweep_ships, (list, tuple)) or not beam_sweep_ships:
        raise ShipStarbaseMineSweepAbstain("at least one typed beam-only sweeping ship required")

    try:
        ships_result = simulate_isolated_standard_beam_sweeps(
            fields=before, ships=beam_sweep_ships,
            confirmed_enemy_by_ship_field=ship_enemy_by_ship_field,
            ion_storm_contains_field_center_by_id=ion,
            standard_web_beam_yield_confirmed_by_field_id=web,
            max_radius=max_radius,
            complete_pre_sweep_field_and_ship_rosters_confirmed=True,
            exact_beam_loadouts_and_positions_confirmed=True,
            complete_diplomacy_and_ion_context_confirmed=True,
            isolated_beam_sweep_only_confirmed=True,
            standard_no_custom_modifiers_confirmed=True,
        )
    except BeamMineSweepAbstain as exc:
        raise ShipStarbaseMineSweepAbstain(f"ship sweep ABSTAIN: {exc}") from exc
    after_ship = ships_result.fields_final
    survivor_ids = {f.field_id for f in after_ship}
    if not survivor_ids.issubset(field_ids):
        raise ShipStarbaseMineSweepAbstain("ship stage introduced unknown field")
    for old in after_ship:
        previous = next(f for f in before if f.field_id == old.field_id)
        if (
            (old.owner_id, old.center, old.is_web)
            != (previous.owner_id, previous.center, previous.is_web)
            or old.mine_units > previous.mine_units
        ):
            raise ShipStarbaseMineSweepAbstain("ship stage changed field identity or grew mines")

    try:
        base_result = quote_isolated_campaign_starbase_mine_sweep(
            starbase=starbase,
            fields_post_ship_sweeps=after_ship,
            enemy_by_field_id={k: v for k, v in base_enemy.items() if k in survivor_ids},
            ion_storm_contains_field_center_by_id={
                k: v for k, v in ion.items() if k in survivor_ids
            },
            standard_web_beam_yield_by_field_id={
                k: v for k, v in web.items() if k in survivor_ids
            },
            max_radius=max_radius,
            campaign_and_advantage_enabled_confirmed=True,
            exact_starbase_beam_tech_and_both_defense_counts_confirmed=True,
            post_ship_pre_starbase_field_roster_complete_confirmed=True,
            complete_enemy_diplomacy_and_ion_storm_context_confirmed=True,
            exactly_one_starbase_and_no_concurrent_scooping_confirmed=True,
            ordinary_sweeping_no_special_campaign_modifiers_confirmed=True,
        )
    except StarbaseMineSweepAbstain as exc:
        raise ShipStarbaseMineSweepAbstain(f"single-starbase stage ABSTAIN: {exc}") from exc

    if ships_result.final_units != base_result.initial_mine_units:
        raise ShipStarbaseMineSweepAbstain("ship->starbase conditional stage boundary mismatch")
    total_swept = ships_result.total_units_swept + base_result.hypothetical_destroyed_mine_units
    if (
        ships_result.initial_units
        != base_result.hypothetical_remaining_mine_units + total_swept
        or ships_result.initial_units != sum(f.mine_units for f in before)
    ):
        raise ShipStarbaseMineSweepAbstain("cross-stage mine-unit conservation failure")
    return ConditionalShipStarbaseSweepLedger(
        ship_sequence=ships_result,
        starbase_quote=base_result,
        initial_fields=before,
        after_ship_fields=after_ship,
        final_hypothetical_fields=base_result.fields_hypothetically_after,
        initial_mine_units=ships_result.initial_units,
        after_ship_mine_units=ships_result.final_units,
        final_hypothetical_mine_units=base_result.hypothetical_remaining_mine_units,
        ship_mine_units_swept=ships_result.total_units_swept,
        starbase_mine_units_swept=base_result.hypothetical_destroyed_mine_units,
        total_hypothetical_mine_units_swept=total_swept,
    )
