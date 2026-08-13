from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from random import Random

from planets_lab.core import GameState, IonStorm
from planets_lab.rules.ion_storm import (
    IonStormCircle,
    integer_drag_delta,
    local_voltage,
)
from planets_lab.sim.engine import HostEvent
from planets_lab.sim.movement_classifier import classify_movement_intents
from planets_lab.sim.orders import TurnOrders


DRAG_OFFSETS_METADATA_KEY = "movement.pre_move_offsets"


class UnsupportedResolvedIonStormEffect(RuntimeError):
    pass


def _circle(storm: IonStorm) -> IonStormCircle:
    return IonStormCircle(
        id=storm.id,
        x=float(storm.x),
        y=float(storm.y),
        radius=float(storm.radius),
        voltage=float(storm.voltage),
        warp=storm.warp,
        heading=float(storm.heading),
        parent_id=storm.parent_id,
    )


def _clusters(
    storms: Iterable[IonStorm],
) -> tuple[tuple[IonStorm, tuple[IonStormCircle, ...]], ...]:
    records = tuple(storms)
    roots = tuple(
        sorted(
            (storm for storm in records if storm.parent_id == 0),
            key=lambda item: item.id,
        )
    )
    result: list[tuple[IonStorm, tuple[IonStormCircle, ...]]] = []
    for root in roots:
        members = [root]
        members.extend(
            sorted(
                (storm for storm in records if storm.parent_id == root.id),
                key=lambda item: item.id,
            )
        )
        result.append((root, tuple(_circle(storm) for storm in members)))
    return tuple(result)


@dataclass(slots=True)
class ResolvedIonStormDragPhase:
    """Compute pre-movement storm displacement from resolved storm state.

    NuHost evolves each storm before it affects ships. The exact stochastic
    storm-evolution algorithm is intentionally not guessed here. This phase
    therefore accepts the already-resolved post-evolution storm snapshot, as
    used by differential validation, and records zero-fuel displacement vectors
    for ordinary Move-Most ships.

    NormalMovementPhase consumes those vectors after computing the ship's own
    movement vector from its pre-storm position. That reproduces the observed
    NuHost endpoint while preserving the documented Host ordering.
    """

    resolved_storms: tuple[IonStorm, ...]
    eligible_ship_ids: frozenset[int] | None = None
    fail_on_extreme_voltage: bool = True
    name: str = field(init=False, default="ion_storm_drag_resolved")

    def run(
        self,
        state: GameState,
        orders: TurnOrders,
        rng: Random,
    ) -> list[HostEvent]:
        del orders, rng

        resolved = {storm.id: storm for storm in self.resolved_storms}
        if len(resolved) != len(self.resolved_storms):
            raise ValueError("resolved ion storm ids must be unique")

        classification = classify_movement_intents(state)
        ordinary_ids = classification.move_most_candidate_ship_ids
        requested_ids = self.eligible_ship_ids or frozenset(state.ships)
        unknown = requested_ids.difference(state.ships)
        if unknown:
            raise ValueError(
                f"ion storm eligibility references unknown ships: {sorted(unknown)}"
            )

        offsets: dict[int, tuple[int, int]] = {}
        events: list[HostEvent] = []
        clusters = _clusters(resolved.values())

        for ship_id in sorted(requested_ids):
            ship = state.ships[ship_id]
            effective_x = ship.x
            effective_y = ship.y
            total_dx = 0
            total_dy = 0

            for root, circles in clusters:
                voltage = local_voltage(circles, effective_x, effective_y)
                if voltage < 150.0:
                    continue
                if self.fail_on_extreme_voltage and voltage >= 400.0:
                    raise UnsupportedResolvedIonStormEffect(
                        f"ship {ship_id} is inside extreme ion storm "
                        f"{root.id} at {voltage:.3f} meV"
                    )
                if ship_id not in ordinary_ids:
                    raise UnsupportedResolvedIonStormEffect(
                        "ion-storm displacement for non-ordinary movement "
                        f"ship {ship_id} is not integrated yet"
                    )

                dx, dy = integer_drag_delta(root.warp, root.heading)
                effective_x += dx
                effective_y += dy
                total_dx += dx
                total_dy += dy

                events.append(
                    HostEvent(
                        phase=self.name,
                        kind="ship_storm_displacement",
                        entity_type="ship",
                        entity_id=ship_id,
                        details=(
                            ("storm_id", str(root.id)),
                            ("voltage", f"{voltage:.6f}"),
                            ("warp", str(root.warp)),
                            ("heading", str(root.heading)),
                            ("dx", str(dx)),
                            ("dy", str(dy)),
                        ),
                        message=(
                            f"ship={ship_id} storm={root.id} "
                            f"voltage={voltage:.3f} displacement=({dx},{dy})"
                        ),
                    )
                )

            if total_dx or total_dy:
                offsets[ship_id] = (total_dx, total_dy)

        state.metadata[DRAG_OFFSETS_METADATA_KEY] = offsets
        state.ion_storms = resolved
        return events
