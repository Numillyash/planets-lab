from __future__ import annotations

from collections.abc import Iterable


WARP_WELL_RADIUS_SQUARED = 9


class WarpWellAmbiguityError(RuntimeError):
    pass


def max_nominal_distance(warp: int, *, gravitonic: bool = False) -> int:
    """Return the documented maximum nominal distance for one movement turn."""

    if not isinstance(warp, int) or isinstance(warp, bool):
        raise TypeError("warp must be an integer")
    if not 0 <= warp <= 9:
        raise ValueError("warp must be between 0 and 9")

    distance = warp * warp
    return distance * 2 if gravitonic else distance


def warp_well_planet_id(
    *,
    origin_x: int,
    origin_y: int,
    end_x: int,
    end_y: int,
    movement_warp: int,
    planets: Iterable[tuple[int, int, int]],
    excluded_planet_ids: frozenset[int] = frozenset(),
) -> int | None:
    """Resolve the ordinary planetary warp well affecting an endpoint.

    `planets` contains `(planet_id, x, y)` tuples. Non-moving ships and ships
    moving at Warp 1 or slower are unaffected. Planetoids should be supplied in
    `excluded_planet_ids` because they do not have warp wells.
    """

    if (origin_x, origin_y) == (end_x, end_y) or movement_warp <= 1:
        return None

    matches: list[int] = []
    for planet_id, planet_x, planet_y in planets:
        if planet_id in excluded_planet_ids:
            continue
        dx = end_x - planet_x
        dy = end_y - planet_y
        if dx * dx + dy * dy <= WARP_WELL_RADIUS_SQUARED:
            matches.append(planet_id)

    if not matches:
        return None
    if len(matches) > 1:
        ids = ", ".join(str(planet_id) for planet_id in sorted(matches))
        raise WarpWellAmbiguityError(
            f"endpoint ({end_x},{end_y}) is inside multiple warp wells: {ids}"
        )
    return matches[0]
