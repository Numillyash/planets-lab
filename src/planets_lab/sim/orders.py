from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class PlanetCargoTransferOrder:
    planet_id: int
    direction: str = "ship_to_planet"
    neutronium: int = 0
    duranium: int = 0
    tritanium: int = 0
    molybdenum: int = 0
    supplies: int = 0
    clans: int = 0
    megacredits: int = 0


@dataclass(slots=True, frozen=True)
class ShipOrder:
    ship_id: int
    waypoint_x: int | None = None
    waypoint_y: int | None = None
    warp: int | None = None
    mission: str | None = None
    primary_enemy_id: int | None = None
    friendly_code: str | None = None
    planet_transfer: PlanetCargoTransferOrder | None = None


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
