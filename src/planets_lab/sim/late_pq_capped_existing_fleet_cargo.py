"""Capped ordinary PQ + fully audited existing-ship transfer/move/economy.

At a complete soft-cap ordinary fleet, queued regular ships NEVER build.
This bounded model executes 2..6 conditional turns with every base/stock/PP
listed, one caller-ordered normal moving ship per turn, explicit full
per-owner ship orders (noops for everyone else), optional ordinary orbital
transfer, and the intact fourteen planetary economy phases.

Not an actual NuHost order or phase-timing claim. Nothing is inferred from
client responses; every unsupported case abstains for the ENTIRE series.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Literal

from planets_lab.core import GameState
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.engine import HostEngine, HostEvent
from planets_lab.sim.late_pq_capped_no_build_carry import (
    CappedPQCarry, CappedPQNoBuildTurn, _admit as _admit_capped,
)
from planets_lab.sim.normal_movement import plan_full_normal_move
from planets_lab.sim.normal_movement_phase import NormalMovementPhase, UnsupportedNormalMovement
from planets_lab.sim.orders import (PlanetCargoTransferOrder, PlayerOrders, ShipOrder, TurnOrders)
from planets_lab.sim.planet_cargo_transfer_phase import (
    PlanetCargoTransferPhase, UnsupportedPlanetCargoTransfer, TRANSFER_FIELDS,
)
from planets_lab.sim.planetary_host_pipeline import PlanetaryHostPipeline
from planets_lab.sim.planetary_structure_multiturn import (
    PlanetEconomicBalance, UnsupportedEconomicLedger, _planet_ledgers,
)
from planets_lab.sim.population_phases import UnsupportedPopulationRule
from planets_lab.sim.standard_movement_economy_turn import (
    ShipFuelBalance, UnsupportedCompositeTurn, _exact_ship_fuel_ledgers,
    _require_no_unmodeled_encounters,
)
from planets_lab.sim.standard_orbital_transfer_turn import (
    OrbitalTransferBalance, _audit_transfers_and_undo,
)

STATUS = "CONDITIONAL_CAPPED_PQ_EXISTING_SHIP_CARGO_MOVE_CARRY_NOT_HOST_VERIFIED"
PLACEMENTS = (
    "load_move_before_economy",
    "economy_before_load_move",
)


@dataclass(frozen=True, slots=True)
class CappedFleetCargoTurn:
    ordinary_queue: CappedPQNoBuildTurn
    all_ship_orders: TurnOrders
    active_ship_id: int
    placement: Literal["load_move_before_economy", "economy_before_load_move"]
    no_other_fleet_or_host_actions_asserted: bool = False


@dataclass(frozen=True, slots=True)
class CappedFleetCargoReceipt:
    turn_after: int
    waiting_queued_base_ids: tuple[int, ...]
    active_ship_id: int
    ship_fuel: ShipFuelBalance
    transfers: tuple[OrbitalTransferBalance, ...]
    planet_balances: tuple[PlanetEconomicBalance, ...]
    events: tuple[HostEvent, ...]
    built_ship_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class CappedFleetCargoOutcome:
    status: str
    state: GameState | None = None
    carry_after: CappedPQCarry | None = None
    turns: tuple[CappedFleetCargoReceipt, ...] = ()
    reason: str | None = None
    authenticated_ship_orders: bool = False
    independently_verified_no_build: bool = False
    nuhost_phase_order_verified: bool = False
    nuhost_execution_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


class UnsupportedCappedFleet(ValueError):
    """All-or-nothing failure: no partial game, transfer or PP sidecar."""


def _checked_orders(
    state: GameState, turn: CappedFleetCargoTurn, specs: NuStaticSpecs,
) -> tuple[ShipOrder, tuple[ShipOrder, ...]]:
    orders = turn.all_ship_orders
    if (
        type(orders) is not TurnOrders or type(orders.by_player) is not dict
        or set(orders.by_player) != set(state.players)
        or type(turn.active_ship_id) is not int
        or turn.active_ship_id not in state.ships
        or turn.no_other_fleet_or_host_actions_asserted is not True
    ):
        raise UnsupportedCappedFleet("incomplete per-owner orders or mover identity")
    seen: set[int] = set()
    mover = None
    transfers: list[ShipOrder] = []
    for owner, row in orders.by_player.items():
        if (
            type(owner) is not int or type(row) is not PlayerOrders
            or type(row.player_id) is not int or row.player_id != owner
            or type(row.ship_orders) is not tuple or row.starbase_tech_orders
        ):
            raise UnsupportedCappedFleet("invalid complete owner record")
        for intent in row.ship_orders:
            if (
                type(intent) is not ShipOrder
                or type(intent.ship_id) is not int
                or intent.ship_id not in state.ships
                or intent.ship_id in seen
                or state.ships[intent.ship_id].owner_id != owner
                or any(type(getattr(intent, k)) is not int
                       for k in ("waypoint_x", "waypoint_y", "warp"))
                or intent.mission is not None
                or intent.primary_enemy_id is not None
                or intent.friendly_code is not None
            ):
                raise UnsupportedCappedFleet("missing, duplicated or unsupported ship order")
            seen.add(intent.ship_id)
            original = state.ships[intent.ship_id]
            if intent.ship_id != turn.active_ship_id:
                if (
                    intent.planet_transfer is not None or intent.warp != 0
                    or (intent.waypoint_x, intent.waypoint_y) != (
                        original.x, original.y
                    )
                ):
                    raise UnsupportedCappedFleet("other ship not an explicit inert noop")
            else:
                if not 1 <= intent.warp <= 9:
                    raise UnsupportedCappedFleet("exactly one active ordinary full move required")
                hull = specs.hulls.get(original.hull_id)
                if (
                    hull is None or hull.special
                    or original.engine_id not in specs.engines
                    or original.mission is not None or original.damage != 0
                    or original.friendly_code
                    or original.beam_count or original.torpedo_launcher_count
                    or original.fighter_bay_count or original.fighters
                    or original.torpedoes or original.unresolved_ammo
                ):
                    raise UnsupportedCappedFleet("special or armed moving ship unsupported")
                mover = intent
                if intent.planet_transfer is not None:
                    t = intent.planet_transfer
                    if (
                        type(t) is not PlanetCargoTransferOrder
                        or type(t.planet_id) is not int
                        or t.direction not in ("planet_to_ship", "ship_to_planet")
                    ):
                        raise UnsupportedCappedFleet("unknown transfer order shape")
                    if (
                        t.planet_id not in state.planets
                        or state.planets[t.planet_id].owner_id != owner
                        or (original.x, original.y) != (
                            state.planets[t.planet_id].x, state.planets[t.planet_id].y
                        )
                    ):
                        raise UnsupportedCappedFleet("only own-planet start-orbit transfer allowed")
                    amounts = [getattr(t, field) for field in TRANSFER_FIELDS]
                    if (
                        any(type(value) is not int or value < 0 for value in amounts)
                        or not any(amounts)
                    ):
                        raise UnsupportedCappedFleet("invalid amount or empty transfer")
                    transfers.append(intent)
    if seen != set(state.ships) or mover is None:
        raise UnsupportedCappedFleet("not one complete explicit order per ship")
    return mover, tuple(transfers)


def simulate_capped_pq_existing_ship_cargo_carry(
    before: GameState, specs: NuStaticSpecs, carry: CappedPQCarry,
    plans: tuple[CappedFleetCargoTurn, ...],
    *,
    standard_rules_asserted: bool = False,
    complete_fleet_queue_warehouse_and_owner_pp_asserted: bool = False,
    no_priority_clone_mining_stations_or_external_effects_asserted: bool = False,
    complete_no_encounter_routes_asserted: bool = False,
    seed: int = 0,
) -> CappedFleetCargoOutcome:
    def abstain(reason: str) -> CappedFleetCargoOutcome:
        return CappedFleetCargoOutcome(
            "ABSTAIN_CAPPED_PQ_EXISTING_SHIP_CARGO_CARRY", reason=reason,
        )

    if (
        type(before) is not GameState or type(specs) is not NuStaticSpecs
        or type(carry) is not CappedPQCarry
        or type(plans) is not tuple or not 2 <= len(plans) <= 6
        or type(seed) is not int
        or standard_rules_asserted is not True
        or complete_fleet_queue_warehouse_and_owner_pp_asserted is not True
        or no_priority_clone_mining_stations_or_external_effects_asserted is not True
        or complete_no_encounter_routes_asserted is not True
    ):
        return abstain("incomplete conditional multi-turn ordinary-capped scope")
    try:
        if any(
            type(turn) is not CappedFleetCargoTurn
            or turn.placement not in PLACEMENTS
            or type(turn.ordinary_queue) is not CappedPQNoBuildTurn
            for turn in plans
        ):
            raise UnsupportedCappedFleet("not a complete sequence of capped fleet turns")
        # Reuse the original all-base, all-stock, all-PP and every per-turn
        # ordinary queue admission from #273. Only fleet motion is new.
        _admit_capped(before, specs, carry, tuple(t.ordinary_queue for t in plans))
        state = before
        receipts: list[CappedFleetCargoReceipt] = []
        for index, turn in enumerate(plans):
            if (
                len(state.ships) != carry.soft_ship_limit
                or set(state.ships) != set(before.ships)
                or state.players != before.players
                or state.starbases != before.starbases
                or state.metadata != before.metadata
                or state.ion_storms != before.ion_storms
            ):
                raise UnsupportedCappedFleet("fleet or base roster mutated between turns")
            _require_no_unmodeled_encounters(state)
            mover, transfers = _checked_orders(state, turn, specs)
            sid = mover.ship_id
            original = state.ships[sid]

            # Normal movement uses the AFTER-transfer mass/fuel if present.
            quote_ship = deepcopy(original)
            if transfers:
                t = transfers[0].planet_transfer
                direction = 1 if t.direction == "planet_to_ship" else -1
                for field in TRANSFER_FIELDS:
                    value = getattr(t, field)
                    setattr(
                        quote_ship.cargo, field,
                        getattr(quote_ship.cargo, field) + direction * value,
                    )
            if any(getattr(quote_ship.cargo, field) < 0 for field in TRANSFER_FIELDS):
                raise UnsupportedCappedFleet("negative ship cargo after quoted transfer")
            route = plan_full_normal_move(
                quote_ship, specs, target_x=mover.waypoint_x,
                target_y=mover.waypoint_y, warp=mover.warp,
                allow_partial=False, allow_fuel_proration=False,
            )
            if (
                not route.executable or route.partial or route.fuel_limited
                or route.fuel_used <= 0
                or (original.x, original.y) == (
                    route.destination_x, route.destination_y
                )
            ):
                raise UnsupportedCappedFleet("move must be full leg with positive accounted fuel")
            if turn.placement == PLACEMENTS[0]:
                phases = (
                    PlanetCargoTransferPhase(specs),
                    NormalMovementPhase(
                        specs=specs, eligible_ship_ids=frozenset({sid}),
                        allow_deferred=False, enable_expanded_movement=False,
                        enable_warp_wells=False,
                    ),
                    *PlanetaryHostPipeline().phases,
                )
            else:
                phases = (
                    *PlanetaryHostPipeline().phases,
                    PlanetCargoTransferPhase(specs),
                    NormalMovementPhase(
                        specs=specs, eligible_ship_ids=frozenset({sid}),
                        allow_deferred=False, enable_expanded_movement=False,
                        enable_warp_wells=False,
                    ),
                )
            after, events = HostEngine(phases).step(
                state, turn.all_ship_orders, seed=seed + index,
            )
            if (
                after.turn != state.turn + 1
                or set(after.ships) != set(state.ships)
                or after.players != state.players
                or after.starbases != state.starbases
                or after.metadata != state.metadata
                or after.ion_storms != state.ion_storms
                or any(after.ships[old] != ship for old, ship in state.ships.items()
                       if old != sid)
            ):
                raise UnsupportedCappedFleet("unexplained old ship/base or fleet effect")
            projection, xfers = _audit_transfers_and_undo(
                state, after, events, transfers,
            )
            balances = _planet_ledgers(state, projection, events)
            if not balances or not all(row.resource_balance_exact for row in balances):
                raise UnsupportedCappedFleet("missing/unbalanced full planetary ledger")
            one_start = state.clone()
            one_start.ships = {sid: state.ships[sid]}
            one_projection = projection.clone()
            one_projection.ships = {sid: projection.ships[sid]}
            fuel = _exact_ship_fuel_ledgers(
                one_start, one_projection, events,
            )
            if (
                len(fuel) != 1 or fuel[0].ship_id != sid
                or fuel[0].fuel_used != route.fuel_used
                or fuel[0].ending_position != (
                    route.destination_x, route.destination_y
                )
            ):
                raise UnsupportedCappedFleet("mismatched movement receipt/fuel")
            expected = deepcopy(state.ships[sid])
            expected.cargo = deepcopy(quote_ship.cargo)
            expected.cargo.neutronium -= route.fuel_used
            expected.x, expected.y = route.destination_x, route.destination_y
            expected.waypoint_x, expected.waypoint_y = (
                mover.waypoint_x, mover.waypoint_y
            )
            expected.warp = mover.warp
            if expected.cargo.neutronium < 0 or after.ships[sid] != expected:
                raise UnsupportedCappedFleet("complete typed moving ship delta mismatch")
            _require_no_unmodeled_encounters(after)
            receipts.append(CappedFleetCargoReceipt(
                turn_after=after.turn,
                waiting_queued_base_ids=tuple(sorted(
                    b.planet_id for b in turn.ordinary_queue.all_bases
                    if b.blueprint is not None
                )),
                active_ship_id=sid,
                ship_fuel=fuel[0],
                transfers=xfers,
                planet_balances=balances,
                events=tuple(events),
            ))
            state = after
        return CappedFleetCargoOutcome(
            STATUS, state=state, carry_after=carry, turns=tuple(receipts),
        )
    except (
        ValueError, TypeError, KeyError, AttributeError, OverflowError,
        UnsupportedNormalMovement, UnsupportedPlanetCargoTransfer,
        UnsupportedCompositeTurn, UnsupportedEconomicLedger,
        UnsupportedPopulationRule,
    ):
        return abstain("unsupported or unreconciled capped PQ, cargo, fuel or economy")
