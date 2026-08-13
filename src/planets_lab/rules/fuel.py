from __future__ import annotations

from math import trunc


def movement_fuel_use(
    *,
    fuel_factor: int,
    total_mass: int,
    distance_traveled: int | float,
    max_distance_per_turn: int,
) -> int:
    """Return normal-movement fuel use using the documented Nu formula.

    The formula truncates total mass to 10-KT units and traveled distance to
    whole light-years before the final truncation. Inputs are deliberately
    explicit: engine/ruleset lookup and movement-mass construction belong to
    separate layers.
    """

    if fuel_factor < 0:
        raise ValueError("fuel_factor must be non-negative")
    if total_mass < 0:
        raise ValueError("total_mass must be non-negative")
    if distance_traveled < 0:
        raise ValueError("distance_traveled must be non-negative")
    if max_distance_per_turn <= 0:
        raise ValueError("max_distance_per_turn must be positive")

    mass_tens = trunc(total_mass / 10)
    distance_ly = trunc(distance_traveled)

    # All values are non-negative, so integer floor division is equivalent to
    # the outer TRUNC in the documented formula and avoids floating error.
    numerator = fuel_factor * mass_tens * distance_ly
    denominator = max_distance_per_turn * 10_000
    return numerator // denominator
