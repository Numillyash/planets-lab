"""One selected PQ build at T; only on T+1, loaded movement+economy."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from planets_lab.sim.late_pq_new_ship_next_turn_move import (
    STATUS, BUILD_PLACEMENTS, NEXT_TURN_PLACEMENTS,
    PQNewShipNextTurnOrders, simulate_pq_new_ship_next_turn_load_move,
)
from test_late_pq_built_ship_cargo_move import context as existing


def fixture():
    state, specs, ctx, movement = existing()
    orders = PQNewShipNextTurnOrders(
        planet_to_ship=movement.planet_to_ship,
        waypoint_x=movement.waypoint_x,
        waypoint_y=movement.waypoint_y,
        warp=movement.warp,
        all_other_ships_and_orders_inert_asserted=True,
        no_interturn_changes_or_special_queue_actions_asserted=True,
        no_unmodeled_combat_or_encounters_asserted=True,
    )
    return state, specs, ctx, orders


def run(state, specs, ctx, orders, **options):
    args = dict(
        build_placement=BUILD_PLACEMENTS[0],
        next_turn_placement=NEXT_TURN_PLACEMENTS[0],
        standard_rules_asserted=True,
        complete_build_queue_warehouse_and_next_turn_orders_asserted=True,
        complete_interturn_planets_fleet_and_pp_without_external_effects_asserted=True,
    )
    args.update(options)
    return simulate_pq_new_ship_next_turn_load_move(
        state, specs, ctx, orders, **args,
    )


@pytest.mark.parametrize("build", BUILD_PLACEMENTS)
@pytest.mark.parametrize("next_turn", NEXT_TURN_PLACEMENTS)
def test_new_ship_waits_for_separate_next_turn_then_loads_moves_and_runs_economy(build, next_turn):
    state, specs, ctx, order = fixture()
    frozen = deepcopy((state, specs, ctx, order))
    out = run(state, specs, ctx, order, build_placement=build,
              next_turn_placement=next_turn)
    assert out.supported and out.status == STATUS
    assert out == run(state, specs, ctx, order, build_placement=build,
                      next_turn_placement=next_turn)
    assert out.first_turn_build.state.turn == state.turn + 1
    assert out.state.turn == state.turn + 2
    assert len(out.state.ships) == ctx.soft_ship_limit
    assert out.state.ships[10].owner_id == 2
    assert (out.first_turn_build.state.ships[10].x,
            out.first_turn_build.state.ships[10].y) == (300, 300)
    assert (out.state.ships[10].x, out.state.ships[10].y) == (310, 300)
    assert out.state.ships[10].cargo.supplies == 4
    assert len(out.next_turn_transfer_balances) == 1
    assert dict(out.next_turn_transfer_balances[0].amounts)["neutronium"] == 60
    assert len(out.next_turn_fuel_balances) == 1
    assert out.next_turn_fuel_balances[0].fuel_used > 0
    assert out.state.ships[10].cargo.neutronium == (
        60 - out.next_turn_fuel_balances[0].fuel_used
    )
    assert len(out.next_turn_planet_balances) == 3
    assert all(p.resource_balance_exact for p in out.next_turn_planet_balances)
    assert all(p.resource_balance_exact for p in out.first_turn_build.planet_balances)
    assert out.first_turn_build.player_pp_after == ((1, 3), (2, 7))
    assert len(out.first_turn_build.warehouses_after) == 3
    assert not out.server_accepted_first_turn_build
    assert not out.authenticated_interturn_boundary
    assert not out.authenticated_next_turn_load_order
    assert not out.nuhost_phase_order_verified
    assert not out.independently_verified_host_execution
    assert (state, specs, ctx, order) == frozen


def test_next_turn_loaded_supply_does_not_change_prior_build_inventory():
    state, specs, ctx, order = fixture()
    heavy = replace(order, planet_to_ship=replace(
        order.planet_to_ship, supplies=20,
    ))
    light_result = run(state, specs, ctx, order)
    heavy_result = run(state, specs, ctx, heavy)
    assert light_result.supported and heavy_result.supported
    assert heavy_result.first_turn_build == light_result.first_turn_build
    assert heavy_result.state.ships[10].cargo.supplies == 20
    assert heavy_result.state.turn == state.turn + 2


@pytest.mark.parametrize("bad", (
    "missing_build_selection", "wrong_build_id", "build_mc_shortfall",
    "wrong_source_planet", "reverse_transfer", "none_transfer",
    "zero_cargo", "negative_neutronium", "bool_cargo",
    "planet_fuel_shortfall", "tank_overfill", "cargo_overfill",
    "partial_waypoint", "zero_warp", "foreign_destination",
    "missing_next_turn_claim", "missing_no_external_change",
    "missing_no_encounters", "missing_complete_queue",
    "missing_complete_state", "false_rules", "bad_build_phase",
    "bad_second_phase", "bool_seed", "old_ship_moving",
))
def test_two_turn_unsupported_scenario_returns_no_partial_outcomes(bad):
    state, specs, ctx, order = fixture()
    opt = {}
    if bad == "missing_build_selection":
        ctx = replace(ctx, caller_explicit_random_selected_base_asserted=False)
    elif bad == "wrong_build_id":
        ctx = replace(ctx, selected_ship_id=33)
    elif bad == "build_mc_shortfall":
        state.planets[20].cargo.megacredits = 0
    elif bad == "wrong_source_planet":
        order = replace(order, planet_to_ship=replace(order.planet_to_ship, planet_id=10))
    elif bad == "reverse_transfer":
        order = replace(order, planet_to_ship=replace(order.planet_to_ship, direction="ship_to_planet"))
    elif bad == "none_transfer":
        order = replace(order, planet_to_ship=None)
    elif bad == "zero_cargo":
        order = replace(order, planet_to_ship=replace(order.planet_to_ship, neutronium=0, supplies=0))
    elif bad == "negative_neutronium":
        order = replace(order, planet_to_ship=replace(order.planet_to_ship, neutronium=-1))
    elif bad == "bool_cargo":
        order = replace(order, planet_to_ship=replace(order.planet_to_ship, neutronium=True))
    elif bad == "planet_fuel_shortfall":
        state.planets[20].cargo.neutronium = 0
    elif bad == "tank_overfill":
        order = replace(order, planet_to_ship=replace(order.planet_to_ship, neutronium=400))
    elif bad == "cargo_overfill":
        order = replace(order, planet_to_ship=replace(order.planet_to_ship, supplies=400))
    elif bad == "partial_waypoint":
        order = replace(order, waypoint_x=900, waypoint_y=900)
    elif bad == "zero_warp":
        order = replace(order, warp=0)
    elif bad == "foreign_destination":
        order = replace(order, waypoint_x=350, waypoint_y=350, warp=9)
    elif bad == "missing_next_turn_claim":
        order = replace(order, all_other_ships_and_orders_inert_asserted=False)
    elif bad == "missing_no_external_change":
        order = replace(order, no_interturn_changes_or_special_queue_actions_asserted=False)
    elif bad == "missing_no_encounters":
        order = replace(order, no_unmodeled_combat_or_encounters_asserted=False)
    elif bad == "missing_complete_queue":
        opt["complete_build_queue_warehouse_and_next_turn_orders_asserted"] = False
    elif bad == "missing_complete_state":
        opt["complete_interturn_planets_fleet_and_pp_without_external_effects_asserted"] = False
    elif bad == "false_rules":
        opt["standard_rules_asserted"] = False
    elif bad == "bad_build_phase":
        opt["build_placement"] = "real_host_proved"
    elif bad == "bad_second_phase":
        opt["next_turn_placement"] = "unmodeled_tow"
    elif bad == "bool_seed":
        opt["seed"] = True
    elif bad == "old_ship_moving":
        state.ships[1].warp = 9
    original = deepcopy((state, specs, ctx, order))
    result = run(state, specs, ctx, order, **opt)
    assert not result.supported
    assert result.state is None and result.first_turn_build is None
    assert result.next_turn_planet_balances == ()
    assert result.next_turn_transfer_balances == ()
    assert result.next_turn_fuel_balances == ()
    assert result.next_turn_events == ()
    assert (state, specs, ctx, order) == original


@pytest.mark.parametrize("corrupt", (
    "ghost_ship", "planet_mc_forgery", "new_ship_crew_forgery",
    "transfer_receipt_forgery", "move_fuel_event_forgery",
))
def test_next_turn_forgery_causes_whole_two_turn_abstention(monkeypatch, corrupt):
    import planets_lab.sim.late_pq_new_ship_next_turn_move as module
    state, specs, ctx, order = fixture()
    frozen = deepcopy(state)
    original = module.HostEngine.step
    count = [0]

    def fabricated(self, source, submitted, *, seed=0):
        after, events = original(self, source, submitted, seed=seed)
        count[0] += 1
        if count[0] != 2:
            return after, events
        after = deepcopy(after)
        if corrupt == "ghost_ship":
            after.ships[33] = deepcopy(after.ships[10])
            after.ships[33].id = 33
        elif corrupt == "planet_mc_forgery":
            after.planets[30].cargo.megacredits += 1
        elif corrupt == "new_ship_crew_forgery":
            after.ships[10].crew += 1
        elif corrupt == "transfer_receipt_forgery":
            events = tuple(replace(e, entity_id=11)
                           if e.phase == "planet_cargo_transfer" else e for e in events)
        elif corrupt == "move_fuel_event_forgery":
            events = tuple(replace(e, entity_id=11)
                           if e.phase == "normal_movement" else e for e in events)
        return after, events

    monkeypatch.setattr(module.HostEngine, "step", fabricated)
    result = run(state, specs, ctx, order)
    assert not result.supported
    assert result.state is None and result.first_turn_build is None
    assert state == frozen
