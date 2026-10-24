"""Conditional canonical ship-ID sweeps followed by ONE Campaign starbase.

Docs:
 https://help.planets.nu/minefields
 https://help.planets.nu/adv-starbase-mine-sweeping

Reuses the preexisting #307 canonical ship beam/fighter/mixed ledger and
#304 isolated starbase quote without changing their formulas or admitting
interleaved MSC, colonial starbase fighters or other Host phases.

All original ship×field, starbase×field hostility, ion, standard web
rate and Colonial entitlement maps are required and checked *before*
any ship exhausts any field. The starbase receives only the returned
post-ship roster; maps are projected from an already validated source.

This is a hypothetical, synthetic, immutable quote, NOT a HostEngine
stage, server-accepted orders, an authenticated Host witness or DIFF.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .minefield_placement_candidate import LocatedMinefield
from .mine_beam_sweeping import (
    SweepingShip, BeamMineSweepAbstain, _map_for_keys, _validate_fields,
)
from .mine_fighter_sweeping import ColonialFighterSweeper
from .colonial_mixed_beam_fighter_sweep import MixedColonialCarrier
from .ordered_ship_mine_sweeps import (
    OrderedShipMineSweepLedger, OrderedShipMineSweepAbstain,
    quote_ordered_isolated_ship_mine_sweeps,
)
from .starbase_mine_sweeping import (
    SweepingStarbase, IsolatedStarbaseMineSweepQuote,
    StarbaseMineSweepAbstain, quote_isolated_campaign_starbase_mine_sweep,
)

EVIDENCE = "DOCUMENTED_CONDITIONAL_CANONICAL_SHIPS_ONE_CAMPAIGN_BASE_TESTED_NOT_HOST_VERIFIED"


class CanonicalShipStarbaseSweepAbstain(ValueError):
    """Missing full stage provenance, nonstandard interaction or uncertain edge."""


@dataclass(frozen=True, slots=True)
class CanonicalShipStarbaseSweepLedger:
    ship_ledger: OrderedShipMineSweepLedger
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
    real_host_ship_order_accepted_verified: bool = False
    real_host_starbase_order_accepted_verified: bool = False
    real_host_phase_order_verified: bool = False
    actual_minefield_state_mutated: bool = False
    actual_campaign_advantage_enabled_verified: bool = False
    host_diff_verified: bool = False


def quote_canonical_ships_then_one_starbase_sweep(
    *,
    fields_before_ship_sweeps: Sequence[LocatedMinefield],
    ships: Sequence[SweepingShip | ColonialFighterSweeper | MixedColonialCarrier],
    starbase: SweepingStarbase,
    ship_enemy_by_ship_field: Mapping[tuple[int, int], bool],
    starbase_enemy_by_field_id: Mapping[int, bool],
    ion_storm_at_field_center_by_id: Mapping[int, bool],
    standard_web_beam_rate_by_field_id: Mapping[int, bool],
    colonial_entitlement_by_ship_id: Mapping[int, bool],
    max_radius: int,
    full_initial_field_ship_and_starbase_rosters_confirmed: bool,
    exact_ship_missions_loadouts_positions_and_colonial_entitlements_confirmed: bool,
    complete_initial_diplomacy_ion_and_web_rate_context_confirmed: bool,
    campaign_advantage_order_and_base_defensive_beams_confirmed: bool,
    ship_id_order_then_single_base_stage_confirmed: bool,
    no_msc_scooping_colonial_base_fighters_or_other_mutations_confirmed: bool,
    standard_no_custom_mechanics_confirmed: bool,
) -> CanonicalShipStarbaseSweepLedger:
    """Apply tested conditional models to ONE full roster and verify accounting.

    Flags are caller-provided assumptions, never independently verified
    evidence of real Host commands/stage order or exact race identity.
    """
    if any(flag is not True for flag in (
        full_initial_field_ship_and_starbase_rosters_confirmed,
        exact_ship_missions_loadouts_positions_and_colonial_entitlements_confirmed,
        complete_initial_diplomacy_ion_and_web_rate_context_confirmed,
        campaign_advantage_order_and_base_defensive_beams_confirmed,
        ship_id_order_then_single_base_stage_confirmed,
        no_msc_scooping_colonial_base_fighters_or_other_mutations_confirmed,
        standard_no_custom_mechanics_confirmed,
    )):
        raise CanonicalShipStarbaseSweepAbstain("complete isolated stage and entitlement context required")
    if type(max_radius) is not int or max_radius not in (100, 150):
        raise CanonicalShipStarbaseSweepAbstain("unknown custom max radius")
    try:
        original = _validate_fields(fields_before_ship_sweeps, max_radius=max_radius)
        original_ids = {f.field_id for f in original}
        # Full source maps MUST be checked before a ship consumes a field.
        base_enemy = _map_for_keys(
            starbase_enemy_by_field_id,
            original_ids, label="original starbase hostility",
        )
        ion = _map_for_keys(
            ion_storm_at_field_center_by_id,
            original_ids, label="original ion centers",
        )
        web = _map_for_keys(
            standard_web_beam_rate_by_field_id,
            {f.field_id for f in original if f.is_web},
            label="original standard web rates",
        )
    except BeamMineSweepAbstain as exc:
        raise CanonicalShipStarbaseSweepAbstain(f"initial field/base context ABSTAIN: {exc}") from exc
    # Avoid masking a real source gap after the ship stage has destroyed
    # every web field; the same all-true requirement applies pre-stage.
    if not all(web.values()):
        raise CanonicalShipStarbaseSweepAbstain("nonstandard or missing original web rates")

    try:
        ship_ledger = quote_ordered_isolated_ship_mine_sweeps(
            fields_pre_ship_stage=original,
            ships=ships,
            enemy_by_ship_field_id=ship_enemy_by_ship_field,
            ion_storm_contains_field_center_by_id=ion,
            standard_web_beam_yield_by_field_id=web,
            colonial_entitlement_by_ship_id=colonial_entitlement_by_ship_id,
            max_radius=max_radius,
            complete_pre_ship_field_and_ship_roster_confirmed=True,
            exact_ship_identity_loadouts_missions_and_positions_confirmed=True,
            all_fighter_carriers_colonial_and_advantage_confirmed=True,
            complete_enemy_diplomacy_ion_and_web_rate_context_confirmed=True,
            ship_id_phase_order_and_no_interleaving_confirmed=True,
            no_msc_scooping_starbase_or_custom_mechanics_confirmed=True,
        )
    except OrderedShipMineSweepAbstain as exc:
        raise CanonicalShipStarbaseSweepAbstain(f"ordered ship stage ABSTAIN: {exc}") from exc

    after_ship = ship_ledger.final_hypothetical_fields
    survivors = {f.field_id for f in after_ship}
    if not survivors.issubset(original_ids):
        raise CanonicalShipStarbaseSweepAbstain("ship stage introduced unknown field")
    initial_by_id = {f.field_id: f for f in original}
    for f in after_ship:
        start = initial_by_id[f.field_id]
        if (
            (f.owner_id, f.center, f.is_web) !=
            (start.owner_id, start.center, start.is_web)
            or f.mine_units > start.mine_units
        ):
            raise CanonicalShipStarbaseSweepAbstain("ship stage changed field identity or grew mines")

    try:
        starbase_quote = quote_isolated_campaign_starbase_mine_sweep(
            starbase=starbase,
            fields_post_ship_sweeps=after_ship,
            enemy_by_field_id={fid: val for fid, val in base_enemy.items() if fid in survivors},
            ion_storm_contains_field_center_by_id={
                fid: val for fid, val in ion.items() if fid in survivors
            },
            standard_web_beam_yield_by_field_id={
                fid: val for fid, val in web.items() if fid in survivors
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
        raise CanonicalShipStarbaseSweepAbstain(f"single Campaign starbase stage ABSTAIN: {exc}") from exc

    initial = sum(f.mine_units for f in original)
    after_ship_total = sum(f.mine_units for f in after_ship)
    final = sum(f.mine_units for f in starbase_quote.fields_hypothetically_after)
    ship_swept = ship_ledger.total_hypothetical_units_swept
    base_swept = starbase_quote.hypothetical_destroyed_mine_units
    if not (
        initial == ship_ledger.initial_units
        and after_ship_total == ship_ledger.final_hypothetical_units
        and after_ship_total == starbase_quote.initial_mine_units
        and final == starbase_quote.hypothetical_remaining_mine_units
        and initial == after_ship_total + ship_swept
        and after_ship_total == final + base_swept
        and initial == final + ship_swept + base_swept
    ):
        raise CanonicalShipStarbaseSweepAbstain("cross-stage field/ledger conservation mismatch")

    final_ids = {f.field_id for f in starbase_quote.fields_hypothetically_after}
    if not final_ids.issubset(survivors):
        raise CanonicalShipStarbaseSweepAbstain("starbase reintroduced an exhausted field")
    post_ship_by_id = {f.field_id: f for f in after_ship}
    for f in starbase_quote.fields_hypothetically_after:
        pre = post_ship_by_id[f.field_id]
        if (
            (f.owner_id, f.center, f.is_web) != (pre.owner_id, pre.center, pre.is_web)
            or f.mine_units > pre.mine_units
        ):
            raise CanonicalShipStarbaseSweepAbstain("starbase changed identity or grew field")
    return CanonicalShipStarbaseSweepLedger(
        ship_ledger=ship_ledger,
        starbase_quote=starbase_quote,
        initial_fields=original,
        after_ship_fields=after_ship,
        final_hypothetical_fields=starbase_quote.fields_hypothetically_after,
        initial_mine_units=initial,
        after_ship_mine_units=after_ship_total,
        final_hypothetical_mine_units=final,
        ship_mine_units_swept=ship_swept,
        starbase_mine_units_swept=base_swept,
        total_hypothetical_mine_units_swept=ship_swept + base_swept,
    )
