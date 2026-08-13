from __future__ import annotations

from dataclasses import dataclass
from math import cos, hypot, radians, sin
from collections.abc import Iterable


CLASS_4_MIN_VOLTAGE = 150.0
DRAG_SPEED_FACTOR = 0.75


@dataclass(frozen=True, slots=True)
class IonStormCircle:
    id: int
    x: float
    y: float
    radius: float
    voltage: float
    warp: int
    heading: float
    parent_id: int = 0


def compass_vector(distance: float, heading_degrees: float) -> tuple[float, float]:
    """Return `(dx, dy)` for Planets compass headings.

    Headings are measured clockwise from north: 0° is +Y and 90° is +X.
    Values outside 0..359 are normalized modulo 360.
    """

    angle = radians(heading_degrees % 360.0)
    return distance * sin(angle), distance * cos(angle)


def storm_nominal_distance(warp: int) -> float:
    if not isinstance(warp, int) or isinstance(warp, bool):
        raise TypeError("warp must be an integer")
    if not 0 <= warp <= 9:
        raise ValueError("warp must be between 0 and 9")
    return float(warp * warp)


def documented_drag_distance(warp: int) -> float:
    """Class-4/5 ship drag distance: 75% of the storm's speed."""

    return DRAG_SPEED_FACTOR * storm_nominal_distance(warp)


def storm_movement_vector(warp: int, heading_degrees: float) -> tuple[float, float]:
    return compass_vector(storm_nominal_distance(warp), heading_degrees)


def drag_vector(warp: int, heading_degrees: float) -> tuple[float, float]:
    return compass_vector(documented_drag_distance(warp), heading_degrees)


def translated_circle(circle: IonStormCircle) -> IonStormCircle:
    """Continuous pre-interaction position after the storm movement substep.

    Host later recalculates heading/voltage/radius before the ship drag substep;
    this helper deliberately changes only the center so validation can isolate
    the documented ordering effect without guessing the undocumented updates.
    """

    dx, dy = storm_movement_vector(circle.warp, circle.heading)
    return IonStormCircle(
        id=circle.id,
        x=circle.x + dx,
        y=circle.y + dy,
        radius=circle.radius,
        voltage=circle.voltage,
        warp=circle.warp,
        heading=circle.heading,
        parent_id=circle.parent_id,
    )


def circle_voltage_at(circle: IonStormCircle, x: float, y: float) -> float:
    """Return the cloudy-circle contribution at a point.

    Planets.nu documents voltage as linear with radius: full voltage at the
    center and zero at the edge. Outside the circle the contribution is zero.
    """

    if circle.radius <= 0:
        return 0.0
    distance = hypot(x - circle.x, y - circle.y)
    if distance >= circle.radius:
        return 0.0
    return circle.voltage * (1.0 - distance / circle.radius)


def local_voltage(circles: Iterable[IonStormCircle], x: float, y: float) -> float:
    """Sum overlapping cloudy-ion-storm circle contributions at a point."""

    return sum(circle_voltage_at(circle, x, y) for circle in circles)


def is_class_4_or_higher(circles: Iterable[IonStormCircle], x: float, y: float) -> bool:
    return local_voltage(circles, x, y) >= CLASS_4_MIN_VOLTAGE
