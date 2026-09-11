from __future__ import annotations

from math import hypot
from pathlib import Path
from typing import Any

import tow_finite_fuel_break_independent_movement_audit as base


VALID_DIRECTIONS = {
    "same_line_route",
    "same_line_beyond_waypoint",
    "same_line_backward",
    "off_route",
}


def _xy(value: Any, field: str) -> tuple[int, int]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError(f"{field} is not an xy pair: {value!r}")
    return int(value[0]), int(value[1])


def route_direction_from_resolution_case(case: dict[str, Any]) -> str:
    """Recover the residual route-shape label dropped by the resolution gate.

    The passenger-Chunnel context log carried ``direction``, but the next
    resolution log did not preserve it. For backward-compatible consumption of
    already completed resolution logs, recompute the same residual-shape class
    from origin -> Tow direct geometry and origin -> factual destination.

    The direct geometry lies on the tower's intended route, so this reproduces
    the same-line/off-route test used by the earlier residual-shape audit while
    avoiding any new Host-mechanics inference.
    """

    existing = case.get("direction")
    if existing in VALID_DIRECTIONS:
        return str(existing)

    origin = _xy(case.get("origin"), "origin")
    geometry = _xy(case.get("geometry"), "geometry")
    observed = _xy(case.get("observed"), "observed")

    rx = geometry[0] - origin[0]
    ry = geometry[1] - origin[1]
    route_len = hypot(rx, ry)
    ox = observed[0] - origin[0]
    oy = observed[1] - origin[1]

    if route_len <= 1e-9:
        return "off_route" if hypot(ox, oy) > 0.75 else "same_line_route"

    cross = (rx * oy - ry * ox) / route_len
    observed_along = (ox * rx + oy * ry) / route_len

    if abs(cross) <= 0.75:
        if observed_along > route_len + 0.75:
            return "same_line_beyond_waypoint"
        if observed_along < -0.75:
            return "same_line_backward"
        return "same_line_route"
    return "off_route"


_original_resolution_cases = base._resolution_cases


def _resolution_cases_with_direction(path: Path):
    expected, cases = _original_resolution_cases(path)
    enriched = []
    for item in cases:
        row = dict(item)
        row["direction"] = route_direction_from_resolution_case(row)
        enriched.append(row)
    return expected, tuple(enriched)


base._resolution_cases = _resolution_cases_with_direction


def main() -> int:
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
