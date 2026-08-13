from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from planets_lab.core import Ship
from planets_lab.data import NuStaticSpecs
from planets_lab.rules import max_nominal_distance, movement_fuel_use, ship_movement_mass


@dataclass(frozen=True, slots=True)
class NormalMovePlan:
    """Validated full-waypoint normal movement for one ship.

    This planner intentionally handles only cases where the waypoint can be
    reached completely in the current normal-movement step. Partial movement,
    insufficient-fuel proration, warp wells, towing, intercept, mines and
    special movement remain separate rules/phases.
    """

    ship_id: int
    target_x: int
    target_y: int
    warp: int
    distance: float
    max_distance: int
    total_mass: int
    fuel_factor: int
    fuel_required: int
    executable: bool
    reason: str | None = None


def plan_full_normal_move(
    ship: Ship,
    specs: NuStaticSpecs,
    *,
    target_x: int,
    target_y: int,
    warp: int,
    gravitonic: bool = False,
) -> NormalMovePlan:
    """Plan a normal move only when the full waypoint is reachable this turn."""

    max_distance = max_nominal_distance(warp, gravitonic=gravitonic)
    distance = hypot(target_x - ship.x, target_y - ship.y)

    if distance == 0 or warp == 0:
        return NormalMovePlan(
            ship_id=ship.id,
            target_x=target_x,
            target_y=target_y,
            warp=warp,
            distance=distance,
            max_distance=max_distance,
            total_mass=0,
            fuel_factor=0,
            fuel_required=0,
            executable=distance == 0,
            reason=None if distance == 0 else "warp_zero",
        )

    if distance > max_distance:
        return NormalMovePlan(
            ship_id=ship.id,
            target_x=target_x,
            target_y=target_y,
            warp=warp,
            distance=distance,
            max_distance=max_distance,
            total_mass=0,
            fuel_factor=0,
            fuel_required=0,
            executable=False,
            reason="partial_waypoint_required",
        )

    if ship.engine_id is None:
        raise ValueError(f"ship {ship.id} cannot move without an engine id")

    engine = specs.engines.get(ship.engine_id)
    if engine is None:
        raise ValueError(f"missing engine spec {ship.engine_id} for ship {ship.id}")

    total_mass = ship_movement_mass(ship, specs)
    fuel_factor = engine.fuel_factor(warp)
    fuel_required = movement_fuel_use(
        fuel_factor=fuel_factor,
        total_mass=total_mass,
        distance_traveled=distance,
        max_distance_per_turn=max_distance,
    )

    if ship.cargo.neutronium < fuel_required:
        return NormalMovePlan(
            ship_id=ship.id,
            target_x=target_x,
            target_y=target_y,
            warp=warp,
            distance=distance,
            max_distance=max_distance,
            total_mass=total_mass,
            fuel_factor=fuel_factor,
            fuel_required=fuel_required,
            executable=False,
            reason="insufficient_fuel",
        )

    return NormalMovePlan(
        ship_id=ship.id,
        target_x=target_x,
        target_y=target_y,
        warp=warp,
        distance=distance,
        max_distance=max_distance,
        total_mass=total_mass,
        fuel_factor=fuel_factor,
        fuel_required=fuel_required,
        executable=True,
    )


def execute_full_normal_move(ship: Ship, plan: NormalMovePlan) -> None:
    """Apply a previously validated full-waypoint movement plan in place."""

    if ship.id != plan.ship_id:
        raise ValueError("movement plan belongs to a different ship")
    if not plan.executable:
        raise ValueError(f"movement plan is not executable: {plan.reason}")
    if ship.cargo.neutronium < plan.fuel_required:
        raise ValueError("ship no longer has the fuel required by the movement plan")

    ship.cargo.neutronium -= plan.fuel_required
    ship.x = plan.target_x
    ship.y = plan.target_y
    ship.waypoint_x = plan.target_x
    ship.waypoint_y = plan.target_y
    ship.warp = plan.warp
