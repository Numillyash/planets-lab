"""Strict research-only standard starbase creation and defenses.

DOCUMENTED standard resource arithmetic, TESTED conditional local execution.
A base and its fighters/defenses do not imply ships or weapons in storage.
This never simulates an actual NuHost build queue, ship limit, new-ship ID,
retrofit/repair or a server-accepted order. Explicit owner-complete orders
are supplied *outside* the legacy signed PlayerOrders V1/V2 schemas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Mapping

from planets_lab.core import GameState, Starbase
from planets_lab.sim.engine import HostEvent

STANDARD_BASE_CREATION = (
    ("megacredits", 900),
    ("duranium", 120),
    ("tritanium", 402),
    ("molybdenum", 340),
)
STANDARD_BASE_FIGHTER_COST = (
    ("megacredits", 100),
    ("tritanium", 3),
    ("molybdenum", 2),
)
STANDARD_BASE_DEFENSE_COST = (
    ("megacredits", 10),
    ("duranium", 1),
)
MAX_STANDARD_BASE_FIGHTERS = 60
MAX_STANDARD_BASE_DEFENSE = 200
RESOURCE_KEYS = ("megacredits", "duranium", "tritanium", "molybdenum")


class UnsupportedStandardStarbaseFacility(RuntimeError):
    """Unsupported starbase action or insufficient resources: fail closed."""


@dataclass(frozen=True, slots=True)
class StandardBaseCreateOrder:
    planet_id: int


@dataclass(frozen=True, slots=True)
class StandardBaseArmOrder:
    """Absolute targets, not deltas; omissions leave the field unchanged."""
    planet_id: int
    defense_target: int | None = None
    fighter_target: int | None = None


StandardBaseFacilityOrder = StandardBaseCreateOrder | StandardBaseArmOrder


@dataclass(slots=True)
class StandardStarbaseFacilitiesPhase:
    """One non-overlapping order per planet, in ascending planet-id order."""

    orders_by_owner: Mapping[int, tuple[StandardBaseFacilityOrder, ...]]
    name: str = field(init=False, default="standard_starbase_facilities_conditional")

    def run(self, state: GameState, _orders: object, _rng: Random) -> list[HostEvent]:
        if type(self.orders_by_owner) is not dict or set(self.orders_by_owner) != set(state.players):
            raise UnsupportedStandardStarbaseFacility("explicit every-player scope required")
        declared: list[tuple[int, StandardBaseFacilityOrder]] = []
        seen: set[int] = set()
        for owner in sorted(state.players):
            records = self.orders_by_owner[owner]
            if type(owner) is not int or type(records) is not tuple:
                raise UnsupportedStandardStarbaseFacility("invalid owner records")
            for order in records:
                if type(order) not in (StandardBaseCreateOrder, StandardBaseArmOrder):
                    raise UnsupportedStandardStarbaseFacility("unsupported base order")
                pid = order.planet_id
                if type(pid) is not int or pid <= 0 or pid in seen:
                    raise UnsupportedStandardStarbaseFacility("duplicate or invalid planet ID")
                seen.add(pid)
                planet = state.planets.get(pid)
                if planet is None or planet.owner_id != owner:
                    raise UnsupportedStandardStarbaseFacility("unknown or foreign planet")
                declared.append((owner, order))
        if not declared:
            raise UnsupportedStandardStarbaseFacility("no explicit base facility order")
        events: list[HostEvent] = []
        for owner, order in sorted(declared, key=lambda x: x[1].planet_id):
            pid = order.planet_id
            planet = state.planets[pid]
            if type(order) is StandardBaseCreateOrder:
                if pid in state.starbases:
                    raise UnsupportedStandardStarbaseFacility("base already exists")
                debits = dict(STANDARD_BASE_CREATION)
                self._spend(planet.cargo, debits)
                state.starbases[pid] = Starbase(planet_id=pid, owner_id=owner)
                events.append(self._event(
                    "starbase_created_conditional", pid, 0, 0, debits,
                ))
                continue

            base = state.starbases.get(pid)
            if base is None or base.owner_id != owner:
                raise UnsupportedStandardStarbaseFacility("same-owner existing base required")
            if (type(base.defense) is not int
                    or not 0 <= base.defense <= MAX_STANDARD_BASE_DEFENSE
                    or type(base.fighters) is not int
                    or not 0 <= base.fighters <= MAX_STANDARD_BASE_FIGHTERS):
                raise UnsupportedStandardStarbaseFacility("invalid starting starbase inventories")
            assert isinstance(order, StandardBaseArmOrder)
            if order.defense_target is None and order.fighter_target is None:
                raise UnsupportedStandardStarbaseFacility("explicit defense or fighter target required")
            defense_target = base.defense if order.defense_target is None else order.defense_target
            fighter_target = base.fighters if order.fighter_target is None else order.fighter_target
            if (type(defense_target) is not int
                    or not base.defense <= defense_target <= MAX_STANDARD_BASE_DEFENSE
                    or type(fighter_target) is not int
                    or not base.fighters <= fighter_target <= MAX_STANDARD_BASE_FIGHTERS):
                raise UnsupportedStandardStarbaseFacility("downgrade, malformed or over-cap target")
            new_defense = defense_target - base.defense
            new_fighters = fighter_target - base.fighters
            if not new_defense and not new_fighters:
                raise UnsupportedStandardStarbaseFacility("no positive base equipment purchase")
            debits = {
                name: dict(STANDARD_BASE_DEFENSE_COST).get(name, 0) * new_defense
                + dict(STANDARD_BASE_FIGHTER_COST).get(name, 0) * new_fighters
                for name in RESOURCE_KEYS
            }
            self._spend(planet.cargo, debits)
            base.defense = defense_target
            base.fighters = fighter_target
            events.append(self._event(
                "starbase_armed_conditional", pid, new_defense, new_fighters, debits,
            ))
        return events

    @staticmethod
    def _spend(cargo: object, debits: Mapping[str, int]) -> None:
        for name in RESOURCE_KEYS:
            value = getattr(cargo, name)
            amount = debits.get(name, 0)
            if (type(value) is not int or value < 0
                    or type(amount) is not int or amount < 0 or amount > value):
                raise UnsupportedStandardStarbaseFacility("insufficient or unknown planet resources")
        for name in RESOURCE_KEYS:
            setattr(cargo, name, getattr(cargo, name) - debits.get(name, 0))

    def _event(
        self, kind: str, planet_id: int, defense: int, fighters: int,
        spent: Mapping[str, int],
    ) -> HostEvent:
        return HostEvent(
            phase=self.name,
            kind=kind,
            entity_type="starbase",
            entity_id=planet_id,
            details=(
                ("planet_id", str(planet_id)),
                ("defense_added", str(defense)),
                ("fighters_added", str(fighters)),
            ) + tuple(
                ("spent_" + name, str(spent.get(name, 0)))
                for name in RESOURCE_KEYS
            ),
            message="caller-asserted standard base purchase, not independently accepted by NuHost",
        )
