from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from planets_lab.core import GameState
from planets_lab.rules.mining import (
    DEFAULT_TRANS_URANIUM_RATE,
    mined_amount,
    mining_rate_for_race,
    trans_uranium_mutation_amount,
)
from planets_lab.sim.engine import HostEvent
from planets_lab.sim.orders import TurnOrders


MINERALS = (
    ("neutronium", "ground_neutronium"),
    ("duranium", "ground_duranium"),
    ("tritanium", "ground_tritanium"),
    ("molybdenum", "ground_molybdenum"),
)


@dataclass(slots=True)
class MineralMiningPhase:
    output_modifier_by_player_id: dict[int, int] = field(default_factory=dict)
    name: str = field(init=False, default="mineral_mining")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        events: list[HostEvent] = []

        for planet_id in sorted(state.planets):
            planet = state.planets[planet_id]
            if planet.owner_id is None or planet.mines <= 0:
                continue

            player = state.players.get(planet.owner_id)
            race_id = None if player is None else player.race_id
            rate = mining_rate_for_race(race_id)
            output_modifier = self.output_modifier_by_player_id.get(planet.owner_id, 100)
            mined: dict[str, int] = {}

            for cargo_name, deposit_name in MINERALS:
                deposit = getattr(planet, deposit_name)
                amount = mined_amount(
                    mines=planet.mines,
                    density=deposit.density,
                    ground_amount=deposit.amount,
                    mining_rate_percent=rate,
                    output_modifier_percent=output_modifier,
                )
                if amount <= 0:
                    continue
                deposit.amount -= amount
                setattr(planet.cargo, cargo_name, getattr(planet.cargo, cargo_name) + amount)
                mined[cargo_name] = amount

            if mined:
                events.append(
                    HostEvent(
                        phase=self.name,
                        kind="minerals_mined",
                        entity_type="planet",
                        entity_id=planet.id,
                        details=tuple((name, str(mined.get(name, 0))) for name, _ in MINERALS),
                        message=f"planet={planet.id} minerals_mined",
                    )
                )

        return events


@dataclass(slots=True)
class TransUraniumMutationPhase:
    mutation_rate: int = DEFAULT_TRANS_URANIUM_RATE
    name: str = field(init=False, default="trans_uranium_mutation")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        events: list[HostEvent] = []

        for planet_id in sorted(state.planets):
            planet = state.planets[planet_id]
            produced: dict[str, int] = {}

            for cargo_name, deposit_name in MINERALS:
                deposit = getattr(planet, deposit_name)
                amount = trans_uranium_mutation_amount(
                    density=deposit.density,
                    mutation_rate=self.mutation_rate,
                )
                if amount <= 0:
                    continue
                deposit.amount += amount
                produced[cargo_name] = amount

            if produced:
                events.append(
                    HostEvent(
                        phase=self.name,
                        kind="minerals_mutated",
                        entity_type="planet",
                        entity_id=planet.id,
                        details=tuple((name, str(produced.get(name, 0))) for name, _ in MINERALS),
                        message=f"planet={planet.id} trans_uranium_mutation",
                    )
                )

        return events
