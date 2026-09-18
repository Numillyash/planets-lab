from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_second_standard_queue_audit import _production_projection  # noqa: E402


def test_production_projection_reverses_second_plain_standard_occurrence() -> None:
    row = {
        "game_id": 620917,
        "battle_turn": 7,
        "x": 1990,
        "y": 1810,
        "pair": [13, 14],
        "stable_owners": True,
        "plain_static_comparable": True,
        "occurrence_count": 2,
        "left_ship_sequence": [14, 13],
        "right_ship_sequence": [13, 14],
        "tminus1": {
            "13": {
                "factual_owner_id": 5,
                "owner_tminus1": 5,
                "mission": 8,
                "mission1target": 0,
                "enemy": 6,
                "friendlycode": "HYP",
            },
            "14": {
                "factual_owner_id": 6,
                "owner_tminus1": 6,
                "mission": 1,
                "mission1target": 0,
                "enemy": 0,
                "friendlycode": "jih",
            },
        },
    }

    result = _production_projection(row)

    assert result["status"] == "resolved"
    assert result["pair"] == [13, 14]
    assert result["occurrence_index"] == 2
    assert result["left_ship_id"] == 13
    assert result["right_ship_id"] == 14
    assert result["expected_left_ship_id"] == 13
    assert result["expected_right_ship_id"] == 14
