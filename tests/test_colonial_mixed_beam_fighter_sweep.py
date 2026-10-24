"""One mixed Colonial carrier; independent beam/fighter potentials, no Host attribution."""
from dataclasses import FrozenInstanceError
from math import isqrt

import pytest

from planets_lab.rules.minefield_placement_candidate import LocatedMinefield, Point
from planets_lab.rules.mine_beam_sweeping import STANDARD_BEAM_SWEEP_YIELDS
from planets_lab.rules.colonial_mixed_beam_fighter_sweep import (
    EVIDENCE, ColonialMixedSweepAbstain, MixedColonialCarrier,
    quote_isolated_colonial_mixed_sweep,
)


def field(fid=11, *, owner=2, x=0, units=1000, web=False):
    return LocatedMinefield(fid, owner, Point(x,0), units, web)


def carrier(*, sid=5, owner=1, x=0, beams=2, fighters=3,
            family="laser", mission="MINE_SWEEP", msc=False):
    return MixedColonialCarrier(
        sid, owner, Point(x,0), mission, family, beams, fighters, msc,
    )


def quote(*, ship=None, fields=None, enemy=None, ion=None, web_rates=None, **overrides):
    ship=carrier() if ship is None else ship
    fields=(field(),) if fields is None else fields
    ids=[f.field_id for f in fields if type(f) is LocatedMinefield] if isinstance(fields,(tuple,list)) else []
    args=dict(
        carrier=ship,
        fields_before_carrier_sweep=fields,
        enemy_by_field_id=(
            {f.field_id:f.owner_id!=ship.owner_id for f in fields
             if type(f) is LocatedMinefield} if enemy is None and isinstance(fields,(tuple,list))
            and type(ship) is MixedColonialCarrier else enemy if enemy is not None else {}
        ),
        ion_storm_contains_field_center_by_id=(
            dict.fromkeys(ids, False) if ion is None else ion
        ),
        standard_web_beam_yield_by_field_id=(
            {f.field_id:True for f in fields if type(f) is LocatedMinefield and f.is_web is True}
            if web_rates is None and isinstance(fields,(tuple,list))
            else web_rates if web_rates is not None else {}
        ),
        max_radius=150,
        missing_colonies_race_and_fighter_advantage_confirmed=True,
        exact_beams_fighters_mission_and_position_confirmed=True,
        complete_pre_carrier_field_roster_confirmed=True,
        complete_diplomacy_ion_and_web_rate_context_confirmed=True,
        isolated_single_carrier_no_msc_or_starbase_confirmed=True,
        standard_no_custom_modifiers_confirmed=True,
    )
    args.update(overrides)
    return quote_isolated_colonial_mixed_sweep(**args)


def test_mixed_laser_and_fighters_same_field_simultaneous_potential():
    r=quote()
    f=r.field_quotes[0]
    assert f.beam_channel_status=="BEAMS_IN_RANGE"
    assert f.fighter_channel_status=="FIGHTERS_IN_RANGE"
    assert f.beam_potential_mine_units==8
    assert f.fighter_potential_mine_units==60
    assert f.combined_potential_mine_units==68
    assert f.total_hypothetical_mines_destroyed==68
    assert f.hypothetical_mines_remaining==932
    assert f.pre_step_integer_radius==31
    assert not f.channel_attribution_verified
    assert r.evidence==EVIDENCE
    assert r.initially_present_mine_units==1000
    assert r.hypothetically_destroyed_mine_units==68
    assert r.hypothetically_remaining_mine_units==932
    assert not r.host_diff_verified
    assert not r.actual_mission_accepted_verified
    assert not r.actual_beam_fighter_host_simultaneity_verified
    assert not r.actual_minefield_state_mutated


def test_overkill_capped_by_field_units_no_speculative_attribution():
    r=quote(fields=(field(units=40),))
    f=r.field_quotes[0]
    assert f.beam_potential_mine_units==8
    assert f.fighter_potential_mine_units==60
    assert f.combined_potential_mine_units==68
    assert f.total_hypothetical_mines_destroyed==40
    assert f.hypothetical_mines_remaining==0
    assert f.channel_attribution_verified is False
    assert r.fields_hypothetically_after==()
    assert r.hypothetically_remaining_mine_units==0


@pytest.mark.parametrize("family,normal,web",[
    (name, rate[0], rate[1])
    for name,rate in STANDARD_BEAM_SWEEP_YIELDS.items()
])
def test_all_standard_beam_families_with_normal_and_web_fields(family,normal,web):
    c=carrier(family=family,beams=1,fighters=1)
    a=quote(ship=c,fields=(field(units=10000),))
    af=a.field_quotes[0]
    assert af.beam_potential_mine_units==normal
    assert af.fighter_potential_mine_units==20
    assert af.combined_potential_mine_units==normal+20
    b=quote(ship=c,fields=(field(units=10000,web=True),))
    bf=b.field_quotes[0]
    assert bf.beam_potential_mine_units==web
    assert bf.fighter_potential_mine_units==0
    assert bf.fighter_channel_status=="WEB_IMMUNE_TO_FIGHTERS"
    assert bf.total_hypothetical_mines_destroyed==web


def test_ion_storm_blocks_only_beams_colonial_fighters_still_sweep():
    r=quote(ion={11:True})
    f=r.field_quotes[0]
    assert f.beam_channel_status=="ION_BLOCKED"
    assert f.beam_potential_mine_units==0
    assert f.fighter_channel_status=="FIGHTERS_IN_RANGE"
    assert f.fighter_potential_mine_units==60
    assert r.hypothetically_destroyed_mine_units==60


def test_web_ion_storm_prevents_beam_and_web_is_immune_to_fighters():
    r=quote(fields=(field(web=True),),ion={11:True})
    f=r.field_quotes[0]
    assert f.beam_channel_status=="ION_BLOCKED"
    assert f.fighter_channel_status=="WEB_IMMUNE_TO_FIGHTERS"
    assert r.hypothetically_destroyed_mine_units==0


def test_fighter_only_at_long_range_and_beam_only_web_at_short_range():
    a=quote(fields=(field(units=100,x=110),))
    assert a.field_quotes[0].beam_channel_status=="BEAMS_OUT_OF_RANGE"
    assert a.field_quotes[0].fighter_channel_status=="FIGHTERS_IN_RANGE"
    assert a.hypothetically_destroyed_mine_units==60
    b=quote(fields=(field(units=100,x=111),))
    assert b.hypothetically_destroyed_mine_units==0
    w=quote(fields=(field(web=True,units=100),),ship=carrier(x=10))
    assert w.field_quotes[0].beam_potential_mine_units==6
    assert w.field_quotes[0].fighter_potential_mine_units==0


def test_web_pre_decay_near_edge_abstains_not_guessed():
    with pytest.raises(ColonialMixedSweepAbstain,match="web beam near-edge"):
        quote(fields=(field(web=True,units=100,x=11),))
    a=quote(fields=(field(web=True,units=100,x=12),))
    assert a.hypothetically_destroyed_mine_units==0


def test_full_field_roster_own_field_non_enemy_distant_and_web():
    fs=(field(31,owner=1,units=50),
        field(9,owner=2,x=0,units=400),
        field(11,owner=2,x=1000,units=100),
        field(25,owner=2,x=0,units=400,web=True))
    r=quote(fields=fs)
    assert [f.field_id for f in r.field_quotes]==[9,11,25,31]
    assert [f.total_hypothetical_mines_destroyed for f in r.field_quotes]==[68,0,6,0]
    assert r.initially_present_mine_units==950
    assert r.hypothetically_remaining_mine_units==876
    assert r.initially_present_mine_units==r.hypothetically_remaining_mine_units+r.hypothetically_destroyed_mine_units


def test_input_permutation_unchanged_immutable():
    fs=[field(30,owner=1),field(3,units=300),field(20,units=100,web=True)]
    a=quote(fields=fs)
    b=quote(fields=list(reversed(fs)))
    assert a==b
    assert fs[1].mine_units==300
    with pytest.raises(FrozenInstanceError):
        a.hypothetically_destroyed_mine_units=10
    with pytest.raises(FrozenInstanceError):
        a.field_quotes[0].fighter_potential_mine_units=0


def test_empty_source_fields_has_no_effect_but_does_not_verify_host():
    r=quote(fields=())
    assert r.field_quotes==()
    assert r.initially_present_mine_units==0
    assert not r.host_phase_order_verified


@pytest.mark.parametrize("bad",[
    {"ship":carrier(msc=True)},
    {"ship":carrier(mission="EXPLORE")},
    {"ship":carrier(family="unknown")},
    {"ship":carrier(beams=0)},
    {"ship":carrier(fighters=0)},
    {"ship":carrier(beams=True)},
    {"ship":carrier(fighters=True)},
    {"ship":carrier(sid=True)},
    {"ship":carrier(owner=True)},
    {"ship":carrier(x=True)},
    {"ship":carrier(x=1000001)},
    {"fields":(field(11),field(11))},
    {"fields":(field(units=0),)},
    {"fields":(field(units=True),)},
    {"fields":(field(web=1),)},
    {"fields":(field(units=10001),),"max_radius":100},
    {"enemy":{}},
    {"enemy":{11:1}},
    {"enemy":{11:True,12:True}},
    {"enemy":{True:True}},
    {"ion":{}},
    {"ion":{11:1}},
    {"web_rates":{11:True}},
    {"fields":(field(web=True),),"web_rates":{11:False}},
    {"fields":(field(owner=1),),"enemy":{11:True}},
    {"max_radius":True},
    {"max_radius":101},
    {"missing_colonies_race_and_fighter_advantage_confirmed":False},
    {"exact_beams_fighters_mission_and_position_confirmed":1},
    {"complete_pre_carrier_field_roster_confirmed":None},
    {"complete_diplomacy_ion_and_web_rate_context_confirmed":False},
    {"isolated_single_carrier_no_msc_or_starbase_confirmed":False},
    {"standard_no_custom_modifiers_confirmed":False},
])
def test_incompatible_or_unverified_fails_closed(bad):
    with pytest.raises(ColonialMixedSweepAbstain):
        quote(**bad)


def test_untyped_none_objects_rejected_at_api_not_implicitly_defaulted():
    with pytest.raises(ColonialMixedSweepAbstain):
        quote_isolated_colonial_mixed_sweep(
            carrier=None,fields_before_carrier_sweep=None,
            enemy_by_field_id={},ion_storm_contains_field_center_by_id={},
            standard_web_beam_yield_by_field_id={},max_radius=150,
            missing_colonies_race_and_fighter_advantage_confirmed=True,
            exact_beams_fighters_mission_and_position_confirmed=True,
            complete_pre_carrier_field_roster_confirmed=True,
            complete_diplomacy_ion_and_web_rate_context_confirmed=True,
            isolated_single_carrier_no_msc_or_starbase_confirmed=True,
            standard_no_custom_modifiers_confirmed=True,
        )
