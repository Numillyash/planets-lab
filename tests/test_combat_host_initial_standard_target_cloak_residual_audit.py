from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_initial_standard_target_cloak_residual_audit import (  # noqa: E402
    _basic_cloak_fuel_cost,
    _boolish,
    _super_spy_cloak_signature,
)


def test_basic_cloak_fuel_cost_uses_documented_minimum() -> None:
    assert _basic_cloak_fuel_cost(120) == 6
    assert _basic_cloak_fuel_cost(50) == 5


def test_basic_cloak_fuel_cost_fails_closed_for_invalid_mass() -> None:
    assert _basic_cloak_fuel_cost(None) is None
    assert _basic_cloak_fuel_cost(-1) is None


def test_super_spy_cloak_signature_requires_bird_mission9_and_cloak_hull() -> None:
    assert _super_spy_cloak_signature(race_id=3, mission=9, hull_can_cloak=True) is True
    assert _super_spy_cloak_signature(race_id=3, mission=9, hull_can_cloak=False) is False
    assert _super_spy_cloak_signature(race_id=5, mission=9, hull_can_cloak=True) is False
    assert _super_spy_cloak_signature(race_id=3, mission=3, hull_can_cloak=True) is False


def test_super_spy_cloak_signature_preserves_unknowns() -> None:
    assert _super_spy_cloak_signature(race_id=None, mission=9, hull_can_cloak=True) is None
    assert _super_spy_cloak_signature(race_id=3, mission=None, hull_can_cloak=True) is None
    assert _super_spy_cloak_signature(race_id=3, mission=9, hull_can_cloak=None) is None


def test_boolish_accepts_archived_boolean_shapes() -> None:
    assert _boolish(True) is True
    assert _boolish(1) is True
    assert _boolish("true") is True
    assert _boolish(False) is False
    assert _boolish(0) is False
    assert _boolish("0") is False
    assert _boolish("unknown") is None
