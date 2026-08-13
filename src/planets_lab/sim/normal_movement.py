from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, hypot

from planets_lab.core import Ship
from planets_lab.data import NuStaticSpecs
from planets_lab.rules import max_nominal_distance, movement_fuel_use, ship_movement_mass
from planets_lab.rules.proration import prorate_waypoint_distance


@dataclass(frozen=True, slots=True)
class NormalMovePlan:
    """Normal movement plan for one ship.

    Full-waypoint movement is documented. Partial movement uses the current
    evidence-backed working geometry: project the documented movement distance
    toward the waypoint and round each map coordinate to the nearest integer
    (half away from zero). This matched the large majority of historical
    ordinary-movement observations; special movement remains outside this
    planner.

    Fuel-limited movement is implemented only when the waypoint itself is
    reachable within the nominal turn distance. Combining insufficient fuel
    with a distant partial waypoint remains fail-closed until separately
    differential-verified.
    """

    ship_id: int
    target_x: int
    target_y: int
    destination_x: int
    destination_y: int
    warp: int
    waypoint_distance: float
    distance: float
    max_distance: int
    total_mass: int
    fuel_factor: int
    fuel_required: int
    fuel_used: int
    partial: bool
    fuel_limited: bool
    executable: bool
    reason: str | None = None


def _round_nearest(value: float) -> int:
    """Round to nearest integer with symmetric half-away-from-zero ties."""

    if value >= 0:
        return floor(value + 0.5)
    return ceil(value - 0.5)


def project_toward_waypoint(
    *,
    x: int,
    y: int,
    target_x: int,
    target_y: int,
    distance: int | float,
) -> tuple[int, int]:
    """Project `distance` toward a waypoint and quantize to map coordinates."""

    if distance < 0:
        raise ValueError("distance must be non-negative")

    dx = target_x - x
    dy = target_y - y
    waypoint_distance = hypot(dx, dy)

    if waypoint_distance == 0 or distance == 0:
        return x, y
    if distance >= waypoint_distance:
        return target_x, target_y

    scale = float(distance) / waypoint_distance
    return (
        _round_nearest(x + dx * scale),
        _round_nearest(y + dy * scale),
    )


def plan_full_normal_move(
    ship: Ship,
    specs: NuStaticSpecs,
    *,
    target_x: int,
    target_y: int,
    warp: int,
    gravitonic: bool = False,
) -> NormalMovePlan:
    """Plan the supported ordinary `Move Most` movement subset."""

    max_distance = max_nominal_distance(warp, gravitonic=gravitonic)
    waypoint_distance = hypot(target_x - ship.x, target_y - ship.y)

    if waypoint_distance == 0 or warp == 0:
        return NormalMovePlan(
            ship_id=ship.id,
            target_x=target_x,
            target_y=target_y,
            destination_x=ship.x,
            destination_y=ship.y,
            warp=warp,
            waypoint_distance=waypoint_distance,
            distance=0.0,
            max_distance=max_distance,
            total_mass=0,
            fuel_factor=0,
            fuel_required=0,
            fuel_used=0,
            partial=False,
            fuel_limited=False,
            executable=waypoint_distance == 0,
            reason=None if waypoint_distance == 0 else "warp_zero",
        )

    if ship.engine_id is None:
        raise ValueError(f"ship {ship.id} cannot move without an engine id")

    engine = specs.engines.get(ship.engine_id)
    if engine is None:
        raise ValueError(f"missing engine spec {ship.engine_id} for ship {ship.id}")

    partial = waypoint_distance > max_distance
    if partial:
        destination_x, destination_y = project_toward_waypoint(
            x=ship.x,
            y=ship.y,
            target_x=target_x,
            target_y=target_y,
            distance=max_distance,
        )
    else:
        destination_x, destination_y = target_x, target_y

    distance = hypot(destination_x - ship.x, destination_y - ship.y)
    total_mass = ship_movement_mass(ship, specs)
    fuel_factor = engine.fuel_factor(warp)
    fuel_required = movement_fuel_use(
        fuel_factor=fuel_factor,
        total_mass=total_mass,
        distance_traveled=distance,
        max_distance_per_turn=max_distance,
    )

    fuel_available = ship.cargo.neutronium

    if fuel_available < fuel_required:
        if partial:
            return NormalMovePlan(
                ship_id=ship.id,
                target_x=target_x,
                target_y=target_y,
                destination_x=ship.x,
                destination_y=ship.y,
                warp=warp,
                waypoint_distance=waypoint_distance,
                distance=distance,
                max_distance=max_distance,
                total_mass=total_mass,
                fuel_factor=fuel_factor,
                fuel_required=fuel_required,
                fuel_used=0,
                partial=True,
                fuel_limited=True,
                executable=False,
                reason="insufficient_fuel_partial_waypoint",
            )

        proration = prorate_waypoint_distance(
            requested_distance=waypoint_distance,
            fuel_available=fuel_available,
            fuel_required=fuel_required,
        )
        destination_x, destination_y = project_toward_waypoint(
            x=ship.x,
            y=ship.y,
            target_x=target_x,
            target_y=target_y,
            distance=proration.distance,
        )
        actual_distance = hypot(
            destination_x - ship.x,
            destination_y - ship.y,
        )

        return NormalMovePlan(
            ship_id=ship.id,
            target_x=target_x,
            target_y=target_y,
            destination_x=destination_x,
            destination_y=destination_y,
            warp=warp,
            waypoint_distance=waypoint_distance,
            distance=actual_distance,
            max_distance=max_distance,
            total_mass=total_mass,
            fuel_factor=fuel_factor,
            fuel_required=fuel_required,
            fuel_used=fuel_available,
            partial=destination_x != target_x or destination_y != target_y,
            fuel_limited=True,
            executable=True,
        )

    return NormalMovePlan(
        ship_id=ship.id,
        target_x=target_x,
        target_y=target_y,
        destination_x=destination_x,
        destination_y=destination_y,
        warp=warp,
        waypoint_distance=waypoint_distance,
        distance=distance,
        max_distance=max_distance,
        total_mass=total_mass,
        fuel_factor=fuel_factor,
        fuel_required=fuel_required,
        fuel_used=fuel_required,
        partial=partial,
        fuel_limited=False,
        executable=True,
    )


def execute_full_normal_move(ship: Ship, plan: NormalMovePlan) -> None:
    """Apply a previously validated normal movement plan in place."""

    if ship.id != plan.ship_id:
        raise ValueError("movement plan belongs to a different ship")
    if not plan.executable:
        raise ValueError(f"movement plan is not executable: {plan.reason}")
    if ship.cargo.neutronium < plan.fuel_used:
        raise ValueError("ship no longer has the fuel required by the movement plan")

    ship.cargo.neutronium -= plan.fuel_used
    ship.x = plan.destination_x
    ship.y = plan.destination_y

    if plan.fuel_limited and ship.cargo.neutronium == 0:
        # Normal movement that consumes the remaining fuel triggers the
        # documented out-of-fuel navigation reset.
        ship.waypoint_x = ship.x
        ship.waypoint_y = ship.y
        ship.warp = 0
    else:
        ship.waypoint_x = plan.target_x
        ship.waypoint_y = plan.target_y
        ship.warp = plan.warp
