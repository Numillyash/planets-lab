"""Synthetic-only post-decay Crystal web drain quotes, never a Host turn."""
from dataclasses import FrozenInstanceError

import pytest

from planets_lab.rules.minefield_placement_candidate import LocatedMinefield, Point
from planets_lab.rules.web_drain_isolated_quote import (
    EVIDENCE, WebDrainQuoteAbstain, quote_isolated_crystal_web_drain,
)

def f(fid=10, owner=7, *, x=0, y=0, units=100, web=True):
    return LocatedMinefield(fid, owner, Point(x, y), units, web)

def quote(*, fields=None, ship=Point(0,0), fuel=100, mission="MINE_SWEEP",
          enemy=None, crystal=None, **overrides):
    fields=(f(),) if fields is None else fields
    web=tuple(item for item in fields if type(item) is LocatedMinefield and item.is_web is True) if isinstance(fields,(list,tuple)) else ()
    args=dict(
        ship_owner_id=1,
        ship_position=ship,
        neutronium_before_kt=fuel,
        ship_mission=mission,
        fields_post_decay=fields,
        enemy_web_by_field_id=({item.field_id:item.owner_id!=1 for item in web} if enemy is None else enemy),
        crystal_owner_by_owner_id=({item.owner_id:True for item in web} if crystal is None else crystal),
        max_radius=150,
        complete_post_decay_field_roster_confirmed=True,
        exact_post_decay_geometry_confirmed=True,
        full_diplomacy_friendly_code_and_web_entitlement_confirmed=True,
        no_other_prior_or_simultaneous_fuel_events_confirmed=True,
        ordinary_no_custom_or_terrain_modifiers_confirmed=True,
        exact_fuel_and_mission_before_drain_confirmed=True,
    )
    args.update(overrides)
    return quote_isolated_crystal_web_drain(**args)

def test_one_crystal_web_field_costs_25_with_no_server_claims():
    r=quote()
    assert r.qualifying_post_decay_web_field_ids==(10,)
    assert r.web_fields_in_source_roster==1
    assert r.requested_drain_neutronium_kt==25
    assert r.hypothetical_neutronium_after_kt==75
    assert r.hypothetical_mission_after=="MINE_SWEEP"
    assert r.evidence==EVIDENCE
    assert not r.host_diff_verified and not r.host_phase_order_verified
    assert not r.ship_fuel_mutated and not r.mission_actually_reset
    assert not r.web_mine_impact_calculated

def test_multiple_crystal_web_fields_stack_exactly_and_are_sorted():
    fields=(f(80, 9, x=2), f(10, 7), f(30, 8, x=0))
    r=quote(fields=fields, fuel=100)
    assert r.qualifying_post_decay_web_field_ids==(10,30,80)
    assert r.requested_drain_neutronium_kt==75
    assert r.hypothetical_neutronium_after_kt==25
    assert quote(fields=list(reversed(fields)),fuel=100)==r

def test_web_owned_by_noncrystal_does_not_drain_and_normal_ignored():
    fields=(f(10), f(20, 9, web=True), f(30, 9, web=False))
    r=quote(fields=fields, crystal={7:True,9:False})
    assert r.qualifying_post_decay_web_field_ids==(10,)
    assert r.web_fields_in_source_roster==2
    assert r.requested_drain_neutronium_kt==25

def test_same_owner_and_passage_does_not_drain():
    fields=(f(10,1),f(20,7))
    r=quote(fields=fields,enemy={10:False,20:False},crystal={1:True,7:True})
    assert r.requested_drain_neutronium_kt==0
    assert r.hypothetical_neutronium_after_kt==100
    with pytest.raises(WebDrainQuoteAbstain,match="own web"):
        quote(fields=fields,enemy={10:True,20:False},crystal={1:True,7:True})

def test_inside_integer_postdecay_circle_and_far_outside_only():
    fields=(f(units=100),) # radius10
    assert quote(fields=fields,ship=Point(10,0)).requested_drain_neutronium_kt==25
    r=quote(fields=fields,ship=Point(12,0))
    assert r.requested_drain_neutronium_kt==0
    with pytest.raises(WebDrainQuoteAbstain,match="near-edge"):
        quote(fields=fields,ship=Point(11,0))

@pytest.mark.parametrize("mission,expected,reset",[
    ("MINE_SWEEP","EXPLORE",True),
    ("CLOAK","EXPLORE",True),
    ("EXPLORE","EXPLORE",True),
    ("BEAM_UP_FUEL","BEAM_UP_FUEL",False),
])
def test_fuel_to_zero_resets_mission_except_beam_up_fuel(mission,expected,reset):
    r=quote(fuel=25,mission=mission)
    assert r.hypothetical_neutronium_after_kt==0
    assert r.hypothetical_mission_after==expected
    assert r.mission_would_reset_if_executed==reset
    assert r.mission_actually_reset is False

def test_no_qualifying_web_does_not_reset_zero_fuel_mission():
    r=quote(fields=(),fuel=0)
    assert r.requested_drain_neutronium_kt==0
    assert r.hypothetical_mission_after=="MINE_SWEEP"
    assert not r.mission_would_reset_if_executed

def test_clipping_abstains_instead_of_assuming_host_saturation():
    for fuel in (0,1,24):
        with pytest.raises(WebDrainQuoteAbstain,match="insufficient"):
            quote(fuel=fuel)
    with pytest.raises(WebDrainQuoteAbstain,match="insufficient"):
        quote(fields=(f(10),f(20,8)),fuel=49)

def test_determinism_and_immutable_no_mutations():
    fields=[f(),f(20,9,x=200)]
    r=quote(fields=fields)
    assert r==quote(fields=list(reversed(fields)))
    assert fields[0].mine_units==100
    with pytest.raises(FrozenInstanceError):
        r.requested_drain_neutronium_kt=500

@pytest.mark.parametrize("bad",[
    {"fields":"wrong"},
    {"fields":(f(),f())},
    {"fields":(f(units=0),)},
    {"fields":(f(units=22501),)},
    {"fields":(f(web=1),)},
    {"fields":(f(owner=True),)},
    {"ship_owner_id":True},
    {"ship":Point(True,0)},
    {"ship":(0,0)},
    {"fuel":True},
    {"fuel":-1},
    {"fuel":1_000_001},
    {"mission":"UNKNOWN_MISSION"},
    {"mission":None},
    {"max_radius":True},
    {"max_radius":101},
    {"enemy":{}},
    {"enemy":{10:1}},
    {"enemy":{True:True}},
    {"enemy":{10:True,20:True}},
    {"crystal":{}},
    {"crystal":{7:1}},
    {"crystal":{True:True}},
    {"crystal":{7:True,8:True}},
    {"complete_post_decay_field_roster_confirmed":False},
    {"exact_post_decay_geometry_confirmed":1},
    {"full_diplomacy_friendly_code_and_web_entitlement_confirmed":None},
    {"no_other_prior_or_simultaneous_fuel_events_confirmed":False},
    {"ordinary_no_custom_or_terrain_modifiers_confirmed":False},
    {"exact_fuel_and_mission_before_drain_confirmed":False},
])
def test_invalid_source_or_unknown_mechanics_abstain(bad):
    with pytest.raises(WebDrainQuoteAbstain):
        quote(**bad)
