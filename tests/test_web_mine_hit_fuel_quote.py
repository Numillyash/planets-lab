"""No real Host run: fractional and fuel-capacity boundaries are fail-closed."""
from dataclasses import FrozenInstanceError
import pytest
from planets_lab.rules.web_mine_hit_fuel_quote import (
    EVIDENCE, WebMineImpactFuelAbstain, quote_exact_single_web_mine_hit_fuel,
)

def quote(*, start=240, before=None, journey=75, tow=False, **changes):
    args=dict(
        start_of_turn_neutronium_kt=start,
        pre_movement_neutronium_kt=start if before is None else before,
        scheduled_journey_fuel_kt=journey,
        ship_under_tow=tow,
        web_field_is_enemy_and_impact_eligible_confirmed=True,
        single_web_impact_only_without_any_other_fuel_effect_confirmed=True,
        exact_start_of_turn_and_pre_movement_fuel_confirmed=True,
        scheduled_full_journey_fuel_from_independent_model_confirmed=True,
        ordinary_no_custom_or_racial_impact_modifiers_confirmed=True,
        no_prior_fuel_changes_or_web_drain_confirmed=True,
    )
    args.update(changes)
    return quote_exact_single_web_mine_hit_fuel(**args)

@pytest.mark.parametrize("start,journey,penalty,remaining,basis",[
    (50,0,50,0,"FIXED_MINIMUM_50_KT"),
    (240,75,50,115,"FIXED_MINIMUM_50_KT"),
    (299,100,50,149,"FIXED_MINIMUM_50_KT"),
    (300,50,50,200,"FIXED_MINIMUM_50_KT"),
    (306,50,51,205,"EXACT_ONE_SIXTH"),
    (600,120,100,380,"EXACT_ONE_SIXTH"),
    (900,300,150,450,"EXACT_ONE_SIXTH"),
])
def test_exact_boundaries(start,journey,penalty,remaining,basis):
    r=quote(start=start,journey=journey)
    assert r.shield_burn_neutronium_kt==penalty
    assert r.hypothetical_total_impact_related_fuel_used_kt==journey+penalty
    assert r.hypothetical_remaining_neutronium_kt==remaining
    assert r.shield_burn_basis==basis
    assert r.start_of_turn_neutronium_kt==r.hypothetical_total_impact_related_fuel_used_kt+remaining
    assert r.stopped_at_warp_zero_if_hit
    assert r.evidence==EVIDENCE
    assert not r.scheduled_movement_calculated and not r.host_diff_verified
    assert not r.actual_web_mine_hit_verified
    assert not r.out_of_fuel_mission_effect_calculated

@pytest.mark.parametrize("start", [301,302,303,304,305,307,311,599,1000000])
def test_fractional_sixth_abstains(start):
    with pytest.raises(WebMineImpactFuelAbstain,match="fractional"):
        quote(start=start,journey=0)

@pytest.mark.parametrize("start,journey",[(0,0),(49,0),(50,1),(60,20),(306,256),(300,300)])
def test_unsupported_clipping_or_no_shield_fuel_abstains(start,journey):
    with pytest.raises(WebMineImpactFuelAbstain,match="insufficient"):
        quote(start=start,journey=journey)

@pytest.mark.parametrize("bad", [
    {"tow":True},
    {"ship_under_tow":None},
    {"start":True},
    {"start":-1},
    {"start":1000001},
    {"start":100.0},
    {"start":"300"},
    {"before":200},
    {"journey":True},
    {"journey":-1},
    {"journey":1000001},
    {"journey":1000},
    {"web_field_is_enemy_and_impact_eligible_confirmed":False},
    {"single_web_impact_only_without_any_other_fuel_effect_confirmed":None},
    {"exact_start_of_turn_and_pre_movement_fuel_confirmed":1},
    {"scheduled_full_journey_fuel_from_independent_model_confirmed":False},
    {"ordinary_no_custom_or_racial_impact_modifiers_confirmed":False},
    {"no_prior_fuel_changes_or_web_drain_confirmed":False},
])
def test_malformed_or_unproven_inputs_abstain(bad):
    with pytest.raises(WebMineImpactFuelAbstain):
        quote(**bad)

def test_immutable_and_no_host_mutation():
    a=quote()
    assert quote()==a
    with pytest.raises(FrozenInstanceError):
        a.hypothetical_remaining_neutronium_kt=0
    assert not a.actual_fuel_inventory_mutated
    assert not a.web_drain_phase_executed
    assert not a.waypoint_or_actual_position_calculated
    assert not a.host_phase_verified
