from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_mutable_ship_queue_audit import _mutation_projection  # noqa: E402


def _previous(**terminal_overrides: object) -> dict[str, object]:
    terminal: dict[str, object] = {
        "shield": 40,
        "damage": 10,
        "crew": 80,
        "torpedoes": 7,
        "fighters": 0,
        "destroyed": False,
        "captured": False,
    }
    terminal.update(terminal_overrides)
    return {
        "game_id": 1,
        "turn": 2,
        "vcr_id": 3,
        "ship_id": 10,
        "hull_id": 20,
        "race_id": 2,
        "terminal": terminal,
    }


def test_survivor_projection_keeps_ship_active() -> None:
    result = _mutation_projection(_previous())
    assert result["resolved"] is True
    assert result["ship_remains_active"] is True
    assert result["carried_ship_ids"] == [10]
    assert result["removed_ship_ids"] == []


def test_destroyed_projection_removes_ship() -> None:
    result = _mutation_projection(
        _previous(destroyed=True, shield=0, damage=100, crew=0)
    )
    assert result["resolved"] is True
    assert result["ship_remains_active"] is False
    assert result["removed_ship_ids"] == [10]


def test_captured_projection_fails_closed_and_keeps_baseline_membership() -> None:
    result = _mutation_projection(_previous(captured=True, crew=0))
    assert result["resolved"] is None
    assert result["ship_remains_active"] is True
    assert "10:capture_branch_unresolved" in result["unresolved_reasons"]


def test_unknown_terminal_flag_is_unresolved_not_error() -> None:
    previous = _previous()
    terminal = dict(previous["terminal"])
    terminal.pop("destroyed")
    previous["terminal"] = terminal
    result = _mutation_projection(previous)
    assert result["status"] == "unresolved"
    assert result["resolved"] is None
    assert "10:destroyed_state_unresolved" in result["unresolved_reasons"]
