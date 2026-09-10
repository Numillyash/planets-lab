from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_initial_standard_target_residual_audit import (  # noqa: E402
    TARGETS,
    _remaining_fuel_from_plan,
)


def test_remaining_fuel_can_resolve_exact_zero() -> None:
    plan = SimpleNamespace(executable=True, fuel_used=25)
    assert _remaining_fuel_from_plan({"neutronium": 25}, plan) == 0


def test_remaining_fuel_preserves_positive_remainder() -> None:
    plan = SimpleNamespace(executable=True, fuel_used=25)
    assert _remaining_fuel_from_plan({"neutronium": 40}, plan) == 15


def test_remaining_fuel_fails_closed_for_unknown_or_invalid_plan() -> None:
    assert _remaining_fuel_from_plan({}, SimpleNamespace(executable=True, fuel_used=1)) is None
    assert _remaining_fuel_from_plan(
        {"neutronium": 5}, SimpleNamespace(executable=False, fuel_used=0)
    ) is None
    assert _remaining_fuel_from_plan(
        {"neutronium": 5}, SimpleNamespace(executable=True, fuel_used=6)
    ) is None


def test_target_population_is_exactly_the_two_broad_runtime_residuals() -> None:
    assert {
        (
            int(row["game_id"]),
            int(row["battle_turn"]),
            int(row["active_ship_id"]),
            int(row["extra_target_ship_id"]),
            int(row["factual_target_ship_id"]),
        )
        for row in TARGETS
    } == {
        (360690, 83, 264, 98, 190),
        (511506, 94, 496, 202, 332),
    }
