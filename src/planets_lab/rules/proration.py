from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FuelProration:
    """Documented Nu insufficient-fuel distance ratio.

    This object deliberately stops at continuous distance. Conversion of that
    distance into integer X/Y coordinates is a separate movement-geometry rule
    and must be differential-tested before it is used by HostEngine.
    """

    requested_distance: float
    fuel_available: int
    fuel_required: int
    ratio: float
    distance: float


def prorate_waypoint_distance(
    *,
    requested_distance: int | float,
    fuel_available: int,
    fuel_required: int,
) -> FuelProration:
    """Return Planets.nu's documented insufficient-fuel travel distance.

    Nu prorates against the distance to the current waypoint:

        actual distance = waypoint distance * fuel available / fuel required

    The function does not project the resulting continuous distance onto the
    integer coordinate grid; that rounding rule is intentionally separate.
    """

    if requested_distance < 0:
        raise ValueError("requested_distance must be non-negative")
    if fuel_available < 0:
        raise ValueError("fuel_available must be non-negative")
    if fuel_required <= 0:
        raise ValueError("fuel_required must be positive")
    if fuel_available > fuel_required:
        raise ValueError(
            "fuel_available must not exceed fuel_required for proration"
        )

    ratio = fuel_available / fuel_required
    distance = float(requested_distance) * ratio

    return FuelProration(
        requested_distance=float(requested_distance),
        fuel_available=fuel_available,
        fuel_required=fuel_required,
        ratio=ratio,
        distance=distance,
    )
