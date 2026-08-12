from __future__ import annotations


def max_nominal_distance(warp: int, *, gravitonic: bool = False) -> int:
    """Return the documented maximum nominal distance for one movement turn.

    Standard movement uses warp**2 light-years. A Gravitonic Accelerator doubles
    that maximum. This helper intentionally does not model fuel limits,
    overdrive efficiency, warp wells, towing, intercept or special movement.
    """

    if not isinstance(warp, int) or isinstance(warp, bool):
        raise TypeError("warp must be an integer")
    if not 0 <= warp <= 9:
        raise ValueError("warp must be between 0 and 9")

    distance = warp * warp
    return distance * 2 if gravitonic else distance
