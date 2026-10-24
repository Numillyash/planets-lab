"""Strict synthetic two-stage ship -> one-starbase mine sweep composition."""
from dataclasses import FrozenInstanceError

import pytest

from planets_lab.rules.minefield_placement_candidate import LocatedMinefield, Point
from planets_lab.rules.mine_beam_sweeping import SweepingShip
from planets_lab.rules.starbase_mine_sweeping import SweepingStarbase
from planets_lab.rules.ship_starbase_sweep_ledger import (
    EVIDENCE, ShipStarbaseMineSweepAbstain,
    quote_conditional_ship_then_starbase_mine_sweeps,
)


def f(fid=12, *, owner=2, x=0, units=100, web=False):
    return LocatedMinefield(fid, owner, Point(x,0), units, web)


def s(sid=5, *, owner=1, x=0, beam="laser", beams=1, mission="MINE_SWEEP", msc=False):
    return SweepingShip(sid, owner, Point(x,0), beam, beams, mission, msc)


def b(*, owner=1, x=0, family="laser", planet=1, defense=1, order="SWEEP_MINES"):
    return SweepingStarbase(4, owner, Point(x,0), order, family, planet, defense)


def calc(*, fields=None, ships=None, base=None, enemies=None, base_enemies=None,
         ion=None, web=None, **flags):
    fields=(f(),) if fields is None else fields
    ships=(s(),) if ships is None else ships
    base=b() if base is None else base
    if enemies is None:
        enemies={(ship.ship_id, field.field_id):ship.owner_id!=field.owner_id
                 for ship in ships for field in fields
                 if type(ship) is SweepingShip and type(field) is LocatedMinefield} if isinstance(ships,(tuple,list)) and isinstance(fields,(tuple,list)) else {}
    if base_enemies is None:
        base_enemies={field.field_id: field.owner_id!=base.owner_id
                     for field in fields if type(field) is LocatedMinefield} if isinstance(fields,(tuple,list)) and type(base) is SweepingStarbase else {}
    if ion is None:
        ion={field.field_id:False for field in fields if type(field) is LocatedMinefield} if isinstance(fields,(tuple,list)) else {}
    if web is None:
        web={field.field_id:True for field in fields if type(field) is LocatedMinefield and field.is_web is True} if isinstance(fields,(tuple,list)) else {}
    args=dict(
        fields_before_ship_sweeps=fields,
        beam_sweep_ships=ships,
        starbase=base,
        ship_enemy_by_ship_field=enemies,
        starbase_enemy_by_field_id=base_enemies,
        ion_storm_at_field_center_by_id=ion,
        standard_web_beam_rate_by_field_id=web,
        max_radius=150,
        full_pre_ship_roster_and_all_ships_confirmed=True,
        complete_diplomacy_ion_and_standard_web_rate_confirmed=True,
        exact_ships_positions_missions_and_beams_confirmed=True,
        campaign_starbase_advantage_and_order_confirmed=True,
        exact_starbase_defenses_and_highest_buildable_beam_confirmed=True,
        exactly_one_sweeping_starbase_confirmed=True,
        no_msc_fighter_or_concurrent_field_mutations_confirmed=True,
        standard_no_custom_mechanics_confirmed=True,
    )
    args.update(flags)
    return quote_conditional_ship_then_starbase_mine_sweeps(**args)


def test_two_stages_each_change_common_mine_roster_and_conserve():
    result=calc(fields=(f(units=1000),))
    assert result.initial_mine_units==1000
    assert result.ship_mine_units_swept==4
    assert result.after_ship_mine_units==996
    assert result.starbase_mine_units_swept==8
    assert result.final_hypothetical_mine_units==988
    assert result.total_hypothetical_mine_units_swept==12
    assert result.initial_mine_units == result.final_hypothetical_mine_units+12
    assert result.after_ship_fields[0].mine_units == 996
    assert result.final_hypothetical_fields[0].mine_units == 988
    assert result.ship_sequence.fields_final==result.after_ship_fields
    assert result.starbase_quote.initial_mine_units==result.after_ship_mine_units
    assert result.evidence==EVIDENCE
    assert not result.real_host_orders_accepted_verified
    assert not result.real_ship_phase_verified
    assert not result.real_starbase_phase_verified
    assert not result.real_host_phase_order_verified
    assert not result.host_diff_verified


def test_ship_sweep_shrinks_radius_and_prevents_later_base_sweep():
    result=calc(
        fields=(f(units=100),),
        ships=(s(3,beam="blaster"),),
        base=b(x=12),
    )
    assert result.ship_mine_units_swept==64
    assert result.after_ship_fields[0].mine_units==36
    assert result.starbase_quote.field_quotes[0].classification=="OUT_OF_RANGE"
    assert result.starbase_mine_units_swept==0
    assert result.final_hypothetical_mine_units==36


def test_exhaustion_in_ship_phase_does_not_recreate_field_at_base():
    result=calc(fields=(f(units=2),),ships=(s(3,beam="laser"),))
    assert result.ship_mine_units_swept==2
    assert result.after_ship_fields==()
    assert result.starbase_quote.field_quotes==()
    assert result.final_hypothetical_fields==()
    assert result.final_hypothetical_mine_units==0


def test_multi_ship_sorted_and_single_base_after_all_ships():
    fields=(f(9,units=1000),f(2,owner=1,units=100),f(20,x=250,units=2500))
    result=calc(fields=fields, ships=(s(25),s(3,beam="blaster")))
    assert [step.ship_id for step in result.ship_sequence.steps]==[3,25]
    assert result.ship_mine_units_swept==68
    assert result.starbase_mine_units_swept==8
    assert tuple(item.field_id for item in result.initial_fields)==(2,9,20)
    assert result.initial_mine_units==result.final_hypothetical_mine_units+76
    assert result.starbase_quote.field_quotes[0].classification=="NOT_ENEMY"


def test_web_after_ship_sweep_recomputes_radius_and_conserves():
    result=calc(fields=(f(web=True,units=1000),), ships=(s(beams=2),))
    assert result.ship_mine_units_swept==6
    assert result.starbase_mine_units_swept==6
    assert result.final_hypothetical_mine_units==988
    assert result.initial_mine_units==1000


def test_web_edge_ambiguity_from_base_abstains_atomically():
    # Ship sweeps at center but base is in the unresolved pre-decay
    # cell/circle band of the updated web field.
    with pytest.raises(ShipStarbaseMineSweepAbstain,match="starbase"):
        calc(fields=(f(web=True,units=100),),base=b(x=10))


def test_friendly_or_ion_fields_are_not_swept():
    result=calc(fields=(f(5,owner=1),f(8,owner=2)),
                ion={5:False,8:True})
    assert result.ship_mine_units_swept==0
    assert result.starbase_mine_units_swept==0
    assert result.final_hypothetical_fields==result.initial_fields


def test_input_order_cannot_change_output_and_is_immutable():
    fs=[f(25,units=200),f(2,units=300),f(30,owner=1,units=300)]
    ss=[s(7),s(2,beam="blaster")]
    a=calc(fields=fs,ships=ss)
    z=calc(fields=list(reversed(fs)),ships=list(reversed(ss)))
    assert a==z
    assert fs[0].mine_units==200
    with pytest.raises(FrozenInstanceError):
        a.total_hypothetical_mine_units_swept=100
    assert not a.actual_minefield_state_mutated


@pytest.mark.parametrize("bad",[
    {"ships":()},
    {"ships":None},
    {"ships":(s(msc=True),)},
    {"ships":(s(mission="EXPLORE"),)},
    {"ships":(s(5),s(5))},
    {"base":b(order="EXPLORE")},
    {"base":b(planet=0,defense=0)},
    {"base":b(family="unsupported")},
    {"fields":None},
    {"fields":(f(),f())},
    {"fields":(f(units=True),)},
    {"fields":(f(units=0),)},
    {"enemies":{}},
    {"enemies":{(5,12):1}},
    {"base_enemies":{}},
    {"base_enemies":{12:1}},
    {"base_enemies":{12:True,13:True}},
    {"ion":{}},
    {"ion":{12:1}},
    {"web":{12:True}},
    {"fields":(f(web=True),),"web":{12:False}},
    {"max_radius":True},
    {"max_radius":101},
    {"full_pre_ship_roster_and_all_ships_confirmed":False},
    {"complete_diplomacy_ion_and_standard_web_rate_confirmed":None},
    {"exact_ships_positions_missions_and_beams_confirmed":0},
    {"campaign_starbase_advantage_and_order_confirmed":False},
    {"exact_starbase_defenses_and_highest_buildable_beam_confirmed":False},
    {"exactly_one_sweeping_starbase_confirmed":False},
    {"no_msc_fighter_or_concurrent_field_mutations_confirmed":False},
    {"standard_no_custom_mechanics_confirmed":False},
])
def test_ambiguous_source_refuses_without_partial_result(bad):
    if bad.get("fields","valid") is None:
        with pytest.raises(ShipStarbaseMineSweepAbstain):
            calc(fields="not a roster")
    elif bad.get("ships","valid") is None:
        with pytest.raises(ShipStarbaseMineSweepAbstain):
            calc(beam_sweep_ships=None)
    else:
        with pytest.raises(ShipStarbaseMineSweepAbstain):
            calc(**bad)
