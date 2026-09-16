from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_bird_super_spy_production_effective_state_audit import (  # noqa: E402
    _production_candidate,
)


def _candidate(**overrides):
    values = {
        "race_id": 3,
        "mission": 9,
        "hull_can_cloak": True,
        "advanced_cloak": False,
        "damage": 0,
        "fuel_before": 37,
        "reference_cost": 5,
        "reference_move_resolved": True,
        "reference_remaining_fuel": 29,
        "prior_iscloaked": True,
        "ion_start_inside": False,
        "planet_ion_pulse_possible": False,
        "loki_start_exposed": False,
        "active_glory_colocated": False,
    }
    values.update(overrides)
    return _production_candidate(**values)


def test_production_wrapper_supports_focused_ordinary_super_spy_state() -> None:
    state, reason = _candidate()
    assert state is True
    assert reason == "documented_super_spy_ordinary_cloak_supported"


def test_production_wrapper_preserves_known_uncloaked_cases() -> None:
    assert _candidate(damage=1) == (False, "damage_blocks_cloak")
    assert _candidate(fuel_before=5) == (False, "fuel_not_safely_above_reference_cost")


def test_production_wrapper_fails_closed_on_dynamic_decloak_context() -> None:
    state, reason = _candidate(loki_start_exposed=True)
    assert state is None
    assert reason == "loki_context_present"


def test_production_wrapper_keeps_advanced_cloak_unresolved() -> None:
    state, reason = _candidate(advanced_cloak=True)
    assert state is None
    assert reason == "advanced_cloak_unresolved"
