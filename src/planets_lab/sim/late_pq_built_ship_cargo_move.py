"""A late-PQ newly assembled ship: orbital load then one normal move.

This deliberately splits the *modeled* #271 ship/economic turn from a
caller-asserted follow-on LOAD -> NORMAL-MOVE subphase sequence, without
running a second planetary economy or advancing a second turn. Host
placement of either subphase relative to the new ship's construction is
NOT proven. New-ship actions/order acceptance are NOT observed.

Only the one externally selected new ship may load from its own base
planet and move. Every pre-existing ship remains completely inert.
Planet/cargo deltas and movement fuel are independently reconstructed.
Unsupported phase placement, interaction or receipt => atomic ABSTAIN.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from random import Random

from planets_lab.core import Cargo, GameState
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.sim.engine import HostEvent
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
from planets_lab.sim.standard_movement_economy_turn import (
    UnsupportedCompositeTurn, _require_no_unmodeled_encounters,
)

STATUS = "CONDITIONAL_PQ_BUILT_SHIP_LOAD_NORMAL_MOVE_NOT_NUHOST_VERIFIED"
PLACEMENTS = (
    "late_pq_build_before_economy",
    "late_pq_build_after_economy",
)


@dataclass(frozen=True, slots=True)
class BuiltShipCargoMove:
    planet_to_ship: PlanetCargoTransferOrder
    waypoint_x: int
    waypoint_y: int
    warp: int
    explicitly_ordered_post_build_load_then_move_asserted: bool = False
    all_other_ships_inert_and_no_path_encounters_asserted: bool = False


@dataclass(frozen=True, slots=True)
class BuiltShipCargoMoveOutcome:
    status: str
    state: GameState | None = None
    construction: LatePQOutcome | None = None
    transfer_events: tuple[HostEvent, ...] = ()
    normal_movement_events: tuple[HostEvent, ...] = ()
    loaded_amounts: tuple[tuple[str, int], ...] = ()
    ship_fuel_used: int | None = None
    reason: str | None = None
    server_accepted_build_verified: bool = False
    host_post_build_transfer_timing_verified: bool = False
    new_ship_navigation_order_verified: bool = False
    host_movement_execution_verified: bool = False
    independent_host_parity_verified: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


class UnsupportedBuiltShipMove(ValueError):
    """Nothing escapes from a failed construction/transfer/move sequence."""


def simulate_pq_built_ship_load_and_move(
    before: GameState,
    specs: NuStaticSpecs,
    context: LatePQContext,
    order: BuiltShipCargoMove,
    *,
    placement: str,
    standard_rules_asserted: bool = False,
    complete_shipyard_warehouse_and_economic_scope_asserted: bool = False,
    no_external_events_other_than_explicit_load_and_move_asserted: bool = False,
    seed: int = 0,
) -> BuiltShipCargoMoveOutcome:
    def abstain(reason: str) -> BuiltShipCargoMoveOutcome:
        return BuiltShipCargoMoveOutcome(
            "ABSTAIN_PQ_BUILT_SHIP_CARGO_MOVE", reason=reason,
        )

    if (
        type(before) is not GameState or type(specs) is not NuStaticSpecs
        or type(context) is not LatePQContext or type(order) is not BuiltShipCargoMove
        or placement not in PLACEMENTS or type(seed) is not int
        or standard_rules_asserted is not True
        or complete_shipyard_warehouse_and_economic_scope_asserted is not True
        or no_external_events_other_than_explicit_load_and_move_asserted is not True
        or order.explicitly_ordered_post_build_load_then_move_asserted is not True
        or order.all_other_ships_inert_and_no_path_encounters_asserted is not True
        or type(order.waypoint_x) is not int
        or type(order.waypoint_y) is not int
        or type(order.warp) is not int or not 1 <= order.warp <= 9
    ):
        return abstain("unsupported or incomplete explicit compound phase scope")

    try:
        transfer = order.planet_to_ship
        if (
            type(transfer) is not PlanetCargoTransferOrder
            or type(transfer.planet_id) is not int
            or transfer.planet_id != context.selected_planet_id
            or transfer.direction != "planet_to_ship"
        ):
            raise UnsupportedBuiltShipMove("only selected own base planet to new ship supported")

        amounts = {}
        for name in TRANSFER_FIELDS:
            v = getattr(transfer, name)
            if type(v) is not int or not 0 <= v <= 1000000:
                raise UnsupportedBuiltShipMove("invalid typed cargo amount")
            amounts[name] = v
        if not any(amounts.values()):
            raise UnsupportedBuiltShipMove("postbuild load must contain real cargo")

        # Construction executes the full intact economic block exactly once.
        build = simulate_late_pq_external_selected_economic_turn(
            before, specs, context, placement=placement,
            standard_rules_asserted=True,
            full_independent_economic_inventory_asserted=True,
            seed=seed,
        )
        if (
            not build.supported or build.state is None
            or build.ship_receipt is None
            or build.selected_base_id != context.selected_planet_id
            or build.ship_receipt.ship_id != context.selected_ship_id
            or not build.planet_balances
            or not all(x.resource_balance_exact for x in build.planet_balances)
        ):
            raise UnsupportedBuiltShipMove("original late PQ build/economy unsupported")

        state = build.state
        sid = context.selected_ship_id
        pid = context.selected_planet_id
        source_ship = state.ships[sid]
        base_planet = state.planets[pid]
        if (
            source_ship.owner_id != base_planet.owner_id
            or (source_ship.x, source_ship.y) != (base_planet.x, base_planet.y)
            or source_ship.cargo != Cargo()
            or not source_ship.engine_id in specs.engines
            or specs.hulls[source_ship.hull_id].special
        ):
            raise UnsupportedBuiltShipMove("new ship not ordinary empty at its own base")

        # Avoid unmodeled co-location, enemy planet attack, special collision.
        _require_no_unmodeled_encounters(state)
        navigation = ShipOrder(
            ship_id=sid, waypoint_x=order.waypoint_x,
            waypoint_y=order.waypoint_y, warp=order.warp,
            planet_transfer=transfer,
        )
        orders = TurnOrders(by_player={
            owner: PlayerOrders(
                player_id=owner,
                ship_orders=(navigation,) if owner == source_ship.owner_id else (),
            )
            for owner in sorted(state.players)
        })
        modeled = state.clone()
        receipts = tuple(PlanetCargoTransferPhase(specs).run(
            modeled, orders, Random(seed),
        ))
        if len(receipts) != 1:
            raise UnsupportedBuiltShipMove("missing or extra transfer receipt")
        details = dict(receipts[0].details)
        if (
            receipts[0].phase != "planet_cargo_transfer"
            or receipts[0].kind != "planet_cargo_transferred"
            or receipts[0].entity_type != "planet"
            or receipts[0].entity_id != pid
            or len(details) != len(receipts[0].details)
            or details != {
                "ship_id": str(sid), "planet_id": str(pid),
                "direction": "planet_to_ship", "colonized": "false",
                **{name: str(amounts[name]) for name in TRANSFER_FIELDS},
            }
        ):
            raise UnsupportedBuiltShipMove("transfer event does not match submitted cargo order")

        projected = state.clone()
        for name in TRANSFER_FIELDS:
            volume = amounts[name]
            setattr(
                projected.planets[pid].cargo, name,
                getattr(projected.planets[pid].cargo, name) - volume,
            )
            setattr(
                projected.ships[sid].cargo, name,
                getattr(projected.ships[sid].cargo, name) + volume,
            )
            if getattr(projected.planets[pid].cargo, name) < 0:
                raise UnsupportedBuiltShipMove("unfunded loaded cargo")
        if projected != modeled:
            raise UnsupportedBuiltShipMove("unaccounted transfer stock or ship delta")

        loaded = modeled.ships[sid]
        move_plan = plan_full_normal_move(
            loaded, specs, target_x=order.waypoint_x,
            target_y=order.waypoint_y, warp=order.warp,
            allow_partial=False, allow_fuel_proration=False,
        )
        if (
            not move_plan.executable or move_plan.partial
            or move_plan.fuel_limited or move_plan.fuel_used <= 0
            or (loaded.x, loaded.y) == (
                move_plan.destination_x, move_plan.destination_y
            )
        ):
            raise UnsupportedBuiltShipMove("only fully fueled real short movement supported")

        moves = tuple(NormalMovementPhase(
            specs=specs, eligible_ship_ids=frozenset({sid}),
            allow_deferred=False, enable_expanded_movement=False,
            enable_warp_wells=False,
        ).run(modeled, orders, Random(seed)))
        if len(moves) != 1:
            raise UnsupportedBuiltShipMove("missing or duplicate normal movement event")
        event = moves[0]
        d = dict(event.details)
        if (
            event.phase != "normal_movement"
            or event.kind != "ship_moved"
            or event.entity_type != "ship" or event.entity_id != sid
            or len(d) != len(event.details)
            or d.get("from_x") != str(loaded.x)
            or d.get("from_y") != str(loaded.y)
            or d.get("to_x") != str(move_plan.destination_x)
            or d.get("to_y") != str(move_plan.destination_y)
            or d.get("fuel_used") != str(move_plan.fuel_used)
            or d.get("partial") != "false"
            or d.get("fuel_limited") != "false"
        ):
            # 'loaded' is an alias into modeled, but its x/y mutate.
            # Compare original pre-move coordinates in the projection.
            origin = projected.ships[sid]
            if (
                event.phase != "normal_movement"
                or event.kind != "ship_moved"
                or event.entity_type != "ship" or event.entity_id != sid
                or len(d) != len(event.details)
                or d.get("from_x") != str(origin.x)
                or d.get("from_y") != str(origin.y)
                or d.get("to_x") != str(move_plan.destination_x)
                or d.get("to_y") != str(move_plan.destination_y)
                or d.get("fuel_used") != str(move_plan.fuel_used)
                or d.get("partial") != "false"
                or d.get("fuel_limited") != "false"
            ):
                raise UnsupportedBuiltShipMove("unsupported movement event identity/fuel")

        expected = projected.clone()
        expected_ship = expected.ships[sid]
        expected_ship.x, expected_ship.y = (
            move_plan.destination_x, move_plan.destination_y
        )
        expected_ship.cargo.neutronium -= move_plan.fuel_used
        expected_ship.waypoint_x, expected_ship.waypoint_y = (
            order.waypoint_x, order.waypoint_y
        )
        expected_ship.warp = order.warp
        if expected_ship.cargo.neutronium < 0 or modeled != expected:
            raise UnsupportedBuiltShipMove("final ship/planet/full game parity failed")
        _require_no_unmodeled_encounters(modeled)
        if (
            modeled.turn != before.turn + 1
            or modeled.players != before.players
            or modeled.starbases != before.starbases
            or set(modeled.ships) != set(before.ships) | {sid}
            or any(modeled.ships[old] != ship
                   for old, ship in before.ships.items())
        ):
            raise UnsupportedBuiltShipMove("existing fleet or model turn changed unexpectedly")
        return BuiltShipCargoMoveOutcome(
            STATUS, state=modeled, construction=build,
            transfer_events=receipts, normal_movement_events=moves,
            loaded_amounts=tuple((name, amounts[name]) for name in TRANSFER_FIELDS),
            ship_fuel_used=move_plan.fuel_used,
        )
    except (
        ValueError, TypeError, KeyError, AttributeError, OverflowError,
        UnsupportedPlanetCargoTransfer, UnsupportedNormalMovement,
        UnsupportedCompositeTurn,
    ):
        return abstain("unsupported conditional construction/cargo/navigation or ledger")
