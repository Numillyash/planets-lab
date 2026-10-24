"""Bounded exact-only web mine impact fuel quote; NEVER actual Host movement.

Source: https://help.planets.nu/minefields (Web Mines → Mine Impact)
A web hit consumes scheduled journey fuel AND additional
max(50 KT, 1/6 of fuel at START OF TURN). Fractional 1/6 rounding is
undocumented, so the calculator REFUSES (>300 and nonmultiple of 6).
No RNG, field collision, web drain, real path, waypoint or Host state.
"""
from __future__ import annotations
from dataclasses import dataclass

EVIDENCE = "DOCUMENTED_WEB_HIT_FUEL_EXACT_SUBSET_TESTED_CONDITIONAL_NOT_HOST_VERIFIED"
MAX_FUEL_KT = 1_000_000   # arithmetic guard, NOT a Host tank-size limit


class WebMineImpactFuelAbstain(ValueError):
    """Unproven scheduled fuel, fractional rounding or phase interaction."""


@dataclass(frozen=True, slots=True)
class WebMineHitFuelQuote:
    start_of_turn_neutronium_kt: int
    pre_movement_neutronium_kt: int
    externally_confirmed_scheduled_journey_fuel_kt: int
    shield_burn_neutronium_kt: int
    hypothetical_total_impact_related_fuel_used_kt: int
    hypothetical_remaining_neutronium_kt: int
    shield_burn_basis: str
    stopped_at_warp_zero_if_hit: bool = True
    evidence: str = EVIDENCE
    scheduled_movement_calculated: bool = False
    impact_random_draw_performed: bool = False
    actual_web_mine_hit_verified: bool = False
    actual_fuel_inventory_mutated: bool = False
    waypoint_or_actual_position_calculated: bool = False
    out_of_fuel_mission_effect_calculated: bool = False
    web_drain_phase_executed: bool = False
    host_phase_verified: bool = False
    host_diff_verified: bool = False


def quote_exact_single_web_mine_hit_fuel(
    *,
    start_of_turn_neutronium_kt: int,
    pre_movement_neutronium_kt: int,
    scheduled_journey_fuel_kt: int,
    ship_under_tow: bool,
    web_field_is_enemy_and_impact_eligible_confirmed: bool,
    single_web_impact_only_without_any_other_fuel_effect_confirmed: bool,
    exact_start_of_turn_and_pre_movement_fuel_confirmed: bool,
    scheduled_full_journey_fuel_from_independent_model_confirmed: bool,
    ordinary_no_custom_or_racial_impact_modifiers_confirmed: bool,
    no_prior_fuel_changes_or_web_drain_confirmed: bool,
) -> WebMineHitFuelQuote:
    """Conditional exact arithmetic only; caller flags are not Host receipts."""
    if any(x is not True for x in (
        web_field_is_enemy_and_impact_eligible_confirmed,
        single_web_impact_only_without_any_other_fuel_effect_confirmed,
        exact_start_of_turn_and_pre_movement_fuel_confirmed,
        scheduled_full_journey_fuel_from_independent_model_confirmed,
        ordinary_no_custom_or_racial_impact_modifiers_confirmed,
        no_prior_fuel_changes_or_web_drain_confirmed,
    )):
        raise WebMineImpactFuelAbstain("unverified impact, schedule, fuel or phase isolation")
    if type(ship_under_tow) is not bool or ship_under_tow:
        raise WebMineImpactFuelAbstain("towed ship or unknown tow context cannot suffer web hit")
    if not all(
        type(v) is int and 0 <= v <= MAX_FUEL_KT
        for v in (
            start_of_turn_neutronium_kt,
            pre_movement_neutronium_kt,
            scheduled_journey_fuel_kt,
        )
    ):
        raise WebMineImpactFuelAbstain("invalid or unbounded fuel")
    if start_of_turn_neutronium_kt != pre_movement_neutronium_kt:
        raise WebMineImpactFuelAbstain("prior fuel mutations outside isolated quote")
    if scheduled_journey_fuel_kt > pre_movement_neutronium_kt:
        raise WebMineImpactFuelAbstain("infeasible scheduled journey fuel")
    if start_of_turn_neutronium_kt <= 300:
        # 1/6 <= 50 including all fractional values: no rounding matters.
        penalty, basis = 50, "FIXED_MINIMUM_50_KT"
    elif start_of_turn_neutronium_kt % 6 == 0:
        penalty, basis = start_of_turn_neutronium_kt // 6, "EXACT_ONE_SIXTH"
    else:
        raise WebMineImpactFuelAbstain("undocumented fractional one-sixth rounding")
    total = scheduled_journey_fuel_kt + penalty
    if total > pre_movement_neutronium_kt:
        raise WebMineImpactFuelAbstain(
            "insufficient fuel for full movement plus shield burn; clipping unsupported"
        )
    remainder = pre_movement_neutronium_kt - total
    if remainder + total != start_of_turn_neutronium_kt:
        raise WebMineImpactFuelAbstain("isolated fuel conservation mismatch")
    return WebMineHitFuelQuote(
        start_of_turn_neutronium_kt=start_of_turn_neutronium_kt,
        pre_movement_neutronium_kt=pre_movement_neutronium_kt,
        externally_confirmed_scheduled_journey_fuel_kt=scheduled_journey_fuel_kt,
        shield_burn_neutronium_kt=penalty,
        hypothetical_total_impact_related_fuel_used_kt=total,
        hypothetical_remaining_neutronium_kt=remainder,
        shield_burn_basis=basis,
    )
