from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from planets_lab.core import GameState
from planets_lab.rules.economy import max_defense_posts, max_factories, max_mines
from planets_lab.rules.society import (
    AMORPHOUS_NATIVE_RACE_ID,
    AVIAN_NATIVE_RACE_ID,
    SILICONOID_NATIVE_RACE_ID,
    amorphous_clans_eaten,
    civil_war_population_after,
    decay_structure_count,
    native_happiness_after_turn,
    native_population_growth,
)
from planets_lab.sim.engine import HostEvent
from planets_lab.sim.orders import TurnOrders


@dataclass(slots=True)
class StructureDecayPhase:
    decay_rate: int = 3
    name: str = field(init=False, default="structure_decay")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        events: list[HostEvent] = []
        for planet_id in sorted(state.planets):
            planet = state.planets[planet_id]
            old_mines = planet.mines
            old_factories = planet.factories
            old_defense = planet.defense_posts

            planet.mines = decay_structure_count(
                current=planet.mines,
                supported_maximum=max_mines(planet.cargo.clans),
                decay_rate=self.decay_rate,
            )
            planet.factories = decay_structure_count(
                current=planet.factories,
                supported_maximum=max_factories(planet.cargo.clans),
                decay_rate=self.decay_rate,
            )
            planet.defense_posts = decay_structure_count(
                current=planet.defense_posts,
                supported_maximum=max_defense_posts(planet.cargo.clans),
                decay_rate=self.decay_rate,
            )

            if (planet.mines, planet.factories, planet.defense_posts) == (
                old_mines,
                old_factories,
                old_defense,
            ):
                continue
            events.append(
                HostEvent(
                    phase=self.name,
                    kind="structures_decayed",
                    entity_type="planet",
                    entity_id=planet.id,
                    details=(
                        ("mines", f"{old_mines}->{planet.mines}"),
                        ("factories", f"{old_factories}->{planet.factories}"),
                        ("defense", f"{old_defense}->{planet.defense_posts}"),
                    ),
                    message=f"planet={planet.id} unsupported structures decayed",
                )
            )
        return events


@dataclass(slots=True)
class NativeHappinessPhase:
    nebula_planet_ids: frozenset[int] = field(default_factory=frozenset)
    name: str = field(init=False, default="native_happiness")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        events: list[HostEvent] = []
        for planet_id in sorted(state.planets):
            planet = state.planets[planet_id]
            natives = planet.natives
            if natives is None or natives.clans <= 0:
                continue
            old = natives.happiness
            natives.happiness = native_happiness_after_turn(
                old_happiness=old,
                native_clans=natives.clans,
                tax_rate=natives.tax_rate,
                factories=planet.factories,
                mines=planet.mines,
                government_id=natives.government_id,
                avian_bonus=10 if natives.race_id == AVIAN_NATIVE_RACE_ID else 0,
                nebula_bonus=5 if planet.id in self.nebula_planet_ids else 0,
            )
            events.append(
                HostEvent(
                    phase=self.name,
                    kind="native_happiness_changed",
                    entity_type="planet",
                    entity_id=planet.id,
                    details=(("old", str(old)), ("new", str(natives.happiness))),
                    message=f"planet={planet.id} native_happiness {old}->{natives.happiness}",
                )
            )
        return events


@dataclass(slots=True)
class NativeGrowthPhase:
    name: str = field(init=False, default="native_growth")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        events: list[HostEvent] = []
        for planet_id in sorted(state.planets):
            planet = state.planets[planet_id]
            natives = planet.natives
            if natives is None or natives.clans <= 0:
                continue
            growth = native_population_growth(
                native_clans=natives.clans,
                tax_rate=natives.tax_rate,
                happiness=natives.happiness,
                temperature=planet.temperature,
                colonized=planet.owner_id is not None and planet.cargo.clans > 0,
                siliconoid=natives.race_id == SILICONOID_NATIVE_RACE_ID,
            )
            if growth <= 0:
                continue
            natives.clans += growth
            events.append(
                HostEvent(
                    phase=self.name,
                    kind="natives_grew",
                    entity_type="planet",
                    entity_id=planet.id,
                    details=(("growth", str(growth)), ("clans", str(natives.clans))),
                    message=f"planet={planet.id} native_growth +{growth}",
                )
            )
        return events


@dataclass(slots=True)
class AmorphousConsumptionPhase:
    amorphous_native_race_id: int = AMORPHOUS_NATIVE_RACE_ID
    name: str = field(init=False, default="amorphous_consumption")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        events: list[HostEvent] = []
        for planet_id in sorted(state.planets):
            planet = state.planets[planet_id]
            natives = planet.natives
            if (
                natives is None
                or natives.race_id != self.amorphous_native_race_id
                or natives.clans <= 0
                or planet.cargo.clans <= 0
            ):
                continue
            eaten = amorphous_clans_eaten(
                colonist_clans=planet.cargo.clans,
                native_happiness=natives.happiness,
            )
            if eaten <= 0:
                continue
            planet.cargo.clans -= eaten
            events.append(
                HostEvent(
                    phase=self.name,
                    kind="colonists_eaten_by_amorphous",
                    entity_type="planet",
                    entity_id=planet.id,
                    details=(("eaten", str(eaten)), ("clans", str(planet.cargo.clans))),
                    message=f"planet={planet.id} amorphous_eaten={eaten}",
                )
            )
        return events


@dataclass(slots=True)
class RiotsPhase:
    colonist_factory_loss: int = 8
    colonist_mine_loss: int = 10
    native_factory_loss: int = 3
    native_mine_loss: int = 5
    name: str = field(init=False, default="riots")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        events: list[HostEvent] = []
        for planet_id in sorted(state.planets):
            planet = state.planets[planet_id]
            colonist_riot = planet.cargo.clans > 0 and planet.happiness < 40
            native_riot = (
                planet.natives is not None
                and planet.natives.clans > 0
                and planet.natives.happiness < 40
            )
            if not colonist_riot and not native_riot:
                continue

            factory_loss = (self.colonist_factory_loss if colonist_riot else 0) + (
                self.native_factory_loss if native_riot else 0
            )
            mine_loss = (self.colonist_mine_loss if colonist_riot else 0) + (
                self.native_mine_loss if native_riot else 0
            )
            old_factories = planet.factories
            old_mines = planet.mines
            planet.factories = max(0, planet.factories - factory_loss)
            planet.mines = max(0, planet.mines - mine_loss)
            events.append(
                HostEvent(
                    phase=self.name,
                    kind="riots_destroyed_structures",
                    entity_type="planet",
                    entity_id=planet.id,
                    details=(
                        ("colonist_riot", str(colonist_riot).lower()),
                        ("native_riot", str(native_riot).lower()),
                        ("factories", f"{old_factories}->{planet.factories}"),
                        ("mines", f"{old_mines}->{planet.mines}"),
                    ),
                    message=f"planet={planet.id} riots damaged structures",
                )
            )
        return events


@dataclass(slots=True)
class CivilWarPhase:
    additional_factory_loss: int = 8
    additional_mine_loss: int = 10
    stack_population_losses_when_both: bool = False
    amorphous_native_race_id: int = AMORPHOUS_NATIVE_RACE_ID
    name: str = field(init=False, default="civil_war")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        events: list[HostEvent] = []
        for planet_id in sorted(state.planets):
            planet = state.planets[planet_id]
            colonist_war = planet.cargo.clans > 0 and planet.happiness < 0
            native_war = (
                planet.natives is not None
                and planet.natives.clans > 0
                and planet.natives.happiness < 0
            )
            if not colonist_war and not native_war:
                continue

            wars = int(colonist_war) + int(native_war)
            old_factories = planet.factories
            old_mines = planet.mines
            planet.factories = max(0, planet.factories - self.additional_factory_loss * wars)
            planet.mines = max(0, planet.mines - self.additional_mine_loss * wars)

            applications = wars if self.stack_population_losses_when_both else 1
            old_colonists = planet.cargo.clans
            old_natives = planet.natives.clans if planet.natives is not None else 0
            for _ in range(applications):
                planet.cargo.clans = civil_war_population_after(clans=planet.cargo.clans)
                if (
                    planet.natives is not None
                    and planet.natives.race_id != self.amorphous_native_race_id
                ):
                    planet.natives.clans = civil_war_population_after(clans=planet.natives.clans)

            events.append(
                HostEvent(
                    phase=self.name,
                    kind="civil_war_losses",
                    entity_type="planet",
                    entity_id=planet.id,
                    details=(
                        ("colonist_war", str(colonist_war).lower()),
                        ("native_war", str(native_war).lower()),
                        ("population_applications", str(applications)),
                        ("colonists", f"{old_colonists}->{planet.cargo.clans}"),
                        (
                            "natives",
                            f"{old_natives}->{planet.natives.clans if planet.natives is not None else 0}",
                        ),
                        ("factories", f"{old_factories}->{planet.factories}"),
                        ("mines", f"{old_mines}->{planet.mines}"),
                    ),
                    message=f"planet={planet.id} civil_war losses applied",
                )
            )
        return events
