"""Classic saved-pointer standard queue × ship assembly × economy.

Fully fictional: all pointer/PBP/order/warehouse data are assertions,
and only standard, low-PBP, no-clone/uncontested Host subphase modeled.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

import pytest

from planets_lab.core import Ship, Starbase
from planets_lab.sim.classic_standard_queue_pointer import (
    ClassicBaseQueueEntry, ClassicStandardSubphase,
)
from planets_lab.sim.classic_standard_pointer_economy_turn import (
    STATUS, PLACEMENTS, ClassicOrdinaryBuild,
    simulate_classic_standard_pointer_economy_turn,
)
from planets_lab.sim.standard_ship_warehouse_assembly import StandardComponentWarehouse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "tools" / "diagnostics"))
from test_standard_unthrottled_multibase_queue import context as two_base_context


def context(*, existing=8, pointer=10):
    state, specs, design = two_base_context()
    # A third base declares an explicit NO-BUILD, demonstrating that the
    # queue must not silently act as though every base is a candidate.
    idle_planet = deepcopy(state.planets[10])
    idle_planet.id = 30
    idle_planet.owner_id = 1
    idle_planet.x, idle_planet.y = 350, 350
    state.planets[30] = idle_planet
    state.starbases[30] = Starbase(
        planet_id=30, owner_id=1, tech_hull=5,
        tech_engine=6, tech_beam=3, tech_torpedo=5,
    )
    for sid in range(1, existing + 1):
        state.ships[sid] = Ship(
            id=sid, owner_id=1, hull_id=7, x=100, y=100, warp=0,
        )
    roster = ClassicStandardSubphase(
        ship_limit=10,
        current_ship_count=existing,
        last_standard_build_planet_id=pointer,
        bases=(
            ClassicBaseQueueEntry(10, 1, True),
            ClassicBaseQueueEntry(20, 2, True),
            ClassicBaseQueueEntry(30, 1, False),
        ),
        player_pbps=((1, 20), (2, 0)),
        standard_phase_after_priorities_asserted=True,
        complete_starbase_roster_asserted=True,
        complete_player_pbp_balances_asserted=True,
        no_cloning_or_other_build_effects_asserted=True,
    )
    stock = {
        pid: ClassicOrdinaryBuild(
            blueprint=design,
            warehouse=StandardComponentWarehouse(),
            allowed_hull_ids=frozenset({7}),
        )
        for pid in (10, 20)
    }
    state.validate()
    return state, specs, roster, stock


def run(state, specs, selection, queue, **changes):
    options = dict(
        placement=PLACEMENTS[0],
        standard_rules_asserted=True,
        complete_warehouses_and_hull_rights_asserted=True,
        no_other_ship_base_or_combat_actions_asserted=True,
    )
    options.update(changes)
    return simulate_classic_standard_pointer_economy_turn(
        state, specs, selection, queue, **options,
    )


@pytest.mark.parametrize("placement", PLACEMENTS)
def test_pointer_order_controls_lowest_ship_ids_and_two_base_materials(placement):
    pre, specs, selection, queue = context()
    frozen = deepcopy((pre, specs, selection, queue))
    r = run(pre, specs, selection, queue, placement=placement)
    again = run(pre, specs, selection, queue, placement=placement)
    assert r == again
    assert r.supported and r.status == STATUS
    assert r.state.turn == pre.turn + 1
    assert r.selected_planet_ids == (20, 10)
    assert r.selected_ship_ids == (9, 10)
    assert r.last_standard_build_planet_id_after == 10
    assert r.state.ships[9].owner_id == 2
    assert r.state.ships[10].owner_id == 1
    assert (r.state.ships[9].x, r.state.ships[9].y) == (300, 300)
    assert (r.state.ships[10].x, r.state.ships[10].y) == (100, 100)
    assert len(r.build_receipts) == 2
    assert [x.starbase_planet_id for x in r.build_receipts] == [20, 10]
    assert [x.ship_id for x in r.build_receipts] == [9, 10]
    assert all(x.purchased.megacredits == 260 for x in r.build_receipts)
    assert len(r.planet_balances) == 3
    assert all(row.resource_balance_exact for row in r.planet_balances)
    assert r.state.starbases == pre.starbases
    assert not r.pointer_independently_witnessed
    assert not r.queue_selection_independently_witnessed
    assert not r.player_pbp_balances_independently_witnessed
    assert not r.ship_id_allocation_independently_witnessed
    assert not r.nuhost_execution_verified
    assert not r.independent_host_parity_verified
    assert not r.nuhost_phase_placement_verified
    assert (pre, specs, selection, queue) == frozen


def test_one_slot_skips_other_queued_base_without_charging_it():
    pre, specs, selection, queue = context(existing=9)
    result = run(pre, specs, selection, queue)
    assert result.supported
    assert result.selected_planet_ids == (20,)
    assert result.selected_ship_ids == (10,)
    assert result.last_standard_build_planet_id_after == 20
    assert len(result.build_receipts) == 1
    assert result.state.planets[10].cargo.megacredits >= pre.planets[10].cargo.megacredits
    assert result.warehouse_states_after[0] == (10, queue[10].warehouse)


def test_full_hard_ship_limit_keeps_pointer_and_builds_nothing():
    pre, specs, selection, queue = context(existing=10)
    result = run(pre, specs, selection, queue)
    assert result.supported
    assert result.selected_planet_ids == ()
    assert result.selected_ship_ids == ()
    assert result.last_standard_build_planet_id_after == 10
    assert result.build_receipts == ()
    assert set(result.state.ships) == set(pre.ships)
    assert len(result.planet_balances) == 3


def test_mixed_inventory_on_selected_base_but_unselected_untouched():
    pre, specs, selection, queue = context(existing=9)
    stocked = StandardComponentWarehouse(
        hulls=((7, 1),), engines=((9, 2),),
        beams=((3, 2),), launchers=((2, 1),),
    )
    queue[20] = replace(queue[20], warehouse=stocked)
    queue[10] = replace(queue[10], warehouse=StandardComponentWarehouse(
        hulls=((7, 2),),
    ))
    r = run(pre, specs, selection, queue)
    assert r.supported
    assert r.build_receipts[0].purchased.megacredits == 0
    stock_after = dict(r.warehouse_states_after)
    assert stock_after[10] == queue[10].warehouse
    assert stock_after[20].hulls == ((7, 0),)


def test_tax_revenue_supports_after_economy_pointer_build_only():
    pre, specs, selection, queue = context(existing=9)
    pre.planets[20].cargo.megacredits = 259
    early = run(pre, specs, selection, queue, placement=PLACEMENTS[0])
    late = run(pre, specs, selection, queue, placement=PLACEMENTS[1])
    assert not early.supported and early.state is None
    assert late.supported
    assert late.planet_balances[1].taxes_collected > 0
    assert late.selected_planet_ids == (20,)


@pytest.mark.parametrize("bad", (
    "missing_full_base", "missing_idle_roster", "queue_missing_candidate",
    "priority_21_pbp", "pb_code", "clone", "missing_pointer",
    "missing_phase_assert", "missing_warehouse_assert",
    "moving_ship", "bad_fleet_count", "bad_limit",
    "wrong_owner", "invalid_seed", "bad_placement",
    "resource_shortfall_second", "fake_component_stock",
    "invalid_ordinary_order",
))
def test_unsupported_scope_and_late_build_failure_no_partial_result(bad):
    pre, specs, selected, queue = context()
    opts = {}
    if bad == "missing_full_base": pre.starbases.pop(30)
    elif bad == "missing_idle_roster":
        selected = replace(selected, bases=selected.bases[:2])
    elif bad == "queue_missing_candidate": queue.pop(10)
    elif bad == "priority_21_pbp":
        selected = replace(selected, player_pbps=((1, 21), (2, 0)))
    elif bad == "pb_code":
        selected = replace(selected, bases=(
            replace(selected.bases[0], priority_build_code=1),
            *selected.bases[1:],
        ))
    elif bad == "clone":
        selected = replace(selected, bases=(
            replace(selected.bases[0], clone_ordered=True),
            *selected.bases[1:],
        ))
    elif bad == "missing_pointer":
        selected = replace(selected, last_standard_build_planet_id=None)
    elif bad == "missing_phase_assert":
        selected = replace(selected, standard_phase_after_priorities_asserted=False)
    elif bad == "missing_warehouse_assert":
        opts["complete_warehouses_and_hull_rights_asserted"] = False
    elif bad == "moving_ship": pre.ships[1].warp = 9
    elif bad == "bad_fleet_count":
        selected = replace(selected, current_ship_count=9)
    elif bad == "bad_limit": selected = replace(selected, ship_limit=1000)
    elif bad == "wrong_owner": pre.starbases[20].owner_id = 1
    elif bad == "invalid_seed": opts["seed"] = True
    elif bad == "bad_placement": opts["placement"] = "claimed_real_nuhost_order"
    elif bad == "resource_shortfall_second": pre.planets[10].cargo.megacredits = 0
    elif bad == "fake_component_stock":
        queue[10] = replace(queue[10], warehouse=StandardComponentWarehouse(
            hulls=((999, 1),),
        ))
    elif bad == "invalid_ordinary_order": queue[20] = {"not_a_build": True}
    snapshot = deepcopy((pre, specs, selected, queue))
    result = run(pre, specs, selected, queue, **opts)
    assert result.status == "ABSTAIN_CLASSIC_POINTER_ECONOMIC_TURN"
    assert not result.supported
    assert result.state is None
    assert result.selected_planet_ids == ()
    assert result.selected_ship_ids == ()
    assert result.build_receipts == ()
    assert result.planet_balances == ()
    assert result.economic_events == ()
    assert not result.nuhost_execution_verified
    assert (pre, specs, selected, queue) == snapshot


@pytest.mark.parametrize("tamper", (
    "missing_component_debit", "bad_second_ship", "planet_stock",
    "ground_stock", "missing_mining_receipt",
))
def test_unaccounted_state_or_receipt_abstains_across_whole_phase(monkeypatch, tamper):
    import planets_lab.sim.classic_standard_pointer_economy_turn as module
    real_assemble = module._execute_all_selected
    real_host = module.HostEngine.step
    calls = 0

    def mutated_build(*args, **kwargs):
        nonlocal calls
        calls += 1
        after, receipts = real_assemble(*args, **kwargs)
        if tamper in ("missing_component_debit", "bad_second_ship") and calls == 2:
            after = deepcopy(after)
            if tamper == "missing_component_debit":
                after.planets[10].cargo.duranium += 1
            else:
                after.ships[10].crew += 1
        return after, receipts

    def mutated_econ(self, state, orders, *, seed=0):
        after, events = real_host(self, state, orders, seed=seed)
        after = deepcopy(after)
        if tamper == "planet_stock": after.planets[20].cargo.megacredits += 1
        elif tamper == "ground_stock": after.planets[20].ground_duranium.amount += 1
        elif tamper == "missing_mining_receipt":
            events = tuple(e for e in events if e.phase != "mineral_mining")
        return after, events

    monkeypatch.setattr(module, "_execute_all_selected", mutated_build)
    monkeypatch.setattr(module.HostEngine, "step", mutated_econ)
    pre, specs, selection, queue = context()
    before = deepcopy(pre)
    r = run(pre, specs, selection, queue)
    assert not r.supported
    assert r.state is None and r.build_receipts == ()
    assert pre == before


def test_no_mutation_to_signed_orders_or_canonical_14_phase_economy():
    from dataclasses import fields
    from planets_lab.sim.orders import PlayerOrders
    from planets_lab.sim.planetary_owner_capture_v2 import OWNER_ROW_KEYS_V2
    from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
    assert len(PlanetaryHostPipeline().phases) == 14
    assert tuple(f.name for f in fields(PlayerOrders)) == (
        "player_id", "ship_orders", "starbase_tech_orders",
    )
    assert OWNER_ROW_KEYS_V2 == frozenset(
        ("player_id", "ship_orders", "starbase_tech_orders")
    )
