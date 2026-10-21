"""Selected ship construction + 14 standard economic phases, model only.

All cases are fictional: no Host receipt, real queue, private snapshot,
global ship-ID allocator or heldout corpus is accessed.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

import pytest

from planets_lab.core import Ship
from planets_lab.sim.standard_ship_economy_turn import (
    PLACEMENTS, STATUS, simulate_selected_ship_economy_turn,
)
from planets_lab.sim.standard_ship_warehouse_assembly import (
    ComponentUse, SelectedBuildSlot, StandardComponentWarehouse,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture
from test_standard_ship_component_quote import pre


def context():
    state = fixture()
    state.ships.clear()
    planet, base, specs, blueprint = pre()
    state.planets[10] = deepcopy(planet)
    state.starbases[10] = deepcopy(base)
    state.validate()
    return state, specs, blueprint


def slot():
    return SelectedBuildSlot(
        starbase_planet_id=10, proposed_ship_id=17,
        global_ship_limit=500,
        complete_global_ship_roster_asserted=True,
        queue_selection_asserted=True,
    )


def run(state, specs, blueprint, warehouse=None, selection=None, **changes):
    args = dict(
        placement=PLACEMENTS[0],
        allowed_hull_ids=frozenset({7}),
        standard_rules_asserted=True,
        complete_warehouse_asserted=True,
        hull_eligibility_asserted=True,
        standard_hull_crew_asserted=True,
        no_other_ship_or_base_actions_asserted=True,
        uncontested_single_prelimit_build_asserted=True,
    )
    args.update(changes)
    return simulate_selected_ship_economy_turn(
        state, specs, blueprint,
        warehouse if warehouse is not None else StandardComponentWarehouse(),
        selection if selection is not None else slot(), **args,
    )


@pytest.mark.parametrize("placement", PLACEMENTS)
def test_complete_turn_creates_exact_ship_and_preserves_economic_ledgers(placement):
    state, specs, blueprint = context()
    initial = deepcopy((state, specs, blueprint))
    first = run(state, specs, blueprint, placement=placement)
    again = run(state, specs, blueprint, placement=placement)
    assert first == again
    assert first.status == STATUS and first.supported
    assert first.state.turn == state.turn + 1
    assert first.state.ships[17].id == 17
    assert len(first.planet_balances) == 1
    assert first.planet_balances[0].planet_id == 10
    assert first.planet_balances[0].taxes_collected > 0
    assert sum(first.planet_balances[0].mined_minerals) > 0
    assert first.ship_balance.material_debit_exact
    assert first.ship_balance.warehouse_debit_exact
    assert first.ship_balance.assembled_ship_exact
    assert first.ship_balance.purchased.megacredits == 260
    assert (first.ship_balance.purchased.duranium,
            first.ship_balance.purchased.tritanium,
            first.ship_balance.purchased.molybdenum) == (9, 13, 6)
    assert not first.nuhost_execution_verified
    assert not first.independently_verified_queue_order
    assert not first.independently_verified_ship_id
    assert not first.independently_verified_warehouse
    assert not first.nuhost_phase_placement_verified
    assert not first.independent_host_parity_verified
    assert (state, specs, blueprint) == initial


def test_mined_duranium_can_make_after_economy_assembly_eligible():
    state, specs, blueprint = context()
    state.planets[10].cargo.duranium = 0
    frozen = deepcopy(state)
    early = run(state, specs, blueprint, placement=PLACEMENTS[0])
    late = run(state, specs, blueprint, placement=PLACEMENTS[1])
    assert early.status == "ABSTAIN_SELECTED_SHIP_ECONOMIC_TURN"
    assert early.state is None and early.planet_balances == ()
    assert late.supported
    assert late.state.planets[10].cargo.duranium >= 0
    assert late.planet_balances[0].mined_minerals[1] >= 9
    assert state == frozen
    assert not late.nuhost_phase_placement_verified


def test_tax_can_finance_after_economy_assembly_but_not_earlier():
    state, specs, blueprint = context()
    state.planets[10].cargo.megacredits = 259
    first = run(state, specs, blueprint, placement=PLACEMENTS[0])
    second = run(state, specs, blueprint, placement=PLACEMENTS[1])
    assert not first.supported
    assert second.supported
    assert second.planet_balances[0].taxes_collected > 0
    assert second.state.planets[10].cargo.megacredits >= 0


def test_warehouse_deducts_only_new_parts_across_full_turn():
    state, specs, blueprint = context()
    warehouse = StandardComponentWarehouse(
        hulls=((7, 1),), engines=((9, 1),),
        beams=((3, 1),), launchers=((2, 0),),
    )
    copy = deepcopy((state, warehouse))
    completed = run(state, specs, blueprint, warehouse=warehouse,
                    placement=PLACEMENTS[1])
    assert completed.supported
    assert completed.ship_balance.purchased.megacredits == 90
    assert completed.ship_balance.warehouse_after == StandardComponentWarehouse(
        hulls=((7, 0),), engines=((9, 0),),
        beams=((3, 0),), launchers=((2, 0),),
    )
    assert completed.ship_balance.component_ledger[0] == ComponentUse(
        "hulls", 7, 1, 0,
    )
    assert (state, warehouse) == copy


def test_full_warehouse_requires_no_planetary_expenditure():
    state, specs, blueprint = context()
    stock = StandardComponentWarehouse(
        hulls=((7, 1),), engines=((9, 2),),
        beams=((3, 2),), launchers=((2, 1),),
    )
    state.planets[10].cargo.megacredits = 0
    state.planets[10].cargo.duranium = 0
    state.planets[10].cargo.tritanium = 0
    state.planets[10].cargo.molybdenum = 0
    completed = run(state, specs, blueprint, warehouse=stock)
    assert completed.supported
    assert completed.ship_balance.purchased.megacredits == 0
    assert completed.ship_balance.purchased.duranium == 0
    assert completed.ship_balance.purchased.tritanium == 0
    assert completed.ship_balance.purchased.molybdenum == 0
    assert all(x.newly_purchased == 0 for x in completed.ship_balance.component_ledger)


@pytest.mark.parametrize("case", (
    "missing_queue_assertion", "missing_stock_assertion", "missing_rules",
    "missing_ship_actions_scope", "missing_uncontested_slot_scope",
    "invalid_placement", "invalid_seed", "ship_id_reused", "ship_limit_full",
    "second_starbase", "unknown_game_modifiers", "unsupported_ship_mission",
    "unknown_hull", "unlicensed_hull", "fake_warehouse",
))
def test_unsupported_context_abstains_without_exposing_state(case):
    state, specs, design = context()
    opts = {}
    selected = slot()
    warehouse = StandardComponentWarehouse()
    if case == "missing_queue_assertion":
        selected = replace(selected, queue_selection_asserted=False)
    elif case == "missing_stock_assertion": opts["complete_warehouse_asserted"] = False
    elif case == "missing_rules": opts["standard_rules_asserted"] = False
    elif case == "missing_ship_actions_scope":
        opts["no_other_ship_or_base_actions_asserted"] = False
    elif case == "missing_uncontested_slot_scope":
        opts["uncontested_single_prelimit_build_asserted"] = False
    elif case == "invalid_placement": opts["placement"] = "real_host_order_claim"
    elif case == "invalid_seed": opts["seed"] = True
    elif case == "ship_id_reused":
        occupied = Ship(id=17, owner_id=1, hull_id=7, x=100, y=100)
        state.ships[17] = occupied
    elif case == "ship_limit_full":
        selected = replace(selected, global_ship_limit=1)
        state.ships[99] = Ship(id=99, owner_id=1, hull_id=7, x=100, y=100)
    elif case == "second_starbase":
        from planets_lab.core import Starbase, Planet
        state.planets[20] = Planet(id=20, owner_id=2, x=300, y=300)
        state.starbases[20] = Starbase(planet_id=20, owner_id=2)
    elif case == "unknown_game_modifiers": state.metadata["unknown_option"] = 1
    elif case == "unsupported_ship_mission":
        state.ships[99] = Ship(id=99, owner_id=1, hull_id=7, x=100, y=100,
                               mission="tow")
    elif case == "unknown_hull": design = replace(design, hull_id=999)
    elif case == "unlicensed_hull": opts["allowed_hull_ids"] = frozenset({2})
    elif case == "fake_warehouse":
        warehouse = StandardComponentWarehouse(hulls=((999, 1),))
    original = deepcopy((state, specs, design, warehouse, selected))
    result = run(state, specs, design, warehouse, selected, **opts)
    assert result.status == "ABSTAIN_SELECTED_SHIP_ECONOMIC_TURN"
    assert result.state is None and result.events == ()
    assert result.planet_balances == () and result.ship_balance is None
    assert not result.nuhost_execution_verified
    assert (state, specs, design, warehouse, selected) == original


@pytest.mark.parametrize("corruption", (
    "bad_cost", "fake_stock", "bad_new_ship", "extra_new_ship",
    "unexpected_old_ship_mutation", "unmodeled_material_gain",
    "unmodeled_mineral_loss", "unmodeled_tax_gain",
))
def test_corrupted_local_assembly_or_economic_state_abstains(monkeypatch, corruption):
    import planets_lab.sim.standard_ship_economy_turn as mod
    original_assembly = mod.assemble_selected_standard_ship
    original_host = mod.HostEngine.step

    def wrong_assembly(*args, **kwargs):
        result = original_assembly(*args, **kwargs)
        assert result.supported
        if corruption == "bad_cost":
            return replace(result, purchased_cost=replace(
                result.purchased_cost, duranium=result.purchased_cost.duranium + 1,
            ))
        if corruption == "fake_stock":
            return replace(result, warehouse_after=StandardComponentWarehouse(
                hulls=((7, 1),),
            ))
        if corruption == "bad_new_ship":
            altered = deepcopy(result.phase_state)
            altered.ships[17].crew += 1
            return replace(result, phase_state=altered, assembled_ship=altered.ships[17])
        return result

    def wrong_host(self, state, orders, *, seed=0):
        after, events = original_host(self, state, orders, seed=seed)
        after = deepcopy(after)
        if corruption == "extra_new_ship":
            after.ships[99] = Ship(id=99, owner_id=1, hull_id=7, x=100, y=100)
        elif corruption == "unexpected_old_ship_mutation":
            after.ships[17].cargo.supplies += 1
        elif corruption == "unmodeled_material_gain":
            after.planets[10].cargo.duranium += 1
        elif corruption == "unmodeled_mineral_loss":
            after.planets[10].ground_duranium.amount -= 1
        elif corruption == "unmodeled_tax_gain":
            after.planets[10].cargo.megacredits += 1
        return after, events

    monkeypatch.setattr(mod, "assemble_selected_standard_ship", wrong_assembly)
    monkeypatch.setattr(mod.HostEngine, "step", wrong_host)
    state, specs, blueprint = context()
    initial = deepcopy(state)
    outcome = run(state, specs, blueprint)
    assert outcome.status == "ABSTAIN_SELECTED_SHIP_ECONOMIC_TURN"
    assert outcome.state is None and outcome.planet_balances == ()
    assert outcome.ship_balance is None and outcome.events == ()
    assert state == initial


def test_canonical_pipeline_and_signed_owner_order_schema_unchanged():
    from dataclasses import fields
    from planets_lab.sim.orders import PlayerOrders
    from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
    from planets_lab.sim.planetary_owner_capture_v2 import OWNER_ROW_KEYS_V2
    assert len(PlanetaryHostPipeline().phases) == 14
    assert tuple(field.name for field in fields(PlayerOrders)) == (
        "player_id", "ship_orders", "starbase_tech_orders",
    )
    assert OWNER_ROW_KEYS_V2 == frozenset((
        "player_id", "ship_orders", "starbase_tech_orders",
    ))
