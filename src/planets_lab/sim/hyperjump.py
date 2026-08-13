from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from planets_lab.core import Ship


HYPERJUMP_FUEL_COST = 50
HYPERJUMP_MIN_DISTANCE = 340.0
HYPERJUMP_MAX_DISTANCE = 360.0
HYPERJUMP_MIN_WAYPOINT_DISTANCE = 20.0


@dataclass(frozen=True, slots=True)
class HyperjumpPlan:
    ship_id: int
    target_x: int | None
    target_y: int | None
    destination_x: int
    destination_y: int
    waypoint_distance: float
    fuel_used: int
    executable: bool
    reason: str | None = None


def plan_hyperjump(
    ship: Ship,
    *,
    hyperjump_hull_ids: frozenset[int],
) -> HyperjumpPlan:
    target_x = ship.waypoint_x
    target_y = ship.waypoint_y

    def rejected(reason: str, *, distance: float = 0.0) -> HyperjumpPlan:
        return HyperjumpPlan(
            ship_id=ship.id,
            target_x=target_x,
            target_y=target_y,
            destination_x=ship.x,
            destination_y=ship.y,
            waypoint_distance=distance,
            fuel_used=0,
            executable=False,
            reason=reason,
        )

    if ship.friendly_code.strip().lower() != "hyp":
        return rejected("friendly_code_not_hyp")

    if ship.hull_id not in hyperjump_hull_ids:
        return rejected("not_hyperjump_capable")

    if ship.warp <= 0:
        return rejected("warp_zero")

    if target_x is None or target_y is None:
        return rejected("missing_waypoint")

    waypoint_distance = hypot(target_x - ship.x, target_y - ship.y)

    if waypoint_distance <= HYPERJUMP_MIN_WAYPOINT_DISTANCE:
        return rejected("waypoint_too_close", distance=waypoint_distance)

    if ship.cargo.neutronium < HYPERJUMP_FUEL_COST:
        return rejected("insufficient_fuel", distance=waypoint_distance)

    if not HYPERJUMP_MIN_DISTANCE <= waypoint_distance <= HYPERJUMP_MAX_DISTANCE:
        return rejected(
            "default_350_projection_required",
            distance=waypoint_distance,
        )

    return HyperjumpPlan(
        ship_id=ship.id,
        target_x=target_x,
        target_y=target_y,
        destination_x=target_x,
        destination_y=target_y,
        waypoint_distance=waypoint_distance,
        fuel_used=HYPERJUMP_FUEL_COST,
        executable=True,
    )


def execute_hyperjump(ship: Ship, plan: HyperjumpPlan) -> None:
    if ship.id != plan.ship_id:
        raise ValueError("hyperjump plan belongs to a different ship")
    if not plan.executable:
        raise ValueError(f"hyperjump plan is not executable: {plan.reason}")
    if ship.cargo.neutronium < plan.fuel_used:
        raise ValueError("ship no longer has the fuel required by the hyperjump plan")

    ship.cargo.neutronium -= plan.fuel_used
    ship.x = plan.destination_x
    ship.y = plan.destination_y
