"""Ordered mixed-capability isolated ship mine sweeping (no starbases/MSC).

Uses three existing pure DOCUMENTED + TESTED conditional simulators:
 * SweepingShip: standard beam only
 * ColonialFighterSweeper: Colonial fighter only (zero beams)
 * MixedColonialCarrier: one Colonial carrier with beams AND fighters

Official https://help.planets.nu/minefields :
Sweeps are resolved by ascending Ship ID with minefield radius
recalculated after each ship. Simultaneous beam/fighter action applies
*within* a mixed carrier's single ship step, not as separate ships.

This is a hypothetical quote on a caller-supplied complete pre-ship
roster; actual Host ship identities, missions, orders and stages remain
UNVERIFIED. No MSC scoop, starbase, campaign custom mechanics or movement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .minefield_placement_candidate import LocatedMinefield
from .mine_beam_sweeping import (
    SweepingShip, BeamSweepSequence, BeamMineSweepAbstain,
    simulate_isolated_standard_beam_sweeps, _validate_fields, _map_for_keys,
)
from .mine_fighter_sweeping import (
    ColonialFighterSweeper, FighterSweepSequence, ColonialFighterSweepAbstain,
    simulate_isolated_colonial_fighter_sweeping,
)
from .colonial_mixed_beam_fighter_sweep import (
    MixedColonialCarrier, MixedColonialSweepQuote, ColonialMixedSweepAbstain,
    quote_isolated_colonial_mixed_sweep,
)

EVIDENCE = "DOCUMENTED_ORDERED_CANONICAL_SHIP_SWEEPS_TESTED_CONDITIONAL_NOT_HOST_VERIFIED"
BEAM_ONLY = "BEAM_ONLY"
COLONIAL_FIGHTERS_ONLY = "COLONIAL_FIGHTERS_ONLY"
COLONIAL_MIXED = "COLONIAL_MIXED"
MAX_SHIPS = 100
MAX_ID = 2_147_483_647


class OrderedShipMineSweepAbstain(ValueError):
    """Unsupported ship class, roster/provenance gap or uncertain web edge."""


@dataclass(frozen=True, slots=True)
class OrderedShipSweepStep:
    ship_id: int
    mode: str
    fields_before: tuple[LocatedMinefield, ...]
    fields_after: tuple[LocatedMinefield, ...]
    units_before: int
    units_after: int
    units_swept: int
    underlying_conditional_report: (
        BeamSweepSequence | FighterSweepSequence | MixedColonialSweepQuote
    )


@dataclass(frozen=True, slots=True)
class OrderedShipMineSweepLedger:
    steps: tuple[OrderedShipSweepStep, ...]
    initial_fields: tuple[LocatedMinefield, ...]
    final_hypothetical_fields: tuple[LocatedMinefield, ...]
    initial_units: int
    final_hypothetical_units: int
    total_hypothetical_units_swept: int
    evidence: str = EVIDENCE
    accepted_ship_missions_verified: bool = False
    actual_host_ship_sweep_stage_verified: bool = False
    exact_race_entitlement_from_host_verified: bool = False
    actual_field_roster_mutated: bool = False
    host_diff_verified: bool = False


def quote_ordered_isolated_ship_mine_sweeps(
    *,
    fields_pre_ship_stage: Sequence[LocatedMinefield],
    ships: Sequence[SweepingShip | ColonialFighterSweeper | MixedColonialCarrier],
    enemy_by_ship_field_id: Mapping[tuple[int, int], bool],
    ion_storm_contains_field_center_by_id: Mapping[int, bool],
    standard_web_beam_yield_by_field_id: Mapping[int, bool],
    colonial_entitlement_by_ship_id: Mapping[int, bool],
    max_radius: int,
    complete_pre_ship_field_and_ship_roster_confirmed: bool,
    exact_ship_identity_loadouts_missions_and_positions_confirmed: bool,
    all_fighter_carriers_colonial_and_advantage_confirmed: bool,
    complete_enemy_diplomacy_ion_and_web_rate_context_confirmed: bool,
    ship_id_phase_order_and_no_interleaving_confirmed: bool,
    no_msc_scooping_starbase_or_custom_mechanics_confirmed: bool,
) -> OrderedShipMineSweepLedger:
    """Strictly typed, chronological and immutable *conditional* ledger."""
    if any(x is not True for x in (
        complete_pre_ship_field_and_ship_roster_confirmed,
        exact_ship_identity_loadouts_missions_and_positions_confirmed,
        all_fighter_carriers_colonial_and_advantage_confirmed,
        complete_enemy_diplomacy_ion_and_web_rate_context_confirmed,
        ship_id_phase_order_and_no_interleaving_confirmed,
        no_msc_scooping_starbase_or_custom_mechanics_confirmed,
    )):
        raise OrderedShipMineSweepAbstain("missing source/phase/Colonial entitlement")
    if type(max_radius) is not int or max_radius not in (100, 150):
        raise OrderedShipMineSweepAbstain("unsupported field radius")
    if not isinstance(ships, (list, tuple)) or not 1 <= len(ships) <= MAX_SHIPS:
        raise OrderedShipMineSweepAbstain("complete bounded nonempty ship roster required")

    identities: set[int] = set()
    modes: dict[int, str] = {}
    for ship in ships:
        if type(ship) is SweepingShip:
            mode = BEAM_ONLY
        elif type(ship) is ColonialFighterSweeper:
            mode = COLONIAL_FIGHTERS_ONLY
        elif type(ship) is MixedColonialCarrier:
            mode = COLONIAL_MIXED
        else:
            raise OrderedShipMineSweepAbstain("uncategorized or invalid ship loadout")
        if (
            type(ship.ship_id) is not int
            or not 1 <= ship.ship_id <= MAX_ID
            or ship.ship_id in identities
        ):
            raise OrderedShipMineSweepAbstain("invalid or duplicate Ship ID across modes")
        identities.add(ship.ship_id)
        modes[ship.ship_id] = mode

    try:
        initial = _validate_fields(fields_pre_ship_stage, max_radius=max_radius)
        field_ids = {f.field_id for f in initial}
        enemy = _map_for_keys(
            enemy_by_ship_field_id,
            {(ship_id, field_id) for ship_id in identities for field_id in field_ids},
            label="all original ship/field enemies", pair_keys=True,
        )
        ion = _map_for_keys(
            ion_storm_contains_field_center_by_id, field_ids, label="all original ion centers",
        )
        web = _map_for_keys(
            standard_web_beam_yield_by_field_id,
            {f.field_id for f in initial if f.is_web},
            label="all original web rates",
        )
        colonial = _map_for_keys(
            colonial_entitlement_by_ship_id,
            {sid for sid in identities if modes[sid] != BEAM_ONLY},
            label="Colonial fighter entitlement",
        )
    except BeamMineSweepAbstain as exc:
        raise OrderedShipMineSweepAbstain(f"incomplete/untyped source context: {exc}") from exc
    if not all(web.values()) or not all(colonial.values()):
        raise OrderedShipMineSweepAbstain("unconfirmed standard web or Colonial entitlement")
    for ship in ships:
        for f in initial:
            if ship.owner_id == f.owner_id and enemy[(ship.ship_id, f.field_id)]:
                raise OrderedShipMineSweepAbstain("own field marked enemy")

    current = initial
    ordered_steps: list[OrderedShipSweepStep] = []
    for ship in sorted(ships, key=lambda s: s.ship_id):
        before = current
        live_ids = {f.field_id for f in before}
        live_enemy = {
            (ship.ship_id, field_id): enemy[(ship.ship_id, field_id)]
            for field_id in live_ids
        }
        live_ion = {key: val for key, val in ion.items() if key in live_ids}
        live_web = {key: val for key, val in web.items() if key in live_ids}
        mode = modes[ship.ship_id]
        try:
            if mode == BEAM_ONLY:
                report = simulate_isolated_standard_beam_sweeps(
                    fields=before, ships=(ship,),
                    confirmed_enemy_by_ship_field=live_enemy,
                    ion_storm_contains_field_center_by_id=live_ion,
                    standard_web_beam_yield_confirmed_by_field_id=live_web,
                    max_radius=max_radius,
                    complete_pre_sweep_field_and_ship_rosters_confirmed=True,
                    exact_beam_loadouts_and_positions_confirmed=True,
                    complete_diplomacy_and_ion_context_confirmed=True,
                    isolated_beam_sweep_only_confirmed=True,
                    standard_no_custom_modifiers_confirmed=True,
                )
                after = report.fields_final
                swept = report.total_units_swept
            elif mode == COLONIAL_FIGHTERS_ONLY:
                report = simulate_isolated_colonial_fighter_sweeping(
                    fields=before, ships=(ship,),
                    confirmed_enemy_by_ship_field=live_enemy,
                    max_radius=max_radius,
                    full_presweep_field_ship_rosters_confirmed=True,
                    colonial_race_and_advantage_confirmed=True,
                    exact_fighters_positions_and_mission_confirmed=True,
                    fighter_only_no_beams_scoop_or_starbase_confirmed=True,
                    ordinary_unmodified_minefields_confirmed=True,
                    independent_host_phase_not_claimed=True,
                )
                after = report.fields_final
                swept = report.total_units_destroyed
            else:
                report = quote_isolated_colonial_mixed_sweep(
                    carrier=ship,
                    fields_before_carrier_sweep=before,
                    enemy_by_field_id={fid:enemy[(ship.ship_id, fid)] for fid in live_ids},
                    ion_storm_contains_field_center_by_id=live_ion,
                    standard_web_beam_yield_by_field_id=live_web,
                    max_radius=max_radius,
                    missing_colonies_race_and_fighter_advantage_confirmed=True,
                    exact_beams_fighters_mission_and_position_confirmed=True,
                    complete_pre_carrier_field_roster_confirmed=True,
                    complete_diplomacy_ion_and_web_rate_context_confirmed=True,
                    isolated_single_carrier_no_msc_or_starbase_confirmed=True,
                    standard_no_custom_modifiers_confirmed=True,
                )
                after = report.fields_hypothetically_after
                swept = report.hypothetically_destroyed_mine_units
        except (
            BeamMineSweepAbstain, ColonialFighterSweepAbstain,
            ColonialMixedSweepAbstain,
        ) as exc:
            raise OrderedShipMineSweepAbstain(
                f"Ship ID {ship.ship_id} ({mode}) refused: {exc}"
            ) from exc

        if not {f.field_id for f in after}.issubset(live_ids):
            raise OrderedShipMineSweepAbstain("later step introduced a new field identity")
        known = {f.field_id: f for f in before}
        for f in after:
            pre = known[f.field_id]
            if (
                (f.owner_id, f.center, f.is_web) != (pre.owner_id, pre.center, pre.is_web)
                or f.mine_units > pre.mine_units
            ):
                raise OrderedShipMineSweepAbstain("a ship step changed field identity or increased mines")

        units_before = sum(f.mine_units for f in before)
        units_after = sum(f.mine_units for f in after)
        if units_before != units_after + swept:
            raise OrderedShipMineSweepAbstain("per-ship mine-unit conservation mismatch")
        ordered_steps.append(OrderedShipSweepStep(
            ship.ship_id, mode, before, after,
            units_before, units_after, swept, report,
        ))
        current = after
    units_initial = sum(f.mine_units for f in initial)
    units_final = sum(f.mine_units for f in current)
    swept_total = sum(x.units_swept for x in ordered_steps)
    if units_initial != units_final + swept_total:
        raise OrderedShipMineSweepAbstain("global mine-unit conservation mismatch")
    return OrderedShipMineSweepLedger(
        steps=tuple(ordered_steps),
        initial_fields=initial,
        final_hypothetical_fields=current,
        initial_units=units_initial,
        final_hypothetical_units=units_final,
        total_hypothetical_units_swept=swept_total,
    )
