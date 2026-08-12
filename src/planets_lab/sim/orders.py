from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class ShipOrder:
    ship_id: int
    waypoint_x: int | None = None
    waypoint_y: int | None = None
    warp: int | None = None
    mission: str | None = None
    primary_enemy_id: int | None = None
    friendly_code: str | None = None


@dataclass(slots=True, frozen=True)
class PlayerOrders:
    player_id: int
    ship_orders: tuple[ShipOrder, ...] = ()


@dataclass(slots=True, frozen=True)
class TurnOrders:
    """Orders submitted for one host turn, grouped by player id."""

    by_player: dict[int, PlayerOrders] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> "TurnOrders":
        return cls()
