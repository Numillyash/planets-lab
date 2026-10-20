"""Opt-in STANDARD normal ship movement + construction + planetary economy.

This is an explicitly bounded composition of existing implementation
phases, not a NuHost turn-order claim. Movement is either before or after
the intact structure/economy block. Every owner and every ship must have
an explicit order; these are CALLER-ASSERTED orders, never HMAC-signed
or server-accepted observations. No automatic default/noop orders.

Supported: ordinary fully reachable non-special normal movement, a
separately scoped standard structure target batch, existing 14 economic
phases. Out-of-scope: tow, intercept, hyperjump, wormholes, warp wells,
fuel proration, combat, missions, starbases and custom/campaign rules.

Only an internally exact per-planet production/structure/mineral ledger
AND per-ship fuel/position ledger leads to a conditional result. Any
failure ABSTAINS without returning the partially executed state.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Mapping, Literal

from planets_lab.core import Cargo, GameState
from planets_lab.data import NuStaticSpecs
from planets_lab.sim.engine import HostEngine, HostEvent
from planets_lab.sim.normal_movement_phase import (
    NormalMovementPhase, UnsupportedNormalMovement,
)
from planets_lab.sim.orders import PlayerOrders, ShipOrder, TurnOrders
from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
from planets_lab.sim.planetary_structure_multiturn import (
    PlanetEconomicBalance, UnsupportedEconomicLedger, _planet_ledgers,
)
from planets_lab.sim.planetary_structure_turn_slice import (
    STRUCTURE_PLACEMENTS, UnsupportedStructureTurn, _ExplicitStructurePhase,
)
from planets_lab.sim.population_phases import UnsupportedPopulationRule
from planets_lab.sim.standard_structure_build import StructureBuildTargets

MOVEMENT_PLACEMENTS = ("normal_before_economy_block", "normal_after_economy_block")
SUPPORTED_STATUS = "CONDITIONAL_STANDARD_MOVEMENT_STRUCTURE_ECONOMY_NOT_NUHOST_VERIFIED"


class UnsupportedCompositeTurn(ValueError):
    """A research-only composition could not be evaluated faithfully."""


@dataclass(frozen=True, slots=True)
class ShipFuelBalance:
    ship_id: int
    starting_position: tuple[int, int]
    ending_position: tuple[int, int]
    fuel_used: int
    exact: bool = True


@dataclass(frozen=True, slots=True)
class StandardCompositeOutcome:
    status: str
    state: GameState | None = None
    events: tuple[HostEvent, ...] = ()
    planet_balances: tuple[PlanetEconomicBalance, ...] = ()
    ship_fuel_balances: tuple[ShipFuelBalance, ...] = ()
    reason: str | None = None
    order_source: str = "COMPLETE_CALLER_ASSERTED_SHIP_AND_STRUCTURE_ORDERS"
    nuhost_order_execution_verified: bool = False
    independent_host_parity_verified: bool = False
    nuhost_phase_placement_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == SUPPORTED_STATUS


def _validate_explicit_scope(
    state: GameState,
    ship_orders: TurnOrders,
    targets_by_player: Mapping[int, tuple[StructureBuildTargets, ...]],
    specs: NuStaticSpecs,
) -> None:
    if (type(ship_orders) is not TurnOrders
            or type(ship_orders.by_player) is not dict
            or set(ship_orders.by_player) != set(state.players)
            or type(targets_by_player) is not dict
            or set(targets_by_player) != set(state.players)):
        raise UnsupportedCompositeTurn("both owner scopes must be explicitly complete")
    if state.starbases or state.ion_storms or state.metadata:
        raise UnsupportedCompositeTurn("starbases, storms and scenario metadata not admitted")
    all_ships: set[int] = set()
    all_planets: set[int] = set()
    for owner_id in sorted(state.players):
        row = ship_orders.by_player[owner_id]
        targets = targets_by_player[owner_id]
        if (type(owner_id) is not int
                or type(row) is not PlayerOrders or row.player_id != owner_id
                or type(row.ship_orders) is not tuple
                or row.starbase_tech_orders
                or type(targets) is not tuple):
            raise UnsupportedCompositeTurn("invalid or omitted explicit owner records")
        for order in row.ship_orders:
            if type(order) is not ShipOrder or type(order.ship_id) is not int:
                raise UnsupportedCompositeTurn("invalid ship order")
            if order.ship_id in all_ships:
                raise UnsupportedCompositeTurn("duplicate ship orders")
            all_ships.add(order.ship_id)
            ship = state.ships.get(order.ship_id)
            if ship is None or ship.owner_id != owner_id:
                raise UnsupportedCompositeTurn("ship order has missing/foreign owner")
            if (any(type(getattr(order, name)) is not int
                    for name in ("waypoint_x", "waypoint_y", "warp"))
                    or not 0 <= order.warp <= 9):
                raise UnsupportedCompositeTurn("complete standard movement waypoint required")
            if (order.mission is not None
                    or order.primary_enemy_id is not None
                    or order.friendly_code is not None
                    or order.planet_transfer is not None):
                raise UnsupportedCompositeTurn("nonmovement or transfer ship order unsupported")
            if (ship.owner_id is None or ship.mission is not None
                    or ship.mission1_target_id is not None
                    or ship.mission2_target_id is not None
                    or ship.friendly_code != ""
                    or ship.damage != 0
                    or any(getattr(ship, name) != 0 for name in (
                        "fighters", "torpedoes", "unresolved_ammo", "beam_count",
                        "torpedo_launcher_count", "fighter_bay_count",
                    ))):
                raise UnsupportedCompositeTurn("special or armed ship interaction unsupported")
            hull = specs.hulls.get(ship.hull_id)
            if (hull is None or hull.special or ship.engine_id not in specs.engines
                    or type(ship.cargo.neutronium) is not int
                    or ship.cargo.neutronium < 0):
                raise UnsupportedCompositeTurn("complete ordinary hull, engine and fuel required")
        for target in targets:
            if type(target) is not StructureBuildTargets or type(target.planet_id) is not int:
                raise UnsupportedCompositeTurn("invalid structure target")
            if target.planet_id in all_planets:
                raise UnsupportedCompositeTurn("duplicate structure target")
            all_planets.add(target.planet_id)
            planet = state.planets.get(target.planet_id)
            if planet is None or planet.owner_id != owner_id:
                raise UnsupportedCompositeTurn("structure target has missing/foreign owner")
    if all_ships != set(state.ships):
        raise UnsupportedCompositeTurn("one explicit ordinary move/noop order per ship required")
    if not all_planets:
        raise UnsupportedCompositeTurn("at least one explicit construction target required")


def _exact_ship_fuel_ledgers(
    before: GameState,
    after: GameState,
    events: tuple[HostEvent, ...],
) -> tuple[ShipFuelBalance, ...]:
    if set(before.ships) != set(after.ships):
        raise UnsupportedCompositeTurn("ship roster changed in bounded turn")
    receipts: dict[int, HostEvent] = {}
    for event in events:
        if event.phase != "normal_movement":
            continue
        if (event.kind not in ("ship_moved", "ship_noop")
                or event.entity_type != "ship"
                or type(event.entity_id) is not int
                or event.entity_id not in before.ships
                or event.entity_id in receipts):
            raise UnsupportedCompositeTurn("invalid or duplicate normal movement event")
        receipts[event.entity_id] = event
    if set(receipts) != set(before.ships):
        raise UnsupportedCompositeTurn("missing ship movement/noop receipts")
    out: list[ShipFuelBalance] = []
    for ship_id in sorted(before.ships):
        first, final = before.ships[ship_id], after.ships[ship_id]
        event = receipts[ship_id]
        if len(dict(event.details)) != len(event.details):
            raise UnsupportedCompositeTurn("duplicate movement event detail")
        details = dict(event.details)
        fuel_text = details.get("fuel_used", "0" if event.kind == "ship_noop" else None)
        if type(fuel_text) is not str or not fuel_text.isdecimal():
            raise UnsupportedCompositeTurn("missing valid movement fuel expense")
        fuel = int(fuel_text)
        if (first.cargo.neutronium - final.cargo.neutronium != fuel
                or (event.kind == "ship_noop" and
                    (first.x, first.y) != (final.x, final.y))
                or (event.kind == "ship_moved" and (
                    any(details.get(key) != str(value) for key, value in (
                        ("from_x", first.x), ("from_y", first.y),
                        ("to_x", final.x), ("to_y", final.y),
                    ))
                ))):
            raise UnsupportedCompositeTurn("ship movement/fuel delta unexplained")
        if any(
            getattr(first.cargo, cargo_name) != getattr(final.cargo, cargo_name)
            for cargo_name in (field.name for field in fields(Cargo))
            if cargo_name != "neutronium"
        ):
            raise UnsupportedCompositeTurn("unsupported ship cargo transfer")
        for field_name in (
            "owner_id", "hull_id", "engine_id", "beam_id", "torpedo_id",
            "beam_count", "torpedo_launcher_count", "fighter_bay_count",
            "mission", "mission1_target_id", "mission2_target_id",
            "primary_enemy_id", "friendly_code", "fighters", "torpedoes",
            "unresolved_ammo", "damage", "crew",
        ):
            if getattr(first, field_name) != getattr(final, field_name):
                raise UnsupportedCompositeTurn("unsupported nonmovement ship state mutation")
        out.append(ShipFuelBalance(
            ship_id=ship_id,
            starting_position=(first.x, first.y),
            ending_position=(final.x, final.y),
            fuel_used=fuel,
        ))
    return tuple(out)


def simulate_standard_movement_economy_turn(
    before: GameState,
    ship_orders: TurnOrders,
    structure_targets: Mapping[int, tuple[StructureBuildTargets, ...]],
    specs: NuStaticSpecs,
    *,
    movement_placement: Literal[
        "normal_before_economy_block", "normal_after_economy_block",
    ],
    structure_placement: Literal[
        "structures_before_planetary", "structures_after_planetary",
    ],
    standard_rules_asserted: bool = False,
    complete_ship_and_structure_orders_asserted: bool = False,
    automatic_supply_sale_enabled: bool = False,
    seed: int = 0,
) -> StandardCompositeOutcome:
    """Run one completely stated, model-internal normal-move/economy turn."""
    def abstain(reason: str) -> StandardCompositeOutcome:
        return StandardCompositeOutcome("ABSTAIN_STANDARD_COMPOSITE_TURN", reason=reason)

    if (type(before) is not GameState or type(specs) is not NuStaticSpecs
            or type(seed) is not int or type(automatic_supply_sale_enabled) is not bool
            or standard_rules_asserted is not True
            or complete_ship_and_structure_orders_asserted is not True
            or movement_placement not in MOVEMENT_PLACEMENTS
            or structure_placement not in STRUCTURE_PLACEMENTS):
        return abstain("unsupported scope or missing explicit standard assumptions")
    try:
        before.validate()
        _validate_explicit_scope(before, ship_orders, structure_targets, specs)
        movement = NormalMovementPhase(
            specs=specs, eligible_ship_ids=frozenset(before.ships),
            allow_deferred=False, enable_expanded_movement=False,
            enable_warp_wells=False,
        )
        structure = _ExplicitStructurePhase(
            targets_by_player=structure_targets,
            automatic_supply_sale_enabled=automatic_supply_sale_enabled,
        )
        planetary = PlanetaryHostPipeline().phases
        economy_block = (
            (structure, *planetary)
            if structure_placement == STRUCTURE_PLACEMENTS[0]
            else (*planetary, structure)
        )
        phases = (
            (movement, *economy_block)
            if movement_placement == MOVEMENT_PLACEMENTS[0]
            else (*economy_block, movement)
        )
        modeled, events = HostEngine(phases).step(before, ship_orders, seed=seed)
        planet_balances = _planet_ledgers(before, modeled, events)
        ship_balances = _exact_ship_fuel_ledgers(before, modeled, events)
    except (
        UnsupportedCompositeTurn, UnsupportedNormalMovement,
        UnsupportedStructureTurn, UnsupportedPopulationRule,
        UnsupportedEconomicLedger, ValueError, TypeError,
        AttributeError, KeyError, OverflowError,
    ):
        return abstain("unsupported operation or unexplained standard inventory delta")
    return StandardCompositeOutcome(
        status=SUPPORTED_STATUS,
        state=modeled,
        events=events,
        planet_balances=planet_balances,
        ship_fuel_balances=ship_balances,
    )
