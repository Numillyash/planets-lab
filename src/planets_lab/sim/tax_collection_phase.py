from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from planets_lab.core import GameState
from planets_lab.rules.economy import colonist_tax_income, combined_planet_tax_income, native_tax_income
from planets_lab.sim.engine import HostEvent
from planets_lab.sim.orders import TurnOrders


@dataclass(slots=True)
class TaxCollectionPhase:
    racial_modifier_by_player_id: dict[int, float] = field(default_factory=dict)
    native_rate_cap_by_player_id: dict[int, int] = field(default_factory=dict)
    insectoid_native_race_ids: frozenset[int] = field(default_factory=frozenset)
    untaxable_native_race_ids: frozenset[int] = field(default_factory=frozenset)
    name: str = field(init=False, default="tax_collection")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        events: list[HostEvent] = []
        for planet_id in sorted(state.planets):
            planet = state.planets[planet_id]
            if planet.owner_id is None or planet.cargo.clans <= 0:
                continue
            modifier = self.racial_modifier_by_player_id.get(planet.owner_id, 1.0)
            colonist_income = colonist_tax_income(
                colonist_clans=planet.cargo.clans,
                tax_rate=planet.tax_rate,
                happiness=planet.happiness,
                racial_tax_modifier=modifier,
            )
            native_income = 0
            if planet.natives is not None:
                natives = planet.natives
                native_income = native_tax_income(
                    native_clans=natives.clans,
                    tax_rate=natives.tax_rate,
                    happiness=natives.happiness,
                    government_id=natives.government_id,
                    colonist_clans=planet.cargo.clans,
                    racial_tax_modifier=modifier,
                    income_per_colonist_cap=2 if natives.race_id in self.insectoid_native_race_ids else 1,
                    taxable=natives.race_id not in self.untaxable_native_race_ids,
                    effective_tax_rate_cap=self.native_rate_cap_by_player_id.get(planet.owner_id),
                )
            collected = combined_planet_tax_income(colonist_income, native_income)
            if collected == 0:
                continue
            planet.cargo.megacredits += collected
            events.append(HostEvent(
                phase=self.name,
                kind="taxes_collected",
                entity_type="planet",
                entity_id=planet.id,
                details=(("colonist_income", str(colonist_income)), ("native_income", str(native_income)), ("collected", str(collected))),
                message=f"planet={planet.id} taxes={collected}",
            ))
        return events
