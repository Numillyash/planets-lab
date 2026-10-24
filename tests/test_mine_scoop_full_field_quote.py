"""Adversarial synthetic MSC exact whole-field quote, NEVER a Host phase."""
from dataclasses import FrozenInstanceError

import pytest

from planets_lab.rules.minefield_placement_candidate import LocatedMinefield, Point
from planets_lab.rules.minelaying_conversion import STANDARD_TORPEDO_MINE_YIELDS
from planets_lab.rules.mine_scoop_full_field_quote import (
    EVIDENCE, MineScoopQuoteAbstain, quote_exact_whole_field_msc,
)


def field(fid=3, *, owner=1, x=0, y=0, units=400, web=False):
    return LocatedMinefield(fid, owner, Point(x, y), units, web)


def quote(*, fields=None, **overrides):
    params = dict(
        ship_id=18,
        owner_id=1,
        position=Point(0, 0),
        mission="MINE_SWEEP",
        friendly_code="MSC",
        beams_present=True,
        torpedo_tubes_present=True,
        torpedo_family="mark_8_photon",
        torpedoes_before=3,
        torpedo_capacity=99,
        target_field_id=3,
        fields=(field(),) if fields is None else fields,
        max_radius=150,
        robot_normal_mine_bonus_confirmed=False,
        crystal_standard_web_permission_confirmed=False,
        complete_prescoop_field_roster_confirmed=True,
        exact_ship_and_field_geometry_confirmed=True,
        exact_torpedo_inventory_and_capacity_confirmed=True,
        standard_racial_multiplier_and_catalog_confirmed=True,
        isolated_scoop_without_beam_or_fighter_sweeps_confirmed=True,
        no_custom_dense_or_phase_interactions_confirmed=True,
    )
    params.update(overrides)
    return quote_exact_whole_field_msc(**params)


def test_documented_federation_and_robot_mark8_examples_are_inverted():
    fed = quote()
    robot = quote(robot_normal_mine_bonus_confirmed=True)
    assert fed.proposed_torpedoes_recovered == 4
    assert robot.proposed_torpedoes_recovered == 1
    assert fed.exact_mine_units_per_recovered_torpedo == 100
    assert robot.exact_mine_units_per_recovered_torpedo == 400
    assert fed.proposed_torpedoes_after == 7
    assert robot.proposed_torpedoes_after == 4
    for result in (fed, robot):
        assert result.evidence == EVIDENCE
        assert result.whole_field_units_mathematically_accounted == 400
        assert result.proposed_units_left_if_entire_field_recovered == 0
        assert result.would_exhaust_field_if_executed
        assert not result.actual_torpedoes_transferred
        assert not result.actual_field_removed
        assert not result.field_roster_mutated
        assert not result.host_scoop_accepted_verified
        assert not result.host_phase_order_verified
        assert not result.host_diff_verified


@pytest.mark.parametrize("family,mine_yield", [
    ("mark_1_photon", 1),
    ("proton_torp", 4),
    ("mark_2_photon", 9),
    ("gamma_bomb", 16),
    ("mark_3_photon", 25),
    ("mark_4_photon", 36),
    ("mark_5_photon", 49),
    ("mark_6_photon", 64),
    ("mark_7_photon", 81),
    ("mark_8_photon", 100),
    ("quantum", 121),
])
def test_all_eleven_exact_inverted_torpedo_yields(family, mine_yield):
    assert STANDARD_TORPEDO_MINE_YIELDS[family] == mine_yield
    for robot in (False, True):
        units = mine_yield * (4 if robot else 1) * 3
        result = quote(
            torpedo_family=family,
            fields=(field(units=units),),
            robot_normal_mine_bonus_confirmed=robot,
        )
        assert result.proposed_torpedoes_recovered == 3
        assert result.whole_field_units_mathematically_accounted == units
        assert result.exact_mine_units_per_recovered_torpedo == mine_yield * (
            4 if robot else 1
        )


def test_web_entitlement_explicit_and_no_robot_bonus():
    mine = (field(units=200, web=True),)
    with pytest.raises(MineScoopQuoteAbstain, match="entitlement"):
        quote(fields=mine)
    good = quote(fields=mine, crystal_standard_web_permission_confirmed=True)
    assert good.proposed_torpedoes_recovered == 2
    assert good.is_web
    with pytest.raises(MineScoopQuoteAbstain, match="Robot"):
        quote(fields=mine, crystal_standard_web_permission_confirmed=True,
              robot_normal_mine_bonus_confirmed=True)


@pytest.mark.parametrize("fc", ["MSC", "msc", "mSc", "MsC"])
def test_real_friendly_code_case_insensitive(fc):
    assert quote(friendly_code=fc).proposed_torpedoes_recovered == 4


def test_source_roster_unchanged_and_result_immutable():
    source = [field(), field(fid=8, owner=2, x=4, units=100)]
    a = quote(fields=source)
    b = quote(fields=list(reversed(source)))
    assert a == b
    assert source[0].mine_units == 400
    assert source[1].mine_units == 100
    with pytest.raises(FrozenInstanceError):
        a.proposed_torpedoes_recovered = 900


def test_geometry_inside_integer_radius_positive_and_outside_fails():
    source = (field(units=400),)  # integer radius 20
    for x in (-20, 0, 20):
        assert quote(fields=source, position=Point(x, 0)).proposed_torpedoes_recovered == 4
    for x in (-21, 21, 200):
        with pytest.raises(MineScoopQuoteAbstain, match="geometry"):
            quote(fields=source, position=Point(x, 0))


def test_second_owner_field_nearby_refused_even_if_web_type_differs():
    target = field(units=400)
    nearby = field(fid=4, x=0, units=9, web=True)
    with pytest.raises(MineScoopQuoteAbstain, match="multiple"):
        quote(fields=(target, nearby))
    far = field(fid=4, x=200, units=9, web=True)
    assert quote(fields=(target, far)).proposed_torpedoes_recovered == 4
    # Enemy fields are not scoop candidates even if their circles overlap.
    enemy = field(fid=4, owner=2, x=0, units=1000)
    assert quote(fields=(target, enemy)).proposed_torpedoes_recovered == 4


def test_fractional_torpedo_remainder_refuses_without_guessing_rounding():
    for units in (1, 99, 101, 399, 401):
        with pytest.raises(MineScoopQuoteAbstain, match="rounding"):
            quote(fields=(field(units=units),))
    # Robot still needs 4x the base mine yield.
    with pytest.raises(MineScoopQuoteAbstain, match="rounding"):
        quote(fields=(field(units=100),), robot_normal_mine_bonus_confirmed=True)


def test_full_or_nearly_full_ammo_refuses_partial_scoop():
    with pytest.raises(MineScoopQuoteAbstain, match="saturation"):
        quote(torpedoes_before=96, torpedo_capacity=99)
    assert quote(torpedoes_before=95, torpedo_capacity=99).proposed_torpedoes_after == 99
    assert quote(torpedoes_before=0, torpedo_capacity=4).proposed_torpedoes_after == 4


def test_radius_100_and_150_and_frozen_id():
    cap100 = quote(fields=(field(units=10000),), max_radius=100,
                   torpedoes_before=0, torpedo_capacity=100)
    assert cap100.proposed_torpedoes_recovered == 100
    with pytest.raises(MineScoopQuoteAbstain, match="field"):
        quote(fields=(field(units=10001),), max_radius=100)
    assert quote(fields=(field(units=22500),),
                 torpedoes_before=0, torpedo_capacity=225).proposed_torpedoes_recovered == 225


@pytest.mark.parametrize("bad", [
    {"ship_id": 0}, {"ship_id": True},
    {"owner_id": -1}, {"owner_id": True},
    {"target_field_id": True}, {"target_field_id": 100},
    {"position": Point(True, 0)}, {"position": (0, 0)},
    {"mission": "LAY_MINES"}, {"mission": None},
    {"friendly_code": "MKT"}, {"friendly_code": None},
    {"beams_present": False}, {"beams_present": 1},
    {"torpedo_tubes_present": False}, {"torpedo_tubes_present": 1},
    {"torpedo_family": "unknown"}, {"torpedo_family": True},
    {"torpedoes_before": True}, {"torpedoes_before": -1},
    {"torpedoes_before": 10001}, {"torpedo_capacity": True},
    {"torpedo_capacity": 0}, {"torpedo_capacity": 10001},
    {"torpedoes_before": 100, "torpedo_capacity": 99},
    {"robot_normal_mine_bonus_confirmed": 1},
    {"crystal_standard_web_permission_confirmed": None},
    {"complete_prescoop_field_roster_confirmed": False},
    {"exact_ship_and_field_geometry_confirmed": 1},
    {"exact_torpedo_inventory_and_capacity_confirmed": False},
    {"standard_racial_multiplier_and_catalog_confirmed": False},
    {"isolated_scoop_without_beam_or_fighter_sweeps_confirmed": False},
    {"no_custom_dense_or_phase_interactions_confirmed": None},
    {"max_radius": 99}, {"max_radius": True},
    {"fields": ()}, {"fields": (field(units=0),)},
    {"fields": (field(fid=True),)},
    {"fields": (field(owner=True),)},
    {"fields": (field(web=1),)},
    {"fields": (field(), field())},
    {"fields": (field(owner=2),)},
    {"fields": (field(fid=4),)},
    {"fields": (field(units=22501),)},
])
def test_fail_closed_on_untyped_unverified_ambiguous_or_custom(bad):
    with pytest.raises(MineScoopQuoteAbstain):
        quote(**bad)


def test_reject_none_roster_and_do_not_create_partial_return():
    with pytest.raises(MineScoopQuoteAbstain, match="roster"):
        quote(fields=[])
    # A valid result contains no live ship or mutable field roster.
    result = quote()
    assert "fields_after" not in result.__dataclass_fields__
    assert "field_id_allocated" not in result.__dataclass_fields__
