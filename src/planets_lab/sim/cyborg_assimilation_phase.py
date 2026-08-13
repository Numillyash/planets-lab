from __future__ import annotations

from dataclasses import dataclass
from random import Random

from planets_lab.core import GameState
from planets_lab.rules.population import CYBORG_RACE_ID, cyborg_assimilation
from planets_lab.sim.engine import HostEvent
from planets_lab.sim.orders import TurnOrders


@dataclass(slots=True)
class CyborgAssimilationPhase:
    assimilation_rate_percent: int = 100
    name: str = "cyborg_assimilation"

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        events: list[HostEvent] = []

        for planet_id in sorted(state.planets):
            planet = state.planets[planet_id]
            if planet.cargo.clans <= 0 or planet.natives is None or planet.natives.clans <= 0:
                continue
            if planet.owner_id is None:
                continue
            player = state.players.get(planet.owner_id)
            if player is None or player.race_id != CYBORG_RACE_ID:
                continue

            converted = cyborg_assimilation(
                colonist_clans=planet.cargo.clans,
                native_clans=planet.natives.clans,
                native_race_id=planet.natives.race_id,
                assimilation_rate_percent=self.assimilation_rate_percent,
            )
            if converted <= 0:
                continue

            planet.cargo.clans += converted
            planet.natives.clans -= converted
            remaining = planet.natives.clans
            if remaining <= 0:
                planet.natives = None

            events.append(
                HostEvent(
                    phase=self.name,
                    kind="natives_assimilated",
                    entity_type="planet",
                    entity_id=planet.id,
                    details=(
                        ("converted", str(converted)),
                        ("native_clans", str(max(0, remaining))),
                    ),
                    message=f"planet={planet.id} converted_natives={converted}",
                )
            )

        return events
