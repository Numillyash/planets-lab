from __future__ import annotations

from collections.abc import Sequence
from math import hypot

from planets_lab.rules.ion_storm import integer_drag_delta
from planets_lab.validation.movement_geometry import MovementSample

from .movement_differential import _warp_well_destination
from .movement_residual_context import (
    StormRecord,
    _navigation_endpoint,
    _storm_expected_category,
)


def _classic_constant_storm_offset(
    storms: Sequence[StormRecord],
    *,
    x: int,
    y: int,
) -> tuple[tuple[int, int] | None, str]:
    """Resolve documented classic ion-storm drag with constant in-circle voltage.

    Classic ion storms have one effective circular area whose published voltage
    applies throughout the circle. This deliberately changes only the voltage
    coverage model; drag distance/vector and multi-storm sequential displacement
    reuse the already validated implementation primitives.
    """

    effective_x = x
    effective_y = y
    total_dx = 0
    total_dy = 0
    affected = False

    roots = sorted(
        (storm for storm in storms if storm.parent_id == 0),
        key=lambda item: item.id,
    )
    for storm in roots:
        if storm.radius <= 0:
            continue
        if hypot(effective_x - storm.x, effective_y - storm.y) >= storm.radius:
            continue
        if storm.voltage < 150.0:
            continue

        affected = True
        if storm.voltage >= 400.0:
            return None, "extreme_voltage"

        dx, dy = integer_drag_delta(storm.warp, storm.heading)
        effective_x += dx
        effective_y += dy
        total_dx += dx
        total_dy += dy

    if not affected:
        return (0, 0), "not_affected"
    return (total_dx, total_dy), "resolved_drag"


def storm_expected_category_for_mode(
    sample: MovementSample,
    *,
    storms: Sequence[StormRecord],
    planets: Sequence[tuple[int, int, int]],
    nuionstorms: bool | None,
) -> tuple[str | None, str]:
    """Classify ion-storm displacement using the game's authoritative storm mode.

    ``nuionstorms=True`` is the cloudy model already implemented by
    ``_storm_expected_category``. ``False`` is the classic constant-voltage
    model. Unknown mode is fail-closed so compiled corpus builds never silently
    reinterpret storm geometry.
    """

    if nuionstorms is True:
        return _storm_expected_category(sample, storms=storms, planets=planets)
    if nuionstorms is None:
        return None, "storm_mode_unknown"

    offset, status = _classic_constant_storm_offset(storms, x=sample.x, y=sample.y)
    if offset is None or offset == (0, 0):
        return None, status

    base = _navigation_endpoint(sample)
    shifted = (base[0] + offset[0], base[1] + offset[1])
    if sample.observed_destination == shifted:
        return "ion_storm_drag", status

    well, ambiguous = _warp_well_destination(
        sample=sample,
        endpoint=shifted,
        planets=planets,
    )
    if ambiguous:
        return None, "warp_well_ambiguous"
    if well is not None and sample.observed_destination == well:
        return "ion_storm_drag_warp_well_match", status
    return None, status
