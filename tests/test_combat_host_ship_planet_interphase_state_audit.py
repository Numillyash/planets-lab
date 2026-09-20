from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_ship_planet_interphase_state_audit import _direction  # noqa: E402


def test_direction_classifies_carry_and_changes() -> None:
    assert _direction(10, 10) == "same"
    assert _direction(10, 7) == "decrease"
    assert _direction(10, 12) == "increase"


def test_direction_fails_closed_for_unknown_values() -> None:
    assert _direction(None, 10) == "unknown"
    assert _direction(10, None) == "unknown"
    assert _direction(True, 1) == "unknown"
