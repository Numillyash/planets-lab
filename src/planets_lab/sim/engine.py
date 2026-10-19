from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Protocol

from planets_lab.core import GameState
from planets_lab.sim.orders import TurnOrders


@dataclass(slots=True, frozen=True)
class HostEvent:
    phase: str
    kind: str
    message: str = ""
    entity_type: str | None = None
    entity_id: int | str | None = None
    details: tuple[tuple[str, str], ...] = ()


class HostPhase(Protocol):
    name: str

    def run(
        self,
        state: GameState,
        orders: TurnOrders,
        rng: Random,
    ) -> list[HostEvent]: ...


class HostEngine:
    """Deterministic host pipeline.

    Host phases are intentionally injected rather than hard-coded here. This
    lets us reproduce NuHost order explicitly and validate each phase in
    isolation as the ruleset grows.
    """

    def __init__(self, phases: tuple[HostPhase, ...] = ()) -> None:
        self._phases = phases

    @property
    def phases(self) -> tuple[HostPhase, ...]:
        return self._phases

    def step(
        self,
        state: GameState,
        orders: TurnOrders,
        *,
        seed: int = 0,
    ) -> tuple[GameState, tuple[HostEvent, ...]]:
        state.validate()
        self._validate_orders(state, orders)
        if any(
            owner.starbase_tech_orders for owner in orders.by_player.values()
        ) and not any(p.name == "starbase_tech_upgrade" for p in self._phases):
            raise ValueError("starbase tech orders require an explicit technology phase")

        next_state = state.clone()
        rng = Random(seed)
        events: list[HostEvent] = []

        for phase in self._phases:
            events.extend(phase.run(next_state, orders, rng))

        next_state.turn += 1
        next_state.validate()
        return next_state, tuple(events)

    @staticmethod
    def _validate_orders(state: GameState, orders: TurnOrders) -> None:
        for player_id, player_orders in orders.by_player.items():
            if player_id not in state.players:
                raise ValueError(f"orders reference unknown player {player_id}")
            if player_orders.player_id != player_id:
                raise ValueError(
                    f"orders key {player_id} does not match player_orders.player_id "
                    f"{player_orders.player_id}"
                )

            seen_base_ids: set[int] = set()
            for upgrade in player_orders.starbase_tech_orders:
                planet_id = upgrade.planet_id
                if type(planet_id) is not int or planet_id <= 0:
                    raise ValueError("starbase order requires positive planet id")
                if planet_id in seen_base_ids:
                    raise ValueError(f"duplicate starbase tech order for planet {planet_id}")
                seen_base_ids.add(planet_id)
                base = state.starbases.get(planet_id)
                planet = state.planets.get(planet_id)
                if base is None or planet is None:
                    raise ValueError("starbase upgrade references missing planet/base")
                if base.owner_id != player_id or planet.owner_id != player_id:
                    raise ValueError("starbase technology order owner mismatch")

            seen_ship_ids: set[int] = set()
            for ship_order in player_orders.ship_orders:
                if ship_order.ship_id in seen_ship_ids:
                    raise ValueError(f"duplicate order for ship {ship_order.ship_id}")
                seen_ship_ids.add(ship_order.ship_id)

                ship = state.ships.get(ship_order.ship_id)
                if ship is None:
                    raise ValueError(f"orders reference unknown ship {ship_order.ship_id}")
                if ship.owner_id != player_id:
                    raise ValueError(
                        f"player {player_id} cannot issue orders for ship {ship_order.ship_id}"
                    )
