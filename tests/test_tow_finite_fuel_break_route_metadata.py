from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = ROOT / "tools" / "diagnostics"
if str(DIAGNOSTICS) not in sys.path:
    sys.path.insert(0, str(DIAGNOSTICS))

from tow_finite_fuel_break_independent_movement_compat_audit import (  # noqa: E402
    route_direction_from_resolution_case,
)


def test_route_direction_recovers_same_line_route() -> None:
    case = {
        "origin": (100, 100),
        "geometry": (140, 100),
        "observed": (120, 100),
    }
    assert route_direction_from_resolution_case(case) == "same_line_route"


def test_route_direction_recovers_off_route() -> None:
    case = {
        "origin": (100, 100),
        "geometry": (140, 100),
        "observed": (120, 110),
    }
    assert route_direction_from_resolution_case(case) == "off_route"


def test_existing_direction_is_preserved() -> None:
    case = {
        "direction": "same_line_backward",
        "origin": (100, 100),
        "geometry": (140, 100),
        "observed": (120, 110),
    }
    assert route_direction_from_resolution_case(case) == "same_line_backward"
