from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from planets_lab.core import GameState
from planets_lab.rules.economy import factory_supply_output
from planets_lab.sim.engine import HostEvent
from planets_lab.sim.orders import TurnOrders


@dataclass(slots=True)
class FactorySupplyPhase:
    name: str = field(init=False, default="factory_supplies")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        events: list[HostEvent] = []
        for planet_id in sorted(state.planets):
            planet = state.planets[planet_id]
            if planet.owner_id is None or planet.cargo.clans <= 0 or planet.factories <= 0:
                continue
            produced = factory_supply_output(planet.factories)
            planet.cargo.supplies += produced
            events.append(HostEvent(
                phase=self.name,
                kind="supplies_produced",
                entity_type="planet",
                entity_id=planet.id,
                details=(("factories", str(planet.factories)), ("supplies", str(produced))),
                message=f"planet={planet.id} factories={planet.factories} supplies={produced}",
            ))
        return events
