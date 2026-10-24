"""Standard mine sweeping synthetic-only: geometry, sequence, rate and abstentions."""
from dataclasses import FrozenInstanceError
from math import isqrt

import pytest

from planets_lab.rules.minefield_placement_candidate import LocatedMinefield, Point
from planets_lab.rules.mine_beam_sweeping import (
    EVIDENCE, STANDARD_BEAM_SWEEP_YIELDS,
    BeamMineSweepAbstain, SweepingShip, simulate_isolated_standard_beam_sweeps,
)


def field(fid=11, *, owner=2, x=0, y=0, units=100, web=False):
    return LocatedMinefield(fid, owner, Point(x, y), units, web)


def ship(sid=15, *, owner=1, x=0, y=0, family="heavy_phaser",
         beams=1, mission="MINE_SWEEP", scoop=False):
    return SweepingShip(sid, owner, Point(x, y), family, beams, mission, scoop)


def calc(*, fields=None, ships=None, enemy=None, ion=None, web_rate=None,
         max_radius=150, **overrides):
    fields = (field(),) if fields is None else fields
    ships = (ship(),) if ships is None else ships
    args = dict(
        fields=fields,
        ships=ships,
        confirmed_enemy_by_ship_field=(
            {(s.ship_id, f.field_id): s.owner_id != f.owner_id for s in ships for f in fields}
            if enemy is None else enemy
        ),
        ion_storm_contains_field_center_by_id=(
            {f.field_id: False for f in fields} if ion is None else ion
        ),
        standard_web_beam_yield_confirmed_by_field_id=(
            {f.field_id: True for f in fields if f.is_web} if web_rate is None else web_rate
        ),
        max_radius=max_radius,
        complete_pre_sweep_field_and_ship_rosters_confirmed=True,
        exact_beam_loadouts_and_positions_confirmed=True,
        complete_diplomacy_and_ion_context_confirmed=True,
        isolated_beam_sweep_only_confirmed=True,
        standard_no_custom_modifiers_confirmed=True,
    )
    args.update(overrides)
    return simulate_isolated_standard_beam_sweeps(**args)


@pytest.mark.parametrize("family,normal,web", [
    ("laser", 4, 3),
    ("x_ray_laser", 16, 12),
    ("plasma_bolt", 36, 27),
    ("blaster", 64, 48),
    ("positron_beam", 100, 75),
    ("disruptor", 144, 108),
    ("heavy_blaster", 196, 147),
    ("phaser", 256, 192),
    ("heavy_disruptor", 324, 243),
    ("heavy_phaser", 400, 300),
])
def test_all_ten_documented_normal_and_web_beam_yields(family, normal, web):
    assert STANDARD_BEAM_SWEEP_YIELDS[family] == (normal, web)
    for is_web, expected in ((False, normal), (True, web)):
        result = calc(
            fields=(field(units=1000, web=is_web),),
            ships=(ship(family=family),),
        )
        assert result.total_units_swept == expected
        assert result.fields_final[0].mine_units == 1000 - expected
        event = result.steps[0].events[0]
        assert event.mine_units_destroyed == expected
        assert event.beam_yield_per_weapon == expected
        assert event.radius_after == isqrt(1000 - expected)
        assert result.evidence == EVIDENCE
        assert not result.host_diff_verified


def test_multiple_beams_all_in_range_fields_are_swept_in_one_step():
    fields = (field(33, units=500), field(1, x=20, units=800),
              field(22, x=300, units=900))
    result = calc(fields=fields, ships=(ship(family="phaser", beams=2),))
    assert tuple(e.field_id for e in result.steps[0].events) == (1, 22, 33)
    assert tuple(e.status for e in result.steps[0].events) == (
        "SWEEPED", "OUT_OF_RANGE", "SWEEPED",
    )
    assert result.total_units_swept == 500 + 512
    assert tuple((f.field_id, f.mine_units) for f in result.fields_final) == (
        (1, 288), (22, 900),
    )


def test_ascending_ship_id_recomputes_field_radius_after_each_sweep():
    # 100 mines -> radius 10; first ship at center destroys 64 => radius 6.
    # Second ship is distance 12: originally within 5 LY of edge,
    # afterward no longer strictly within 5 LY, so it does NOT sweep.
    a = ship(20, x=12, family="laser")
    b = ship(5, family="blaster")
    result = calc(fields=(field(units=100),), ships=(a, b))
    assert [step.ship_id for step in result.steps] == [5, 20]
    assert [step.units_swept for step in result.steps] == [64, 0]
    assert result.steps[1].events[0].status == "OUT_OF_RANGE"
    assert result.fields_final[0].mine_units == 36
    assert result.initial_units == result.final_units + result.total_units_swept


def test_boundary_normal_sweep_strictly_less_than_five_from_integer_edge():
    f = (field(units=100),)  # radius 10.
    assert calc(fields=f, ships=(ship(x=14, family="laser"),)).total_units_swept == 4
    assert calc(fields=f, ships=(ship(x=15, family="laser"),)).total_units_swept == 0
    assert calc(fields=f, ships=(ship(x=10, family="laser"),)).total_units_swept == 4
    assert calc(fields=f, ships=(ship(x=-14, family="laser"),)).total_units_swept == 4


def test_web_inside_supported_near_edge_outside_abstains_and_far_skips():
    f = (field(units=100, web=True),)
    assert calc(fields=f, ships=(ship(x=10, family="laser"),)).total_units_swept == 3
    with pytest.raises(BeamMineSweepAbstain, match="web mine sweep near-edge"):
        calc(fields=f, ships=(ship(x=11, family="laser"),))
    result = calc(fields=f, ships=(ship(x=12, family="laser"),))
    assert result.total_units_swept == 0
    assert result.steps[0].events[0].status == "OUT_OF_RANGE"


def test_enemy_matrix_is_not_inferred_from_field_ids():
    friendly = field(1, owner=1, units=500)
    enemy = field(2, owner=2, units=500)
    result = calc(fields=(friendly, enemy), ships=(ship(beams=2),))
    assert result.steps[0].events[0].status == "NOT_ENEMY"
    assert result.steps[0].events[1].status == "SWEEPED"
    assert result.total_units_swept == 500
    assert result.fields_final == (friendly,)
    with pytest.raises(BeamMineSweepAbstain, match="same-owner"):
        calc(fields=(friendly,), enemy={(15, 1): True})


def test_ion_storm_center_blocks_beams_without_mutating_fields():
    f = field(units=800)
    result = calc(fields=(f,), ion={11: True})
    assert result.steps[0].events[0].status == "ION_BLOCKED"
    assert result.fields_final == (f,) and result.total_units_swept == 0


def test_ship_order_and_empty_field_roster_noop():
    result = calc(fields=(), ships=(ship(9), ship(2)))
    assert [step.ship_id for step in result.steps] == [2, 9]
    assert result.fields_final == ()
    assert result.total_units_swept == result.initial_units == 0
    no_ships = calc(fields=(field(),), ships=())
    assert no_ships.fields_final == (field(),)
    assert not no_ships.steps


def test_exhaustion_drops_field_from_following_ship_and_both_books_conserve():
    result = calc(fields=(field(units=7),),
                  ships=(ship(4, family="laser", beams=2), ship(5)))
    assert result.steps[0].events[0].status == "SWEEPED"
    assert result.steps[0].events[0].mine_units_destroyed == 7
    assert result.steps[0].fields_after == ()
    assert result.steps[1].events == ()
    assert result.final_units == 0 and result.total_units_swept == 7
    with pytest.raises(FrozenInstanceError):
        result.steps[0].units_swept = 2


def test_determinism_and_original_rosters_untouched():
    orig = [field(20, x=20, units=1000), field(5, x=0, units=1000)]
    a = calc(fields=orig, ships=(ship(8), ship(2)))
    b = calc(fields=tuple(reversed(orig)), ships=(ship(2), ship(8)))
    assert a == b
    assert a.initial_units == 2000
    assert [f.mine_units for f in orig] == [1000, 1000]
    assert not a.host_orders_accepted_verified and not a.host_phase_order_verified


def test_max_radius_100_acceptance_and_capacity_rejection():
    result = calc(fields=(field(units=10000),), max_radius=100)
    assert result.initial_units == 10000
    with pytest.raises(BeamMineSweepAbstain, match="field"):
        calc(fields=(field(units=10001),), max_radius=100)


@pytest.mark.parametrize("case", [
    {"complete_pre_sweep_field_and_ship_rosters_confirmed": False},
    {"exact_beam_loadouts_and_positions_confirmed": None},
    {"complete_diplomacy_and_ion_context_confirmed": False},
    {"isolated_beam_sweep_only_confirmed": 1},
    {"standard_no_custom_modifiers_confirmed": False},
    {"ships": (ship(mission="EXPLORE"),)},
    {"ships": (ship(scoop=True),)},
    {"ships": (ship(family="unknown"),)},
    {"ships": (ship(beams=0),)},
    {"ships": (ship(beams=True),)},
    {"ships": (ship(15), ship(15))},
    {"ships": (ship(x=True),)},
    {"ships": (ship(owner=True),)},
    {"fields": (field(11, units=0),)},
    {"fields": (field(11, units=True),)},
    {"fields": (field(11), field(11))},
    {"fields": (field(11, web=1),)},
    {"fields": None},  # invalidity of None is exercised directly below
    {"max_radius": 200},
    {"max_radius": True},
    {"enemy": {}},
    {"enemy": {(15, 11): 1}},
    {"enemy": {(15, 11): True, (3, 3): False}},
    {"ion": {}},
    {"ion": {11: 1}},
    {"ion": {11: False, 99: False}},
    {"web_rate": {11: True}},  # non-web field cannot have web-rate entry
])
def test_adversarial_inputs_fail_closed(case):
    if case == {"fields": None}:
        # calc() default sentinel creates a single field; call the raw API.
        with pytest.raises(BeamMineSweepAbstain):
            simulate_isolated_standard_beam_sweeps(
                fields=None, ships=(), confirmed_enemy_by_ship_field={},
                ion_storm_contains_field_center_by_id={},
                standard_web_beam_yield_confirmed_by_field_id={},
                max_radius=150,
                complete_pre_sweep_field_and_ship_rosters_confirmed=True,
                exact_beam_loadouts_and_positions_confirmed=True,
                complete_diplomacy_and_ion_context_confirmed=True,
                isolated_beam_sweep_only_confirmed=True,
                standard_no_custom_modifiers_confirmed=True,
            )
    else:
        with pytest.raises(BeamMineSweepAbstain):
            calc(**case)


def test_nonstandard_web_rates_refuse_instead_of_guessing_bonus():
    with pytest.raises(BeamMineSweepAbstain, match="nonstandard web"):
        calc(fields=(field(web=True),), web_rate={11: False})
    with pytest.raises(BeamMineSweepAbstain, match="standard-web-yield"):
        calc(fields=(field(web=True),), web_rate={})


def test_synthetic_two_player_multifield_sequence_conserves_typed_units():
    fields = (
        field(1, owner=2, x=0, units=1000),
        field(3, owner=2, x=50, units=400, web=True),
        field(4, owner=1, x=0, units=50),
        field(7, owner=3, x=500, units=100),
    )
    ships = (ship(9, x=0, family="laser", beams=2),
             ship(2, x=0, family="phaser", beams=2))
    result = calc(fields=fields, ships=ships)
    assert [s.ship_id for s in result.steps] == [2, 9]
    assert all(
        step.units_before == step.units_after + step.units_swept
        for step in result.steps
    )
    assert result.initial_units == result.final_units + result.total_units_swept
    assert result.fields_final != tuple(fields)
