from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from planets_lab.core import GameState, Ship
from planets_lab.data import NuStaticSpecs
from planets_lab.rules.movement import warp_well_planet_id
from planets_lab.sim.engine import HostEvent
from planets_lab.sim.normal_movement import NormalMovePlan, execute_full_normal_move, plan_full_normal_move
from planets_lab.sim.orders import ShipOrder, TurnOrders


class UnsupportedNormalMovement(RuntimeError):
    def __init__(self, plan: NormalMovePlan) -> None:
        self.plan = plan
        super().__init__(f"ship {plan.ship_id} normal movement is not implemented for reason={plan.reason!r}")


@dataclass(slots=True)
class NormalMovementPhase:
    specs: NuStaticSpecs
    eligible_ship_ids: frozenset[int]
    gravitonic_hull_ids: frozenset[int] = field(default_factory=frozenset)
    allow_deferred: bool = False
    enable_expanded_movement: bool = False
    enable_warp_wells: bool = False
    non_warp_well_planet_ids: frozenset[int] = field(default_factory=frozenset)
    name: str = field(init=False, default="normal_movement")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del rng

        unknown_ids = self.eligible_ship_ids.difference(state.ships)
        if unknown_ids:
            unknown = ", ".join(str(ship_id) for ship_id in sorted(unknown_ids))
            raise ValueError(f"normal movement eligibility references unknown ships: {unknown}")

        unknown_planet_ids = self.non_warp_well_planet_ids.difference(state.planets)
        if unknown_planet_ids:
            unknown = ", ".join(str(planet_id) for planet_id in sorted(unknown_planet_ids))
            raise ValueError(f"warp-well exclusions reference unknown planets: {unknown}")

        ship_orders = self._ship_orders(orders)
        events: list[HostEvent] = []

        planet_tuples = tuple(
            (planet.id, planet.x, planet.y)
            for planet in state.planets.values()
        )

        for ship_id in sorted(self.eligible_ship_ids):
            ship = state.ships[ship_id]
            target_x, target_y, warp = self._apply_navigation_order(ship, ship_orders.get(ship_id))
            plan = plan_full_normal_move(
                ship,
                self.specs,
                target_x=target_x,
                target_y=target_y,
                warp=warp,
                gravitonic=ship.hull_id in self.gravitonic_hull_ids,
                allow_partial=self.enable_expanded_movement,
                allow_fuel_proration=self.enable_expanded_movement,
            )

            if plan.executable:
                origin = (ship.x, ship.y)
                execute_full_normal_move(ship, plan)

                warp_well_planet = None
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

                if origin == (ship.x, ship.y):
                    events.append(HostEvent(
                        phase=self.name,
                        kind="ship_noop",
                        entity_type="ship",
                        entity_id=ship.id,
                        details=(("x", str(ship.x)), ("y", str(ship.y)), ("warp", str(warp)), ("fuel_used", "0")),
                        message=f"ship={ship.id} position=({ship.x},{ship.y}) warp={warp} fuel=0",
                    ))
                else:
                    details = [
                        ("from_x", str(origin[0])), ("from_y", str(origin[1])),
                        ("to_x", str(ship.x)), ("to_y", str(ship.y)),
                        ("target_x", str(plan.target_x)), ("target_y", str(plan.target_y)),
                        ("warp", str(warp)), ("distance", repr(plan.distance)),
                        ("fuel_used", str(plan.fuel_used)), ("movement_mass", str(plan.total_mass)),
                        ("partial", str(plan.partial).lower()),
                        ("fuel_limited", str(plan.fuel_limited).lower()),
                    ]
                    if warp_well_planet is not None:
                        details.append(("warp_well_planet_id", str(warp_well_planet)))

                    events.append(HostEvent(
                        phase=self.name,
                        kind="ship_moved",
                        entity_type="ship",
                        entity_id=ship.id,
                        details=tuple(details),
                        message=f"ship={ship.id} from=({origin[0]},{origin[1]}) to=({ship.x},{ship.y}) warp={warp} fuel={plan.fuel_used}",
                    ))
                continue

            if plan.reason == "warp_zero":
                events.append(HostEvent(
                    phase=self.name,
                    kind="ship_noop",
                    entity_type="ship",
                    entity_id=ship.id,
                    details=(("x", str(ship.x)), ("y", str(ship.y)), ("warp", "0"), ("reason", "warp_zero")),
                    message=f"ship={ship.id} position=({ship.x},{ship.y}) warp=0 reason=warp_zero",
                ))
                continue

            if not self.allow_deferred:
                raise UnsupportedNormalMovement(plan)

            events.append(HostEvent(
                phase=self.name,
                kind="ship_deferred",
                entity_type="ship",
                entity_id=ship.id,
                details=(
                    ("x", str(ship.x)), ("y", str(ship.y)),
                    ("target_x", str(target_x)), ("target_y", str(target_y)),
                    ("warp", str(warp)), ("reason", str(plan.reason)),
                ),
                message=f"ship={ship.id} position=({ship.x},{ship.y}) target=({target_x},{target_y}) warp={warp} reason={plan.reason}",
            ))

        return events

    @staticmethod
    def _ship_orders(orders: TurnOrders) -> dict[int, ShipOrder]:
        result: dict[int, ShipOrder] = {}
        for player_orders in orders.by_player.values():
            for ship_order in player_orders.ship_orders:
                result[ship_order.ship_id] = ship_order
        return result

    @staticmethod
    def _apply_navigation_order(ship: Ship, order: ShipOrder | None) -> tuple[int, int, int]:
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
