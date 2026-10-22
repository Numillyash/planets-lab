"""Capped late PQ queues cannot make ordinary ships without free slots."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from planets_lab.sim.late_pq_capped_no_build_carry import (
    STATUS, CappedPQBaseIntent, CappedPQCarry, CappedPQNoBuildTurn,
    simulate_soft_capped_pq_no_build_carry,
)
from planets_lab.sim.standard_ship_warehouse_assembly import StandardComponentWarehouse
from test_late_pq_external_regular_economy import fixture, run as one_turn_run


def fixture_capped():
    before, specs, pqctx = fixture()
    built = one_turn_run(before, specs, pqctx)
    assert built.supported and built.state is not None
    state = built.state
    assert len(state.ships) == pqctx.soft_ship_limit
    first = CappedPQNoBuildTurn(
        all_bases=tuple(CappedPQBaseIntent(
            planet_id=row.planet_id, blueprint=row.blueprint,
            allowed_hull_ids=row.allowed_hull_ids or frozenset(),
        ) for row in pqctx.all_bases),
        no_priority_or_special_orders_on_this_turn_asserted=True,
    )
    rows = list(first.all_bases)
    rows[0] = replace(rows[0], blueprint=None, allowed_hull_ids=frozenset())
    rows[2] = replace(
        rows[2], blueprint=rows[1].blueprint, allowed_hull_ids=frozenset({7}),
    )
    second = CappedPQNoBuildTurn(
        all_bases=tuple(rows),
        no_priority_or_special_orders_on_this_turn_asserted=True,
    )
    carry = CappedPQCarry(
        soft_ship_limit=pqctx.soft_ship_limit,
        owner_pp=pqctx.player_pp,
        all_base_warehouses=built.warehouses_after,
    )
    return state, specs, carry, (first, second)


def run(state, specs, carry, plans, **overrides):
    flags = dict(
        standard_rules_asserted=True,
        complete_owner_planet_base_fleet_and_queue_roster_asserted=True,
        no_priority_clone_mining_stations_or_external_actions_asserted=True,
        default_no_pp_income_or_regular_pp_spend_asserted=True,
    )
    flags.update(overrides)
    return simulate_soft_capped_pq_no_build_carry(
        state, specs, carry, plans, **flags,
    )


def test_two_soft_capped_turns_do_not_build_or_debit_waiting_ship_orders():
    state, specs, carry, plans = fixture_capped()
    frozen = deepcopy((state, specs, carry, plans))
    result = run(state, specs, carry, plans)
    assert result.status == STATUS and result.supported
    assert result == run(state, specs, carry, plans)
    assert result.state.turn == state.turn + 2
    assert set(result.state.ships) == set(state.ships)
    assert result.state.ships == state.ships
    assert result.state.starbases == state.starbases
    assert result.carry_after == carry
    assert result.carry_after.owner_pp == ((1,3),(2,7))
    assert len(result.turns) == 2
    assert result.turns[0].queued_base_ids == (10,20)
    assert result.turns[1].queued_base_ids == (20,30)
    assert all(row.built_ship_ids == () for row in result.turns)
    assert all(row.all_planet_ledgers_exact for row in result.turns)
    assert all(len(row.planet_balances) == 3 for row in result.turns)
    assert all(
        x.resource_balance_exact for turn in result.turns
        for x in turn.planet_balances
    )
    assert not result.nuhost_regular_queue_selection_verified
    assert not result.independently_verified_no_priority_orders
    assert not result.independent_host_economy_verified
    assert not result.nuhost_execution_verified
    assert not result.nuhost_phase_order_verified
    assert not result.independent_host_parity_verified
    assert (state, specs, carry, plans) == frozen


def test_eight_no_build_turns_keep_same_warehouses_and_full_fleet():
    state, specs, carry, plans = fixture_capped()
    sequence = plans * 4
    result = run(state, specs, carry, sequence)
    assert result.supported
    assert result.state.turn == state.turn + 8
    assert result.state.ships == state.ships
    assert result.carry_after == carry
    assert len(result.turns) == 8


@pytest.mark.parametrize("case", (
    "below_soft_cap", "above_soft_cap", "missing_base",
    "duplicate_base", "one_queued_base", "unknown_queued_hull",
    "unknown_engine", "idle_has_rights", "no_perturn_assertion",
    "missing_stock", "duplicate_stock", "negative_idle_stock",
    "unknown_unselected_stock", "unknown_owner_pp", "duplicate_pp",
    "boolean_pp", "wrong_planet_owner", "old_ship_moving",
    "bool_ship_id", "custom_metadata", "no_standard_rules",
    "no_full_roster_claim", "no_other_action_exclusion",
    "no_default_pp", "bool_seed", "only_one_turn",
    "nine_turns", "wrong_soft_limit", "not_full_queue",
))
def test_unsupported_cap_state_or_plan_abstains_entire_sequence(case):
    state, specs, carry, plans = fixture_capped()
    rows = list(plans[1].all_bases)
    history = list(plans)
    stock = list(carry.all_base_warehouses)
    options = {}
    if case == "below_soft_cap":
        state.ships.pop(10)
    elif case == "above_soft_cap":
        state.ships[11] = deepcopy(state.ships[10])
        state.ships[11].id = 11
    elif case == "missing_base":
        rows.pop()
    elif case == "duplicate_base":
        rows[2] = rows[1]
    elif case == "one_queued_base":
        rows[1] = replace(rows[1], blueprint=None, allowed_hull_ids=frozenset())
    elif case == "unknown_queued_hull":
        rows[1] = replace(rows[1], blueprint=replace(rows[1].blueprint, hull_id=999))
    elif case == "unknown_engine":
        rows[1] = replace(rows[1], blueprint=replace(rows[1].blueprint, engine_id=999))
    elif case == "idle_has_rights":
        rows[0] = replace(rows[0], allowed_hull_ids=frozenset({7}))
    elif case == "no_perturn_assertion":
        history[1] = replace(history[1], no_priority_or_special_orders_on_this_turn_asserted=False)
    elif case == "missing_stock":
        stock.pop()
    elif case == "duplicate_stock":
        stock[2] = stock[0]
    elif case == "negative_idle_stock":
        stock[2] = (30, StandardComponentWarehouse(hulls=((7,-1),)))
    elif case == "unknown_unselected_stock":
        stock[2] = (30, StandardComponentWarehouse(hulls=((999,1),)))
    elif case == "unknown_owner_pp":
        carry = replace(carry, owner_pp=((1,3),))
    elif case == "duplicate_pp":
        carry = replace(carry, owner_pp=((1,3),(1,7)))
    elif case == "boolean_pp":
        carry = replace(carry, owner_pp=((1,True),(2,7)))
    elif case == "wrong_planet_owner":
        state.planets[20].owner_id = 1
    elif case == "old_ship_moving":
        state.ships[1].warp = 8
    elif case == "bool_ship_id":
        state.ships[True] = deepcopy(state.ships[1])
        state.ships[True].id = True
    elif case == "custom_metadata":
        state.metadata["mod"] = 1
    elif case == "no_standard_rules":
        options["standard_rules_asserted"] = False
    elif case == "no_full_roster_claim":
        options["complete_owner_planet_base_fleet_and_queue_roster_asserted"] = False
    elif case == "no_other_action_exclusion":
        options["no_priority_clone_mining_stations_or_external_actions_asserted"] = False
    elif case == "no_default_pp":
        options["default_no_pp_income_or_regular_pp_spend_asserted"] = False
    elif case == "bool_seed":
        options["seed"] = True
    elif case == "only_one_turn":
        history = history[:1]
    elif case == "nine_turns":
        history = history * 4 + history[:1]
    elif case == "wrong_soft_limit":
        carry = replace(carry, soft_ship_limit=11)
    elif case == "not_full_queue":
        rows = [replace(row, blueprint=None, allowed_hull_ids=frozenset()) for row in rows]
    if tuple(rows) != plans[1].all_bases and len(history) > 1:
        history[1] = replace(history[1], all_bases=tuple(rows))
    if tuple(stock) != carry.all_base_warehouses:
        carry = replace(carry, all_base_warehouses=tuple(stock))
    frozen = deepcopy((state, specs, carry, tuple(history)))
    result = run(state, specs, carry, tuple(history), **options)
    assert not result.supported
    assert result.state is None and result.carry_after is None
    assert result.turns == ()
    assert (state, specs, carry, tuple(history)) == frozen


@pytest.mark.parametrize("corrupt", (
    "free_ship_id", "shift_ship_crew", "stealth_mc",
    "fabricated_ground", "missing_mining_event",
))
def test_forged_engine_must_abstain_without_any_partial_capped_economy(monkeypatch, corrupt):
    import planets_lab.sim.late_pq_capped_no_build_carry as module
    original = module.HostEngine.step

    def forged(self, game, orders, *, seed=0):
        result, events = original(self, game, orders, seed=seed)
        result = deepcopy(result)
        if corrupt == "free_ship_id":
            result.ships[33] = deepcopy(result.ships[10])
            result.ships[33].id = 33
        elif corrupt == "shift_ship_crew":
            result.ships[10].crew += 1
        elif corrupt == "stealth_mc":
            result.planets[30].cargo.megacredits += 1
        elif corrupt == "fabricated_ground":
            result.planets[20].ground_duranium.amount += 1
        elif corrupt == "missing_mining_event":
            events = tuple(e for e in events if e.phase != "mineral_mining")
        return result, events

    monkeypatch.setattr(module.HostEngine, "step", forged)
    state, specs, carry, plans = fixture_capped()
    original_state = deepcopy(state)
    result = run(state, specs, carry, plans)
    assert not result.supported
    assert result.state is None and result.carry_after is None
    assert result.turns == ()
    assert state == original_state
