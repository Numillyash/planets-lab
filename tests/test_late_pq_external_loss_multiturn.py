"""Test full conditional late PQ carry with EXTERNAL exact loss boundary."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from planets_lab.sim.late_pq_external_loss_multiturn import (
    STATUS, LatePQCarry, LatePQTurnBase, LatePQExplicitTurn,
    simulate_bounded_late_pq_external_loss_carry,
)
from planets_lab.sim.standard_ship_warehouse_assembly import StandardComponentWarehouse
from test_late_pq_external_regular_economy import fixture, run as one_turn_run


def setup():
    state, specs, ctx = fixture()
    carry = LatePQCarry(
        soft_ship_limit=ctx.soft_ship_limit,
        player_pp=ctx.player_pp,
        base_warehouses=tuple(
            (row.planet_id, row.warehouse) for row in ctx.all_bases
        ),
    )
    roster = tuple(
        LatePQTurnBase(row.planet_id, row.blueprint,
                       row.allowed_hull_ids or frozenset())
        for row in ctx.all_bases
    )
    first = LatePQExplicitTurn(
        bases=roster, selected_planet_id=20, selected_ship_id=10,
        placement="late_pq_build_before_economy",
    )
    modeled = one_turn_run(state, specs, ctx)
    assert modeled.supported
    snapshot = modeled.state.clone()
    snapshot.ships.pop(1)
    second = LatePQExplicitTurn(
        bases=roster, selected_planet_id=10, selected_ship_id=1,
        placement="late_pq_build_after_economy",
        external_removed_ship_id=1,
        externally_supplied_preturn_state=snapshot,
        external_single_inert_ship_loss_asserted=True,
    )
    return state, specs, carry, (first, second)


def run(state, specs, carry, plans, **overrides):
    options = dict(
        standard_rules_asserted=True,
        complete_all_turn_queues_and_warehouses_asserted=True,
        exact_external_loss_snapshots_asserted=True,
        no_other_interturn_planet_pp_fleet_mutations_asserted=True,
    )
    options.update(overrides)
    return simulate_bounded_late_pq_external_loss_carry(
        state, specs, carry, plans, **options,
    )


def test_consecutive_two_turns_carry_warehouse_pp_exact_external_slot_reopening():
    state, specs, carry, plans = setup()
    frozen = deepcopy((state, specs, carry, plans))
    result = run(state, specs, carry, plans)
    assert result.supported and result.status == STATUS
    assert result == run(state, specs, carry, plans)
    assert result.state.turn == state.turn + 2
    assert len(result.state.ships) == carry.soft_ship_limit
    assert set(result.state.ships) == (set(state.ships) - {1}) | {10, 1}
    assert result.state.ships[10].owner_id == 2
    assert result.state.ships[1].owner_id == 1
    assert [row.built_ship_id for row in result.turns] == [10, 1]
    assert [row.externally_removed_ship_id for row in result.turns] == [None, 1]
    assert [row.selected_base_id for row in result.turns] == [20, 10]
    assert all(row.planet_balance_exact for row in result.turns)
    assert result.carry_after.player_pp == ((1, 3), (2, 7))
    assert dict(result.carry_after.base_warehouses)[30] == StandardComponentWarehouse()
    assert len(result.carry_after.base_warehouses) == 3
    assert not result.externally_removed_ship_independently_verified
    assert not result.random_pq_selection_independently_verified
    assert not result.accepted_orders_verified
    assert not result.nuhost_execution_verified
    assert not result.nuhost_phase_order_verified
    assert not result.independent_host_parity_verified
    assert (state, specs, carry, plans) == frozen


def test_reused_warehouse_is_depleted_on_first_build_then_second_purchases_parts():
    state, specs, carry, plans = setup()
    full = StandardComponentWarehouse(
        hulls=((7, 1),), engines=((9, 2),),
        beams=((3, 2),), launchers=((2, 1),),
    )
    # First modeled turn's selected base 20 consumes the full inventory.
    warehouses = list(carry.base_warehouses)
    warehouses[1] = (20, full)
    carry = replace(carry, base_warehouses=tuple(warehouses))
    first_state, _, ctx = fixture()
    bases = list(ctx.all_bases)
    bases[1] = replace(bases[1], warehouse=full)
    ctx = replace(ctx, all_bases=tuple(bases))
    modeled = one_turn_run(first_state, specs, ctx)
    assert modeled.supported
    snapshot = modeled.state.clone()
    snapshot.ships.pop(1)
    second = replace(
        plans[1], selected_planet_id=20,
        externally_supplied_preturn_state=snapshot,
    )
    output = run(state, specs, carry, (plans[0], second))
    assert output.supported
    after = dict(output.carry_after.base_warehouses)[20]
    assert after.hulls == ((7, 0),)
    assert after.engines == ((9, 0),)
    assert output.carry_after.player_pp == carry.player_pp
    # If the stocks had magically replenished, this second 260 MC
    # purchase would instead have cost nothing.
    assert output.state.planets[20].cargo.megacredits < snapshot.planets[20].cargo.megacredits


@pytest.mark.parametrize("case", (
    "missing_second_snapshot", "no_loss_assertion", "bool_loss_id",
    "wrong_removed_id", "double_loss", "phantom_extra_ship",
    "invented_planet_mc", "changed_base_owner", "advanced_preturn_turn",
    "preturn_wrong_pp", "initial_external_loss", "incomplete_base_plan",
    "duplicate_plan_base", "one_queued_only", "idle_selected",
    "wrong_second_id", "first_wrong_id", "missing_pp_owner",
    "negative_idle_warehouse", "unknown_stock", "incomplete_history",
    "no_standard", "missing_turns", "invalid_seed", "no_external_claim",
    "unsupported_placement", "moving_removed_ship", "ship_cargo_loss",
    "after_first_broken_economy",
))
def test_invalid_second_turn_or_loss_boundary_abstains_entire_history(case, monkeypatch):
    state, specs, carry, plans = setup()
    steps = list(plans)
    second = steps[1]
    options = {}
    if case == "missing_second_snapshot":
        second = replace(second, externally_supplied_preturn_state=None)
    elif case == "no_loss_assertion":
        second = replace(second, external_single_inert_ship_loss_asserted=False)
    elif case == "bool_loss_id":
        second = replace(second, external_removed_ship_id=True)
    elif case == "wrong_removed_id":
        second = replace(second, external_removed_ship_id=2)
    elif case == "double_loss":
        snap = second.externally_supplied_preturn_state.clone()
        snap.ships.pop(2)
        second = replace(second, externally_supplied_preturn_state=snap)
    elif case == "phantom_extra_ship":
        snap = second.externally_supplied_preturn_state.clone()
        snap.ships[45] = deepcopy(snap.ships[3])
        snap.ships[45].id = 45
        second = replace(second, externally_supplied_preturn_state=snap)
    elif case == "invented_planet_mc":
        snap = second.externally_supplied_preturn_state.clone()
        snap.planets[20].cargo.megacredits += 1
        second = replace(second, externally_supplied_preturn_state=snap)
    elif case == "changed_base_owner":
        snap = second.externally_supplied_preturn_state.clone()
        snap.starbases[20].owner_id = 1
        second = replace(second, externally_supplied_preturn_state=snap)
    elif case == "advanced_preturn_turn":
        snap = second.externally_supplied_preturn_state.clone()
        snap.turn += 1
        second = replace(second, externally_supplied_preturn_state=snap)
    elif case == "preturn_wrong_pp":
        carry = replace(carry, player_pp=((1, 3), (2, True)))
    elif case == "initial_external_loss":
        steps[0] = replace(steps[0], external_removed_ship_id=1)
    elif case == "incomplete_base_plan":
        second = replace(second, bases=second.bases[:2])
    elif case == "duplicate_plan_base":
        second = replace(second, bases=(second.bases[0],second.bases[0],second.bases[2]))
    elif case == "one_queued_only":
        rows = list(second.bases)
        rows[1] = replace(rows[1], blueprint=None, allowed_hull_ids=frozenset())
        second = replace(second, bases=tuple(rows))
    elif case == "idle_selected":
        second = replace(second, selected_planet_id=30)
    elif case == "wrong_second_id":
        second = replace(second, selected_ship_id=11)
    elif case == "first_wrong_id":
        steps[0] = replace(steps[0], selected_ship_id=11)
    elif case == "missing_pp_owner":
        carry = replace(carry, player_pp=((1, 3),))
    elif case == "negative_idle_warehouse":
        stock = list(carry.base_warehouses)
        stock[2] = (30, StandardComponentWarehouse(hulls=((7,-1),)))
        carry = replace(carry, base_warehouses=tuple(stock))
    elif case == "unknown_stock":
        stock = list(carry.base_warehouses)
        stock[2] = (30, StandardComponentWarehouse(hulls=((999, 1),)))
        carry = replace(carry, base_warehouses=tuple(stock))
    elif case == "incomplete_history":
        steps.append(second)
    elif case == "no_standard":
        options["standard_rules_asserted"] = False
    elif case == "missing_turns":
        steps = [steps[0]]
    elif case == "invalid_seed":
        options["seed"] = True
    elif case == "no_external_claim":
        options["exact_external_loss_snapshots_asserted"] = False
    elif case == "unsupported_placement":
        second = replace(second, placement="actual_host_order")
    elif case == "moving_removed_ship":
        state.ships[1].warp = 8
    elif case == "ship_cargo_loss":
        state.ships[1].cargo.megacredits = 1
    elif case == "after_first_broken_economy":
        import planets_lab.sim.late_pq_external_loss_multiturn as mod
        actual = mod.simulate_late_pq_external_selected_economic_turn
        calls = [0]
        def malicious(*args, **kwargs):
            calls[0] += 1
            result = actual(*args, **kwargs)
            if calls[0] == 2:
                return replace(result, player_pp_after=((1,4),(2,7)))
            return result
        monkeypatch.setattr(mod, "simulate_late_pq_external_selected_economic_turn", malicious)
    if len(steps) > 1:\n        steps[1] = second\n    frozen = deepcopy((state, specs, carry, tuple(steps)))
    output = run(state, specs, carry, tuple(steps), **options)
    assert not output.supported
    assert output.state is None and output.carry_after is None
    assert output.turns == ()
    assert (state, specs, carry, tuple(steps)) == frozen
