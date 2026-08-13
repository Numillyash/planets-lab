from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from planets_lab.core import GameState
from planets_lab.data import NuStaticSpecs
from planets_lab.rules import ship_movement_mass
from planets_lab.rules.movement import warp_well_planet_id
from planets_lab.sim.engine import HostEvent
from planets_lab.sim.normal_movement import NormalMovePlan, execute_full_normal_move, plan_full_normal_move
from planets_lab.sim.orders import TurnOrders
from planets_lab.sim.tow import resolve_tow_locks


class UnsupportedTowMovement(RuntimeError):
    def __init__(self, plan: NormalMovePlan) -> None:
        self.plan = plan
        super().__init__(f"tow movement for ship {plan.ship_id} unsupported: {plan.reason}")


@dataclass(slots=True)
class TowMovementPhase:
    specs: NuStaticSpecs
    gravitonic_hull_ids: frozenset[int] = field(default_factory=frozenset)
    enable_expanded_movement: bool = False
    enable_warp_wells: bool = False
    excluded_warp_well_planet_ids: frozenset[int] = field(default_factory=frozenset)
    allow_single_engine_tow: bool = False
    allow_deferred: bool = False
    name: str = field(init=False, default="tow_movement")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng
        resolution = resolve_tow_locks(
            state,
            self.specs,
            gravitonic_hull_ids=self.gravitonic_hull_ids,
            allow_single_engine_tow=self.allow_single_engine_tow,
        )
        events: list[HostEvent] = []
        bumped: set[int] = set()
        reserved: set[int] = set()

        for attempt in resolution.attempts:
            if not attempt.locked:
                bumped.add(attempt.tower_ship_id)
                events.append(HostEvent(
                    phase=self.name,
                    kind="tow_failed",
                    entity_type="ship",
                    entity_id=attempt.tower_ship_id,
                    details=(("target_ship_id", str(attempt.target_ship_id)), ("reason", str(attempt.reason))),
                    message=f"ship={attempt.tower_ship_id} tow failed reason={attempt.reason}",
                ))
                continue

            tower = state.ships[attempt.tower_ship_id]
            target = state.ships[attempt.target_ship_id]
            target_waypoint = (target.waypoint_x, target.waypoint_y)
            combined_mass = ship_movement_mass(tower, self.specs) + ship_movement_mass(target, self.specs)
            target_x = tower.waypoint_x if tower.waypoint_x is not None else tower.x
            target_y = tower.waypoint_y if tower.waypoint_y is not None else tower.y
            plan = plan_full_normal_move(
                tower,
                self.specs,
                target_x=target_x,
                target_y=target_y,
                warp=tower.warp,
                gravitonic=tower.hull_id in self.gravitonic_hull_ids,
                allow_partial=self.enable_expanded_movement,
                allow_fuel_proration=self.enable_expanded_movement,
                movement_mass_override=combined_mass,
            )

            if not plan.executable:
                if not self.allow_deferred:
                    raise UnsupportedTowMovement(plan)
                reserved.update((tower.id, target.id))
                events.append(HostEvent(
                    phase=self.name,
                    kind="tow_deferred",
                    entity_type="ship",
                    entity_id=tower.id,
                    details=(("target_ship_id", str(target.id)), ("reason", str(plan.reason))),
                    message=f"ship={tower.id} tow deferred reason={plan.reason}",
                ))
                continue

            origin = (tower.x, tower.y)
            execute_full_normal_move(tower, plan)

            warpwell_planet_id: int | None = None
            if self.enable_warp_wells:
                warpwell_planet_id = warp_well_planet_id(
                    origin_x=origin[0],
                    origin_y=origin[1],
                    end_x=tower.x,
                    end_y=tower.y,
                    movement_warp=plan.warp,
                    planets=((p.id, p.x, p.y) for p in state.planets.values()),
                    excluded_planet_ids=self.excluded_warp_well_planet_ids,
                )
                if warpwell_planet_id is not None:
                    planet = state.planets[warpwell_planet_id]
                    tower.x, tower.y = planet.x, planet.y

            target.x, target.y = tower.x, tower.y
            target.warp = 0
            target.waypoint_x, target.waypoint_y = target_waypoint
            reserved.update((tower.id, target.id))

            events.append(HostEvent(
                phase=self.name,
                kind="tow_moved",
                entity_type="ship",
                entity_id=tower.id,
                details=(
                    ("target_ship_id", str(target.id)),
                    ("from_x", str(origin[0])), ("from_y", str(origin[1])),
                    ("to_x", str(tower.x)), ("to_y", str(tower.y)),
                    ("fuel_used", str(plan.fuel_used)),
                    ("movement_mass", str(combined_mass)),
                    ("warpwell_planet_id", str(warpwell_planet_id)),
                ),
                message=f"ship={tower.id} towed={target.id} to=({tower.x},{tower.y}) fuel={plan.fuel_used}",
            ))

        state.metadata["movement.bumped_to_move_most_ship_ids"] = tuple(sorted(bumped))
        state.metadata["movement.reserved_ship_ids"] = tuple(sorted(reserved))
        return events
