from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, hypot

from planets_lab.core import Ship
from planets_lab.data import NuStaticSpecs
from planets_lab.rules import max_nominal_distance, movement_fuel_use, ship_movement_mass
from planets_lab.rules.proration import prorate_waypoint_distance


@dataclass(frozen=True, slots=True)
class NormalMovePlan:
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
    if value >= 0:
        return floor(value + 0.5)
    return ceil(value - 0.5)


def project_toward_waypoint(*, x: int, y: int, target_x: int, target_y: int, distance: int | float) -> tuple[int, int]:
    """Project movement using the Host major/minor-axis integer geometry.

    NuHost real-game differential samples show that partial movement is not
    produced by rounding two continuous endpoint coordinates independently.
    Instead, Host rounds travel on the major axis first and derives the minor
    axis from that integer movement. This reproduces the classic HOST stepping
    algorithm and the observed NuHost +/-1 coordinate cases.
    """

    if distance < 0:
        raise ValueError("distance must be non-negative")

    dx = target_x - x
    dy = target_y - y
    waypoint_distance = hypot(dx, dy)
    if waypoint_distance == 0 or distance == 0:
        return x, y
    if distance >= waypoint_distance:
        return target_x, target_y

    abs_dx = abs(dx)
    abs_dy = abs(dy)

    if abs_dx >= abs_dy:
        major = abs_dx
        minor = abs_dy
        major_move = _round_nearest(float(distance) * major / waypoint_distance)
        minor_move = _round_nearest(major_move * minor / major) if major else 0
        move_x = major_move if dx >= 0 else -major_move
        move_y = minor_move if dy >= 0 else -minor_move
    else:
        major = abs_dy
        minor = abs_dx
        major_move = _round_nearest(float(distance) * major / waypoint_distance)
        minor_move = _round_nearest(major_move * minor / major) if major else 0
        move_y = major_move if dy >= 0 else -major_move
        move_x = minor_move if dx >= 0 else -minor_move

    return x + move_x, y + move_y


def plan_full_normal_move(
    ship: Ship,
    specs: NuStaticSpecs,
    *,
    target_x: int,
    target_y: int,
    warp: int,
    gravitonic: bool = False,
    allow_partial: bool = False,
    allow_fuel_proration: bool = False,
    movement_mass_override: int | None = None,
) -> NormalMovePlan:
    if movement_mass_override is not None and movement_mass_override < 0:
        raise ValueError("movement_mass_override must be non-negative")

    max_distance = max_nominal_distance(warp, gravitonic=gravitonic)
    waypoint_distance = hypot(target_x - ship.x, target_y - ship.y)

    if waypoint_distance == 0 or warp == 0:
        return NormalMovePlan(ship.id, target_x, target_y, ship.x, ship.y, warp, waypoint_distance, 0.0, max_distance, 0, 0, 0, 0, False, False, waypoint_distance == 0, None if waypoint_distance == 0 else "warp_zero")

    partial = waypoint_distance > max_distance
    if partial and not allow_partial:
        return NormalMovePlan(ship.id, target_x, target_y, ship.x, ship.y, warp, waypoint_distance, waypoint_distance, max_distance, 0, 0, 0, 0, True, False, False, "partial_waypoint_required")

    if ship.engine_id is None:
        raise ValueError(f"ship {ship.id} cannot move without an engine id")
    engine = specs.engines.get(ship.engine_id)
    if engine is None:
        raise ValueError(f"missing engine spec {ship.engine_id} for ship {ship.id}")

    if partial:
        destination_x, destination_y = project_toward_waypoint(x=ship.x, y=ship.y, target_x=target_x, target_y=target_y, distance=max_distance)
    else:
        destination_x, destination_y = target_x, target_y

    distance = hypot(destination_x - ship.x, destination_y - ship.y)
    total_mass = movement_mass_override if movement_mass_override is not None else ship_movement_mass(ship, specs)
    fuel_factor = engine.fuel_factor(warp)
    fuel_required = movement_fuel_use(fuel_factor=fuel_factor, total_mass=total_mass, distance_traveled=distance, max_distance_per_turn=max_distance)
    fuel_available = ship.cargo.neutronium

    if fuel_available < fuel_required:
        if not allow_fuel_proration:
            return NormalMovePlan(ship.id, target_x, target_y, ship.x, ship.y, warp, waypoint_distance, distance, max_distance, total_mass, fuel_factor, fuel_required, 0, partial, True, False, "insufficient_fuel")
        if partial:
            return NormalMovePlan(ship.id, target_x, target_y, ship.x, ship.y, warp, waypoint_distance, distance, max_distance, total_mass, fuel_factor, fuel_required, 0, True, True, False, "insufficient_fuel_partial_waypoint")

        proration = prorate_waypoint_distance(requested_distance=waypoint_distance, fuel_available=fuel_available, fuel_required=fuel_required)
        destination_x, destination_y = project_toward_waypoint(x=ship.x, y=ship.y, target_x=target_x, target_y=target_y, distance=proration.distance)
        actual_distance = hypot(destination_x - ship.x, destination_y - ship.y)
        return NormalMovePlan(ship.id, target_x, target_y, destination_x, destination_y, warp, waypoint_distance, actual_distance, max_distance, total_mass, fuel_factor, fuel_required, fuel_available, destination_x != target_x or destination_y != target_y, True, True)

    return NormalMovePlan(ship.id, target_x, target_y, destination_x, destination_y, warp, waypoint_distance, distance, max_distance, total_mass, fuel_factor, fuel_required, fuel_required, partial, False, True)


def execute_full_normal_move(ship: Ship, plan: NormalMovePlan) -> None:
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
        ship.waypoint_x = ship.x
        ship.waypoint_y = ship.y
        ship.warp = 0
    else:
        ship.waypoint_x = plan.target_x
        ship.waypoint_y = plan.target_y
        ship.warp = plan.warp
