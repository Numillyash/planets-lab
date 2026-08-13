from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from planets_lab.core import GameState
from planets_lab.rules.economy import factory_supply_output
from planets_lab.rules.society import BOVINOID_NATIVE_RACE_ID, bovinoid_supply_output
from planets_lab.sim.engine import HostEvent
from planets_lab.sim.orders import TurnOrders


@dataclass(slots=True)
class FactorySupplyPhase:
    bovinoid_native_race_id: int = BOVINOID_NATIVE_RACE_ID
    name: str = field(init=False, default="factory_supplies")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        events: list[HostEvent] = []
        for planet_id in sorted(state.planets):
            planet = state.planets[planet_id]
            if planet.owner_id is None or planet.cargo.clans <= 0:
                continue

            factory_output = factory_supply_output(planet.factories)
            bovinoid_output = 0
            if planet.natives is not None and planet.natives.race_id == self.bovinoid_native_race_id:
                bovinoid_output = bovinoid_supply_output(
                    native_clans=planet.natives.clans,
                    colonist_clans=planet.cargo.clans,
                )

            produced = factory_output + bovinoid_output
            if produced <= 0:
                continue
            planet.cargo.supplies += produced
            events.append(HostEvent(
                phase=self.name,
                kind="supplies_produced",
                entity_type="planet",
                entity_id=planet.id,
                details=(
                    ("factories", str(planet.factories)),
                    ("factory_supplies", str(factory_output)),
                    ("bovinoid_supplies", str(bovinoid_output)),
                    ("supplies", str(produced)),
                ),
                message=(
                    f"planet={planet.id} factories={planet.factories} "
                    f"bovinoids={bovinoid_output} supplies={produced}"
                ),
            ))
        return events
