"""Conditional research integration of explicit standard construction targets.

Only fake fully controlled states. No legacy PlayerOrders/schema changes.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest

from planets_lab.sim.planetary_structure_turn_slice import (
    TURN_STATUS, STRUCTURE_PLACEMENTS, compare_structure_phase_placements,
    simulate_explicit_structure_turn,
)
from planets_lab.sim.standard_structure_build import StructureBuildTargets

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture


def context():
    before = fixture()
    before.ships.clear()
    return before


def owners(**kwargs):
    return {
        1: (StructureBuildTargets(planet_id=10, **kwargs),),
        2: (),  # explicit empty owner; never synthesized from absence
    }


def run(before, target, placement, **kwargs):
    return simulate_explicit_structure_turn(
        before, target, placement=placement,
        standard_rules_asserted=True,
        complete_structure_target_scope_asserted=True,
        **kwargs,
    )


@pytest.mark.parametrize("placement", STRUCTURE_PLACEMENTS)
def test_integrated_turn_is_deterministic_immutable_and_noncausal(placement):
    before = context()
    original = deepcopy(before)
    targets = owners(factories=11)
    a = run(before, targets, placement)
    b = run(before, targets, placement)
    assert a.supported and a.status == TURN_STATUS
    assert a.state == b.state and a.events == b.events
    assert a.state.turn == before.turn + 1
    assert a.state.planets[10].factories == 11
    assert len([e for e in a.events
                if e.phase == "standard_structure_build_conditional"]) == 1
    assert not a.nuhost_execution_verified
    assert not a.nuhost_phase_placement_verified
    assert not a.independent_host_parity_verified
    assert before == original


def test_factory_supply_production_differs_by_conditional_placement():
    before = context()
    target = owners(factories=11)
    compare = compare_structure_phase_placements(
        before, target, standard_rules_asserted=True,
        complete_structure_target_scope_asserted=True,
    )
    assert compare.status == "CONDITIONAL_PLACEMENTS_DISTINCT_NOT_HOST_VERIFIED"
    assert compare.observationally_distinct_final_states
    assert compare.before.state is not None and compare.after.state is not None
    assert compare.before.state.planets[10].factories == 11
    assert compare.after.state.planets[10].factories == 11
    # FactorySupplyPhase is inside the 14-phase economy block.
    # This is a model difference, not an observed Host schedule.
    assert (compare.before.state.planets[10].cargo.supplies
            - compare.after.state.planets[10].cargo.supplies) == 1
    assert not compare.nuhost_phase_placement_verified
    assert before.turn == 7


def test_income_can_fund_after_economy_but_not_before():
    before = context()
    before.planets[10].cargo.supplies = 0
    before.planets[10].cargo.megacredits = 0
    compare = compare_structure_phase_placements(
        before, owners(factories=11),
        standard_rules_asserted=True,
        complete_structure_target_scope_asserted=True,
        automatic_supply_sale_enabled=True,
    )
    assert compare.before.supported and compare.after.supported
    assert compare.before.state.planets[10].factories == 10
    assert compare.after.state.planets[10].factories == 11
    assert compare.observationally_distinct_final_states


def test_partial_order_does_not_rewrite_canonical_host_pipeline():
    from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
    before = context()
    frozen = tuple(x.name for x in PlanetaryHostPipeline().phases)
    after = run(before, owners(defense_posts=1), STRUCTURE_PLACEMENTS[1])
    assert after.supported
    assert before == context()
    assert tuple(x.name for x in PlanetaryHostPipeline().phases) == frozen
    assert len(frozen) == 14
    assert "standard_structure_build_conditional" not in frozen


@pytest.mark.parametrize("change", [
    "missing_owner", "duplicate_target", "wrong_owner", "no_targets",
    "wrong_target_type", "ships", "base", "storms", "no_supplies",
    "missing_complete_assertion", "missing_standard_assertion",
    "invalid_sale_flag", "unknown_phase", "invalid_target",
])
def test_missing_scope_or_unmodeled_rules_fail_closed(change):
    before = context()
    t = owners(factories=11)
    opts = dict(
        placement=STRUCTURE_PLACEMENTS[0],
        complete_structure_target_scope_asserted=True,
        standard_rules_asserted=True,
        automatic_supply_sale_enabled=False,
    )
    if change == "missing_owner": t.pop(2)
    elif change == "duplicate_target": t[1] += t[1]
    elif change == "wrong_owner": t = {1: (), 2: t[1]}
    elif change == "no_targets": t = {1: (), 2: ()}
    elif change == "wrong_target_type": t = {1: ({"planet_id": 10},), 2: ()}
    elif change == "ships": before.ships = fixture().ships
    elif change == "base":
        from planets_lab.core import Starbase
        before.starbases[10] = Starbase(planet_id=10, owner_id=1)
    elif change == "storms":
        from planets_lab.core import IonStorm
        before.ion_storms[1] = IonStorm(
            id=1, x=150, y=150, radius=50, voltage=10, warp=0, heading=0,
        )
    elif change == "no_supplies": before.metadata["no_supplies"] = True
    elif change == "missing_complete_assertion":
        opts["complete_structure_target_scope_asserted"] = False
    elif change == "missing_standard_assertion":
        opts["standard_rules_asserted"] = False
    elif change == "invalid_sale_flag": opts["automatic_supply_sale_enabled"] = "yes"
    elif change == "unknown_phase": opts["placement"] = "guessed_nuhost_phase"
    elif change == "invalid_target":
        t = owners(factories=9)  # below existing 10
    original = deepcopy(before)
    result = simulate_explicit_structure_turn(before, t, **opts)
    assert result.status == "ABSTAIN_STRUCTURE_TURN"
    assert not result.supported
    assert result.state is None
    assert not result.events
    assert not result.nuhost_execution_verified
    assert before == original


def test_research_targets_separate_from_owner_scoped_v1_v2_signatures():
    from dataclasses import fields
    from planets_lab.sim.orders import PlayerOrders
    from planets_lab.sim.planetary_owner_capture_v2 import OWNER_ROW_KEYS_V2
    assert tuple(field.name for field in fields(PlayerOrders)) == (
        "player_id", "ship_orders", "starbase_tech_orders",
    )
    assert OWNER_ROW_KEYS_V2 == frozenset(
        ("player_id", "ship_orders", "starbase_tech_orders")
    )
