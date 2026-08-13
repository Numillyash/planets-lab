from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from planets_lab.core import GameState, Ship
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.engine import HostEvent
from planets_lab.sim.orders import PlanetCargoTransferOrder, TurnOrders

TRANSFER_FIELDS = (
    "neutronium",
    "duranium",
    "tritanium",
    "molybdenum",
    "supplies",
    "clans",
    "megacredits",
)
BULK_CARGO_FIELDS = ("duranium", "tritanium", "molybdenum", "supplies", "clans")


class UnsupportedPlanetCargoTransfer(RuntimeError):
    pass


def _amounts(transfer: PlanetCargoTransferOrder) -> dict[str, int]:
    result: dict[str, int] = {}
    for name in TRANSFER_FIELDS:
        value = getattr(transfer, name)
        if value < 0:
            raise ValueError(f"transfer {name} must be non-negative")
        if value:
            result[name] = value
    return result


def _bulk_cargo_load(ship: Ship) -> int:
    return sum(getattr(ship.cargo, name) for name in BULK_CARGO_FIELDS)


@dataclass(slots=True)
class PlanetCargoTransferPhase:
    specs: NuStaticSpecs
    allow_unowned_megacredits: bool = False
    name: str = field(init=False, default="planet_cargo_transfer")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del rng
        events: list[HostEvent] = []
        ship_orders = sorted(
            (
                ship_order
                for player_id in sorted(orders.by_player)
                for ship_order in orders.by_player[player_id].ship_orders
                if ship_order.planet_transfer is not None
            ),
            key=lambda order: order.ship_id,
        )

        for ship_order in ship_orders:
            ship = state.ships[ship_order.ship_id]
            transfer = ship_order.planet_transfer
            assert transfer is not None
            planet = state.planets.get(transfer.planet_id)
            if planet is None:
                raise ValueError(f"transfer references unknown planet {transfer.planet_id}")
            if (ship.x, ship.y) != (planet.x, planet.y):
                raise UnsupportedPlanetCargoTransfer(
                    f"ship {ship.id} is not orbiting planet {planet.id}"
                )

            amounts = _amounts(transfer)
            if not amounts:
                continue

            if transfer.direction == "ship_to_planet":
                if planet.owner_id not in (None, ship.owner_id):
                    raise UnsupportedPlanetCargoTransfer(
                        "transfer to a planet owned by another player is not implemented"
                    )
                if (
                    planet.owner_id is None
                    and amounts.get("megacredits", 0) > 0
                    and not self.allow_unowned_megacredits
                ):
                    raise UnsupportedPlanetCargoTransfer(
                        "ordinary transfers cannot beam MegaCredits to an unowned planet"
                    )
                self._require_available(ship.cargo, amounts, source=f"ship {ship.id}")
                for name, amount in amounts.items():
                    setattr(ship.cargo, name, getattr(ship.cargo, name) - amount)
                    setattr(planet.cargo, name, getattr(planet.cargo, name) + amount)
                colonized = planet.owner_id is None and amounts.get("clans", 0) > 0
                if colonized:
                    planet.owner_id = ship.owner_id
                events.append(
                    self._event(ship.id, planet.id, transfer.direction, amounts, colonized)
                )
                continue

            if transfer.direction == "planet_to_ship":
                if planet.owner_id != ship.owner_id:
                    raise UnsupportedPlanetCargoTransfer(
                        "ordinary planet-to-ship transfer requires common ownership"
                    )
                self._require_available(planet.cargo, amounts, source=f"planet {planet.id}")
                self._require_ship_capacity(ship, amounts)
                for name, amount in amounts.items():
                    setattr(planet.cargo, name, getattr(planet.cargo, name) - amount)
                    setattr(ship.cargo, name, getattr(ship.cargo, name) + amount)
                events.append(
                    self._event(ship.id, planet.id, transfer.direction, amounts, False)
                )
                continue

            raise ValueError(
                "planet cargo transfer direction must be ship_to_planet or planet_to_ship"
            )

        return events

    @staticmethod
    def _require_available(cargo: object, amounts: dict[str, int], *, source: str) -> None:
        for name, amount in amounts.items():
            available = getattr(cargo, name)
            if amount > available:
                raise ValueError(
                    f"{source} has insufficient {name}: requested {amount}, available {available}"
                )

    def _require_ship_capacity(self, ship: Ship, amounts: dict[str, int]) -> None:
        hull = self.specs.hulls.get(ship.hull_id)
        if hull is None:
            raise UnsupportedPlanetCargoTransfer(
                f"unknown hull {ship.hull_id} for ship {ship.id}"
            )
        resulting_bulk = _bulk_cargo_load(ship) + sum(
            amounts.get(name, 0) for name in BULK_CARGO_FIELDS
        )
        if resulting_bulk > hull.cargo_capacity:
            raise UnsupportedPlanetCargoTransfer(
                f"ship {ship.id} cargo capacity exceeded: "
                f"{resulting_bulk}>{hull.cargo_capacity}"
            )
        resulting_fuel = ship.cargo.neutronium + amounts.get("neutronium", 0)
        if resulting_fuel > hull.fuel_tank:
            raise UnsupportedPlanetCargoTransfer(
                f"ship {ship.id} fuel tank exceeded: {resulting_fuel}>{hull.fuel_tank}"
            )

    def _event(
        self,
        ship_id: int,
        planet_id: int,
        direction: str,
        amounts: dict[str, int],
        colonized: bool,
    ) -> HostEvent:
        details = (
            ("ship_id", str(ship_id)),
            ("planet_id", str(planet_id)),
            ("direction", direction),
            ("colonized", str(colonized).lower()),
        ) + tuple((name, str(amounts.get(name, 0))) for name in TRANSFER_FIELDS)
        return HostEvent(
            phase=self.name,
            kind="planet_colonized" if colonized else "planet_cargo_transferred",
            entity_type="planet",
            entity_id=planet_id,
            details=details,
            message=f"ship={ship_id} planet={planet_id} direction={direction}",
        )
