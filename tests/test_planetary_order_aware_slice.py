from __future__ import annotations

import pytest

from pathlib import Path
import sys

# Single dependency-free fixture source for CI and server runtime.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "diagnostics"))
from planetary_order_aware_scenarios_v1 import (
    fixture, order, orders_sequence, specs, unsupported_scenarios,
)
from planets_lab.sim.orders import PlanetCargoTransferOrder, PlayerOrders, ShipOrder, TurnOrders
from planets_lab.sim.planetary_order_aware_slice import PlanetaryOrderAwareSlice


def totals(state):
    return {name: sum(getattr(s.cargo, name) for s in state.ships.values()) +
            sum(getattr(p.cargo, name) for p in state.planets.values())
            for name in ("supplies", "neutronium", "duranium", "megacredits", "clans")}


@pytest.mark.parametrize("placement", ["transfer_before_planetary", "transfer_after_planetary"])
def test_three_real_turn_orders_and_phase_ledger(placement):
    pipe = PlanetaryOrderAwareSlice(specs(), placement)
    source = fixture()
    sequence = orders_sequence()
    state = source
    trace = []
    for index, orders in enumerate(sequence):
        original = state.clone()
        result = pipe.step(state, orders, seed=13 + index)
        assert state == original
        assert result.supported
        assert result.state is not None
        assert result.state.turn == original.turn + 1
        assert len(result.balances) == 15
        phase_names = [item.phase for item in result.balances]
        assert phase_names.index("planet_cargo_transfer") == (0 if placement == "transfer_before_planetary" else 14)
        assert all(not item.combined_net_delta and not item.ground_mineral_delta
                   for item in result.balances if item.category == "explicit_transfer")
        assert any(item.phase == "factory_supplies" and item.combined_net_delta.get("supplies", 0) > 0
                   for item in result.balances)
        assert any(item.phase == "mineral_mining" and
                   item.planet_cargo_delta.get(10, {}).get("duranium", 0) > 0 and
                   item.ground_mineral_delta.get(10, {}).get("duranium", 0) < 0
                   for item in result.balances)
        assert any(item.phase == "tax_collection" and item.combined_net_delta.get("megacredits", 0) > 0
                   for item in result.balances)
        if index == 0:
            assert result.state.ships[1].cargo.supplies == 30
            assert result.state.ships[1].cargo.neutronium == 20
            assert result.state.ships[1].cargo.clans == 15
        if index == 1:
            assert result.state.ships[1].cargo.supplies == 26
            assert result.state.ships[1].cargo.neutronium == 15
            assert result.state.ships[1].cargo.clans == 12
        trace.append((result.state, result.events, result.balances))
        state = result.state
    assert source.turn == 7
    assert state.turn == 10
    replay = fixture()
    for i, orders in enumerate(sequence):
        outcome = pipe.step(replay, orders, seed=13 + i)
        assert outcome.state == trace[i][0]
        assert outcome.events == trace[i][1]
        assert outcome.balances == trace[i][2]
        replay = outcome.state


@pytest.mark.parametrize("kind", ["cargo", "fuel", "owner", "orbit", "funds", "unowned_money", "unknown_hull", "movement"])
def test_abstain_fail_closed_and_no_source_mutation(kind):
    state = fixture()
    spec = specs(capacity=45 if kind == "cargo" else 200, fuel=12 if kind == "fuel" else 100)
    request = order(supplies=40 if kind == "cargo" else 0,
                    neutronium=5 if kind == "fuel" else 0,
                    megacredits=100000 if kind == "funds" else 0)
    if kind == "owner":
        state.planets[10].owner_id = 2
        request = order(supplies=1)
    if kind == "orbit":
        state.ships[1].x = 101
        request = order(supplies=1)
    if kind == "unowned_money":
        state.planets[10].owner_id = None
        request = order("ship_to_planet", megacredits=1)
    if kind == "unknown_hull":
        state.ships[1].hull_id = 200
        request = order(supplies=1)
    if kind == "movement":
        request = TurnOrders(by_player={1: PlayerOrders(
            player_id=1, ship_orders=(ShipOrder(ship_id=1, warp=9, planet_transfer=
                PlanetCargoTransferOrder(planet_id=10, supplies=1, direction="planet_to_ship")),)
        )})
    original = state.clone()
    result = PlanetaryOrderAwareSlice(spec, "transfer_before_planetary").attempt_step(state, request)
    assert result.status == "ABSTAIN_UNSUPPORTED_OR_INVALID"
    assert result.state is None and not result.events and not result.balances
    assert result.abstain_reason
    assert state == original


def test_placement_is_required_and_changes_observable_supply_on_load():
    with pytest.raises(ValueError):
        PlanetaryOrderAwareSlice(specs(), "unspecified")
    state = fixture()
    # Initial supplies 40: factories add 10, but a request for 45 is
    # possible only under the explicit post-economy placement assumption.
    request = order(supplies=45)
    pre = PlanetaryOrderAwareSlice(specs(), "transfer_before_planetary").attempt_step(state, request)
    post = PlanetaryOrderAwareSlice(specs(), "transfer_after_planetary").attempt_step(state, request)
    assert not pre.supported
    assert post.supported
    assert post.state.ships[1].cargo.supplies == 65
    assert state.planets[10].cargo.supplies == 40


def test_input_orders_cannot_impersonate_owner():
    state = fixture()
    request = TurnOrders(by_player={2: PlayerOrders(player_id=2, ship_orders=(
        ShipOrder(ship_id=1, planet_transfer=PlanetCargoTransferOrder(planet_id=10, supplies=1)),)
    )})
    result = PlanetaryOrderAwareSlice(specs(), "transfer_before_planetary").attempt_step(state, request)
    assert not result.supported and result.state is None
