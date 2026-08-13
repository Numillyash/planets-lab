from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from planets_lab.core import GameState, Ship
from planets_lab.data import NuStaticSpecs
from planets_lab.sim.engine import HostEvent
from planets_lab.sim.normal_movement import (
    NormalMovePlan,
    execute_full_normal_move,
    plan_full_normal_move,
)
from planets_lab.sim.orders import ShipOrder, TurnOrders


class UnsupportedNormalMovement(RuntimeError):
    """Raised when the phase reaches a NuHost case not implemented yet."""

    def __init__(self, plan: NormalMovePlan) -> None:
        self.plan = plan
        super().__init__(
            f"ship {plan.ship_id} normal movement is not implemented for "
            f"reason={plan.reason!r}"
        )


@dataclass(slots=True)
class NormalMovementPhase:
    """Execute the currently supported `Move Most` subset.

    Ships are processed in ascending Ship ID order, matching the documented
    movement ordering. This phase currently supports only complete waypoint
    moves that the full-waypoint planner can validate exactly.

    Partial movement and insufficient-fuel proration are fail-closed by
    default. Research/replay tooling can set ``allow_deferred=True`` to keep
    the turn running while emitting an explicit deferred event, but production
    simulation should leave that disabled until those mechanics are verified.

    Tow, intercept, mines, warp wells, hyperjump and other special movement are
    intentionally outside this phase. Until movement classification is modeled
    explicitly, callers may provide ``eligible_ship_ids`` to restrict this
    phase to ships already classified for normal `Move Most` processing.
    """

    specs: NuStaticSpecs
    gravitonic_hull_ids: frozenset[int] = field(default_factory=frozenset)
    eligible_ship_ids: frozenset[int] | None = None
    allow_deferred: bool = False

    name: str = "normal_movement"

    def run(
        self,
        state: GameState,
        orders: TurnOrders,
        rng: Random,
    ) -> list[HostEvent]:
        del rng  # Normal movement in the supported subset is deterministic.

        ship_orders = self._ship_orders(orders)
        events: list[HostEvent] = []

        for ship_id in sorted(state.ships):
            if self.eligible_ship_ids is not None and ship_id not in self.eligible_ship_ids:
                continue

            ship = state.ships[ship_id]
            order = ship_orders.get(ship_id)

            target_x, target_y, warp = self._apply_navigation_order(ship, order)

            plan = plan_full_normal_move(
                ship,
                self.specs,
                target_x=target_x,
                target_y=target_y,
                warp=warp,
                gravitonic=ship.hull_id in self.gravitonic_hull_ids,
            )

            if plan.executable:
                origin = (ship.x, ship.y)
                execute_full_normal_move(ship, plan)

                if origin == (ship.x, ship.y):
                    events.append(
                        HostEvent(
                            phase=self.name,
                            kind="ship_noop",
                            message=(
                                f"ship={ship.id} position=({ship.x},{ship.y}) "
                                f"warp={warp} fuel=0"
                            ),
                        )
                    )
                else:
                    events.append(
                        HostEvent(
                            phase=self.name,
                            kind="ship_moved",
                            message=(
                                f"ship={ship.id} from=({origin[0]},{origin[1]}) "
                                f"to=({ship.x},{ship.y}) warp={warp} "
                                f"fuel={plan.fuel_required}"
                            ),
                        )
                    )
                continue

            if plan.reason == "warp_zero":
                events.append(
                    HostEvent(
                        phase=self.name,
                        kind="ship_noop",
                        message=(
                            f"ship={ship.id} position=({ship.x},{ship.y}) "
                            f"warp=0 reason=warp_zero"
                        ),
                    )
                )
                continue

            if not self.allow_deferred:
                raise UnsupportedNormalMovement(plan)

            events.append(
                HostEvent(
                    phase=self.name,
                    kind="ship_deferred",
                    message=(
                        f"ship={ship.id} position=({ship.x},{ship.y}) "
                        f"target=({target_x},{target_y}) warp={warp} "
                        f"reason={plan.reason}"
                    ),
                )
            )

        return events

    @staticmethod
    def _ship_orders(orders: TurnOrders) -> dict[int, ShipOrder]:
        result: dict[int, ShipOrder] = {}
        for player_orders in orders.by_player.values():
            for ship_order in player_orders.ship_orders:
                result[ship_order.ship_id] = ship_order
        return result

    @staticmethod
    def _apply_navigation_order(
        ship: Ship,
        order: ShipOrder | None,
    ) -> tuple[int, int, int]:
        target_x = ship.waypoint_x if ship.waypoint_x is not None else ship.x
        target_y = ship.waypoint_y if ship.waypoint_y is not None else ship.y
        warp = ship.warp

        if order is not None:
            if order.waypoint_x is not None:
                target_x = order.waypoint_x
            if order.waypoint_y is not None:
                target_y = order.waypoint_y
            if order.warp is not None:
                warp = order.warp

        ship.waypoint_x = target_x
        ship.waypoint_y = target_y
        ship.warp = warp
        return target_x, target_y, warp
