"""Hypothetical one-hit mine quote; no RNG/path/fuel or real Host outcome."""
from dataclasses import FrozenInstanceError
from fractions import Fraction

import pytest

from planets_lab.rules.mine_impact_single_quote import (
    EVIDENCE, MineImpactQuoteAbstain, quote_one_documented_mine_impact,
)


def quote(*, kind="NORMAL", mass=100, cloaked=False, tow=False, **overrides):
    args = dict(
        mine_kind=kind,
        hull_mass_kt=mass,
        ship_cloaked=cloaked,
        ship_under_tow=tow,
        confirmed_enemy_mine_context=True,
        confirmed_hull_only_mass_without_components_fuel_or_cargo=True,
        ordinary_standard_impact_settings_confirmed=True,
        no_custom_or_racial_damage_modifiers_confirmed=True,
        hypothetical_one_impact_only_confirmed=True,
    )
    args.update(overrides)
    return quote_one_documented_mine_impact(**args)


@pytest.mark.parametrize("kind,mass,expected", [
    ("NORMAL", 100, 100),  # documented 100 KT reference
    ("NORMAL", 500, 20),
    ("NORMAL", 999, 10),
    ("NORMAL", 1, 5000),  # raw single-hit damage never silently capped
    ("NORMAL", 9999, 1),
    ("WEB", 100, 10),  # documented 100 KT reference
    ("WEB", 500, 2),
    ("WEB", 1, 500),
    ("WEB", 999, 1),
    ("WEB", 10000, 1),
])
def test_documented_exact_integer_ceil_damage_per_one_hit(kind, mass, expected):
    r = quote(kind=kind, mass=mass)
    assert r.damage_percent_if_one_hit == expected
    assert r.damage_percent_if_one_hit == (
        r.exact_damage_numerator + r.exact_damage_denominator - 1
    ) // r.exact_damage_denominator
    assert not r.damage_capped_to_100_percent
    assert not r.ship_destroyed_verified


@pytest.mark.parametrize("kind,cloak,odds", [
    ("NORMAL", False, Fraction(1, 100)),
    ("NORMAL", True, Fraction(1, 200)),
    ("WEB", False, Fraction(1, 20)),
    ("WEB", True, Fraction(1, 20)),
])
def test_documented_single_ly_base_odds_not_route_probability(kind, cloak, odds):
    r = quote(kind=kind, cloaked=cloak)
    assert Fraction(
        r.base_hit_odds_per_ly_numerator,
        r.base_hit_odds_per_ly_denominator,
    ) == odds
    assert r.ship_cloaked is cloak
    assert r.evidence == EVIDENCE
    assert not r.actual_mine_hit_verified
    assert not r.travel_route_or_movement_calculated
    assert not r.host_diff_verified


def test_divisible_damage_does_not_claim_rounded_up_fraction():
    r = quote(mass=99)
    assert r.exact_damage_numerator == 10000
    assert r.exact_damage_denominator == 100
    assert r.damage_percent_if_one_hit == 100
    assert r.damage_rounded_up is False
    w = quote(kind="WEB", mass=99)
    assert w.damage_percent_if_one_hit == 10
    assert w.damage_rounded_up is False
    odd = quote(mass=100)
    assert odd.damage_rounded_up is True


def test_exact_mass_formula_excludes_cargo_and_fuel_by_contract():
    before = quote(mass=100)
    assert before.hull_mass_kt == 100
    assert before.damage_percent_if_one_hit == 100
    assert not before.cumulative_damage_calculated
    assert not before.web_fuel_burn_calculated
    assert not before.host_phase_order_verified
    assert not before.host_orders_accepted_verified


def test_no_tow_damage_quote_even_for_web_mines_and_cloaked_ship():
    for kind in ("NORMAL", "WEB"):
        for cloak in (True, False):
            with pytest.raises(MineImpactQuoteAbstain, match="towed"):
                quote(kind=kind, cloaked=cloak, tow=True)


def test_immutable_and_repeatable_output():
    a = quote(kind="WEB", mass=315, cloaked=True)
    b = quote(kind="WEB", mass=315, cloaked=True)
    assert a == b
    with pytest.raises(FrozenInstanceError):
        a.damage_percent_if_one_hit = 0


@pytest.mark.parametrize("bad", [
    {"kind": "PROTOFIELD"}, {"kind": "normal"}, {"kind": "WEB_MINE"},
    {"kind": None}, {"kind": True},
    {"mass": 0}, {"mass": -1}, {"mass": True}, {"mass": 1.0},
    {"mass": 1_000_001}, {"mass": None}, {"mass": "100"},
    {"cloaked": None}, {"cloaked": 0},
    {"tow": None}, {"tow": 1},
    {"confirmed_enemy_mine_context": False},
    {"confirmed_enemy_mine_context": 1},
    {"confirmed_hull_only_mass_without_components_fuel_or_cargo": False},
    {"ordinary_standard_impact_settings_confirmed": False},
    {"no_custom_or_racial_damage_modifiers_confirmed": None},
    {"hypothetical_one_impact_only_confirmed": False},
])
def test_bad_or_unproven_source_fails_closed(bad):
    with pytest.raises(MineImpactQuoteAbstain):
        quote(**bad)


def test_high_mass_returns_at_least_one_percent_without_guessing_zero_damage():
    r = quote(mass=1_000_000)
    assert r.damage_percent_if_one_hit == 1
    assert r.exact_damage_denominator == 1_000_001
