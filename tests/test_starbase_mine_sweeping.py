"""Synthetic Campaign starbase sweeps are only conditional arithmetic."""
from dataclasses import FrozenInstanceError
from math import isqrt

import pytest

from planets_lab.rules.minefield_placement_candidate import LocatedMinefield, Point
from planets_lab.rules.mine_beam_sweeping import STANDARD_BEAM_SWEEP_YIELDS
from planets_lab.rules.starbase_mine_sweeping import (
    EVIDENCE, SWEEP_ORDER, SweepingStarbase, StarbaseMineSweepAbstain,
    quote_isolated_campaign_starbase_mine_sweep,
)


def field(fid=20, owner=2, *, x=0, y=0, units=1000, web=False):
    return LocatedMinefield(fid, owner, Point(x, y), units, web)


def base(*, bid=4, owner=1, x=0, y=0, beam="laser", planet=1, defense=1,
         order=SWEEP_ORDER):
    return SweepingStarbase(bid, owner, Point(x, y), order, beam, planet, defense)


def calc(*, starbase=None, fields=None, enemy=None, ion=None, web_rate=None, **changes):
    starbase = base() if starbase is None else starbase
    fields = (field(),) if fields is None else fields
    if enemy is None:
        enemy = {
            f.field_id: f.owner_id != starbase.owner_id
            for f in fields if type(f) is LocatedMinefield
        } if isinstance(fields, (list, tuple)) and type(starbase) is SweepingStarbase else {}
    if ion is None:
        ion = {f.field_id: False for f in fields if type(f) is LocatedMinefield} if isinstance(fields, (list, tuple)) else {}
    if web_rate is None:
        web_rate = {f.field_id: True for f in fields if type(f) is LocatedMinefield and f.is_web is True} if isinstance(fields, (list, tuple)) else {}
    kw = dict(
        starbase=starbase, fields_post_ship_sweeps=fields,
        enemy_by_field_id=enemy,
        ion_storm_contains_field_center_by_id=ion,
        standard_web_beam_yield_by_field_id=web_rate,
        max_radius=150,
        campaign_and_advantage_enabled_confirmed=True,
        exact_starbase_beam_tech_and_both_defense_counts_confirmed=True,
        post_ship_pre_starbase_field_roster_complete_confirmed=True,
        complete_enemy_diplomacy_and_ion_storm_context_confirmed=True,
        exactly_one_starbase_and_no_concurrent_scooping_confirmed=True,
        ordinary_sweeping_no_special_campaign_modifiers_confirmed=True,
    )
    kw.update(changes)
    return quote_isolated_campaign_starbase_mine_sweep(**kw)


@pytest.mark.parametrize("family,normal,web", [
    (family, rates[0], rates[1]) for family, rates in STANDARD_BEAM_SWEEP_YIELDS.items()
])
def test_all_documented_beam_families_and_both_field_types(family, normal, web):
    for is_web, per_beam in ((False, normal), (True, web)):
        b = base(beam=family, planet=2, defense=3)
        r = calc(starbase=b, fields=(field(units=5000, web=is_web),))
        assert r.total_defensive_beams == 5
        assert r.hypothetical_destroyed_mine_units == 5 * per_beam
        assert r.field_quotes[0].beam_yield_per_weapon == per_beam
        assert r.field_quotes[0].mine_units_after_if_executed == 5000 - 5 * per_beam
        assert r.initial_mine_units == 5000
        assert r.evidence == EVIDENCE
        assert not r.host_diff_verified
        assert not r.real_host_advantage_activation_verified
        assert not r.real_host_order_accepted_verified


def test_highest_starbase_buildable_beam_technology_applies_to_planet_beams():
    # Planetary 9 beams plus starbase 1; all use highest-buildable heavy phaser.
    r = calc(starbase=base(beam="heavy_phaser", planet=9, defense=1),
             fields=(field(units=5000),))
    assert r.hypothetical_destroyed_mine_units == 4000
    assert r.field_quotes[0].mine_units_after_if_executed == 1000


def test_ion_block_and_non_enemy_do_not_mutate_selected_fields():
    fields=(field(9, owner=1, units=50), field(20, units=1000),
            field(30, x=100, units=1000))
    r=calc(fields=fields, ion={9:False,20:True,30:False})
    assert [(x.field_id,x.classification) for x in r.field_quotes] == [
        (9,"NOT_ENEMY"),(20,"ION_BLOCKED"),(30,"OUT_OF_RANGE"),
    ]
    assert r.hypothetical_destroyed_mine_units == 0
    assert [f.field_id for f in r.fields_hypothetically_after] == [9,20,30]


def test_full_field_depletion_and_conservation_across_multiple_targets():
    fields=(field(30, x=30, units=400), field(10, units=3),
            field(20, web=True, units=5))
    result=calc(fields=fields,starbase=base(beam="laser",planet=2,defense=0))
    assert [x.field_id for x in result.field_quotes] == [10,20,30]
    assert [x.mine_units_potentially_destroyed for x in result.field_quotes] == [3,5,0]
    assert [f.field_id for f in result.fields_hypothetically_after] == [30]
    assert result.hypothetical_destroyed_mine_units == 8
    assert result.initial_mine_units == 408
    assert result.initial_mine_units == result.hypothetical_remaining_mine_units+8
    assert result.field_quotes[0].radius_after_if_executed == 0


def test_normal_boundary_strictly_less_than_five_ly():
    r=calc(fields=(field(units=100,x=14),))
    assert r.field_quotes[0].classification == "SWEEPED"
    r=calc(fields=(field(units=100,x=15),))
    assert r.field_quotes[0].classification == "OUT_OF_RANGE"


def test_web_uses_presweep_circle_and_near_edge_abstains():
    assert calc(fields=(field(web=True,units=100,x=10),)).field_quotes[0].mine_units_potentially_destroyed == 6
    with pytest.raises(StarbaseMineSweepAbstain,match="web edge"):
        calc(fields=(field(web=True,units=100,x=11),))
    result=calc(fields=(field(web=True,units=100,x=12),))
    assert result.field_quotes[0].classification == "OUT_OF_RANGE"


def test_empty_field_roster_is_a_conditional_noop_not_a_real_host_receipt():
    result=calc(fields=())
    assert result.field_quotes == ()
    assert result.hypothetical_destroyed_mine_units == 0
    assert not result.actual_ship_sweeps_verified


def test_input_order_determinism_and_no_mutation():
    original=[field(9,x=30),field(2,units=3000,web=True)]
    r=calc(fields=original)
    assert r == calc(fields=list(reversed(original)))
    assert original[1].mine_units == 3000
    with pytest.raises(FrozenInstanceError):
        r.field_quotes[0].classification = "HOST_VERIFIED"
    assert not r.actual_field_roster_mutated
    assert not r.host_phase_order_verified
    assert not r.real_host_starbase_sweep_verified


@pytest.mark.parametrize("bad", [
    {"starbase":base(order="MINE_SWEEP")},
    {"starbase":base(order="EXPLORE")},
    {"starbase":base(beam="quantum")},
    {"starbase":base(planet=0,defense=0)},
    {"starbase":base(planet=-1)},
    {"starbase":base(planet=True)},
    {"starbase":base(defense=True)},
    {"starbase":base(planet=1999,defense=2)},
    {"starbase":base(bid=True)},
    {"starbase":base(owner=True)},
    {"starbase":base(x=True)},
    {"starbase":base(x=1000001)},
    {"starbase":None, "campaign_and_advantage_enabled_confirmed":False},
    {"campaign_and_advantage_enabled_confirmed":1},
    {"exact_starbase_beam_tech_and_both_defense_counts_confirmed":False},
    {"post_ship_pre_starbase_field_roster_complete_confirmed":None},
    {"complete_enemy_diplomacy_and_ion_storm_context_confirmed":0},
    {"exactly_one_starbase_and_no_concurrent_scooping_confirmed":False},
    {"ordinary_sweeping_no_special_campaign_modifiers_confirmed":False},
    {"max_radius":True},
    {"max_radius":200},
    {"fields":None},
    {"fields":(field(20),field(20))},
    {"fields":(field(units=0),)},
    {"fields":(field(units=10001),), "max_radius":100},
    {"fields":(field(web=1),)},
    {"enemy":{}},
    {"enemy":{20:1}},
    {"enemy":{20:True,30:True}},
    {"enemy":{True:True}},
    {"enemy":{20:False}, "fields":(field(owner=2),),
     "ion":{20:False}, "web_rate":{20:True}},
    {"ion":{}},
    {"ion":{20:1}},
    {"web_rate":{20:True}},
    {"fields":(field(web=True),), "web_rate":{20:False}},
    {"fields":(field(owner=1),), "enemy":{20:True}},
])
def test_invalid_or_unproven_source_fails_closed(bad):
    if bad.get("fields", "sentinel") is None:
        with pytest.raises(StarbaseMineSweepAbstain):
            quote_isolated_campaign_starbase_mine_sweep(
                starbase=base(),fields_post_ship_sweeps=None,
                enemy_by_field_id={},ion_storm_contains_field_center_by_id={},
                standard_web_beam_yield_by_field_id={},max_radius=150,
                campaign_and_advantage_enabled_confirmed=True,
                exact_starbase_beam_tech_and_both_defense_counts_confirmed=True,
                post_ship_pre_starbase_field_roster_complete_confirmed=True,
                complete_enemy_diplomacy_and_ion_storm_context_confirmed=True,
                exactly_one_starbase_and_no_concurrent_scooping_confirmed=True,
                ordinary_sweeping_no_special_campaign_modifiers_confirmed=True,
            )
    elif bad.get("starbase","sentinel") is None:
        with pytest.raises(StarbaseMineSweepAbstain):
            calc(**{**bad, "starbase":base()})
    else:
        with pytest.raises(StarbaseMineSweepAbstain):
            calc(**bad)
