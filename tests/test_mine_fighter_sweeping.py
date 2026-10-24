"""Synthetic Colonial fighter sweep: per-field 20x, ion immunity, strict roster."""
from dataclasses import FrozenInstanceError

import pytest

from planets_lab.rules.minefield_placement_candidate import LocatedMinefield, Point
from planets_lab.rules.mine_fighter_sweeping import (
    EVIDENCE, ColonialFighterSweepAbstain, ColonialFighterSweeper,
    FIGHTER_EDGE_REACH_LY, MINES_PER_FIGHTER,
    simulate_isolated_colonial_fighter_sweeping,
)


def field(fid=1, *, x=0, owner=2, units=10000, web=False):
    return LocatedMinefield(fid, owner, Point(x, 0), units, web)


def ship(sid=10, *, x=0, owner=1, count=5, beams=0, mission="MINE_SWEEP"):
    return ColonialFighterSweeper(sid, owner, Point(x, 0), count, beams, mission)


def run(*, fields=None, ships=None, enemy=None, max_radius=150, **kw):
    fields = (field(),) if fields is None else fields
    ships = (ship(),) if ships is None else ships
    args = dict(
        fields=fields, ships=ships,
        confirmed_enemy_by_ship_field=(
            {(s.ship_id, f.field_id): s.owner_id != f.owner_id
             for s in ships for f in fields}
            if enemy is None else enemy
        ),
        max_radius=max_radius,
        full_presweep_field_ship_rosters_confirmed=True,
        colonial_race_and_advantage_confirmed=True,
        exact_fighters_positions_and_mission_confirmed=True,
        fighter_only_no_beams_scoop_or_starbase_confirmed=True,
        ordinary_unmodified_minefields_confirmed=True,
        independent_host_phase_not_claimed=True,
    )
    args.update(kw)
    return simulate_isolated_colonial_fighter_sweeping(**args)


def test_basic_documented_units_rate_and_not_consuming_fighters():
    r = run()
    assert MINES_PER_FIGHTER == 20
    assert FIGHTER_EDGE_REACH_LY == 100
    assert r.total_units_destroyed == 5 * 20
    assert r.fields_final[0].mine_units == 9900
    assert r.steps[0].events[0].maximum_per_field_units == 100
    assert r.steps[0].events[0].fighter_count == 5
    assert r.evidence == EVIDENCE
    assert not r.host_diff_verified and not r.host_phase_order_verified


def test_all_eligible_normal_fields_are_swept_once_per_ship_web_is_immune():
    r = run(fields=(
        field(7, x=10, units=10000),
        field(5, x=40, units=25, web=True),
        field(2, x=1000),
        field(3, x=0, units=300),
    ))
    events = r.steps[0].events
    assert [e.field_id for e in events] == [2, 3, 5, 7]
    assert [e.status for e in events] == [
        "OUT_OF_RANGE", "FIGHTERS_SWEPT", "WEB_IMMUNE_TO_FIGHTERS", "FIGHTERS_SWEPT",
    ]
    assert r.total_units_destroyed == 200
    assert next(f for f in r.fields_final if f.field_id == 5).mine_units == 25


def test_edge_100_light_years_reach_inclusive_and_beyond_exclusive():
    # radius = floor(sqrt(100)) = 10 LY, ship x=110 exactly at +100.
    f = (field(units=100),)
    assert run(fields=f, ships=(ship(x=110),)).total_units_destroyed == 100
    assert run(fields=f, ships=(ship(x=111),)).total_units_destroyed == 0
    assert run(fields=f, ships=(ship(x=-110),)).total_units_destroyed == 100


def test_can_sweep_field_center_inside_ion_storm_by_documented_exception():
    # No ion center input is needed/allowed: Colonial fighters are unaffected.
    r = run(fields=(field(units=400),), ships=(ship(count=2),))
    assert r.total_units_destroyed == 40
    assert r.fields_final[0].mine_units == 360


def test_id_order_after_radius_shrinks_can_push_carrier_out_of_range():
    # Initial radius 10, second ship x109 is within radius+100=110.
    # First ship kills 64 mines -> radius 6; x109 now out of 106.
    first = ship(sid=2, x=0, count=4)
    second = ship(sid=9, x=109, count=1)
    r = run(fields=(field(units=100),), ships=(second, first))
    assert [x.ship_id for x in r.steps] == [2, 9]
    assert [x.units_destroyed for x in r.steps] == [80, 0]
    assert r.steps[1].events[0].status == "OUT_OF_RANGE"
    assert r.fields_final[0].mine_units == 20


def test_own_field_is_not_enemy_and_explicit_hostility_must_be_consistent():
    mine = field(owner=1, units=200)
    r = run(fields=(mine,))
    assert r.steps[0].events[0].status == "NOT_ENEMY"
    assert r.fields_final == (mine,)
    with pytest.raises(ColonialFighterSweepAbstain, match="own field"):
        run(fields=(mine,), enemy={(10, 1): True})


def test_exhaustion_removes_field_only_from_conditional_next_roster():
    r = run(fields=(field(units=50),), ships=(ship(sid=5), ship(sid=8)))
    assert r.steps[0].units_destroyed == 50
    assert r.steps[0].fields_after == ()
    assert not r.steps[1].events
    assert r.initial_units == r.total_units_destroyed == 50
    assert r.final_units == 0


def test_empty_ship_and_field_rosters_are_stable_noops():
    r = run(fields=(), ships=(ship(),))
    assert r.fields_final == () and r.total_units_destroyed == 0
    p = run(fields=(field(),), ships=())
    assert p.fields_final == (field(),)
    assert p.steps == () and p.initial_units == p.final_units == 10000


def test_determinism_immutable_and_each_ship_conserves():
    fields = [field(8, x=0, units=1000), field(5, x=12, units=25)]
    ships = [ship(10, count=3), ship(3, count=2)]
    a = run(fields=fields, ships=ships)
    b = run(fields=tuple(reversed(fields)), ships=tuple(reversed(ships)))
    assert a == b
    assert all(x.units_before == x.units_after + x.units_destroyed for x in a.steps)
    assert a.initial_units == a.final_units + a.total_units_destroyed
    assert fields[0].mine_units == 1000
    with pytest.raises(FrozenInstanceError):
        a.total_units_destroyed = 3


def test_100_ly_cap_and_typed_rosters():
    assert run(fields=(field(units=10000),), max_radius=100).initial_units == 10000
    with pytest.raises(ColonialFighterSweepAbstain, match="field"):
        run(fields=(field(units=10001),), max_radius=100)


@pytest.mark.parametrize("override", [
    {"full_presweep_field_ship_rosters_confirmed": False},
    {"colonial_race_and_advantage_confirmed": 1},
    {"exact_fighters_positions_and_mission_confirmed": None},
    {"fighter_only_no_beams_scoop_or_starbase_confirmed": False},
    {"ordinary_unmodified_minefields_confirmed": False},
    {"independent_host_phase_not_claimed": False},
    {"ships": (ship(beams=1),)},
    {"ships": (ship(count=0),)},
    {"ships": (ship(count=True),)},
    {"ships": (ship(mission="EXPLORE"),)},
    {"ships": (ship(9), ship(9))},
    {"ships": (ship(x=True),)},
    {"fields": (field(1, units=0),)},
    {"fields": (field(1, units=True),)},
    {"fields": (field(1, web=1),)},
    {"fields": (field(1), field(1))},
    {"enemy": {}},
    {"enemy": {(10, 1): 1}},
    {"enemy": {(10, 1): True, (10, 2): False}},
    {"enemy": {(True, 1): True}},
    {"max_radius": True},
    {"max_radius": 99},
])
def test_rejects_untyped_incomplete_noncolonial_or_nonisolated_source(override):
    with pytest.raises(ColonialFighterSweepAbstain):
        run(**override)


def test_none_rosters_refused_by_direct_api():
    with pytest.raises(ColonialFighterSweepAbstain):
        simulate_isolated_colonial_fighter_sweeping(
            fields=None, ships=(), confirmed_enemy_by_ship_field={},
            max_radius=150,
            full_presweep_field_ship_rosters_confirmed=True,
            colonial_race_and_advantage_confirmed=True,
            exact_fighters_positions_and_mission_confirmed=True,
            fighter_only_no_beams_scoop_or_starbase_confirmed=True,
            ordinary_unmodified_minefields_confirmed=True,
            independent_host_phase_not_claimed=True,
        )
