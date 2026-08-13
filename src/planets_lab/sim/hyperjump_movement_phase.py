from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from planets_lab.core import GameState
from planets_lab.sim.engine import HostEvent
from planets_lab.sim.hyperjump import HyperjumpPlan, execute_hyperjump, plan_hyperjump
from planets_lab.sim.movement_classifier import classify_movement_intents
from planets_lab.sim.orders import TurnOrders


class UnsupportedHyperjumpMovement(RuntimeError):
    def __init__(self, plan: HyperjumpPlan) -> None:
        self.plan = plan
        super().__init__(
            f"hyperjump movement for ship {plan.ship_id} unsupported: {plan.reason}"
        )


class HyperjumpWarpWellAmbiguityError(RuntimeError):
    pass


def _hyperjump_warp_well_planet_id(
    state: GameState,
    *,
    end_x: int,
    end_y: int,
    excluded_planet_ids: frozenset[int],
) -> int | None:
    matches: list[int] = []
    for planet in state.planets.values():
        if planet.id in excluded_planet_ids:
            continue
        dx = end_x - planet.x
        dy = end_y - planet.y
        if dx * dx + dy * dy < 9:
            matches.append(planet.id)

    if not matches:
        return None
    if len(matches) > 1:
        ids = ", ".join(str(pid) for pid in sorted(matches))
        raise HyperjumpWarpWellAmbiguityError(
            f"hyperjump endpoint ({end_x},{end_y}) is inside multiple warp wells: {ids}"
        )
    return matches[0]


@dataclass(slots=True)
class HyperjumpMovementPhase:
    hyperjump_hull_ids: frozenset[int]
    enable_warp_wells: bool = False
    non_warp_well_planet_ids: frozenset[int] = field(default_factory=frozenset)
    allow_deferred: bool = False
    name: str = field(init=False, default="hyperjump_movement")

    def run(self, state: GameState, orders: TurnOrders, rng: Random) -> list[HostEvent]:
        del orders, rng

        unknown_planet_ids = self.non_warp_well_planet_ids.difference(state.planets)
        if unknown_planet_ids:
            unknown = ", ".join(str(pid) for pid in sorted(unknown_planet_ids))
            raise ValueError(f"warp-well exclusions reference unknown planets: {unknown}")

        classification = classify_movement_intents(state)
        reserved = set(state.metadata.get("movement.reserved_ship_ids", ()))
        events: list[HostEvent] = []

        for ship_id in sorted(classification.special_move_most_ship_ids):
            ship = state.ships[ship_id]

            if ship_id in reserved:
                events.append(
                    HostEvent(
                        phase=self.name,
                        kind="hyperjump_skipped",
                        entity_type="ship",
                        entity_id=ship_id,
                        details=(("reason", "reserved_by_tow"),),
                        message=f"ship={ship_id} hyperjump skipped reason=reserved_by_tow",
                    )
                )
                continue

            plan = plan_hyperjump(
                ship,
                hyperjump_hull_ids=self.hyperjump_hull_ids,
            )

            if not plan.executable:
                if plan.reason == "warp_zero":
                    events.append(
                        HostEvent(
                            phase=self.name,
                            kind="hyperjump_noop",
                            entity_type="ship",
                            entity_id=ship_id,
                            details=(("reason", "warp_zero"),),
                            message=f"ship={ship_id} hyperjump noop reason=warp_zero",
                        )
                    )
                    continue

                if not self.allow_deferred:
                    raise UnsupportedHyperjumpMovement(plan)

                events.append(
                    HostEvent(
                        phase=self.name,
                        kind="hyperjump_deferred",
                        entity_type="ship",
                        entity_id=ship_id,
                        details=(("reason", str(plan.reason)),),
                        message=f"ship={ship_id} hyperjump deferred reason={plan.reason}",
                    )
                )
                continue

            origin = (ship.x, ship.y)
            execute_hyperjump(ship, plan)

            warp_well_planet_id: int | None = None
            if self.enable_warp_wells:
                warp_well_planet_id = _hyperjump_warp_well_planet_id(
                    state,
                    end_x=ship.x,
                    end_y=ship.y,
                    excluded_planet_ids=self.non_warp_well_planet_ids,
                )
                if warp_well_planet_id is not None:
                    planet = state.planets[warp_well_planet_id]
                    ship.x = planet.x
                    ship.y = planet.y

            details = [
                ("from_x", str(origin[0])),
                ("from_y", str(origin[1])),
                ("to_x", str(ship.x)),
                ("to_y", str(ship.y)),
                ("fuel_used", str(plan.fuel_used)),
                ("waypoint_distance", repr(plan.waypoint_distance)),
            ]
            if warp_well_planet_id is not None:
                details.append(("warp_well_planet_id", str(warp_well_planet_id)))

            events.append(
                HostEvent(
                    phase=self.name,
                    kind="hyperjump_moved",
                    entity_type="ship",
                    entity_id=ship_id,
                    details=tuple(details),
                    message=(
                        f"ship={ship_id} hyperjump from=({origin[0]},{origin[1]}) "
                        f"to=({ship.x},{ship.y}) fuel={plan.fuel_used}"
                    ),
                )
            )

        return events
