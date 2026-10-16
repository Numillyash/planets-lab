"""Research-only, explicit-order composition of cargo transfers and planet economy.

This is an internal deterministic Host slice, NOT a reconstruction of the
NuHost ship-cargo/planet-economy phase boundary. Full-information, stationary
ships and explicit TurnOrders are mandatory for attributable transfer results.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from planets_lab.core import GameState
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.engine import HostEngine, HostEvent, HostPhase
from planets_lab.sim.orders import TurnOrders
from planets_lab.sim.planet_cargo_transfer_phase import (
    BULK_CARGO_FIELDS,
    TRANSFER_FIELDS,
    PlanetCargoTransferPhase,
    UnsupportedPlanetCargoTransfer,
)
from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
from planets_lab.sim.population_phases import UnsupportedPopulationRule

Placement = Literal["transfer_before_planetary", "transfer_after_planetary"]
MINERALS = ("neutronium", "duranium", "tritanium", "molybdenum")


class UnsupportedPlanetaryOrderSlice(RuntimeError):
    """ABSTAIN: the research slice cannot attribute this transition."""


def _inventory(state: GameState) -> dict[str, dict[int, dict[str, int]]]:
    return {
        "planets": {
            key: {name: getattr(p.cargo, name) for name in TRANSFER_FIELDS}
            for key, p in sorted(state.planets.items())
        },
        "ships": {
            key: {name: getattr(s.cargo, name) for name in TRANSFER_FIELDS}
            for key, s in sorted(state.ships.items())
        },
        "ground": {
            key: {name: getattr(p, "ground_" + name).amount for name in MINERALS}
            for key, p in sorted(state.planets.items())
        },
    }


def _differences(
    before: dict[int, dict[str, int]], after: dict[int, dict[str, int]]
) -> dict[int, dict[str, int]]:
    if before.keys() != after.keys():
        raise UnsupportedPlanetaryOrderSlice("phase changed entity identities")
    result: dict[int, dict[str, int]] = {}
    for entity_id in sorted(before):
        change = {
            name: after[entity_id][name] - value
            for name, value in before[entity_id].items()
        }
        nonzero = {key: val for key, val in change.items() if val}
        if nonzero:
            result[entity_id] = nonzero
    return result


def _sum_deltas(
    planet: dict[int, dict[str, int]],
    ship: dict[int, dict[str, int]],
    ground: dict[int, dict[str, int]],
) -> dict[str, int]:
    total = {name: 0 for name in TRANSFER_FIELDS}
    for by_entity in (planet, ship, ground):
        for changes in by_entity.values():
            for name, amount in changes.items():
                total[name] += amount
    return {name: value for name, value in total.items() if value}


@dataclass(slots=True, frozen=True)
class PhaseResourceBalance:
    phase: str
    category: str
    planet_cargo_delta: dict[int, dict[str, int]]
    ship_cargo_delta: dict[int, dict[str, int]]
    ground_mineral_delta: dict[int, dict[str, int]]
    combined_net_delta: dict[str, int]
    event_kinds: tuple[str, ...]

    @classmethod
    def from_states(
        cls, phase: str, before: GameState, after: GameState,
        events: list[HostEvent],
    ) -> "PhaseResourceBalance":
        b, a = _inventory(before), _inventory(after)
        planets = _differences(b["planets"], a["planets"])
        ships = _differences(b["ships"], a["ships"])
        ground = _differences(b["ground"], a["ground"])
        net = _sum_deltas(planets, ships, ground)
        transfer = phase == "planet_cargo_transfer"
        if transfer and (net or ground):
            raise UnsupportedPlanetaryOrderSlice(
                "cargo transfer failed total inventory conservation"
            )
        if not transfer and ships:
            raise UnsupportedPlanetaryOrderSlice(
                f"planetary phase {phase} unexpectedly changed ship cargo"
            )
        return cls(
            phase=phase,
            category="explicit_transfer" if transfer else "planetary_economy",
            planet_cargo_delta=planets,
            ship_cargo_delta=ships,
            ground_mineral_delta=ground,
            combined_net_delta=net,
            event_kinds=tuple(event.kind for event in events),
        )


@dataclass(slots=True)
class _RecordedPhase:
    delegate: HostPhase
    balances: list[PhaseResourceBalance]

    @property
    def name(self) -> str:
        return self.delegate.name

    def run(self, state: GameState, orders: TurnOrders, rng: object) -> list[HostEvent]:
        before = state.clone()
        events = self.delegate.run(state, orders, rng)
        self.balances.append(
            PhaseResourceBalance.from_states(self.name, before, state, events)
        )
        return events


@dataclass(slots=True, frozen=True)
class PlanetarySliceOutcome:
    status: str
    state: GameState | None = None
    events: tuple[HostEvent, ...] = ()
    balances: tuple[PhaseResourceBalance, ...] = ()
    abstain_reason: str | None = None

    @property
    def supported(self) -> bool:
        return self.status == "MODELED_CONDITIONAL_NOT_NUHOST_VERIFIED"


@dataclass(slots=True)
class PlanetaryOrderAwareSlice:
    """Requires explicit hypothetical transfer placement; never infers NuHost order."""

    specs: NuStaticSpecs
    placement: Placement
    planetary: PlanetaryHostPipeline = field(default_factory=PlanetaryHostPipeline)

    def __post_init__(self) -> None:
        if self.placement not in ("transfer_before_planetary", "transfer_after_planetary"):
            raise ValueError("explicit transfer placement is required")

    @property
    def phases(self) -> tuple[HostPhase, ...]:
        cargo = PlanetCargoTransferPhase(specs=self.specs)
        if self.placement == "transfer_before_planetary":
            return (cargo, *self.planetary.phases)
        return (*self.planetary.phases, cargo)

    def engine(self) -> HostEngine:
        """Composable uninstrumented HostEngine with the same stated assumption."""
        return HostEngine(self.phases)

    def _require_supported_context(self, state: GameState, orders: TurnOrders) -> None:
        if state.starbases or state.ion_storms:
            raise UnsupportedPlanetaryOrderSlice(
                "starbase/ion-storm interactions are outside this research slice"
            )
        for ship in state.ships.values():
            if (
                ship.warp != 0 or ship.waypoint_x is not None
                or ship.waypoint_y is not None or ship.mission is not None
            ):
                raise UnsupportedPlanetaryOrderSlice(
                    f"ship {ship.id} has unresolved movement or mission"
                )
            for name in TRANSFER_FIELDS:
                if getattr(ship.cargo, name) < 0:
                    raise UnsupportedPlanetaryOrderSlice(
                        f"ship {ship.id} has negative {name}"
                    )
        for planet in state.planets.values():
            for name in TRANSFER_FIELDS:
                if getattr(planet.cargo, name) < 0:
                    raise UnsupportedPlanetaryOrderSlice(
                        f"planet {planet.id} has negative {name}"
                    )
            for name in MINERALS:
                if getattr(planet, "ground_" + name).amount < 0:
                    raise UnsupportedPlanetaryOrderSlice(
                        f"planet {planet.id} has negative ground {name}"
                    )
        for player_orders in orders.by_player.values():
            for order in player_orders.ship_orders:
                if (
                    order.planet_transfer is None
                    or order.waypoint_x is not None or order.waypoint_y is not None
                    or order.warp is not None or order.mission is not None
                    or order.primary_enemy_id is not None or order.friendly_code is not None
                ):
                    raise UnsupportedPlanetaryOrderSlice(
                        f"ship {order.ship_id} has unmodeled order fields"
                    )
                ship = state.ships.get(order.ship_id)
                if ship is None:
                    continue  # HostEngine validates unknown ships as invalid orders
                hull = self.specs.hulls.get(ship.hull_id)
                if hull is None:
                    raise UnsupportedPlanetaryOrderSlice(
                        f"ship {ship.id} has unknown hull {ship.hull_id}"
                    )
                bulk = sum(getattr(ship.cargo, name) for name in BULK_CARGO_FIELDS)
                if bulk > hull.cargo_capacity or ship.cargo.neutronium > hull.fuel_tank:
                    raise UnsupportedPlanetaryOrderSlice(
                        f"ship {ship.id} begins above cargo or fuel capacity"
                    )

    def step(self, state: GameState, orders: TurnOrders, *, seed: int = 0) -> PlanetarySliceOutcome:
        self._require_supported_context(state, orders)
        ledger: list[PhaseResourceBalance] = []
        recorded = tuple(_RecordedPhase(p, ledger) for p in self.phases)
        next_state, events = HostEngine(recorded).step(state, orders, seed=seed)
        return PlanetarySliceOutcome(
            status="MODELED_CONDITIONAL_NOT_NUHOST_VERIFIED",
            state=next_state,
            events=events,
            balances=tuple(ledger),
        )

    def attempt_step(
        self, state: GameState, orders: TurnOrders, *, seed: int = 0
    ) -> PlanetarySliceOutcome:
        """Fail closed: no next state, partial trace or partial inventory on ABSTAIN."""
        try:
            return self.step(state, orders, seed=seed)
        except (UnsupportedPlanetaryOrderSlice, UnsupportedPlanetCargoTransfer,
                UnsupportedPopulationRule, ValueError) as exc:
            return PlanetarySliceOutcome(
                status="ABSTAIN_UNSUPPORTED_OR_INVALID",
                abstain_reason=f"{type(exc).__name__}: {exc}",
            )
