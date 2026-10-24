"""Conditional ascending-ID minefield sweeping by three canonical ship variants."""
from dataclasses import FrozenInstanceError

import pytest

from planets_lab.rules.minefield_placement_candidate import LocatedMinefield, Point
from planets_lab.rules.mine_beam_sweeping import SweepingShip
from planets_lab.rules.mine_fighter_sweeping import ColonialFighterSweeper
from planets_lab.rules.colonial_mixed_beam_fighter_sweep import MixedColonialCarrier
from planets_lab.rules.ordered_ship_mine_sweeps import (
    BEAM_ONLY, COLONIAL_FIGHTERS_ONLY, COLONIAL_MIXED, EVIDENCE,
    OrderedShipMineSweepAbstain, quote_ordered_isolated_ship_mine_sweeps,
)


def field(fid=20, *, owner=2, x=0, units=1000, web=False):
    return LocatedMinefield(fid, owner, Point(x,0), units, web)


def beam(sid=3, *, owner=1, x=0, family="laser", count=1, msc=False):
    return SweepingShip(sid, owner, Point(x,0), family, count, "MINE_SWEEP", msc)


def fighter(sid=7, *, owner=1, x=0, count=2, beams=0):
    return ColonialFighterSweeper(sid, owner, Point(x,0), count, beams, "MINE_SWEEP")


def mixed(sid=9, *, owner=1, x=0, beams=1, fighters=1, family="laser", msc=False):
    return MixedColonialCarrier(
        sid, owner, Point(x,0), "MINE_SWEEP", family, beams, fighters, msc,
    )


def calc(*, fields=None, ships=None, enemy=None, ion=None, web=None,
         colonial=None, **flags):
    fields=(field(),) if fields is None else fields
    ships=(beam(),fighter(),mixed()) if ships is None else ships
    if enemy is None:
        enemy={(s.ship_id, f.field_id):s.owner_id!=f.owner_id for s in ships for f in fields} if isinstance(ships,(tuple,list)) and isinstance(fields,(tuple,list)) and all(hasattr(s,"owner_id") for s in ships) else {}
    if ion is None:
        ion={f.field_id:False for f in fields} if isinstance(fields,(tuple,list)) else {}
    if web is None:
        web={f.field_id:True for f in fields if type(f) is LocatedMinefield and f.is_web is True} if isinstance(fields,(tuple,list)) else {}
    if colonial is None:
        colonial={s.ship_id:True for s in ships
                  if type(s) in (ColonialFighterSweeper,MixedColonialCarrier)} if isinstance(ships,(tuple,list)) else {}
    args=dict(
        fields_pre_ship_stage=fields,
        ships=ships,
        enemy_by_ship_field_id=enemy,
        ion_storm_contains_field_center_by_id=ion,
        standard_web_beam_yield_by_field_id=web,
        colonial_entitlement_by_ship_id=colonial,
        max_radius=150,
        complete_pre_ship_field_and_ship_roster_confirmed=True,
        exact_ship_identity_loadouts_missions_and_positions_confirmed=True,
        all_fighter_carriers_colonial_and_advantage_confirmed=True,
        complete_enemy_diplomacy_ion_and_web_rate_context_confirmed=True,
        ship_id_phase_order_and_no_interleaving_confirmed=True,
        no_msc_scooping_starbase_or_custom_mechanics_confirmed=True,
    )
    args.update(flags)
    return quote_ordered_isolated_ship_mine_sweeps(**args)


def test_all_three_ship_classes_share_one_mutable_in_quote_only_roster():
    r=calc()
    assert [s.ship_id for s in r.steps]==[3,7,9]
    assert [s.mode for s in r.steps]==[
        BEAM_ONLY,COLONIAL_FIGHTERS_ONLY,COLONIAL_MIXED,
    ]
    assert [s.units_swept for s in r.steps]==[4,40,24]
    assert [s.units_after for s in r.steps]==[996,956,932]
    assert r.initial_units==1000
    assert r.total_hypothetical_units_swept==68
    assert r.final_hypothetical_units==932
    assert r.initial_units==r.final_hypothetical_units+r.total_hypothetical_units_swept
    assert r.steps[0].fields_after==r.steps[1].fields_before
    assert r.steps[1].fields_after==r.steps[2].fields_before
    assert r.steps[2].fields_after==r.final_hypothetical_fields
    assert r.evidence==EVIDENCE
    assert not r.accepted_ship_missions_verified
    assert not r.actual_host_ship_sweep_stage_verified
    assert not r.exact_race_entitlement_from_host_verified
    assert not r.host_diff_verified


def test_ship_order_not_input_sequence_and_radius_shrink_affects_later_ship():
    # 100 mines radius 10; blaster removes 64 -> radius6.
    # Fighter at x109 was at <=110 but after shrink it is >106, misses.
    # Mixed x14 has beam range <11 (miss) but fighter still reaches.
    ships=(mixed(18,x=14),fighter(8,x=109,count=2),beam(2,family="blaster"))
    r=calc(fields=(field(units=100),),ships=ships)
    assert [s.ship_id for s in r.steps]==[2,8,18]
    assert [s.units_swept for s in r.steps]==[64,0,20]
    assert [s.units_after for s in r.steps]==[36,36,16]
    mixed_report=r.steps[2].underlying_conditional_report
    assert mixed_report.field_quotes[0].beam_channel_status=="BEAMS_OUT_OF_RANGE"
    assert mixed_report.field_quotes[0].fighter_channel_status=="FIGHTERS_IN_RANGE"
    assert r.final_hypothetical_units==16


def test_web_fighters_immune_beams_still_operate_and_ordered():
    ships=(beam(10),mixed(4),fighter(1))
    r=calc(fields=(field(web=True,units=100),),ships=ships)
    assert [s.units_swept for s in r.steps]==[0,3,4]
    assert r.final_hypothetical_units==93
    assert r.steps[0].underlying_conditional_report.steps[0].events[0].status == "WEB_IMMUNE_TO_FIGHTERS"
    mixed_report=r.steps[1].underlying_conditional_report
    assert mixed_report.field_quotes[0].fighter_potential_mine_units==0
    assert mixed_report.field_quotes[0].beam_potential_mine_units==3


def test_field_exhaustion_leaves_no_field_for_later_ships():
    r=calc(fields=(field(units=2),))
    assert [s.units_swept for s in r.steps]==[2,0,0]
    assert r.final_hypothetical_fields==()
    assert r.steps[1].fields_before==()
    assert r.steps[2].fields_before==()


def test_ion_storm_blocks_beam_steps_but_fighter_and_mixed_fighters_work():
    r=calc(ion={20:True})
    assert [s.units_swept for s in r.steps]==[0,40,20]
    assert r.final_hypothetical_units==940


def test_own_and_distant_web_fields_are_retained():
    fs=(field(9,owner=1,units=50),
        field(20,x=2000,units=500),
        field(40,web=True,units=100,x=2000))
    r=calc(fields=fs)
    assert r.total_hypothetical_units_swept==0
    assert r.final_hypothetical_fields==tuple(sorted(fs,key=lambda x:x.field_id))


def test_empty_field_roster_with_three_ships_is_bounded_noop():
    r=calc(fields=())
    assert r.steps and len(r.steps)==3
    assert r.initial_units==r.final_hypothetical_units==0
    assert all(s.units_swept==0 for s in r.steps)


def test_permutation_determinism_immutability_and_zero_host_proof():
    fs=[field(31,units=1000),field(11,owner=1,units=60),
        field(22,x=500,web=True,units=100)]
    ss=[mixed(14),fighter(9),beam(2)]
    a=calc(fields=fs,ships=ss)
    b=calc(fields=list(reversed(fs)),ships=list(reversed(ss)))
    assert a==b
    assert fs[0].mine_units==1000
    with pytest.raises(FrozenInstanceError):
        a.steps[0].units_swept=100
    assert not a.actual_field_roster_mutated
    assert not a.host_diff_verified


def test_original_enemy_matrix_required_even_for_fields_destroyed_early():
    ships=(beam(2),mixed(10))
    fs=(field(units=2),)
    with pytest.raises(OrderedShipMineSweepAbstain,match="source"):
        calc(fields=fs,ships=ships,enemy={(2,20):True})
    with pytest.raises(OrderedShipMineSweepAbstain,match="source"):
        calc(fields=fs,ships=ships,ion={})


def test_later_mixed_web_edge_error_abstains_atomically():
    # Fighter first leaves web intact; beam-bearing mixed carrier at x11
    # is in conservative PRE_DECAY raster uncertainty region.
    with pytest.raises(OrderedShipMineSweepAbstain,match="Ship ID 9"):
        calc(fields=(field(units=100,web=True),),
             ships=(fighter(1),mixed(9,x=11)))


@pytest.mark.parametrize("case",[
    {"ships":()},
    {"ships":(beam(2),beam(2))},
    {"ships":(beam(2),mixed(2))},
    {"ships":(fighter(2),mixed(2))},
    {"ships":(object(),)},
    {"ships":(beam(msc=True),)},
    {"ships":(fighter(beams=1),)},
    {"ships":(mixed(fighters=0),)},
    {"ships":(mixed(msc=True),)},
    {"ships":(beam(sid=True),)},
    {"fields":(field(),field())},
    {"fields":(field(units=0),)},
    {"fields":(field(units=True),)},
    {"fields":(field(web=1),)},
    {"fields":(field(units=10001),),"max_radius":100},
    {"enemy":{}},
    {"enemy":{(3,20):True}},
    {"enemy":{(3,20):1,(7,20):True,(9,20):True}},
    {"enemy":{(3,20):True,(7,20):True,(9,20):True,(2,20):True}},
    {"ion":{}},
    {"ion":{20:1}},
    {"web":{20:True}},
    {"colonial":{}},
    {"colonial":{7:True}},
    {"colonial":{7:True,9:False}},
    {"colonial":{7:True,9:True,3:True}},
    {"max_radius":True},
    {"max_radius":101},
    {"complete_pre_ship_field_and_ship_roster_confirmed":False},
    {"exact_ship_identity_loadouts_missions_and_positions_confirmed":1},
    {"all_fighter_carriers_colonial_and_advantage_confirmed":False},
    {"complete_enemy_diplomacy_ion_and_web_rate_context_confirmed":None},
    {"ship_id_phase_order_and_no_interleaving_confirmed":False},
    {"no_msc_scooping_starbase_or_custom_mechanics_confirmed":False},
])
def test_invalid_rosters_modes_or_source_refuse_atomically(case):
    with pytest.raises(OrderedShipMineSweepAbstain):
        calc(**case)


def test_direct_none_fields_and_untyped_ship_rosters_abstain():
    with pytest.raises(OrderedShipMineSweepAbstain):
        calc(fields_pre_ship_stage=None)
    with pytest.raises(OrderedShipMineSweepAbstain):
        calc(ships="not a list")
