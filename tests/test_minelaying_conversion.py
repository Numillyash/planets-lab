"""Standard documented torpedo to *unallocated* mine-unit quote tests."""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from planets_lab.rules.minelaying_conversion import (
    EVIDENCE, MAX_QUOTED_TORPEDOES, STANDARD_TORPEDO_MINE_YIELDS,
    MineLayingQuoteAbstain, quote_standard_starship_minelaying,
)


def quote(*, family="mark_8_photon", count=100, code="ALL",
          mission="LAY_MINES", robot=False, robot_owner=True,
          web_permitted=False, **overrides):
    kwargs = dict(
        torpedo_family=family,
        torpedoes_held=count,
        drop_code=code,
        mission=mission,
        standard_torpedo_catalog_confirmed=True,
        ordinary_no_custom_modifiers_confirmed=True,
        mission_and_tubes_eligible_confirmed=True,
        web_permission_confirmed=web_permitted,
        robot_fourfold_bonus_confirmed=robot,
        robot_field_owner_is_self_confirmed=robot_owner,
    )
    kwargs.update(overrides)
    return quote_standard_starship_minelaying(**kwargs)


@pytest.mark.parametrize("family,yield_", [
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
def test_all_documented_standard_torpedo_yields(family, yield_):
    result=quote(family=family, count=1)
    assert STANDARD_TORPEDO_MINE_YIELDS[family] == yield_
    assert result.unallocated_mine_units == yield_
    assert result.base_mine_units_per_torpedo == yield_
    assert result.torpedoes_converted == 1
    assert result.torpedoes_remaining == 0
    assert result.single_empty_standard_field_capacity == 22500
    assert result.field_created_or_expanded is False
    assert result.minefield_allocation_verified is False
    assert result.host_causal_verified is False
    assert result.evidence == EVIDENCE


def test_documented_mark8_hundred_torps_are_unallocated_10000_mine_units():
    q=quote()
    assert q.torpedoes_before == 100
    assert q.torpedoes_converted == 100
    assert q.unallocated_mine_units == 10000
    assert not q.unallocated_units_exceed_single_field_capacity


@pytest.mark.parametrize("code,count,used", [
    ("ALL", 111, 111),
    ("MDA", 111, 111),
    ("MD0", 140, 100),
    ("MD1", 140, 10),
    ("MD3", 140, 30),
    ("MD9", 140, 90),
    ("MD9", 5, 5),
])
def test_friendly_code_limits_and_ammunition_conservation(code, count, used):
    q = quote(count=count,code=code,family="mark_2_photon")
    assert q.torpedoes_converted == used
    assert q.torpedoes_remaining == count-used
    assert q.unallocated_mine_units == 9*used


def test_robot_fourfold_bonus_quote_and_explicit_capacity_uncertainty():
    q=quote(robot=True, family="mark_8_photon")
    assert q.unallocated_mine_units == 40000
    assert q.asserted_robot_laying_multiplier == 4
    assert q.unallocated_units_exceed_single_field_capacity
    assert q.minefield_allocation_verified is False
    assert q.field_created_or_expanded is False


def test_web_uses_same_documented_yields_without_robot_bonus():
    q=quote(mission="LAY_WEB_MINES", web_permitted=True, family="quantum",count=10)
    assert q.unallocated_mine_units == 1210
    assert q.uses_web_mine_units
    assert q.asserted_robot_laying_multiplier == 1
    assert q.host_mission_accepted_verified is False


def test_reduced_100ly_capacity_checked_but_does_not_allocate():
    q=quote(count=100, family="mark_8_photon",max_radius=100)
    assert q.single_empty_standard_field_capacity == 10000
    assert not q.unallocated_units_exceed_single_field_capacity
    assert quote(count=200, family="mark_8_photon",max_radius=100).unallocated_units_exceed_single_field_capacity


def test_zero_ammunition_is_supported_noop_quote_without_field_creation():
    q=quote(count=0, code="MD0")
    assert q.torpedoes_before == q.torpedoes_remaining == 0
    assert q.unallocated_mine_units == 0
    assert q.torpedoes_converted == 0
    assert not q.field_created_or_expanded


def test_quote_immutable_and_deterministic():
    assert quote(family="mark_5_photon", count=79, code="MD2") == quote(
        family="mark_5_photon",count=79,code="MD2",
    )
    with pytest.raises(FrozenInstanceError):
        quote().torpedoes_converted = 45


@pytest.mark.parametrize("bad", [
    {"family":"unknown"},
    {"family":1},
    {"count":-1},
    {"count":True},
    {"count":MAX_QUOTED_TORPEDOES+1},
    {"code":"MDX"},
    {"code":"MDH"},  # half rounding needs a separate exact rule
    {"code":"MDQ"},  # quarter rounding needs a separate exact rule
    {"code":"MI1"},  # owner redirection is not in isolated quote
    {"code":"abc"},  # client mission + arbitrary FC not authenticated
    {"code":None},
    {"mission":"MINE_SWEEP"},
    {"mission":None},
    {"max_radius":101},
    {"max_radius":True},
    {"web_permitted":1},
    {"robot":True,"robot_owner":False},
    {"robot":True,"mission":"LAY_WEB_MINES","web_permitted":True},
    {"mission":"LAY_WEB_MINES","web_permitted":False},
    {"standard_torpedo_catalog_confirmed":False},
    {"ordinary_no_custom_modifiers_confirmed":False},
    {"mission_and_tubes_eligible_confirmed":False},
])
def test_unknown_mission_or_unsupported_source_never_silently_promoted(bad):
    with pytest.raises(MineLayingQuoteAbstain):
        quote(**bad)


def test_documented_drop_limit_is_capped_by_actual_ammunition_not_potential_mines():
    q=quote(family="quantum",count=7,code="MD0")
    assert q.torpedoes_converted==7
    assert q.torpedoes_remaining==0
    assert q.unallocated_mine_units == 7*121


def test_quote_has_no_field_identifier_or_mutated_game_state():
    q=quote(family="mark_1_photon",count=20,code="MD1")
    fields={name for name in q.__dataclass_fields__}
    assert "field_id" not in fields
    assert "field_center" not in fields
    assert "ship_id" not in fields
    assert "player_id" not in fields
    assert q.torpedoes_before == 20
    assert q.torpedoes_converted == 10
    assert q.torpedoes_remaining == 10
    assert not q.host_causal_verified
