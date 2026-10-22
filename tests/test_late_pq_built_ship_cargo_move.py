"""Conditional freshly built late PQ ship load+movement with strict ledgers."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from planets_lab.sim.late_pq_built_ship_cargo_move import (
    STATUS, PLACEMENTS, BuiltShipCargoMove,
    simulate_pq_built_ship_load_and_move,
)
from planets_lab.sim.orders import PlanetCargoTransferOrder
from test_late_pq_external_regular_economy import fixture


def context():
    state, specs, pqctx = fixture()
    # #271's fictional engine uses tiny factors (0..9), truncating
    # every short-leg cost to zero. Supply a nonzero fictional engine
    # factor to exercise fuel accounting rather than weakening guards.
    specs.engines[9] = replace(
        specs.engines[9],
        warp_fuel_factors=(0, 2000, 4000, 10000, 20000,
                           50000, 80000, 130000, 160000, 180000),
    )
    order = BuiltShipCargoMove(
        planet_to_ship=PlanetCargoTransferOrder(
            planet_id=20, direction="planet_to_ship",
            neutronium=60, supplies=4,
        ),
        waypoint_x=310, waypoint_y=300, warp=5,
        explicitly_ordered_post_build_load_then_move_asserted=True,
        all_other_ships_inert_and_no_path_encounters_asserted=True,
    )
    return state, specs, pqctx, order


def run(state, specs, pqctx, order, **overrides):
    options = dict(
        placement=PLACEMENTS[0],
        standard_rules_asserted=True,
        complete_shipyard_warehouse_and_economic_scope_asserted=True,
        no_external_events_other_than_explicit_load_and_move_asserted=True,
    )
    options.update(overrides)
    return simulate_pq_built_ship_load_and_move(
        state, specs, pqctx, order, **options,
    )


@pytest.mark.parametrize("placement", PLACEMENTS)
def test_new_selected_pq_ship_loads_fuel_and_supplies_then_moves_with_exact_ledgers(placement):
    state, specs, pqctx, order = context()
    original = deepcopy((state, specs, pqctx, order))
    out = run(state, specs, pqctx, order, placement=placement)
    assert out.supported and out.status == STATUS
    assert out == run(state, specs, pqctx, order, placement=placement)
    assert out.state.turn == state.turn + 1
    assert set(out.state.ships) == set(state.ships) | {10}
    assert out.state.ships[10].owner_id == 2
    assert (out.state.ships[10].x, out.state.ships[10].y) == (310,300)
    assert out.ship_fuel_used > 0
    assert out.state.ships[10].cargo.neutronium == 60 - out.ship_fuel_used
    assert out.state.ships[10].cargo.supplies == 4
    assert out.state.planets[20].cargo.neutronium == (
        out.construction.state.planets[20].cargo.neutronium - 60
    )
    assert out.state.planets[20].cargo.supplies == (
        out.construction.state.planets[20].cargo.supplies - 4
    )
    assert all(x.resource_balance_exact for x in out.construction.planet_balances)
    assert len(out.transfer_events) == 1
    assert len(out.normal_movement_events) == 1
    assert dict(out.loaded_amounts)["neutronium"] == 60
    assert out.construction.player_pp_after == ((1,3), (2,7))
    assert out.construction.warehouses_after[0][0] == 10
    assert all(out.state.ships[i] == state.ships[i] for i in state.ships)
    assert not out.server_accepted_build_verified
    assert not out.host_post_build_transfer_timing_verified
    assert not out.new_ship_navigation_order_verified
    assert not out.host_movement_execution_verified
    assert not out.independent_host_parity_verified
    assert (state, specs, pqctx, order) == original


def test_loaded_mass_and_fuel_are_accounted_and_not_a_second_economy_turn():
    state, specs, ctx, order = context()
    light = run(state, specs, ctx, order)
    heavy = replace(
        order,
        planet_to_ship=replace(order.planet_to_ship, supplies=20),
    )
    weightier = run(state, specs, ctx, heavy)
    assert weightier.supported
    assert light.supported
    assert weightier.state.turn == light.state.turn == state.turn + 1
    assert weightier.state.ships[10].cargo.supplies == 20
    assert weightier.state.planets[20].cargo.supplies == (
        weightier.construction.state.planets[20].cargo.supplies - 20
    )
    assert weightier.state.ships[10].cargo.neutronium == (
        60 - weightier.ship_fuel_used
    )


@pytest.mark.parametrize("case", (
    "unconfirmed_selection", "wrong_build_id", "insufficient_build_mc",
    "no_transfer", "wrong_planet", "wrong_direction",
    "zero_transfer", "negative_fuel", "boolean_fuel",
    "insufficient_planet_fuel", "overfilled_fuel_tank",
    "too_much_bulk", "unreachable_waypoint", "warp_zero",
    "foreign_planet_arrival", "no_staged_order_assertion",
    "no_route_assertion", "bad_scope", "no_economic_scope",
    "wrong_phase", "boolean_seed", "other_ship_moving",
))
def test_unsupported_build_load_or_move_abstains_without_partial_result(case):
    state, specs, ctx, order = context()
    opts = {}
    if case == "unconfirmed_selection":
        ctx = replace(ctx, caller_explicit_random_selected_base_asserted=False)
    elif case == "wrong_build_id":
        ctx = replace(ctx, selected_ship_id=33)
    elif case == "insufficient_build_mc":
        state.planets[20].cargo.megacredits = 0
    elif case == "no_transfer":
        order = replace(order, planet_to_ship=None)
    elif case == "wrong_planet":
        order = replace(order, planet_to_ship=replace(order.planet_to_ship, planet_id=10))
    elif case == "wrong_direction":
        order = replace(order, planet_to_ship=replace(order.planet_to_ship, direction="ship_to_planet"))
    elif case == "zero_transfer":
        order = replace(order, planet_to_ship=replace(order.planet_to_ship, neutronium=0, supplies=0))
    elif case == "negative_fuel":
        order = replace(order, planet_to_ship=replace(order.planet_to_ship, neutronium=-1))
    elif case == "boolean_fuel":
        order = replace(order, planet_to_ship=replace(order.planet_to_ship, neutronium=True))
    elif case == "insufficient_planet_fuel":
        state.planets[20].cargo.neutronium = 0
    elif case == "overfilled_fuel_tank":
        order = replace(order, planet_to_ship=replace(order.planet_to_ship, neutronium=300))
    elif case == "too_much_bulk":
        order = replace(order, planet_to_ship=replace(order.planet_to_ship, supplies=500))
    elif case == "unreachable_waypoint":
        order = replace(order, waypoint_x=900, waypoint_y=900)
    elif case == "warp_zero":
        order = replace(order, warp=0)
    elif case == "foreign_planet_arrival":
        order = replace(order, waypoint_x=350, waypoint_y=350, warp=9)
    elif case == "no_staged_order_assertion":
        order = replace(order, explicitly_ordered_post_build_load_then_move_asserted=False)
    elif case == "no_route_assertion":
        order = replace(order, all_other_ships_inert_and_no_path_encounters_asserted=False)
    elif case == "bad_scope":
        opts["no_external_events_other_than_explicit_load_and_move_asserted"] = False
    elif case == "no_economic_scope":
        opts["complete_shipyard_warehouse_and_economic_scope_asserted"] = False
    elif case == "wrong_phase":
        opts["placement"] = "claimed_NuHost_transfer_first"
    elif case == "boolean_seed":
        opts["seed"] = True
    elif case == "other_ship_moving":
        state.ships[1].warp = 8
    original = deepcopy((state, specs, ctx, order))
    out = run(state, specs, ctx, order, **opts)
    assert not out.supported
    assert out.state is None and out.construction is None
    assert out.transfer_events == () and out.normal_movement_events == ()
    assert out.loaded_amounts == () and out.ship_fuel_used is None
    assert (state, specs, ctx, order) == original


@pytest.mark.parametrize("corrupt", (
    "extra_planet_supplies", "wrong_transfer_receipt",
    "wrong_move_position", "wrong_move_fuel_receipt",
    "phantom_ship",
))
def test_adversarial_transfer_or_move_forgery_abstains_atomically(monkeypatch, corrupt):
    import planets_lab.sim.late_pq_built_ship_cargo_move as module
    state, specs, ctx, order = context()
    original_state = deepcopy(state)
    if corrupt in ("extra_planet_supplies", "wrong_transfer_receipt"):
        actual = module.PlanetCargoTransferPhase.run
        def forged_transfer(self, world, orders, rng):
            result = actual(self, world, orders, rng)
            if corrupt == "extra_planet_supplies":
                world.planets[20].cargo.supplies += 1
            else:
                result[0] = replace(result[0], entity_id=10)
            return result
        monkeypatch.setattr(module.PlanetCargoTransferPhase, "run", forged_transfer)
    else:
        actual = module.NormalMovementPhase.run
        def forged_move(self, world, orders, rng):
            result = actual(self, world, orders, rng)
            if corrupt == "wrong_move_position":
                world.ships[10].x += 1
            elif corrupt == "wrong_move_fuel_receipt":
                result[0] = replace(result[0], entity_id=11)
            elif corrupt == "phantom_ship":
                world.ships[34] = deepcopy(world.ships[10])
                world.ships[34].id = 34
            return result
        monkeypatch.setattr(module.NormalMovementPhase, "run", forged_move)
    out = run(state, specs, ctx, order)
    assert not out.supported
    assert out.state is None and out.construction is None
    assert state == original_state
