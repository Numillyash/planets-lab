from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from planets_lab.core import GameState
from planets_lab.data import NuStaticSpecs
from planets_lab.rules.movement import warp_well_planet_id
from planets_lab.sim.engine import HostEvent
from planets_lab.sim.movement_classifier import classify_movement_intents
from planets_lab.sim.normal_movement import (
    NormalMovePlan,
    execute_full_normal_move,
    plan_full_normal_move,
)
from planets_lab.sim.orders import TurnOrders


class UnsupportedInterceptMovement(RuntimeError):
    def __init__(self, ship_id: int, reason: str, plan: NormalMovePlan | None = None) -> None:
        self.ship_id = ship_id
        self.reason = reason
        self.plan = plan
        super().__init__(f"intercept movement for ship {ship_id} unsupported: {reason}")


@dataclass(slots=True)
class InterceptMovementPhase:
    """Move Intercept ships after Move Most toward the target's current position.

    This phase intentionally implements only the ordinary intercept geometry.
    It consumes the target coordinates from the state as they exist when the
    phase runs, so a preceding Move Most phase is naturally reflected.
    """

    specs: NuStaticSpecs
    gravitonic_hull_ids: frozenset[int] = field(default_factory=frozenset)
    enable_expanded_movement: bool = False
    enable_warp_wells: bool = False
    non_warp_well_planet_ids: frozenset[int] = field(default_factory=frozenset)
    allow_deferred: bool = False
    name: str = field(init=False, default="intercept_movement")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng

        classification = classify_movement_intents(state)
        reserved = set(state.metadata.get("movement.reserved_ship_ids", ()))
        events: list[HostEvent] = []

        unknown_planet_ids = self.non_warp_well_planet_ids.difference(state.planets)
        if unknown_planet_ids:
            unknown = ", ".join(str(pid) for pid in sorted(unknown_planet_ids))
            raise ValueError(f"warp-well exclusions reference unknown planets: {unknown}")

        planet_tuples = tuple((p.id, p.x, p.y) for p in state.planets.values())

        for ship_id in sorted(classification.intercept_ship_ids):
            ship = state.ships[ship_id]

            if ship_id in reserved:
                events.append(
                    HostEvent(
                        phase=self.name,
                        kind="intercept_skipped",
                        entity_type="ship",
                        entity_id=ship_id,
                        details=(("reason", "reserved_by_tow"),),
                        message=f"ship={ship_id} intercept skipped reason=reserved_by_tow",
                    )
                )
                continue

            target_id = ship.mission1_target_id
            if target_id is None or target_id == ship_id or target_id not in state.ships:
                if not self.allow_deferred:
                    raise UnsupportedInterceptMovement(ship_id, "invalid_target")
                events.append(
                    HostEvent(
                        phase=self.name,
                        kind="intercept_deferred",
                        entity_type="ship",
                        entity_id=ship_id,
                        details=(
                            ("target_ship_id", str(target_id)),
                            ("reason", "invalid_target"),
                        ),
                        message=f"ship={ship_id} intercept deferred reason=invalid_target",
                    )
                )
                continue

            target = state.ships[target_id]
            origin = (ship.x, ship.y)
            target_position = (target.x, target.y)

            plan = plan_full_normal_move(
                ship,
                self.specs,
                target_x=target.x,
                target_y=target.y,
                warp=ship.warp,
                gravitonic=ship.hull_id in self.gravitonic_hull_ids,
                allow_partial=self.enable_expanded_movement,
                allow_fuel_proration=self.enable_expanded_movement,
            )

            if not plan.executable:
                if plan.reason == "warp_zero":
                    events.append(
                        HostEvent(
                            phase=self.name,
                            kind="intercept_noop",
                            entity_type="ship",
                            entity_id=ship_id,
                            details=(
                                ("target_ship_id", str(target_id)),
                                ("reason", "warp_zero"),
                            ),
                            message=f"ship={ship_id} intercept noop reason=warp_zero",
                        )
                    )
                    continue
                if not self.allow_deferred:
                    raise UnsupportedInterceptMovement(ship_id, str(plan.reason), plan)
                events.append(
                    HostEvent(
                        phase=self.name,
                        kind="intercept_deferred",
                        entity_type="ship",
                        entity_id=ship_id,
                        details=(
                            ("target_ship_id", str(target_id)),
                            ("reason", str(plan.reason)),
                        ),
                        message=f"ship={ship_id} intercept deferred reason={plan.reason}",
                    )
                )
                continue

            execute_full_normal_move(ship, plan)

            warp_well_planet: int | None = None
            if self.enable_warp_wells:
                warp_well_planet = warp_well_planet_id(
                    origin_x=origin[0],
                    origin_y=origin[1],
                    end_x=ship.x,
                    end_y=ship.y,
                    movement_warp=plan.warp,
                    planets=planet_tuples,
                    excluded_planet_ids=self.non_warp_well_planet_ids,
                )
                if warp_well_planet is not None:
                    planet = state.planets[warp_well_planet]
                    ship.x = planet.x
                    ship.y = planet.y

            details = [
                ("target_ship_id", str(target_id)),
                ("target_x", str(target_position[0])),
                ("target_y", str(target_position[1])),
                ("from_x", str(origin[0])),
                ("from_y", str(origin[1])),
                ("to_x", str(ship.x)),
                ("to_y", str(ship.y)),
                ("fuel_used", str(plan.fuel_used)),
                ("partial", str(plan.partial).lower()),
                ("fuel_limited", str(plan.fuel_limited).lower()),
            ]
            if warp_well_planet is not None:
                details.append(("warp_well_planet_id", str(warp_well_planet)))

            events.append(
                HostEvent(
                    phase=self.name,
                    kind="intercept_moved",
                    entity_type="ship",
                    entity_id=ship_id,
                    details=tuple(details),
                    message=(
                        f"ship={ship_id} intercepted={target_id} "
                        f"to=({ship.x},{ship.y}) fuel={plan.fuel_used}"
                    ),
                )
            )

        return events
