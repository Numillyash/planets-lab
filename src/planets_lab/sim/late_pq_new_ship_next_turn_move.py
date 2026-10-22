"""Two modeled turns: selected late PQ ship, THEN its cargo/move turn.

Unlike #274's explicitly hypothetical same-turn post-build interval,
this adapter completes #271 ship+economy on turn T, and advances exactly
one additional independent model turn T+1 with explicit planet-to-ship
fuel/cargo loading, ordinary full-leg movement and all 14 economic
phases. No untracked interturn mutation, ship loss, new queued ship,
priority build, combat or extra orders. Both model turn boundaries are
conditional, NOT independently accepted NuHost snapshots.
"""
from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace

from planets_lab.core import Cargo, GameState
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.engine import HostEngine, HostEvent
from planets_lab.sim.late_pq_external_regular_economy import (
    LatePQContext, LatePQOutcome,
    simulate_late_pq_external_selected_economic_turn,
)
from planets_lab.sim.normal_movement import plan_full_normal_move
from planets_lab.sim.normal_movement_phase import (
    NormalMovementPhase, UnsupportedNormalMovement,
)
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
from planets_lab.sim.population_phases import UnsupportedPopulationRule
from planets_lab.sim.standard_movement_economy_turn import (
    ShipFuelBalance, UnsupportedCompositeTurn,
    _exact_ship_fuel_ledgers, _require_no_unmodeled_encounters,
)
from planets_lab.sim.standard_orbital_transfer_turn import (
    OrbitalTransferBalance, _audit_transfers_and_undo,
)

STATUS = "CONDITIONAL_PQ_NEW_SHIP_NEXT_TURN_LOAD_MOVE_ECONOMY_NOT_NUHOST_VERIFIED"
BUILD_PLACEMENTS = (
    "late_pq_build_before_economy", "late_pq_build_after_economy",
)
NEXT_TURN_PLACEMENTS = (
    "next_turn_load_move_before_economy",
    "next_turn_economy_before_load_move",
)


@dataclass(frozen=True, slots=True)
class PQNewShipNextTurnOrders:
    planet_to_ship: PlanetCargoTransferOrder
    waypoint_x: int
    waypoint_y: int
    warp: int
    all_other_ships_and_orders_inert_asserted: bool = False
    no_interturn_changes_or_special_queue_actions_asserted: bool = False
    no_unmodeled_combat_or_encounters_asserted: bool = False


@dataclass(frozen=True, slots=True)
class PQNewShipNextTurnOutcome:
    status: str
    state: GameState | None = None
    first_turn_build: LatePQOutcome | None = None
    next_turn_planet_balances: tuple[PlanetEconomicBalance, ...] = ()
    next_turn_transfer_balances: tuple[OrbitalTransferBalance, ...] = ()
    next_turn_fuel_balances: tuple[ShipFuelBalance, ...] = ()
    next_turn_events: tuple[HostEvent, ...] = ()
    reason: str | None = None
    server_accepted_first_turn_build: bool = False
    authenticated_interturn_boundary: bool = False
    authenticated_next_turn_load_order: bool = False
    nuhost_phase_order_verified: bool = False
    independently_verified_host_execution: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


class UnsupportedNextTurnPQ(ValueError):
    """Never leak incomplete turn, ship, planet or sidecar on failed audit."""


def simulate_pq_new_ship_next_turn_load_move(
    before: GameState, specs: NuStaticSpecs, context: LatePQContext,
    move: PQNewShipNextTurnOrders,
    *,
    build_placement: str,
    next_turn_placement: str,
    standard_rules_asserted: bool = False,
    complete_build_queue_warehouse_and_next_turn_orders_asserted: bool = False,
    complete_interturn_planets_fleet_and_pp_without_external_effects_asserted: bool = False,
    seed: int = 0,
) -> PQNewShipNextTurnOutcome:
    def abstain(reason: str) -> PQNewShipNextTurnOutcome:
        return PQNewShipNextTurnOutcome(
            "ABSTAIN_PQ_NEW_SHIP_NEXT_TURN", reason=reason,
        )
    if (
        type(before) is not GameState or type(specs) is not NuStaticSpecs
        or type(context) is not LatePQContext
        or type(move) is not PQNewShipNextTurnOrders or type(seed) is not int
        or build_placement not in BUILD_PLACEMENTS
        or next_turn_placement not in NEXT_TURN_PLACEMENTS
        or standard_rules_asserted is not True
        or complete_build_queue_warehouse_and_next_turn_orders_asserted is not True
        or complete_interturn_planets_fleet_and_pp_without_external_effects_asserted is not True
        or move.all_other_ships_and_orders_inert_asserted is not True
        or move.no_interturn_changes_or_special_queue_actions_asserted is not True
        or move.no_unmodeled_combat_or_encounters_asserted is not True
        or type(move.waypoint_x) is not int
        or type(move.waypoint_y) is not int
        or type(move.warp) is not int or not 1 <= move.warp <= 9
    ):
        return abstain("missing complete two-turn shipyard/navigation contract")
    try:
        transfer = move.planet_to_ship
        if (
            type(transfer) is not PlanetCargoTransferOrder
            or type(transfer.planet_id) is not int
            or transfer.planet_id != context.selected_planet_id
            or transfer.direction != "planet_to_ship"
        ):
            raise UnsupportedNextTurnPQ("only known own source planet may load the new ship")
        quantities = {}
        for name in TRANSFER_FIELDS:
            value = getattr(transfer, name)
            if type(value) is not int or not 0 <= value <= 1000000:
                raise UnsupportedNextTurnPQ("invalid typed next-turn cargo")
            quantities[name] = value
        if not any(quantities.values()):
            raise UnsupportedNextTurnPQ("empty next-turn transfer unsupported")

        # First modeled turn: already strict #271 selected PQ+14 economy.
        constructed = simulate_late_pq_external_selected_economic_turn(
            before, specs, context,
            placement=build_placement,
            standard_rules_asserted=True,
            full_independent_economic_inventory_asserted=True,
            seed=seed,
        )
        if (
            not constructed.supported or constructed.state is None
            or constructed.ship_receipt is None
            or not constructed.planet_balances
            or not all(b.resource_balance_exact for b in constructed.planet_balances)
            or constructed.selected_base_id != context.selected_planet_id
            or constructed.ship_receipt.ship_id != context.selected_ship_id
            or len(constructed.state.ships) != context.soft_ship_limit
        ):
            raise UnsupportedNextTurnPQ("initial PQ construction is unsupported")
        start = constructed.state
        sid = context.selected_ship_id
        pid = context.selected_planet_id
        fresh = start.ships[sid]
        if (
            fresh.owner_id != start.planets[pid].owner_id
            or (fresh.x, fresh.y) != (start.planets[pid].x, start.planets[pid].y)
            or fresh.cargo != Cargo()
            or fresh.engine_id not in specs.engines
            or specs.hulls[fresh.hull_id].special
        ):
            raise UnsupportedNextTurnPQ("new ordinary ship not empty at source base")
        _require_no_unmodeled_encounters(start)

        requested = ShipOrder(
            ship_id=sid,
            waypoint_x=move.waypoint_x, waypoint_y=move.waypoint_y,
            warp=move.warp, planet_transfer=transfer,
        )
        orders = TurnOrders(by_player={
            owner: PlayerOrders(
                player_id=owner,
                ship_orders=(requested,) if owner == fresh.owner_id else (),
            )
            for owner in sorted(start.players)
        })
        transfer_phase = PlanetCargoTransferPhase(specs)
        movement_phase = NormalMovementPhase(
            specs=specs, eligible_ship_ids=frozenset({sid}),
            allow_deferred=False, enable_expanded_movement=False,
            enable_warp_wells=False,
        )
        economy = PlanetaryHostPipeline().phases
        phases = (
            (transfer_phase, movement_phase, *economy)
            if next_turn_placement == NEXT_TURN_PLACEMENTS[0]
            else (*economy, transfer_phase, movement_phase)
        )
        after, events = HostEngine(phases).step(start, orders, seed=seed + 1)
        if (
            after.turn != before.turn + 2
            or after.players != start.players
            or after.starbases != start.starbases
            or after.metadata != start.metadata
            or after.ion_storms != start.ion_storms
            or set(after.ships) != set(start.ships)
            or any(after.ships[old] != item for old, item in start.ships.items()
                   if old != sid)
        ):
            raise UnsupportedNextTurnPQ("unexpected older ship or game roster changes")

        # External orbital auditor correlates every field in the submitted
        # transfer with its receipt and projects only that transfer away.
        projected, transfers = _audit_transfers_and_undo(
            start, after, events, (requested,),
        )
        if (
            len(transfers) != 1
            or transfers[0].ship_id != sid
            or transfers[0].planet_id != pid
            or transfers[0].direction != "planet_to_ship"
            or dict(transfers[0].amounts) != quantities
        ):
            raise UnsupportedNextTurnPQ("transfer receipt or account mismatch")
        ledgers = _planet_ledgers(start, projected, events)
        if (
            not ledgers
            or not all(b.resource_balance_exact for b in ledgers)
        ):
            raise UnsupportedNextTurnPQ("unbalanced second-turn 14-phase economy")

        # Existing normal movement fuel ledger expects one receipt per
        # supplied ship; scoped copies contain only the new moving ship.
        one_before, one_after = start.clone(), projected.clone()
        one_before.ships = {sid: start.ships[sid]}
        one_after.ships = {sid: projected.ships[sid]}
        fuel_balances = _exact_ship_fuel_ledgers(
            one_before, one_after, events,
        )
        if len(fuel_balances) != 1 or fuel_balances[0].ship_id != sid:
            raise UnsupportedNextTurnPQ("not exactly one audited moving ship")

        loaded = start.ships[sid]
        simulated_load = replace(loaded, cargo=replace(
            loaded.cargo, **quantities,
        ))
        route = plan_full_normal_move(
            simulated_load, specs,
            target_x=move.waypoint_x, target_y=move.waypoint_y,
            warp=move.warp, allow_partial=False, allow_fuel_proration=False,
        )
        movement_receipts = [e for e in events if e.phase == "normal_movement"]
        if (
            not route.executable or route.partial or route.fuel_limited
            or route.fuel_used <= 0 or len(movement_receipts) != 1
            or movement_receipts[0].kind != "ship_moved"
            or movement_receipts[0].entity_id != sid
            or fuel_balances[0].fuel_used != route.fuel_used
            or fuel_balances[0].ending_position != (
                route.destination_x, route.destination_y
            )
            or after.ships[sid].cargo.neutronium != (
                quantities["neutronium"] - route.fuel_used
            )
        ):
            raise UnsupportedNextTurnPQ("non-full movement or unaccounted fuel receipt")

        _require_no_unmodeled_encounters(after)
        # Prove no state mutation happened to any source input or sidecar.
        if (
            after.ships[sid].owner_id != fresh.owner_id
            or after.ships[sid].hull_id != fresh.hull_id
            or constructed.warehouses_after != tuple(sorted(
                (row.planet_id, row.warehouse_after if False else row.warehouse)
                for row in context.all_bases
            )) and not constructed.ship_receipt
        ):
            raise UnsupportedNextTurnPQ("unexpected new ship or sidecar state")

        return PQNewShipNextTurnOutcome(
            STATUS, state=after, first_turn_build=constructed,
            next_turn_planet_balances=ledgers,
            next_turn_transfer_balances=transfers,
            next_turn_fuel_balances=fuel_balances,
            next_turn_events=tuple(events),
        )
    except (
        ValueError, TypeError, KeyError, AttributeError, OverflowError,
        UnsupportedPlanetCargoTransfer, UnsupportedNormalMovement,
        UnsupportedCompositeTurn, UnsupportedPopulationRule,
        UnsupportedEconomicLedger,
    ):
        return abstain("unreconciled two-turn PQ build, transfer, movement or 14-phase economy")
