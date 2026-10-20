"""M2 core construction V2: priority, partial budgets and 1:1 supply sale.

Uses fictional planets only; no archive order inference or NuHost parity.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest

from planets_lab.sim.standard_structure_build import (
    PRIORITY_RESEARCH_STATUS_FULL, PRIORITY_RESEARCH_STATUS_PARTIAL,
    StructureBuildTargets, forecast_priority_structure_build,
    forecast_standard_structure_build,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture


def planet(mc=100, supplies=100):
    p = fixture().planets[10]
    p.cargo.megacredits = mc
    p.cargo.supplies = supplies
    return p


def run(p, targets, sale=False):
    return forecast_priority_structure_build(
        p, targets, standard_rules_asserted=True,
        automatic_supply_sale_enabled=sale,
    )


def check_ledger(before, actual):
    assert actual.supported and actual.resulting_planet is not None
    after = actual.resulting_planet
    assert before.cargo.supplies - after.cargo.supplies == (
        actual.supplies_used_for_building + actual.supplies_sold_for_mc
    )
    assert before.cargo.megacredits + actual.supplies_sold_for_mc - (
        after.cargo.megacredits
    ) == actual.megacredits_spent_on_building
    assert after.cargo.supplies >= 0 and after.cargo.megacredits >= 0
    assert not actual.nuhost_execution_verified
    assert not actual.host_phase_position_verified


def test_exact_fully_funded_equivalent_to_v1_when_supply_sale_disabled():
    p = planet()
    original = deepcopy(p)
    targets = StructureBuildTargets(10, defense_posts=1, factories=12, mines=13)
    legacy = forecast_standard_structure_build(
        p, targets, standard_rules_asserted=True,
    )
    v2 = run(p, targets)
    assert v2.status == PRIORITY_RESEARCH_STATUS_FULL
    assert v2.resulting_planet == legacy.resulting_planet
    assert v2.supplies_used_for_building == legacy.spent_supplies == 6
    assert v2.megacredits_spent_on_building == legacy.spent_megacredits == 28
    assert v2.supplies_sold_for_mc == 0
    assert v2.built == (
        ("defense_posts", 1), ("factories", 2), ("mines", 3),
    )
    check_ledger(p, v2)
    assert p == original


def test_auto_sale_uses_one_supply_per_mc_and_one_for_the_structure():
    p = planet(mc=0, supplies=5)
    original = deepcopy(p)
    target = StructureBuildTargets(10, mines=11)
    no_sale = run(p, target, sale=False)
    assert no_sale.status == PRIORITY_RESEARCH_STATUS_PARTIAL
    assert no_sale.built == (("mines", 0),)
    assert no_sale.unbuilt == (("mines", 1),)
    with_sale = run(p, target, sale=True)
    assert with_sale.status == PRIORITY_RESEARCH_STATUS_FULL
    assert with_sale.supplies_sold_for_mc == 4
    assert with_sale.supplies_used_for_building == 1
    assert with_sale.megacredits_spent_on_building == 4
    assert with_sale.resulting_planet.cargo.supplies == 0
    assert with_sale.resulting_planet.cargo.megacredits == 0
    assert with_sale.resulting_planet.mines == 11
    check_ledger(p, with_sale)
    assert p == original


def test_not_enough_supply_to_build_and_sell_same_unit():
    p = planet(mc=0, supplies=4)
    result = run(p, StructureBuildTargets(10, mines=11), sale=True)
    assert result.status == PRIORITY_RESEARCH_STATUS_PARTIAL
    assert result.supplies_sold_for_mc == 0
    assert result.resulting_planet == p
    check_ledger(p, result)


def test_higher_priority_unaffordable_does_not_block_cheaper_types():
    p = planet(mc=6, supplies=2)
    target = StructureBuildTargets(10, defense_posts=1, factories=11, mines=11)
    result = run(p, target, sale=True)
    assert result.status == PRIORITY_RESEARCH_STATUS_PARTIAL
    assert result.built == (
        ("defense_posts", 0), ("factories", 1), ("mines", 0),
    )
    assert result.unbuilt == (
        ("defense_posts", 1), ("factories", 0), ("mines", 1),
    )
    assert result.resulting_planet.cargo.supplies == 1
    assert result.resulting_planet.cargo.megacredits == 3
    check_ledger(p, result)


def test_expensive_defense_skip_still_allows_factory_then_mine_with_sale():
    p = planet(mc=0, supplies=10)
    targets = StructureBuildTargets(10, defense_posts=1, factories=11, mines=11)
    result = run(p, targets, sale=True)
    assert result.built == (
        ("defense_posts", 0), ("factories", 1), ("mines", 1),
    )
    assert result.supplies_sold_for_mc == 7
    assert result.supplies_used_for_building == 2
    assert result.resulting_planet.cargo.supplies == 1
    check_ledger(p, result)


def test_defense_exhausts_all_supplies_if_budget_exact():
    p = planet(mc=0, supplies=11)
    targets = StructureBuildTargets(10, defense_posts=1, factories=11, mines=11)
    result = run(p, targets, sale=True)
    assert result.built == (
        ("defense_posts", 1), ("factories", 0), ("mines", 0),
    )
    assert result.supplies_sold_for_mc == 10
    assert result.resulting_planet.cargo.supplies == 0
    check_ledger(p, result)


def test_population_cap_clips_targets_without_silently_calling_full_match():
    p = planet(mc=1000, supplies=1000)
    p.cargo.clans = 20
    result = run(p, StructureBuildTargets(
        10, defense_posts=25, factories=30, mines=50,
    ))
    assert result.status == PRIORITY_RESEARCH_STATUS_PARTIAL
    assert result.capped_by_population == (
        "defense_posts", "factories", "mines",
    )
    assert result.resulting_planet.defense_posts == 20
    assert result.resulting_planet.factories == 20
    assert result.resulting_planet.mines == 20
    assert result.unbuilt == (
        ("defense_posts", 0), ("factories", 0), ("mines", 0),
    )
    check_ledger(p, result)


def test_overcap_historical_structures_are_not_silently_removed():
    p = planet()
    p.cargo.clans = 5
    original = deepcopy(p)
    result = run(p, StructureBuildTargets(10, mines=11))
    assert result.status == PRIORITY_RESEARCH_STATUS_PARTIAL
    assert result.capped_by_population == ("mines",)
    assert result.resulting_planet == p
    assert p == original
    check_ledger(p, result)


def test_zero_budget_is_supported_partial_not_abstention():
    p = planet(mc=0, supplies=0)
    target = StructureBuildTargets(10, mines=11)
    result = run(p, target, sale=True)
    assert result.supported and result.status == PRIORITY_RESEARCH_STATUS_PARTIAL
    assert result.unbuilt == (("mines", 1),)
    assert result.resulting_planet == p


@pytest.mark.parametrize("change,reason", [
    ("missing_rules", "standard"),
    ("wrong_id", "identity"),
    ("no_owner", "owner"),
    ("bool_target", "target"),
    ("target_downgrade", "downgrade"),
    ("bad_supply", "resources"),
    ("bad_mc", "resources"),
    ("bad_clans", "population"),
    ("bad_existing", "structures"),
    ("no_target", "target"),
    ("bad_sale", "boolean"),
])
def test_fail_closed_invalid_context_without_partial_state(change, reason):
    p = planet()
    target = StructureBuildTargets(10, mines=11)
    rule = True
    sale = False
    if change == "missing_rules": rule = False
    if change == "wrong_id": target = StructureBuildTargets(11, mines=11)
    if change == "no_owner": p.owner_id = None
    if change == "bool_target": target = StructureBuildTargets(10, mines=True)
    if change == "target_downgrade": target = StructureBuildTargets(10, mines=9)
    if change == "bad_supply": p.cargo.supplies = -1
    if change == "bad_mc": p.cargo.megacredits = -1
    if change == "bad_clans": p.cargo.clans = -1
    if change == "bad_existing": p.mines = -1
    if change == "no_target": target = StructureBuildTargets(10)
    if change == "bad_sale": sale = "on"
    original = deepcopy(p)
    result = forecast_priority_structure_build(
        p, target, standard_rules_asserted=rule,
        automatic_supply_sale_enabled=sale,
    )
    assert result.status == "ABSTAIN_UNSUPPORTED_PRIORITY_STRUCTURE_BUILD"
    assert reason in (result.reason or "")
    assert result.resulting_planet is None
    assert not result.supported
    assert p == original


@pytest.mark.parametrize("mc", (0, 1, 2, 3, 4, 6, 9, 10, 11, 20))
@pytest.mark.parametrize("supplies", (0, 1, 2, 3, 4, 5, 8, 10, 20))
@pytest.mark.parametrize("sale", (False, True))
def test_small_budget_grid_conserves_real_resources_without_overbuild(mc, supplies, sale):
    p = planet(mc=mc, supplies=supplies)
    before = deepcopy(p)
    t = StructureBuildTargets(10, defense_posts=1, factories=11, mines=12)
    forecast = run(p, t, sale=sale)
    check_ledger(p, forecast)
    assert p == before
    after = forecast.resulting_planet
    assert 0 <= after.defense_posts <= 1
    assert 10 <= after.factories <= 11
    assert 10 <= after.mines <= 12
    assert sum(count for _, count in forecast.built) == (
        forecast.supplies_used_for_building
    )
    if not sale:
        assert forecast.supplies_sold_for_mc == 0
