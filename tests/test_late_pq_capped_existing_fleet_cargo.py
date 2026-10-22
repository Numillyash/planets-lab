"""Capped ordinary ship queue: cargo and movement of EXISTING vessels."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from planets_lab.sim.late_pq_capped_existing_fleet_cargo import (
    STATUS, PLACEMENTS, CappedFleetCargoTurn,
    simulate_capped_pq_existing_ship_cargo_carry,
)
from planets_lab.sim.orders import (
    PlanetCargoTransferOrder, PlayerOrders, ShipOrder, TurnOrders,
)
from test_late_pq_capped_no_build_carry import fixture_capped


def orders(state, *, dest=310, transfer=True):
    rows = {}
    for owner in sorted(state.players):
        ship_orders = []
        for sid, ship in sorted(state.ships.items()):
            if ship.owner_id != owner:
                continue
            if sid == 10:
                ship_orders.append(ShipOrder(
                    ship_id=sid, waypoint_x=dest, waypoint_y=300, warp=5,
                    planet_transfer=(
                        PlanetCargoTransferOrder(
                            planet_id=20, direction="planet_to_ship",
                            neutronium=60, supplies=4,
                        ) if transfer else None
                    ),
                ))
            else:
                ship_orders.append(ShipOrder(
                    ship_id=sid, waypoint_x=ship.x,
                    waypoint_y=ship.y, warp=0,
                ))
        rows[owner] = PlayerOrders(owner, ship_orders=tuple(ship_orders))
    return TurnOrders(by_player=rows)


def setup():
    state, specs, carry, queues = fixture_capped()
    specs.engines[9] = replace(
        specs.engines[9],
        warp_fuel_factors=(0, 2000, 4000, 10000, 20000, 50000,
                           80000, 130000, 160000, 180000),
    )
    plans = (
        CappedFleetCargoTurn(
            ordinary_queue=queues[0],
            all_ship_orders=orders(state),
            active_ship_id=10,
            placement=PLACEMENTS[0],
            no_other_fleet_or_host_actions_asserted=True,
        ),
        CappedFleetCargoTurn(
            ordinary_queue=queues[1],
            all_ship_orders=orders(state, dest=320, transfer=False),
            active_ship_id=10,
            placement=PLACEMENTS[1],
            no_other_fleet_or_host_actions_asserted=True,
        ),
    )
    return state, specs, carry, plans


def run(state, specs, carry, plans, **overrides):
    kwargs = dict(
        standard_rules_asserted=True,
        complete_fleet_queue_warehouse_and_owner_pp_asserted=True,
        no_priority_clone_mining_stations_or_external_effects_asserted=True,
        complete_no_encounter_routes_asserted=True,
    )
    kwargs.update(overrides)
    return simulate_capped_pq_existing_ship_cargo_carry(
        state, specs, carry, plans, **kwargs,
    )


@pytest.mark.parametrize("first", PLACEMENTS)
@pytest.mark.parametrize("second", PLACEMENTS)
def test_full_soft_cap_waits_while_existing_ship_loads_and_moves_twice(first, second):
    state, specs, carry, plans = setup()
    steps = (
        replace(plans[0], placement=first),
        replace(plans[1], placement=second),
    )
    frozen = deepcopy((state, specs, carry, steps))
    outcome = run(state, specs, carry, steps)
    assert outcome.supported and outcome.status == STATUS, outcome.reason
    assert outcome == run(state, specs, carry, steps)
    assert outcome.state.turn == state.turn + 2
    assert len(outcome.state.ships) == carry.soft_ship_limit == 10
    assert set(outcome.state.ships) == set(state.ships)
    assert (outcome.state.ships[10].x, outcome.state.ships[10].y) == (320, 300)
    assert outcome.state.ships[10].cargo.supplies == 4
    assert outcome.state.ships[10].cargo.neutronium == (
        60 - sum(step.ship_fuel.fuel_used for step in outcome.turns)
    )
    assert all(step.ship_fuel.fuel_used > 0 for step in outcome.turns)
    assert [step.waiting_queued_base_ids for step in outcome.turns] == [
        (10, 20), (20, 30),
    ]
    assert all(step.built_ship_ids == () for step in outcome.turns)
    assert len(outcome.turns[0].transfers) == 1
    assert outcome.turns[1].transfers == ()
    assert outcome.carry_after == carry
    assert outcome.carry_after.owner_pp == ((1, 3), (2, 7))
    assert len(outcome.carry_after.all_base_warehouses) == 3
    assert all(b.resource_balance_exact for t in outcome.turns
               for b in t.planet_balances)
    assert outcome.state.starbases == state.starbases
    assert all(outcome.state.ships[sid] == state.ships[sid]
               for sid in state.ships if sid != 10)
    assert not outcome.authenticated_ship_orders
    assert not outcome.independently_verified_no_build
    assert not outcome.nuhost_phase_order_verified
    assert not outcome.nuhost_execution_verified
    assert not outcome.independent_host_parity_verified
    assert (state, specs, carry, steps) == frozen


def test_capped_fleet_cargo_movement_amount_affects_planet_but_not_warehouses():
    state, specs, carry, plans = setup()
    changed = deepcopy(plans)
    first = changed[0]
    by = deepcopy(first.all_ship_orders)
    rows = list(by.by_player[2].ship_orders)
    rows[0] = replace(rows[0], planet_transfer=replace(
        rows[0].planet_transfer, supplies=15,
    ))
    by.by_player[2] = replace(by.by_player[2], ship_orders=tuple(rows))
    changed = (replace(first, all_ship_orders=by), changed[1])
    a = run(state, specs, carry, plans)
    b = run(state, specs, carry, changed)
    assert a.supported and b.supported
    assert b.state.ships[10].cargo.supplies == 15
    assert b.carry_after == a.carry_after == carry
    assert b.state.planets[20].cargo.supplies == a.state.planets[20].cargo.supplies - 11


@pytest.mark.parametrize("bad", (
    "below_soft", "wrong_soft", "duplicate_pp", "bad_idle_stock",
    "missing_base", "single_queue", "missing_tech", "missing_owner_orders",
    "missing_ship_order", "duplicate_ship_order", "wrong_ship_owner",
    "not_noop_other_ship", "unknown_mover", "bool_mover",
    "invalid_transfer_owner", "transfer_from_other_planet",
    "unknown_transfer", "empty_transfer", "negative_transfer",
    "bool_transfer", "overfilled_tank", "unfunded_planet",
    "unreachable_waypoint", "zero_warp", "wrong_ship_mission",
    "unsupported_hull", "other_ship_moving_before",
    "no_full_roster", "no_special_exclusion", "no_routes",
    "no_standard", "bad_seed", "no_priority_per_turn",
    "invalid_phase", "external_mutation",
))
def test_invalid_step_rejects_whole_multi_turn_carry(bad):
    state, specs, carry, steps = setup()
    plans = list(deepcopy(steps))
    options = {}
    if bad == "below_soft":
        state.ships.pop(10)
    elif bad == "wrong_soft":
        carry = replace(carry, soft_ship_limit=11)
    elif bad == "duplicate_pp":
        carry = replace(carry, owner_pp=((1, 3), (1, 7)))
    elif bad == "bad_idle_stock":
        from planets_lab.sim.standard_ship_warehouse_assembly import StandardComponentWarehouse
        rows = list(carry.all_base_warehouses)
        rows[2] = (30, StandardComponentWarehouse(hulls=((999, 1),)))
        carry = replace(carry, all_base_warehouses=tuple(rows))
    elif bad == "missing_base":
        plans[1] = replace(plans[1], ordinary_queue=replace(
            plans[1].ordinary_queue,
            all_bases=plans[1].ordinary_queue.all_bases[:2],
        ))
    elif bad == "single_queue":
        bs = list(plans[1].ordinary_queue.all_bases)
        bs[1] = replace(bs[1], blueprint=None, allowed_hull_ids=frozenset())
        plans[1] = replace(plans[1], ordinary_queue=replace(
            plans[1].ordinary_queue, all_bases=tuple(bs),
        ))
    elif bad == "missing_tech":
        bs = list(plans[1].ordinary_queue.all_bases)
        bs[1] = replace(bs[1], blueprint=replace(bs[1].blueprint, engine_id=999))
        plans[1] = replace(plans[1], ordinary_queue=replace(
            plans[1].ordinary_queue, all_bases=tuple(bs),
        ))
    elif bad == "missing_owner_orders":
        plans[1].all_ship_orders.by_player.pop(2)
    elif bad == "missing_ship_order":
        own = plans[1].all_ship_orders.by_player[1]
        plans[1].all_ship_orders.by_player[1] = replace(
            own, ship_orders=own.ship_orders[:-1],
        )
    elif bad == "duplicate_ship_order":
        own = plans[1].all_ship_orders.by_player[1]
        plans[1].all_ship_orders.by_player[1] = replace(
            own, ship_orders=own.ship_orders + (own.ship_orders[0],),
        )
    elif bad == "wrong_ship_owner":
        own = plans[1].all_ship_orders.by_player[1]
        plans[1].all_ship_orders.by_player[1] = replace(
            own, ship_orders=own.ship_orders + (
                plans[1].all_ship_orders.by_player[2].ship_orders[0],
            ),
        )
    elif bad == "not_noop_other_ship":
        own = plans[1].all_ship_orders.by_player[1]
        rows = list(own.ship_orders)
        rows[0] = replace(rows[0], warp=5)
        plans[1].all_ship_orders.by_player[1] = replace(own, ship_orders=tuple(rows))
    elif bad == "unknown_mover":
        plans[1] = replace(plans[1], active_ship_id=99)
    elif bad == "bool_mover":
        plans[1] = replace(plans[1], active_ship_id=True)
    elif bad == "invalid_transfer_owner":
        t = plans[0].all_ship_orders.by_player[2].ship_orders[0]
        plans[0].all_ship_orders.by_player[2] = replace(
            plans[0].all_ship_orders.by_player[2],
            ship_orders=(replace(t, planet_transfer=replace(
                t.planet_transfer, planet_id=10,
            )),),
        )
    elif bad == "transfer_from_other_planet":
        t = plans[0].all_ship_orders.by_player[2].ship_orders[0]
        plans[0].all_ship_orders.by_player[2] = replace(
            plans[0].all_ship_orders.by_player[2],
            ship_orders=(replace(t, planet_transfer=replace(
                t.planet_transfer, planet_id=30,
            )),),
        )
    elif bad == "unknown_transfer":
        t = plans[0].all_ship_orders.by_player[2].ship_orders[0]
        plans[0].all_ship_orders.by_player[2] = replace(
            plans[0].all_ship_orders.by_player[2],
            ship_orders=(replace(t, planet_transfer="opaque"),),
        )
    elif bad == "empty_transfer":
        t = plans[0].all_ship_orders.by_player[2].ship_orders[0]
        plans[0].all_ship_orders.by_player[2] = replace(
            plans[0].all_ship_orders.by_player[2],
            ship_orders=(replace(t, planet_transfer=replace(
                t.planet_transfer, neutronium=0, supplies=0,
            )),),
        )
    elif bad == "negative_transfer":
        t = plans[0].all_ship_orders.by_player[2].ship_orders[0]
        plans[0].all_ship_orders.by_player[2] = replace(
            plans[0].all_ship_orders.by_player[2],
            ship_orders=(replace(t, planet_transfer=replace(
                t.planet_transfer, neutronium=-1,
            )),),
        )
    elif bad == "bool_transfer":
        t = plans[0].all_ship_orders.by_player[2].ship_orders[0]
        plans[0].all_ship_orders.by_player[2] = replace(
            plans[0].all_ship_orders.by_player[2],
            ship_orders=(replace(t, planet_transfer=replace(
                t.planet_transfer, neutronium=True,
            )),),
        )
    elif bad == "overfilled_tank":
        t = plans[0].all_ship_orders.by_player[2].ship_orders[0]
        plans[0].all_ship_orders.by_player[2] = replace(
            plans[0].all_ship_orders.by_player[2],
            ship_orders=(replace(t, planet_transfer=replace(
                t.planet_transfer, neutronium=400,
            )),),
        )
    elif bad == "unfunded_planet":
        state.planets[20].cargo.neutronium = 0
    elif bad == "unreachable_waypoint":
        t = plans[1].all_ship_orders.by_player[2].ship_orders[0]
        plans[1].all_ship_orders.by_player[2] = replace(
            plans[1].all_ship_orders.by_player[2],
            ship_orders=(replace(t, waypoint_x=800, waypoint_y=800),),
        )
    elif bad == "zero_warp":
        t = plans[1].all_ship_orders.by_player[2].ship_orders[0]
        plans[1].all_ship_orders.by_player[2] = replace(
            plans[1].all_ship_orders.by_player[2],
            ship_orders=(replace(t, warp=0),),
        )
    elif bad == "wrong_ship_mission":
        t = plans[1].all_ship_orders.by_player[2].ship_orders[0]
        plans[1].all_ship_orders.by_player[2] = replace(
            plans[1].all_ship_orders.by_player[2],
            ship_orders=(replace(t, mission="intercept"),),
        )
    elif bad == "unsupported_hull":
        state.ships[10].hull_id = 999
    elif bad == "other_ship_moving_before":
        state.ships[1].warp = 8
    elif bad == "no_full_roster":
        options["complete_fleet_queue_warehouse_and_owner_pp_asserted"] = False
    elif bad == "no_special_exclusion":
        options["no_priority_clone_mining_stations_or_external_effects_asserted"] = False
    elif bad == "no_routes":
        options["complete_no_encounter_routes_asserted"] = False
    elif bad == "no_standard":
        options["standard_rules_asserted"] = False
    elif bad == "bad_seed":
        options["seed"] = True
    elif bad == "no_priority_per_turn":
        plans[1] = replace(plans[1], ordinary_queue=replace(
            plans[1].ordinary_queue,
            no_priority_or_special_orders_on_this_turn_asserted=False,
        ))
    elif bad == "invalid_phase":
        plans[1] = replace(plans[1], placement="actual_NuHost_verified")
    elif bad == "external_mutation":
        state.metadata["external"] = True
    frozen = deepcopy((state, specs, carry, tuple(plans)))
    result = run(state, specs, carry, tuple(plans), **options)
    assert not result.supported
    assert result.state is None and result.carry_after is None
    assert result.turns == ()
    assert (state, specs, carry, tuple(plans)) == frozen


@pytest.mark.parametrize("bad", (
    "planet_minted_mc", "ground_minted", "missing_transfer",
    "forged_transfer_id", "missing_move", "wrong_move_fuel",
    "extra_ship", "crew_modified", "second_turn_minted",
))
def test_forged_events_and_changes_reject_all_turn_receipts(monkeypatch, bad):
    import planets_lab.sim.late_pq_capped_existing_fleet_cargo as module
    state, specs, carry, plans = setup()
    original = module.HostEngine.step
    seen = [0]

    def forged(self, previous, orders, *, seed=0):
        after, events = original(self, previous, orders, seed=seed)
        seen[0] += 1
        if seen[0] == 2 or bad != "second_turn_minted":
            after = deepcopy(after)
            if bad in ("planet_minted_mc", "second_turn_minted"):
                after.planets[30].cargo.megacredits += 1
            elif bad == "ground_minted":
                after.planets[30].ground_duranium.amount += 1
            elif bad == "missing_transfer":
                events = tuple(x for x in events if x.phase != "planet_cargo_transfer")
            elif bad == "forged_transfer_id":
                events = tuple(replace(x, entity_id=99)
                               if x.phase == "planet_cargo_transfer" else x for x in events)
            elif bad == "missing_move":
                events = tuple(x for x in events if x.phase != "normal_movement")
            elif bad == "wrong_move_fuel":
                events = tuple(replace(x, entity_id=11)
                               if x.phase == "normal_movement" else x for x in events)
            elif bad == "extra_ship":
                after.ships[99] = deepcopy(after.ships[10])
                after.ships[99].id = 99
            elif bad == "crew_modified":
                after.ships[10].crew += 1
        return after, events

    monkeypatch.setattr(module.HostEngine, "step", forged)
    r = run(state, specs, carry, plans)
    assert not r.supported and r.state is None and r.carry_after is None
    assert r.turns == ()
