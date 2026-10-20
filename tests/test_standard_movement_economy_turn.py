"""Real component composition (synthetic inputs), strict external provenance gate.

Composes ordinary movement and planetary building/economy in HostEngine.
Does NOT execute combat, tow, hyperjump, intercept, cargo transfer or
real NuHost accepted orders.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from planets_lab.core import Ship, Starbase
from planets_lab.data import EngineSpec, NuStaticSpecs, ResourceCost
from planets_lab.sim.orders import PlayerOrders, ShipOrder, TurnOrders, PlanetCargoTransferOrder
from planets_lab.sim.standard_movement_economy_turn import (
    SUPPORTED_STATUS, simulate_standard_movement_economy_turn,
)
from planets_lab.sim.standard_structure_build import StructureBuildTargets

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import fixture, specs as fake_specs


def world():
    state = fixture()
    state.ships[1].engine_id = 9
    state.ships[1].cargo.neutronium = 70
    # Ordinary, unarmed, two-owner noninteracting synthetic ships.
    ship = deepcopy(state.ships[1])
    ship.id = 2
    ship.owner_id = 2
    ship.x, ship.y = 300, 300
    state.ships[2] = ship
    planet = deepcopy(state.planets[10])
    planet.id = 20
    planet.owner_id = 2
    planet.x, planet.y = 300, 300
    planet.factories = 5
    planet.mines = 8
    planet.cargo.megacredits = 40
    state.planets[20] = planet
    state.validate()
    return state


def static():
    out = fake_specs()
    out.engines[9] = EngineSpec(
        id=9, name="synthetic", tech_level=9, cost=ResourceCost(),
        warp_fuel_factors=(0,) + (10_000,) * 9,
    )
    return out


def orders(*, x1=110, x2=300, warp1=9, warp2=0):
    return TurnOrders(by_player={
        1: PlayerOrders(
            player_id=1,
            ship_orders=(ShipOrder(
                ship_id=1, waypoint_x=x1, waypoint_y=100, warp=warp1,
            ),),
        ),
        2: PlayerOrders(
            player_id=2,
            ship_orders=(ShipOrder(
                ship_id=2, waypoint_x=x2, waypoint_y=300, warp=warp2,
            ),),
        ),
    })


def targets():
    return {
        1: (StructureBuildTargets(planet_id=10, factories=11, mines=11),),
        2: (StructureBuildTargets(planet_id=20, factories=6, mines=9),),
    }


def run(before, ship_orders=None, builds=None, **overrides):
    params = {
        "movement_placement": "normal_before_economy_block",
        "structure_placement": "structures_before_planetary",
        "standard_rules_asserted": True,
        "complete_ship_and_structure_orders_asserted": True,
        "automatic_supply_sale_enabled": False,
    }
    params.update(overrides)
    return simulate_standard_movement_economy_turn(
        before,
        orders() if ship_orders is None else ship_orders,
        targets() if builds is None else builds,
        static(),
        **params,
    )


@pytest.mark.parametrize("movement", (
    "normal_before_economy_block",
    "normal_after_economy_block",
))
@pytest.mark.parametrize("construction", (
    "structures_before_planetary",
    "structures_after_planetary",
))
def test_two_players_two_planets_two_ships_conditional_cross_system_turn(
    movement, construction,
):
    state = world()
    original = deepcopy(state)
    o = run(state, movement_placement=movement, structure_placement=construction)
    replay = run(state, movement_placement=movement, structure_placement=construction)
    assert o.supported and o.status == SUPPORTED_STATUS
    assert o == replay
    assert state == original
    assert o.state.turn == state.turn + 1
    assert {p.planet_id for p in o.planet_balances} == {10, 20}
    assert {s.ship_id for s in o.ship_fuel_balances} == {1, 2}
    assert o.state.ships[1].x == 110
    assert o.state.ships[1].cargo.neutronium < state.ships[1].cargo.neutronium
    assert o.state.ships[2].x == state.ships[2].x
    assert o.state.ships[2].cargo.neutronium == state.ships[2].cargo.neutronium
    assert all(p.resource_balance_exact for p in o.planet_balances)
    assert all(s.exact for s in o.ship_fuel_balances)
    assert sum(p.built_factories for p in o.planet_balances) == 2
    assert any(p.taxes_collected > 0 for p in o.planet_balances)
    assert any(sum(p.mined_minerals) > 0 for p in o.planet_balances)
    assert not o.nuhost_order_execution_verified
    assert not o.independent_host_parity_verified
    assert not o.nuhost_phase_placement_verified


def test_structure_timing_still_affects_supply_output_with_movement_enabled():
    before = world()
    early = run(before, structure_placement="structures_before_planetary")
    late = run(before, structure_placement="structures_after_planetary")
    assert early.supported and late.supported
    assert (early.state.planets[10].cargo.supplies
            - late.state.planets[10].cargo.supplies) == 1
    assert early.state.ships == late.state.ships
    assert not early.nuhost_phase_placement_verified


def test_movement_relative_to_economy_is_not_claimed_distinguishable():
    before = world()
    early = run(before, movement_placement="normal_before_economy_block")
    late = run(before, movement_placement="normal_after_economy_block")
    assert early.supported and late.supported
    assert early.state == late.state
    assert early.events != late.events  # phase trace is NOT external Host evidence
    assert not early.nuhost_phase_placement_verified


@pytest.mark.parametrize("scenario", [
    "missing_ship_owner", "missing_target_owner", "missing_ship_order",
    "duplicate_ship", "wrong_ship_owner", "foreign_build_owner",
    "ship_transfer", "tech_order", "movement_mission", "ship_mission",
    "ship_friendly_code", "armed_ship", "unknown_engine",
    "special_hull", "wrong_waypoint_type", "unreachable",
    "insufficient_fuel", "unsupported_structure", "storm",
    "starbase", "metadata", "foreign_planet_arrival",
    "opponent_colocation", "missing_rule_scope", "missing_order_scope",
    "no_ships", "no_build_orders", "unsupported_placement",
])
def test_excluded_contexts_abstain_without_partial_state(scenario):
    pre = world()
    cmd = orders()
    builds = targets()
    settings = {}
    if scenario == "missing_ship_owner": cmd.by_player.pop(2)
    elif scenario == "missing_target_owner": builds.pop(2)
    elif scenario == "missing_ship_order":
        cmd.by_player[2] = PlayerOrders(player_id=2)
    elif scenario == "duplicate_ship":
        row = cmd.by_player[1]
        cmd.by_player[1] = replace(row, ship_orders=row.ship_orders * 2)
    elif scenario == "wrong_ship_owner":
        row = cmd.by_player[2]
        cmd.by_player[2] = replace(row, ship_orders=(replace(row.ship_orders[0], ship_id=1),))
    elif scenario == "foreign_build_owner":
        builds = {1: (), 2: (StructureBuildTargets(10, factories=11),)}
    elif scenario == "ship_transfer":
        row = cmd.by_player[1]
        cmd.by_player[1] = replace(row, ship_orders=(
            replace(row.ship_orders[0], planet_transfer=PlanetCargoTransferOrder(10)),))
    elif scenario == "tech_order":
        from planets_lab.sim.orders import StarbaseTechUpgradeOrder
        cmd.by_player[1] = replace(cmd.by_player[1], starbase_tech_orders=(
            StarbaseTechUpgradeOrder(10, engine=2),))
    elif scenario == "movement_mission":
        row = cmd.by_player[1]
        cmd.by_player[1] = replace(row, ship_orders=(
            replace(row.ship_orders[0], mission="tow"),))
    elif scenario == "ship_mission": pre.ships[1].mission = "6"
    elif scenario == "ship_friendly_code": pre.ships[1].friendly_code = "HYP"
    elif scenario == "armed_ship": pre.ships[1].beam_count = 1
    elif scenario == "unknown_engine": pre.ships[1].engine_id = 1000
    elif scenario == "special_hull":
        from dataclasses import replace as data_replace
        # A nonexistent hull must not be treated as an ordinary hull.
        pre.ships[1].hull_id = 999
    elif scenario == "wrong_waypoint_type":
        row = cmd.by_player[1]
        cmd.by_player[1] = replace(row, ship_orders=(
            replace(row.ship_orders[0], waypoint_x=True),))
    elif scenario == "unreachable":
        row = cmd.by_player[1]
        cmd.by_player[1] = replace(row, ship_orders=(
            replace(row.ship_orders[0], waypoint_x=5000),))
    elif scenario == "insufficient_fuel": pre.ships[1].cargo.neutronium = 0
    elif scenario == "unsupported_structure":
        builds[2] = (StructureBuildTargets(20, factories=1),)
    elif scenario == "storm":
        from planets_lab.core import IonStorm
        pre.ion_storms[1] = IonStorm(
            id=1, x=100, y=100, radius=10, voltage=10, warp=0, heading=0,
        )
    elif scenario == "starbase":
        pre.starbases[10] = Starbase(planet_id=10, owner_id=1)
    elif scenario == "metadata": pre.metadata["campaign.no_supplies"] = True
    elif scenario == "foreign_planet_arrival":
        row = cmd.by_player[1]
        cmd.by_player[1] = replace(row, ship_orders=(
            replace(row.ship_orders[0], waypoint_x=300, waypoint_y=300),))
    elif scenario == "opponent_colocation":
        pre.ships[2].x, pre.ships[2].y = 100, 100
    elif scenario == "missing_rule_scope": settings["standard_rules_asserted"] = False
    elif scenario == "missing_order_scope":
        settings["complete_ship_and_structure_orders_asserted"] = False
    elif scenario == "no_ships":
        pre.ships.clear()
        cmd = TurnOrders(by_player={
            1: PlayerOrders(player_id=1),
            2: PlayerOrders(player_id=2),
        })
    elif scenario == "no_build_orders": builds = {1: (), 2: ()}
    elif scenario == "unsupported_placement":
        settings["movement_placement"] = "nu_host_claimed"
    frozen = deepcopy(pre)
    out = run(pre, cmd, builds, **settings)
    assert out.status == "ABSTAIN_STANDARD_COMPOSITE_TURN"
    assert not out.supported
    assert out.state is None
    assert out.events == ()
    assert out.planet_balances == ()
    assert out.ship_fuel_balances == ()
    assert not out.nuhost_order_execution_verified
    assert pre == frozen


@pytest.mark.parametrize("tamper", (
    "ship_fuel", "ship_supply", "ship_coordinates", "planet_mc",
    "planet_mineral", "structure", "missing_move_receipt",
    "missing_build_receipt",
))
def test_corrupted_poststate_or_receipt_abstains_before_exposing_partial_output(
    monkeypatch, tamper,
):
    from planets_lab.sim import standard_movement_economy_turn as module
    real = module.HostEngine.step

    def corrupted(self, state, submitted, *, seed=0):
        post, events = real(self, state, submitted, seed=seed)
        post = deepcopy(post)
        if tamper == "ship_fuel": post.ships[1].cargo.neutronium += 1
        elif tamper == "ship_supply": post.ships[1].cargo.supplies += 1
        elif tamper == "ship_coordinates": post.ships[1].x += 1
        elif tamper == "planet_mc": post.planets[20].cargo.megacredits += 1
        elif tamper == "planet_mineral": post.planets[20].ground_duranium.amount += 1
        elif tamper == "structure": post.planets[20].factories += 1
        elif tamper == "missing_move_receipt":
            events = tuple(x for x in events if x.phase != "normal_movement")
        elif tamper == "missing_build_receipt":
            events = tuple(x for x in events
                           if x.phase != "standard_structure_build_conditional")
        return post, events

    monkeypatch.setattr(module.HostEngine, "step", corrupted)
    pre = world()
    copy = deepcopy(pre)
    out = run(pre)
    assert not out.supported
    assert out.state is None and out.events == ()
    assert out.planet_balances == () and out.ship_fuel_balances == ()
    assert pre == copy


def test_legacy_signed_owner_schemas_remain_unchanged():
    from dataclasses import fields
    from planets_lab.sim.planetary_owner_capture_v2 import OWNER_ROW_KEYS_V2
    assert [f.name for f in fields(PlayerOrders)] == [
        "player_id", "ship_orders", "starbase_tech_orders",
    ]
    assert OWNER_ROW_KEYS_V2 == frozenset(
        ("player_id", "ship_orders", "starbase_tech_orders")
    )
