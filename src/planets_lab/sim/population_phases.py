from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from planets_lab.core import GameState, Planet
from planets_lab.rules.population import (
    colonist_happiness_after_turn,
    ordinary_colonist_growth,
    ordinary_colonist_max_population,
    overpopulation_loss,
)
from planets_lab.sim.engine import HostEvent
from planets_lab.sim.orders import TurnOrders


ORDINARY_CLIMATE_RACE_IDS = frozenset({1, 2, 3, 5, 6, 8})


class UnsupportedPopulationRule(RuntimeError):
    pass


def _require_supported_owner(
    state: GameState,
    planet: Planet,
    supported_race_ids: frozenset[int],
) -> int:
    if planet.owner_id is None:
        raise UnsupportedPopulationRule(f"planet {planet.id} has colonists but no owner")
    player = state.players.get(planet.owner_id)
    if player is None or player.race_id is None:
        raise UnsupportedPopulationRule(
            f"planet {planet.id} owner {planet.owner_id} has unknown race"
        )
    if player.race_id not in supported_race_ids:
        raise UnsupportedPopulationRule(
            f"planet {planet.id} owner race {player.race_id} requires special population rules"
        )
    return player.race_id


@dataclass(slots=True)
class ColonistHappinessPhase:
    supported_race_ids: frozenset[int] = field(
        default_factory=lambda: ORDINARY_CLIMATE_RACE_IDS
    )
    name: str = field(init=False, default="colonist_happiness")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        events: list[HostEvent] = []
        for planet_id in sorted(state.planets):
            planet = state.planets[planet_id]
            if planet.cargo.clans <= 0:
                continue
            _require_supported_owner(state, planet, self.supported_race_ids)
            old = planet.happiness
            planet.happiness = colonist_happiness_after_turn(
                old_happiness=old,
                colonist_clans=planet.cargo.clans,
                tax_rate=planet.tax_rate,
                temperature=planet.temperature,
                factories=planet.factories,
                mines=planet.mines,
            )
            events.append(
                HostEvent(
                    phase=self.name,
                    kind="colonist_happiness_changed",
                    entity_type="planet",
                    entity_id=planet.id,
                    details=(("old", str(old)), ("new", str(planet.happiness))),
                    message=f"planet={planet.id} colonist_happiness {old}->{planet.happiness}",
                )
            )
        return events


@dataclass(slots=True)
class ColonistGrowthPhase:
    supported_race_ids: frozenset[int] = field(
        default_factory=lambda: ORDINARY_CLIMATE_RACE_IDS
    )
    name: str = field(init=False, default="colonist_growth")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        events: list[HostEvent] = []
        for planet_id in sorted(state.planets):
            planet = state.planets[planet_id]
            if planet.cargo.clans <= 0:
                continue
            _require_supported_owner(state, planet, self.supported_race_ids)
            growth = ordinary_colonist_growth(
                colonist_clans=planet.cargo.clans,
                tax_rate=planet.tax_rate,
                happiness=planet.happiness,
                temperature=planet.temperature,
            )
            if growth <= 0:
                continue
            planet.cargo.clans += growth
            events.append(
                HostEvent(
                    phase=self.name,
                    kind="colonists_grew",
                    entity_type="planet",
                    entity_id=planet.id,
                    details=(("growth", str(growth)), ("clans", str(planet.cargo.clans))),
                    message=f"planet={planet.id} colonist_growth +{growth}",
                )
            )
        return events


@dataclass(slots=True)
class ColonistOverpopulationPhase:
    supported_race_ids: frozenset[int] = field(
        default_factory=lambda: ORDINARY_CLIMATE_RACE_IDS
    )
    climate_death_rate_percent: int = 10
    name: str = field(init=False, default="colonist_overpopulation")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        events: list[HostEvent] = []
        for planet_id in sorted(state.planets):
            planet = state.planets[planet_id]
            if planet.cargo.clans <= 0:
                continue
            _require_supported_owner(state, planet, self.supported_race_ids)
            maximum = ordinary_colonist_max_population(planet.temperature)
            killed, supplies_used = overpopulation_loss(
                colonist_clans=planet.cargo.clans,
                maximum_population=maximum,
                supplies=planet.cargo.supplies,
                climate_death_rate_percent=self.climate_death_rate_percent,
            )
            if killed <= 0:
                continue
            planet.cargo.clans = max(0, planet.cargo.clans - killed)
            planet.cargo.supplies = max(0, planet.cargo.supplies - supplies_used)
            events.append(
                HostEvent(
                    phase=self.name,
                    kind="colonists_lost_to_overpopulation",
                    entity_type="planet",
                    entity_id=planet.id,
                    details=(
                        ("maximum_population", str(maximum)),
                        ("killed", str(killed)),
                        ("supplies_used", str(supplies_used)),
                        ("clans", str(planet.cargo.clans)),
                    ),
                    message=(
                        f"planet={planet.id} overpopulation killed={killed} "
                        f"supplies={supplies_used}"
                    ),
                )
            )
        return events
