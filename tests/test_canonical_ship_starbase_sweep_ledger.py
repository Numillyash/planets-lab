"""Strict canonical mixed-ship -> single Campaign base conditional ledger."""
from dataclasses import FrozenInstanceError

import pytest

from planets_lab.rules.minefield_placement_candidate import LocatedMinefield, Point
from planets_lab.rules.mine_beam_sweeping import SweepingShip
from planets_lab.rules.mine_fighter_sweeping import ColonialFighterSweeper
from planets_lab.rules.colonial_mixed_beam_fighter_sweep import MixedColonialCarrier
from planets_lab.rules.starbase_mine_sweeping import SweepingStarbase
from planets_lab.rules.ship_starbase_sweep_ledger import (
    quote_conditional_ship_then_starbase_mine_sweeps,
)
from planets_lab.rules.canonical_ship_starbase_sweep_ledger import (
    EVIDENCE, CanonicalShipStarbaseSweepAbstain,
    quote_canonical_ships_then_one_starbase_sweep,
)


def f(fid=20, *, owner=2, x=0, units=1000, web=False):
    return LocatedMinefield(fid, owner, Point(x, 0), units, web)


def beam(sid=3, *, owner=1, x=0, family="laser", beams=1, mission="MINE_SWEEP", msc=False):
    return SweepingShip(sid, owner, Point(x, 0), family, beams, mission, msc)


def fighter(sid=7, *, owner=1, x=0, count=2, beams=0):
    return ColonialFighterSweeper(sid, owner, Point(x, 0), count, beams, "MINE_SWEEP")


def mixed(sid=9, *, owner=1, x=0, beams=1, fighters=1, msc=False):
    return MixedColonialCarrier(sid, owner, Point(x, 0), "MINE_SWEEP", "laser", beams, fighters, msc)


def base(*, owner=1, x=0, beams_planet=1, beams_base=1, order="SWEEP_MINES"):
    return SweepingStarbase(
        4, owner, Point(x, 0), order, "laser", beams_planet, beams_base,
    )


def run(*, fields=None, ships=None, starbase=None, ship_enemy=None,
        base_enemy=None, ion=None, web=None, colonial=None, **overrides):
    fields = (f(),) if fields is None else fields
    ships = (beam(), fighter(), mixed()) if ships is None else ships
    starbase = base() if starbase is None else starbase
    if ship_enemy is None:
        ship_enemy = {
            (s.ship_id, fld.field_id): s.owner_id != fld.owner_id
            for s in ships for fld in fields
        } if isinstance(ships, (tuple, list)) and isinstance(fields, (tuple, list)) \
            and all(hasattr(s, "owner_id") for s in ships) else {}
    if base_enemy is None:
        base_enemy = {fld.field_id: fld.owner_id != starbase.owner_id
                      for fld in fields} if isinstance(fields, (tuple, list)) else {}
    if ion is None:
        ion = {fld.field_id: False for fld in fields} if isinstance(fields, (tuple, list)) else {}
    if web is None:
        web = {fld.field_id: True for fld in fields if fld.is_web is True} \
            if isinstance(fields, (tuple, list)) else {}
    if colonial is None:
        colonial = {s.ship_id: True for s in ships
                    if type(s) in (ColonialFighterSweeper, MixedColonialCarrier)} \
            if isinstance(ships, (tuple, list)) else {}
    params = dict(
        fields_before_ship_sweeps=fields,
        ships=ships,
        starbase=starbase,
        ship_enemy_by_ship_field=ship_enemy,
        starbase_enemy_by_field_id=base_enemy,
        ion_storm_at_field_center_by_id=ion,
        standard_web_beam_rate_by_field_id=web,
        colonial_entitlement_by_ship_id=colonial,
        max_radius=150,
        full_initial_field_ship_and_starbase_rosters_confirmed=True,
        exact_ship_missions_loadouts_positions_and_colonial_entitlements_confirmed=True,
        complete_initial_diplomacy_ion_and_web_rate_context_confirmed=True,
        campaign_advantage_order_and_base_defensive_beams_confirmed=True,
        ship_id_order_then_single_base_stage_confirmed=True,
        no_msc_scooping_colonial_base_fighters_or_other_mutations_confirmed=True,
        standard_no_custom_mechanics_confirmed=True,
    )
    params.update(overrides)
    return quote_canonical_ships_then_one_starbase_sweep(**params)


def test_three_ship_modes_then_one_starbase_staged_global_conservation():
    r = run(ships=(mixed(), fighter(), beam()))
    assert [x.ship_id for x in r.ship_ledger.steps] == [3, 7, 9]
    assert [x.units_swept for x in r.ship_ledger.steps] == [4, 40, 24]
    assert r.initial_mine_units == 1000
    assert r.after_ship_mine_units == 932
    assert r.starbase_mine_units_swept == 8
    assert r.final_hypothetical_mine_units == 924
    assert r.total_hypothetical_mine_units_swept == 76
    assert r.initial_mine_units == (
        r.final_hypothetical_mine_units
        + r.ship_mine_units_swept + r.starbase_mine_units_swept
    )
    assert r.after_ship_fields == r.ship_ledger.final_hypothetical_fields
    assert r.after_ship_mine_units == r.starbase_quote.initial_mine_units
    assert r.final_hypothetical_fields == r.starbase_quote.fields_hypothetically_after
    assert r.evidence == EVIDENCE
    assert not r.real_host_ship_order_accepted_verified
    assert not r.real_host_starbase_order_accepted_verified
    assert not r.real_host_phase_order_verified
    assert not r.actual_minefield_state_mutated
    assert not r.actual_campaign_advantage_enabled_verified
    assert not r.host_diff_verified


def test_shrinking_radius_during_ships_blocks_later_starbase():
    # beam2 blaster: 100 -> 36; fighter8(x109) misses reduced radius;
    # mixed18(x14): fighter only 20 -> 16, new radius4;
    # base x11 was in range of the initial radius10, not the final radius4.
    r = run(fields=(f(units=100),),
            ships=(mixed(18, x=14), fighter(8, x=109), beam(2, family="blaster")),
            starbase=base(x=11))
    assert [x.units_swept for x in r.ship_ledger.steps] == [64, 0, 20]
    assert r.after_ship_mine_units == 16
    assert r.starbase_quote.field_quotes[0].classification == "OUT_OF_RANGE"
    assert r.starbase_mine_units_swept == 0
    assert r.final_hypothetical_mine_units == 16


def test_complete_field_exhaustion_in_ship_stage_does_not_recreate_in_base():
    r = run(fields=(f(units=2),))
    assert [x.units_swept for x in r.ship_ledger.steps] == [2, 0, 0]
    assert r.after_ship_fields == ()
    assert r.starbase_quote.field_quotes == ()
    assert r.final_hypothetical_fields == ()
    assert r.total_hypothetical_mine_units_swept == 2


def test_ion_blocks_all_beams_not_colonial_fighters_or_web_immunity():
    r = run(fields=(f(20, units=1000), f(40, web=True, units=100)),
            ion={20: True, 40: True})
    assert [x.units_swept for x in r.ship_ledger.steps] == [0, 40, 20]
    assert r.starbase_mine_units_swept == 0
    assert r.after_ship_mine_units == 1040
    assert r.final_hypothetical_mine_units == 1040
    assert any(g.field_id == 40 and g.mine_units == 100 for g in r.final_hypothetical_fields)


def test_base_can_sweep_web_from_post_ship_radius_if_not_at_edge():
    r = run(fields=(f(web=True, units=100),))
    # ship laser4, Colonial fighter0, mixed laser3 => 93; base laser3*2=6
    assert [s.units_swept for s in r.ship_ledger.steps] == [3, 0, 3]
    assert r.after_ship_mine_units == 94
    assert r.starbase_mine_units_swept == 6
    assert r.final_hypothetical_mine_units == 88


def test_starbase_web_near_edge_refuses_atomically_after_ship_phase():
    # After ship laser sweeps 6 of 100 from web -> 94, integer radius 9.
    # starbase at x10 lies in [r,r+2) uncertain web raster.
    with pytest.raises(CanonicalShipStarbaseSweepAbstain, match="starbase stage"):
        run(fields=(f(web=True, units=100),),
            ships=(beam(2), fighter(7)),
            starbase=base(x=10))


def test_initial_base_hostility_must_include_fields_exhausted_by_ships():
    with pytest.raises(CanonicalShipStarbaseSweepAbstain, match="initial field/base"):
        run(fields=(f(units=2),), base_enemy={})
    with pytest.raises(CanonicalShipStarbaseSweepAbstain, match="initial field/base"):
        run(fields=(f(20, units=2), f(30, units=100)), base_enemy={30: True})


def test_full_original_ship_enemy_and_colonial_maps_must_be_supplied():
    with pytest.raises(CanonicalShipStarbaseSweepAbstain, match="ordered ship"):
        run(fields=(f(units=2),), ship_enemy={(3, 20): True})
    with pytest.raises(CanonicalShipStarbaseSweepAbstain, match="ordered ship"):
        run(colonial={7: True})
    with pytest.raises(CanonicalShipStarbaseSweepAbstain, match="ordered ship"):
        run(fields=(f(units=2),), ship_enemy={(3,20):True,(7,20):True,(9,20):1})


def test_deterministic_permutations_and_frozen_reports_preserve_inputs():
    fields = [f(30, x=300, units=400), f(20, units=1000),
              f(9, owner=1, web=True, units=100)]
    ships = [mixed(), beam(), fighter()]
    a = run(fields=fields, ships=ships)
    b = run(fields=list(reversed(fields)), ships=list(reversed(ships)))
    assert a == b
    assert fields[1].mine_units == 1000
    assert a.initial_fields[0].field_id == 9
    with pytest.raises(FrozenInstanceError):
        a.final_hypothetical_mine_units = 0
    with pytest.raises(FrozenInstanceError):
        a.starbase_quote.field_quotes[0].mine_units_potentially_destroyed = 0


def test_beam_only_parity_with_prior_305_stage_sequence():
    fields = (f(20, units=1000), f(30, x=500, units=100))
    ships = (beam(9), beam(2, family="blaster"))
    b = base(x=0)
    shared_enemy = {(s.ship_id, fld.field_id): True for s in ships for fld in fields}
    enemy_base = {20: True, 30: True}
    ion = {20: False, 30: False}
    older = quote_conditional_ship_then_starbase_mine_sweeps(
        fields_before_ship_sweeps=fields,
        beam_sweep_ships=ships,
        starbase=b,
        ship_enemy_by_ship_field=shared_enemy,
        starbase_enemy_by_field_id=enemy_base,
        ion_storm_at_field_center_by_id=ion,
        standard_web_beam_rate_by_field_id={},
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
    updated = run(fields=fields, ships=ships, starbase=b,
                  ship_enemy=shared_enemy, base_enemy=enemy_base, ion=ion)
    assert updated.after_ship_fields == older.after_ship_fields
    assert updated.final_hypothetical_fields == older.final_hypothetical_fields
    assert updated.ship_mine_units_swept == older.ship_mine_units_swept
    assert updated.starbase_mine_units_swept == older.starbase_mine_units_swept
    assert updated.total_hypothetical_mine_units_swept == older.total_hypothetical_mine_units_swept


def test_base_enemy_can_differ_from_individual_ships_but_own_field_never_enemy():
    fields = (f(20, owner=2, units=1000), f(30, owner=1, units=200))
    r = run(fields=fields, base_enemy={20: False, 30: False})
    assert r.starbase_mine_units_swept == 0
    assert r.ship_mine_units_swept > 0
    with pytest.raises(CanonicalShipStarbaseSweepAbstain, match="starbase stage"):
        run(fields=fields, base_enemy={20: True, 30: True})


@pytest.mark.parametrize("bad", [
    {"ships": ()},
    {"ships": (beam(2), mixed(2))},
    {"ships": (beam(msc=True),)},
    {"ships": (mixed(msc=True),)},
    {"ships": (fighter(beams=1),)},
    {"ships": (mixed(fighters=0),)},
    {"fields": (f(20), f(20))},
    {"fields": (f(units=True),)},
    {"fields": (f(units=0),)},
    {"starbase": base(order="EXPLORE")},
    {"starbase": base(beams_planet=0, beams_base=0)},
    {"base_enemy": {}},
    {"base_enemy": {20: 1}},
    {"base_enemy": {20: True, 30: True}},
    {"ion": {}},
    {"ion": {20: 1}},
    {"web": {20: True}},
    {"fields": (f(web=True),), "web": {20: False}},
    {"colonial": {}},
    {"colonial": {7: True}},
    {"max_radius": True},
    {"max_radius": 101},
    {"full_initial_field_ship_and_starbase_rosters_confirmed": False},
    {"exact_ship_missions_loadouts_positions_and_colonial_entitlements_confirmed": 1},
    {"complete_initial_diplomacy_ion_and_web_rate_context_confirmed": None},
    {"campaign_advantage_order_and_base_defensive_beams_confirmed": False},
    {"ship_id_order_then_single_base_stage_confirmed": False},
    {"no_msc_scooping_colonial_base_fighters_or_other_mutations_confirmed": False},
    {"standard_no_custom_mechanics_confirmed": False},
])
def test_invalid_context_refuses_as_one_atomic_multi_stage_result(bad):
    with pytest.raises(CanonicalShipStarbaseSweepAbstain):
        run(**bad)


def test_untyped_field_or_base_fails_closed():
    with pytest.raises(CanonicalShipStarbaseSweepAbstain):
        run(fields_before_ship_sweeps=None)
    with pytest.raises(CanonicalShipStarbaseSweepAbstain):
        run(starbase="not a base")
