from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_bird_advanced_cloak_decisive_closure_audit import (  # noqa: E402
    _mine_hit_from_message,
    _stable_same_ship,
)


def test_mine_hit_parser_requires_exact_ship_identity_and_positive_damage_field() -> None:
    message = {
        "id": 2701,
        "turn": 31,
        "x": 1989,
        "y": 2273,
        "messagetype": 16,
        "headline": "RESOLUTE CLASS BATTLECRUISER ID#68",
        "body": "RESOLUTE CLASS BATTLECRUISER ID#68 has struck a mine!<br/>Damage is at: 55<br/>( 1989, 2273 )",
    }
    hit = _mine_hit_from_message(message, 68)
    assert hit is not None
    assert hit["damage"] == 55
    assert hit["x"] == 1989
    assert hit["y"] == 2273
    assert _mine_hit_from_message(message, 69) is None


def test_mine_hit_parser_rejects_unrelated_mine_scan_text() -> None:
    message = {
        "headline": "RESOLUTE CLASS BATTLECRUISER ID#68",
        "body": "We are scanning for mines. Enemy Mine field detected! 968 mines remain.",
    }
    assert _mine_hit_from_message(message, 68) is None


def test_stable_same_ship_requires_same_owner_and_hull() -> None:
    before = {"ownerid": 3, "hullid": 31}
    assert _stable_same_ship(before, {"ownerid": 3, "hullid": 31}, owner_id=3)
    assert not _stable_same_ship(before, {"ownerid": 4, "hullid": 31}, owner_id=3)
    assert not _stable_same_ship(before, {"ownerid": 3, "hullid": 47}, owner_id=3)
    assert not _stable_same_ship(before, None, owner_id=3)
