"""Synthetic full-turn orbital transfer, movement and economic balance controls."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from planets_lab.sim.orders import (
    PlanetCargoTransferOrder, PlayerOrders, ShipOrder, TurnOrders,
)
from planets_lab.sim.standard_orbital_transfer_turn import (
    STATUS, simulate_orbital_transfer_movement_economy_turn,
)
from planets_lab.sim.standard_structure_build import StructureBuildTargets

from test_standard_movement_economy_turn import (
    world, static, orders as ordinary_orders, targets,
)


def with_transfer(
    *, direction="ship_to_planet", planet_id=10, supplies=5,
    x1=110, warp1=9,
):
    rows = ordinary_orders(x1=x1, warp1=warp1)
    first = rows.by_player[1]
    original = first.ship_orders[0]
    rows.by_player[1] = replace(first, ship_orders=(replace(
        original, planet_transfer=PlanetCargoTransferOrder(
            planet_id=planet_id, direction=direction, supplies=supplies,
        ),
    ),))
    return rows


def simulate(state, orders=None, buildings=None, **opts):
    args = {
        "movement_placement": "normal_before_economy_block",
        "transfer_placement": "transfer_before_movement",
        "structure_placement": "structures_before_planetary",
        "standard_rules_asserted": True,
        "complete_ship_and_structure_orders_asserted": True,
        "automatic_supply_sale_enabled": False,
    }
    args.update(opts)
    return simulate_orbital_transfer_movement_economy_turn(
        state, orders or with_transfer(), buildings or targets(), static(), **args
    )


@pytest.mark.parametrize("movement", (
    "normal_before_economy_block", "normal_after_economy_block",
))
@pytest.mark.parametrize("building", (
    "structures_before_planetary", "structures_after_planetary",
))
def test_before_move_unload_has_conserved_ship_and_planet_ledger(movement, building):
    initial = world()
    initial_copy = deepcopy(initial)
    result = simulate(
        initial, movement_placement=movement,
        structure_placement=building,
    )
    again = simulate(
        initial, movement_placement=movement,
        structure_placement=building,
    )
    assert result == again
    assert result.supported and result.status == STATUS
    assert initial == initial_copy
    assert result.state.turn == initial.turn + 1
    assert result.state.ships[1].x == 110
    assert result.state.ships[1].cargo.supplies == (
        initial.ships[1].cargo.supplies - 5
    )
    assert all(x.exact for x in result.ship_fuel_balances)
    assert all(x.resource_balance_exact for x in result.planet_balances)
    assert len(result.ship_fuel_balances) == 2
    assert {x.planet_id for x in result.planet_balances} == {10, 20}
    assert len(result.transfer_balances) == 1
    transfer = result.transfer_balances[0]
    assert transfer.ship_id == 1 and transfer.planet_id == 10
    assert transfer.direction == "ship_to_planet"
    assert dict(transfer.amounts)["supplies"] == 5
    assert transfer.resource_conserved
    assert len([e for e in result.events
                if e.phase == "planet_cargo_transfer"]) == 1
    assert not result.nuhost_order_execution_verified
    assert not result.nuhost_phase_placement_verified
    assert not result.independent_host_parity_verified


def test_transfer_before_and_after_movement_have_distinct_orbital_eligibility():
    state = world()
    original = deepcopy(state)
    intent = with_transfer()
    before = simulate(state, intent)
    after = simulate(state, intent, transfer_placement="transfer_after_movement")
    assert before.supported
    assert after.status == "ABSTAIN_ORBITAL_COMPOSITE_TURN"
    assert after.state is None and after.transfer_balances == ()
    assert state == original


def test_ship_can_arrive_and_then_load_from_owned_planet():
    state = world()
    extra = deepcopy(state.planets[10])
    extra.id = 11
    extra.x, extra.y = 110, 100
    extra.owner_id = 1
    extra.cargo.supplies = 50
    state.planets[11] = extra
    initial = deepcopy(state)
    request = with_transfer(
        direction="planet_to_ship", planet_id=11, supplies=6,
    )
    after = simulate(
        state, request, transfer_placement="transfer_after_movement",
    )
    before = simulate(
        state, request, transfer_placement="transfer_before_movement",
    )
    assert after.supported and before.status == "ABSTAIN_ORBITAL_COMPOSITE_TURN"
    assert after.state.ships[1].x == 110
    assert after.state.ships[1].cargo.supplies == (
        initial.ships[1].cargo.supplies + 6
    )
    assert after.transfer_balances[0].direction == "planet_to_ship"
    assert dict(after.transfer_balances[0].amounts)["supplies"] == 6
    assert state == initial


def test_transfer_funds_same_turn_construction_only_if_economy_after_transfer():
    state = world()
    state.planets[10].cargo.supplies = 0
    state.planets[10].cargo.megacredits = 0
    state.ships[1].cargo.supplies = 20
    build = {1: (StructureBuildTargets(10, factories=11),), 2: ()}
    request = with_transfer(supplies=8, x1=100, warp1=0)
    early = simulate(
        state, request, build,
        movement_placement="normal_before_economy_block",
        automatic_supply_sale_enabled=True,
    )
    late = simulate(
        state, request, build,
        movement_placement="normal_after_economy_block",
        automatic_supply_sale_enabled=True,
    )
    assert early.supported and late.supported
    assert early.state.planets[10].factories == 11
    assert late.state.planets[10].factories == 10
    assert early.planet_balances[0].construction_supplies_sold > 0
    assert late.planet_balances[0].construction_supplies_sold == 0
    assert not early.nuhost_phase_placement_verified


def test_planet_to_ship_loading_affects_fuel_and_cargo_mass_before_move():
    state = world()
    state.planets[10].cargo.neutronium = 100
    state.ships[1].cargo.neutronium = 0
    # Start with zero fuel: pre-move loading enables motion, post-move
    # loading comes too late and cannot rescue the otherwise unsupported leg.
    request = with_transfer(
        direction="planet_to_ship", supplies=0, x1=181,
    )
    first = request.by_player[1].ship_orders[0]
    request.by_player[1] = replace(
        request.by_player[1], ship_orders=(replace(
            first, planet_transfer=PlanetCargoTransferOrder(
                planet_id=10, direction="planet_to_ship", neutronium=20,
            )),)
    )
    before = simulate(state, request)
    after = simulate(state, request,
                     transfer_placement="transfer_after_movement")
    assert before.supported
    assert before.state.ships[1].cargo.neutronium < 20
    assert after.status == "ABSTAIN_ORBITAL_COMPOSITE_TURN"


@pytest.mark.parametrize("failure", (
    "absent_transfer", "zero_transfer", "negative_transfer",
    "bool_transfer", "foreign_planet", "missing_planet",
    "transfer_exceeds_ship", "transfer_exceeds_planet",
    "load_exceeds_capacity", "load_exceeds_fuel_tank",
    "bad_direction", "double_order", "missing_owner",
    "missing_build_owner", "after_movement_offsite",
    "unmodeled_starbase", "special_mission", "missing_assertion",
    "bad_placement",
))
def test_bad_scope_or_unaffordable_transfer_abstains_entire_turn(failure):
    state = world()
    requests = with_transfer()
    buildings = targets()
    opts = {}
    row = requests.by_player[1]
    order = row.ship_orders[0]
    transfer = order.planet_transfer
    assert transfer is not None
    if failure == "absent_transfer":
        requests.by_player[1] = replace(
            row, ship_orders=(replace(order, planet_transfer=None),))
    elif failure == "zero_transfer":
        transfer = replace(transfer, supplies=0)
    elif failure == "negative_transfer":
        transfer = replace(transfer, supplies=-1)
    elif failure == "bool_transfer":
        transfer = replace(transfer, supplies=True)
    elif failure == "foreign_planet":
        transfer = replace(transfer, planet_id=20)
    elif failure == "missing_planet":
        transfer = replace(transfer, planet_id=999)
    elif failure == "transfer_exceeds_ship":
        transfer = replace(transfer, supplies=999)
    elif failure == "transfer_exceeds_planet":
        transfer = replace(transfer, direction="planet_to_ship", supplies=999)
    elif failure == "load_exceeds_capacity":
        transfer = replace(transfer, direction="planet_to_ship", clans=1000)
    elif failure == "load_exceeds_fuel_tank":
        transfer = replace(transfer, direction="planet_to_ship", neutronium=999)
    elif failure == "bad_direction":
        transfer = replace(transfer, direction="skip_server")
    elif failure == "double_order":
        requests.by_player[1] = replace(row, ship_orders=row.ship_orders * 2)
    elif failure == "missing_owner":
        requests.by_player.pop(2)
    elif failure == "missing_build_owner":
        buildings.pop(2)
    elif failure == "after_movement_offsite":
        opts["transfer_placement"] = "transfer_after_movement"
    elif failure == "unmodeled_starbase":
        from planets_lab.core import Starbase
        state.starbases[10] = Starbase(planet_id=10, owner_id=1)
    elif failure == "special_mission":
        state.ships[1].mission = "6"
    elif failure == "missing_assertion":
        opts["complete_ship_and_structure_orders_asserted"] = False
    elif failure == "bad_placement":
        opts["transfer_placement"] = "nuhost_said_yes"
    if transfer is not order.planet_transfer and failure != "absent_transfer":
        requests.by_player[1] = replace(
            requests.by_player[1],
            ship_orders=(replace(order, planet_transfer=transfer),),
        )
    frozen = deepcopy(state)
    output = simulate(state, requests, buildings, **opts)
    assert not output.supported
    assert output.state is None
    assert output.events == ()
    assert output.planet_balances == ()
    assert output.ship_fuel_balances == ()
    assert output.transfer_balances == ()
    assert not output.nuhost_order_execution_verified
    assert state == frozen


@pytest.mark.parametrize("tamper", (
    "ship_supply", "planet_supply", "ship_fuel", "planet_mc",
    "transfer_amount", "transfer_ship_id", "transfer_direction",
    "removed_transfer", "duplicate_transfer", "removed_movement",
))
def test_poststate_or_transfer_receipt_tampering_abstains(tamper, monkeypatch):
    import planets_lab.sim.standard_orbital_transfer_turn as module
    original_step = module.HostEngine.step

    def damaged(self, pre, orders, *, seed=0):
        after, receipts = original_step(self, pre, orders, seed=seed)
        after = deepcopy(after)
        seq = list(receipts)
        if tamper == "ship_supply":
            after.ships[1].cargo.supplies += 1
        elif tamper == "planet_supply":
            after.planets[10].cargo.supplies += 1
        elif tamper == "ship_fuel":
            after.ships[1].cargo.neutronium += 1
        elif tamper == "planet_mc":
            after.planets[10].cargo.megacredits += 1
        elif tamper in (
            "transfer_amount", "transfer_ship_id", "transfer_direction",
        ):
            idx = next(i for i, e in enumerate(seq)
                       if e.phase == "planet_cargo_transfer")
            ev = seq[idx]
            body = dict(ev.details)
            key, bad = (
                ("supplies", "6") if tamper == "transfer_amount"
                else ("ship_id", "999") if tamper == "transfer_ship_id"
                else ("direction", "planet_to_ship")
            )
            body[key] = bad
            seq[idx] = replace(ev, details=tuple(body.items()))
        elif tamper == "removed_transfer":
            seq = [e for e in seq if e.phase != "planet_cargo_transfer"]
        elif tamper == "duplicate_transfer":
            seq += [e for e in seq if e.phase == "planet_cargo_transfer"]
        elif tamper == "removed_movement":
            seq = [e for e in seq if e.phase != "normal_movement"]
        return after, tuple(seq)

    monkeypatch.setattr(module.HostEngine, "step", damaged)
    state = world()
    preserved = deepcopy(state)
    result = simulate(state)
    assert not result.supported
    assert result.state is None and result.events == ()
    assert result.planet_balances == ()
    assert result.ship_fuel_balances == ()
    assert result.transfer_balances == ()
    assert state == preserved


def test_existing_owner_v2_signature_schema_is_not_modified():
    from dataclasses import fields
    from planets_lab.sim.planetary_owner_capture_v2 import OWNER_ROW_KEYS_V2
    assert [x.name for x in fields(PlayerOrders)] == [
        "player_id", "ship_orders", "starbase_tech_orders",
    ]
    assert OWNER_ROW_KEYS_V2 == frozenset(
        ("player_id", "ship_orders", "starbase_tech_orders")
    )
