"""Conditional orbital cargo transfer + ordinary movement + planet economy.

Research-only composition of existing NormalMovementPhase,
PlanetCargoTransferPhase, structure purchases and 14 economic phases.
All owner/ship/planet identities and every transfer are caller-asserted,
NOT independently accepted NuHost orders. Timing is explicit hypothesis.

Transfer deltas are algebraically removed from a projected poststate for
independent reuse of tested planet and ship ledgers; every applied delta
is verified against a strict original transfer-order/event correspondence.
The final returned state is the actual modeled state, not the projection.
Unsupported scenarios ABSTAIN without partial state or event disclosure.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
from random import Random
from typing import Mapping, Literal

from planets_lab.core import Cargo, GameState
from planets_lab.data import NuStaticSpecs
from planets_lab.sim.engine import HostEngine, HostEvent
from planets_lab.sim.normal_movement_phase import NormalMovementPhase, UnsupportedNormalMovement
from planets_lab.sim.orders import (
    PlanetCargoTransferOrder, PlayerOrders, ShipOrder, TurnOrders,
)
from planets_lab.sim.planet_cargo_transfer_phase import (
    PlanetCargoTransferPhase, UnsupportedPlanetCargoTransfer, TRANSFER_FIELDS,
)
from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
from planets_lab.sim.planetary_structure_multiturn import (
    PlanetEconomicBalance, UnsupportedEconomicLedger, _planet_ledgers,
)
from planets_lab.sim.planetary_structure_turn_slice import (
    STRUCTURE_PLACEMENTS, UnsupportedStructureTurn, _ExplicitStructurePhase,
)
from planets_lab.sim.population_phases import UnsupportedPopulationRule
from planets_lab.sim.standard_structure_build import StructureBuildTargets
from planets_lab.sim.standard_movement_economy_turn import (
    MOVEMENT_PLACEMENTS, UnsupportedCompositeTurn, ShipFuelBalance,
    _validate_explicit_scope, _require_no_unmodeled_encounters,
    _exact_ship_fuel_ledgers,
)

TRANSFER_PLACEMENTS = ("transfer_before_movement", "transfer_after_movement")
STATUS = "CONDITIONAL_ORBITAL_TRANSFER_MOVEMENT_ECONOMY_NOT_NUHOST_VERIFIED"


@dataclass(frozen=True, slots=True)
class OrbitalTransferBalance:
    ship_id: int
    planet_id: int
    direction: str
    amounts: tuple[tuple[str, int], ...]
    resource_conserved: bool = True


@dataclass(frozen=True, slots=True)
class OrbitalCompositeOutcome:
    status: str
    state: GameState | None = None
    events: tuple[HostEvent, ...] = ()
    planet_balances: tuple[PlanetEconomicBalance, ...] = ()
    ship_fuel_balances: tuple[ShipFuelBalance, ...] = ()
    transfer_balances: tuple[OrbitalTransferBalance, ...] = ()
    reason: str | None = None
    order_source: str = "CALLER_ASSERTED_COMPLETE_MOVEMENT_AND_CARGO_ORDERS"
    independent_host_parity_verified: bool = False
    nuhost_order_execution_verified: bool = False
    nuhost_phase_placement_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


@dataclass(slots=True)
class _GuardedTransferPhase:
    delegate: PlanetCargoTransferPhase
    name: str = "planet_cargo_transfer"

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        _require_no_unmodeled_encounters(state)
        return self.delegate.run(state, orders, rng)


def _admit_complete_transfer_orders(
    before: GameState, orders: TurnOrders,
    structure_targets: Mapping[int, tuple[StructureBuildTargets, ...]],
    specs: NuStaticSpecs,
) -> tuple[tuple[ShipOrder, ...], TurnOrders]:
    """Run existing no-transfer scope validator on the same orders stripped
    ONLY for admission. HostEngine receives the ORIGINAL orders unchanged.
    """
    if type(orders) is not TurnOrders or type(orders.by_player) is not dict:
        raise UnsupportedCompositeTurn("complete order map required")
    original: list[ShipOrder] = []
    sanitized: dict[int, PlayerOrders] = {}
    for player_id, row in orders.by_player.items():
        if type(row) is not PlayerOrders or type(row.ship_orders) is not tuple:
            raise UnsupportedCompositeTurn("invalid per-owner ship order record")
        stripped = []
        for order in row.ship_orders:
            if type(order) is not ShipOrder:
                raise UnsupportedCompositeTurn("invalid ship order type")
            transfer = order.planet_transfer
            if transfer is not None:
                if (type(transfer) is not PlanetCargoTransferOrder
                        or type(transfer.planet_id) is not int
                        or transfer.direction not in ("ship_to_planet", "planet_to_ship")):
                    raise UnsupportedCompositeTurn("invalid transfer order shape")
                amounts = [getattr(transfer, key) for key in TRANSFER_FIELDS]
                if (any(type(value) is not int or value < 0 for value in amounts)
                        or not any(amounts)):
                    raise UnsupportedCompositeTurn("zero or unsupported transfer amounts")
                ship = before.ships.get(order.ship_id)
                planet = before.planets.get(transfer.planet_id)
                if (ship is None or planet is None
                        or ship.owner_id != player_id
                        or planet.owner_id != player_id):
                    raise UnsupportedCompositeTurn("only known same-owner orbital transfer admitted")
                original.append(order)
            stripped.append(replace(order, planet_transfer=None))
        sanitized[player_id] = replace(row, ship_orders=tuple(stripped))
    _validate_explicit_scope(
        before, TurnOrders(by_player=sanitized), structure_targets, specs,
    )
    if not original:
        raise UnsupportedCompositeTurn("at least one explicit nonzero orbital transfer required")
    for ship in before.ships.values():
        for key in TRANSFER_FIELDS:
            if type(getattr(ship.cargo, key)) is not int or getattr(ship.cargo, key) < 0:
                raise UnsupportedCompositeTurn("nonnegative ship inventories required")
    for planet in before.planets.values():
        for key in TRANSFER_FIELDS:
            if type(getattr(planet.cargo, key)) is not int or getattr(planet.cargo, key) < 0:
                raise UnsupportedCompositeTurn("nonnegative planet inventories required")
    return tuple(sorted(original, key=lambda x: x.ship_id)), TurnOrders(by_player=sanitized)


def _audit_transfers_and_undo(
    before: GameState,
    after: GameState,
    events: tuple[HostEvent, ...],
    submitted: tuple[ShipOrder, ...],
) -> tuple[GameState, tuple[OrbitalTransferBalance, ...]]:
    """Verify all transfer events exactly; erase only their recorded deltas
    from a cloned POSTSTATE for independent normal+economy balance checks.
    """
    receipts = [e for e in events if e.phase == "planet_cargo_transfer"]
    if len(receipts) != len(submitted):
        raise UnsupportedCompositeTurn("missing or extra orbital transfer receipts")
    planet_effects: dict[int, dict[str, int]] = {}
    ship_effects: dict[int, dict[str, int]] = {}
    balances: list[OrbitalTransferBalance] = []
    expected_keys = {
        "ship_id", "planet_id", "direction", "colonized", *TRANSFER_FIELDS,
    }
    for submitted_order, event in zip(submitted, receipts, strict=True):
        transfer = submitted_order.planet_transfer
        assert transfer is not None
        if (event.kind != "planet_cargo_transferred"
                or event.entity_type != "planet"
                or type(event.entity_id) is not int
                or event.entity_id != transfer.planet_id
                or len(event.details) != len(expected_keys)):
            raise UnsupportedCompositeTurn("unexpected transfer receipt type")
        details = dict(event.details)
        if (set(details) != expected_keys
                or details["ship_id"] != str(submitted_order.ship_id)
                or details["planet_id"] != str(transfer.planet_id)
                or details["direction"] != transfer.direction
                or details["colonized"] != "false"
                or any(details[key] != str(getattr(transfer, key))
                       for key in TRANSFER_FIELDS)):
            raise UnsupportedCompositeTurn("transfer receipt does not match explicit submitted intent")
        multiplier = 1 if transfer.direction == "ship_to_planet" else -1
        incoming_planet = planet_effects.setdefault(transfer.planet_id, {})
        incoming_ship = ship_effects.setdefault(submitted_order.ship_id, {})
        amounts: list[tuple[str, int]] = []
        for name in TRANSFER_FIELDS:
            value = getattr(transfer, name)
            incoming_planet[name] = incoming_planet.get(name, 0) + multiplier * value
            incoming_ship[name] = incoming_ship.get(name, 0) - multiplier * value
            amounts.append((name, value))
        balances.append(OrbitalTransferBalance(
            ship_id=submitted_order.ship_id,
            planet_id=transfer.planet_id,
            direction=transfer.direction,
            amounts=tuple(amounts),
        ))

    projected = after.clone()
    for pid, delta in planet_effects.items():
        if pid not in projected.planets:
            raise UnsupportedCompositeTurn("transfer changed planet identity")
        cargo = projected.planets[pid].cargo
        for name, value in delta.items():
            if type(getattr(cargo, name)) is not int or getattr(cargo, name) < 0:
                raise UnsupportedCompositeTurn("invalid post-transfer planetary inventory")
            setattr(cargo, name, getattr(cargo, name) - value)
    for sid, delta in ship_effects.items():
        if sid not in projected.ships:
            raise UnsupportedCompositeTurn("transfer changed ship identity")
        cargo = projected.ships[sid].cargo
        for name, value in delta.items():
            if type(getattr(cargo, name)) is not int or getattr(cargo, name) < 0:
                raise UnsupportedCompositeTurn("invalid post-transfer ship inventory")
            setattr(cargo, name, getattr(cargo, name) - value)
    return projected, tuple(balances)


def simulate_orbital_transfer_movement_economy_turn(
    before: GameState,
    ship_orders: TurnOrders,
    structure_targets: Mapping[int, tuple[StructureBuildTargets, ...]],
    specs: NuStaticSpecs,
    *,
    movement_placement: Literal[
        "normal_before_economy_block", "normal_after_economy_block",
    ],
    transfer_placement: Literal[
        "transfer_before_movement", "transfer_after_movement",
    ],
    structure_placement: Literal[
        "structures_before_planetary", "structures_after_planetary",
    ],
    standard_rules_asserted: bool = False,
    complete_ship_and_structure_orders_asserted: bool = False,
    automatic_supply_sale_enabled: bool = False,
    seed: int = 0,
) -> OrbitalCompositeOutcome:
    def abstain(reason: str) -> OrbitalCompositeOutcome:
        return OrbitalCompositeOutcome("ABSTAIN_ORBITAL_COMPOSITE_TURN", reason=reason)

    if (type(before) is not GameState or type(specs) is not NuStaticSpecs
            or type(seed) is not int
            or type(automatic_supply_sale_enabled) is not bool
            or standard_rules_asserted is not True
            or complete_ship_and_structure_orders_asserted is not True
            or movement_placement not in MOVEMENT_PLACEMENTS
            or transfer_placement not in TRANSFER_PLACEMENTS
            or structure_placement not in STRUCTURE_PLACEMENTS):
        return abstain("unsupported or omitted explicit standard rules/phase positions")
    try:
        before.validate()
        admitted, _ = _admit_complete_transfer_orders(
            before, ship_orders, structure_targets, specs,
        )
        _require_no_unmodeled_encounters(before)
        transfer = _GuardedTransferPhase(PlanetCargoTransferPhase(specs))
        movement = NormalMovementPhase(
            specs=specs, eligible_ship_ids=frozenset(before.ships),
            allow_deferred=False, enable_expanded_movement=False,
            enable_warp_wells=False,
        )
        construction = _ExplicitStructurePhase(
            targets_by_player=structure_targets,
            automatic_supply_sale_enabled=automatic_supply_sale_enabled,
        )
        economy = PlanetaryHostPipeline().phases
        economic_block = (
            (construction, *economy) if structure_placement == STRUCTURE_PLACEMENTS[0]
            else (*economy, construction)
        )
        movement_block = (
            (transfer, movement) if transfer_placement == TRANSFER_PLACEMENTS[0]
            else (movement, transfer)
        )
        phases = (
            (*movement_block, *economic_block)
            if movement_placement == MOVEMENT_PLACEMENTS[0]
            else (*economic_block, *movement_block)
        )
        modeled, events = HostEngine(phases).step(before, ship_orders, seed=seed)
        _require_no_unmodeled_encounters(modeled)
        projection, receipts = _audit_transfers_and_undo(
            before, modeled, events, admitted,
        )
        planet_balances = _planet_ledgers(before, projection, events)
        ship_balances = _exact_ship_fuel_ledgers(before, projection, events)
    except (
        UnsupportedCompositeTurn, UnsupportedPlanetCargoTransfer,
        UnsupportedNormalMovement, UnsupportedStructureTurn,
        UnsupportedPopulationRule, UnsupportedEconomicLedger,
        ValueError, TypeError, AttributeError, KeyError, OverflowError,
    ):
        return abstain("unsupported phase context or inventory/receipt imbalance")
    return OrbitalCompositeOutcome(
        STATUS, state=modeled, events=events,
        planet_balances=planet_balances,
        ship_fuel_balances=ship_balances, transfer_balances=receipts,
    )
