from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_capture_continuation_audit import _capture_transition  # noqa: E402


def _appearance(
    *,
    ship_id: int,
    vcr_id: int,
    race_id: int,
    side: str,
    terminal: dict[str, object] | None = None,
    start: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "game_id": 1,
        "turn": 7,
        "vcr_id": vcr_id,
        "position": [100, 200],
        "side": side,
        "ship_id": ship_id,
        "hull_id": 20,
        "race_id": race_id,
        "start": start
        or {
            "shield": 40,
            "damage": 20,
            "crew": 10,
            "torpedos": 7,
            "fighters": 0,
        },
        "terminal": terminal
        or {
            "shield": 40,
            "damage": 20,
            "crew": 10,
            "torpedoes": 7,
            "fighters": 0,
            "destroyed": False,
            "captured": False,
        },
    }


def test_capture_transition_recognizes_captor_race_and_exact_carry() -> None:
    previous = _appearance(
        ship_id=10,
        vcr_id=1,
        race_id=3,
        side="left",
        terminal={
            "shield": 20,
            "damage": 30,
            "crew": 0,
            "torpedoes": 5,
            "fighters": 0,
            "destroyed": False,
            "captured": True,
        },
    )
    captor = _appearance(
        ship_id=20,
        vcr_id=1,
        race_id=5,
        side="right",
    )
    current = _appearance(
        ship_id=10,
        vcr_id=2,
        race_id=5,
        side="right",
        start={
            "shield": 20,
            "damage": 30,
            "crew": 0,
            "torpedos": 5,
            "fighters": 0,
        },
    )
    next_opponent = _appearance(
        ship_id=30,
        vcr_id=2,
        race_id=6,
        side="left",
    )

    result = _capture_transition(
        previous=previous,
        current=current,
        previous_opponent=captor,
        current_opponent=next_opponent,
    )

    assert result["status"] == "capture_continuation"
    assert result["race_changes_to_captor"] is True
    assert result["race_changed"] is True
    assert result["hull_preserved"] is True
    assert result["next_opponent_is_captor"] is False
    assert result["carry_all_exact"] is True
    assert result["shield"]["model"] == "exact_carry"


def test_capture_transition_detects_federation_recovery_candidate() -> None:
    previous = _appearance(
        ship_id=10,
        vcr_id=1,
        race_id=3,
        side="left",
        terminal={
            "shield": 40,
            "damage": 0,
            "crew": 0,
            "torpedoes": 5,
            "fighters": 0,
            "destroyed": False,
            "captured": True,
        },
    )
    federation_captor = _appearance(
        ship_id=20,
        vcr_id=1,
        race_id=1,
        side="right",
    )
    current = _appearance(
        ship_id=10,
        vcr_id=2,
        race_id=1,
        side="right",
        start={
            "shield": 65,
            "damage": 0,
            "crew": 0,
            "torpedos": 5,
            "fighters": 0,
        },
    )
    next_opponent = _appearance(
        ship_id=30,
        vcr_id=2,
        race_id=6,
        side="left",
    )

    result = _capture_transition(
        previous=previous,
        current=current,
        previous_opponent=federation_captor,
        current_opponent=next_opponent,
    )

    assert result["race_changes_to_captor"] is True
    assert result["shield"]["captor_federation_candidate"] == 65
    assert result["shield"]["captor_federation_exact"] is True
    assert result["shield"]["model"] == "captor_federation_recovery"
