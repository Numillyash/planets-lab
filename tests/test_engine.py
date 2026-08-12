from random import Random

import pytest

from planets_lab.core import GameState, Player, Ship
from planets_lab.sim import HostEngine, HostEvent, PlayerOrders, ShipOrder, TurnOrders


class RandomMarkerPhase:
    name = "random-marker"

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        state.metadata["marker"] = rng.randint(0, 1_000_000)
        return [HostEvent(phase=self.name, kind="marker")]


def make_state() -> GameState:
    return GameState(
        game_id="test-game",
        turn=7,
        players={
            1: Player(id=1, name="Alpha"),
            2: Player(id=2, name="Beta"),
        },
        ships={
            10: Ship(id=10, owner_id=1, hull_id=1, x=1000, y=1000),
        },
    )


def test_step_is_deterministic_and_does_not_mutate_input() -> None:
    state = make_state()
    engine = HostEngine(phases=(RandomMarkerPhase(),))

    next_a, events_a = engine.step(state, TurnOrders.empty(), seed=12345)
    next_b, events_b = engine.step(state, TurnOrders.empty(), seed=12345)

    assert state.turn == 7
    assert "marker" not in state.metadata

    assert next_a == next_b
    assert events_a == events_b
    assert next_a.turn == 8
    assert next_a.metadata["marker"] == next_b.metadata["marker"]


def test_orders_cannot_control_another_players_ship() -> None:
    state = make_state()
    orders = TurnOrders(
        by_player={
            2: PlayerOrders(
                player_id=2,
                ship_orders=(ShipOrder(ship_id=10, warp=9),),
            )
        }
    )

    with pytest.raises(ValueError, match="cannot issue orders"):
        HostEngine().step(state, orders)


def test_duplicate_ship_orders_are_rejected() -> None:
    state = make_state()
    orders = TurnOrders(
        by_player={
            1: PlayerOrders(
                player_id=1,
                ship_orders=(
                    ShipOrder(ship_id=10, warp=8),
                    ShipOrder(ship_id=10, warp=9),
                ),
            )
        }
    )

    with pytest.raises(ValueError, match="duplicate order"):
        HostEngine().step(state, orders)
