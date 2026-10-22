"""Contested single-open-slot late PQ random selection is caller asserted."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from planets_lab.sim.late_pq_external_regular_economy import (
    STATUS, PLACEMENTS, LatePQBase, LatePQContext,
    simulate_late_pq_external_selected_economic_turn,
)
from planets_lab.sim.standard_ship_warehouse_assembly import StandardComponentWarehouse
from test_classic_standard_pointer_economy_turn import context as classic_context


def fixture():
    game, specs, _, designs = classic_context(existing=9)
    rows = (
        LatePQBase(
            10, StandardComponentWarehouse(),
            blueprint=designs[10].blueprint, allowed_hull_ids=frozenset({7}),
        ),
        LatePQBase(
            20, StandardComponentWarehouse(),
            blueprint=designs[20].blueprint, allowed_hull_ids=frozenset({7}),
        ),
        LatePQBase(30, StandardComponentWarehouse()),
    )
    ctx = LatePQContext(
        soft_ship_limit=10, selected_planet_id=20,
        selected_ship_id=10, all_bases=rows,
        player_pp=((1, 3), (2, 7)),
        complete_fleet_planets_all_buildable_bases_and_warehouses_asserted=True,
        caller_explicit_random_selected_base_asserted=True,
        no_priority_cloning_mining_stations_or_other_actions_asserted=True,
        default_regular_zero_pp_no_idle_pp_income_asserted=True,
    )
    return game, specs, ctx


def run(game, specs, ctx, **overrides):
    opts = dict(
        placement=PLACEMENTS[0], standard_rules_asserted=True,
        full_independent_economic_inventory_asserted=True,
    )
    opts.update(overrides)
    return simulate_late_pq_external_selected_economic_turn(game, specs, ctx, **opts)


@pytest.mark.parametrize("placement", PLACEMENTS)
def test_competing_late_pq_one_slot_selected_externally_builds_exactly_one(placement):
    game, specs, ctx = fixture()
    frozen = deepcopy((game, specs, ctx))
    r = run(game, specs, ctx, placement=placement)
    assert r.supported and r.status == STATUS
    assert r == run(game, specs, ctx, placement=placement)
    assert r.selected_base_id == 20
    assert r.state.turn == game.turn + 1
    assert set(r.state.ships) == set(game.ships) | {10}
    assert r.state.ships[10].owner_id == 2
    assert r.ship_receipt.purchased.megacredits == 260
    assert r.player_pp_after == ((1,3),(2,7))
    assert len(r.planet_balances) == 3
    assert all(x.resource_balance_exact for x in r.planet_balances)
    assert r.warehouses_after[0] == (10, StandardComponentWarehouse())
    assert r.warehouses_after[2] == (30, StandardComponentWarehouse())
    assert r.state.starbases == game.starbases
    assert not r.independently_verified_random_base_choice
    assert not r.independently_verified_ship_id
    assert not r.independently_verified_orders
    assert not r.nuhost_execution_verified
    assert not r.nuhost_phase_placement_verified
    assert not r.independent_host_parity_verified
    assert (game, specs, ctx) == frozen


def test_other_explicit_random_winner_is_conditional_not_host_order():
    game, specs, ctx = fixture()
    ctx = replace(ctx, selected_planet_id=10)
    r = run(game, specs, ctx)
    assert r.supported
    assert r.state.ships[10].owner_id == 1
    assert r.selected_base_id == 10
    assert r.player_pp_after == ((1,3),(2,7))
    assert not r.independently_verified_random_base_choice


def test_full_stock_requires_no_surface_component_payment():
    game, specs, ctx = fixture()
    stock = StandardComponentWarehouse(
        hulls=((7,1),), engines=((9,2),),
        beams=((3,2),), launchers=((2,1),),
    )
    rows = list(ctx.all_bases)
    rows[1] = replace(rows[1], warehouse=stock)
    ctx = replace(ctx, all_bases=tuple(rows))
    for field in ("megacredits", "duranium", "tritanium", "molybdenum"):
        setattr(game.planets[20].cargo, field, 0)
    r = run(game, specs, ctx)
    assert r.supported
    assert all(getattr(r.ship_receipt.purchased, f) == 0 for f in (
        "megacredits", "duranium", "tritanium", "molybdenum",
    ))
    assert dict(r.warehouses_after)[20].hulls == ((7,0),)


@pytest.mark.parametrize("case", (
    "no_full_roster", "missing_base", "duplicate_base", "no_warehouse",
    "unknown_idle_component", "unknown_other_queue_stock",
    "negative_unselected_stock", "wrong_selected_base", "idle_selected",
    "not_lowest_ship_id", "bool_ship_id", "missing_player_pp",
    "duplicate_pp", "bool_pp", "wrong_owner",
    "too_many_ships", "not_one_slot", "priority_claim",
    "not_externally_selected", "nondefault_pp",
    "only_one_queued", "missing_unselected_rights",
    "unselected_unknown_hull", "moving_ship", "custom_metadata",
    "affordability", "missing_minerals", "bad_seed",
    "unverified_placement", "no_economic_assert", "no_standard_rules",
))
def test_invalid_pq_scenario_abstains_without_partial_state(case):
    game, specs, ctx = fixture()
    rows = list(ctx.all_bases)
    opts = {}
    if case == "no_full_roster":
        ctx = replace(ctx, complete_fleet_planets_all_buildable_bases_and_warehouses_asserted=False)
    elif case == "missing_base":
        rows.pop()
    elif case == "duplicate_base":
        rows[1] = rows[0]
    elif case == "no_warehouse":
        rows[0] = replace(rows[0], warehouse=None)
    elif case == "unknown_idle_component":
        rows[2] = replace(rows[2], warehouse=StandardComponentWarehouse(hulls=((999,1),)))
    elif case == "unknown_other_queue_stock":
        rows[0] = replace(rows[0], warehouse=StandardComponentWarehouse(engines=((999,1),)))
    elif case == "negative_unselected_stock":
        rows[0] = replace(rows[0], warehouse=StandardComponentWarehouse(hulls=((7,-1),)))
    elif case == "wrong_selected_base":
        ctx = replace(ctx, selected_planet_id=999)
    elif case == "idle_selected":
        ctx = replace(ctx, selected_planet_id=30)
    elif case == "not_lowest_ship_id":
        ctx = replace(ctx, selected_ship_id=99)
    elif case == "bool_ship_id":
        ctx = replace(ctx, selected_ship_id=True)
    elif case == "missing_player_pp":
        ctx = replace(ctx, player_pp=((1,3),))
    elif case == "duplicate_pp":
        ctx = replace(ctx, player_pp=((1,3),(1,7)))
    elif case == "bool_pp":
        ctx = replace(ctx, player_pp=((1,True),(2,7)))
    elif case == "wrong_owner":
        game.starbases[20].owner_id = 1
    elif case == "too_many_ships":
        game.ships[10] = deepcopy(game.ships[9])
        game.ships[10].id = 10
    elif case == "not_one_slot":
        ctx = replace(ctx, soft_ship_limit=11)
    elif case == "priority_claim":
        ctx = replace(ctx, no_priority_cloning_mining_stations_or_other_actions_asserted=False)
    elif case == "not_externally_selected":
        ctx = replace(ctx, caller_explicit_random_selected_base_asserted=False)
    elif case == "nondefault_pp":
        ctx = replace(ctx, default_regular_zero_pp_no_idle_pp_income_asserted=False)
    elif case == "only_one_queued":
        rows[0] = replace(rows[0], blueprint=None, allowed_hull_ids=None)
    elif case == "missing_unselected_rights":
        rows[0] = replace(rows[0], allowed_hull_ids=None)
    elif case == "unselected_unknown_hull":
        rows[0] = replace(rows[0], blueprint=replace(rows[0].blueprint, hull_id=999))
    elif case == "moving_ship":
        game.ships[1].warp = 8
    elif case == "custom_metadata":
        game.metadata["variant"] = 1
    elif case == "affordability":
        game.planets[20].cargo.megacredits = 0
    elif case == "missing_minerals":
        game.planets[20].cargo.duranium = 0
    elif case == "bad_seed":
        opts["seed"] = True
    elif case == "unverified_placement":
        opts["placement"] = "claimed_host"
    elif case == "no_economic_assert":
        opts["full_independent_economic_inventory_asserted"] = False
    elif case == "no_standard_rules":
        opts["standard_rules_asserted"] = False
    if tuple(rows) != ctx.all_bases:
        ctx = replace(ctx, all_bases=tuple(rows))
    frozen = deepcopy((game, specs, ctx))
    r = run(game, specs, ctx, **opts)
    assert not r.supported
    assert r.state is None and r.ship_receipt is None
    assert r.player_pp_after == () and r.warehouses_after == ()
    assert r.planet_balances == () and r.economic_events == ()
    assert (game, specs, ctx) == frozen


@pytest.mark.parametrize("corrupt", (
    "invented_mc", "invented_ground", "lost_mining_event",
    "wrong_new_ship", "extra_ship",
))
def test_forged_economy_abstains_whole_pq_turn(monkeypatch, corrupt):
    import planets_lab.sim.late_pq_external_regular_economy as module
    real = module.HostEngine.step
    def forged(self, state, orders, *, seed=0):
        after, events = real(self, state, orders, seed=seed)
        after = deepcopy(after)
        if corrupt == "invented_mc":
            after.planets[30].cargo.megacredits += 1
        elif corrupt == "invented_ground":
            after.planets[30].ground_duranium.amount += 1
        elif corrupt == "lost_mining_event":
            events = tuple(ev for ev in events if ev.phase != "mineral_mining")
        elif corrupt == "wrong_new_ship":
            after.ships[10].crew += 1
        elif corrupt == "extra_ship":
            from planets_lab.core import Ship
            after.ships[77] = Ship(id=77, owner_id=1, hull_id=7, x=0, y=0)
        return after, events
    monkeypatch.setattr(module.HostEngine, "step", forged)
    game, specs, ctx = fixture()
    result = run(game, specs, ctx)
    assert not result.supported and result.state is None
