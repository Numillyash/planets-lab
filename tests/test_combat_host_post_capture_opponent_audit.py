from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_post_capture_opponent_audit import (  # noqa: E402
    _opponent_projection,
    _vcr_index,
)


def _capture_row(*, side: str = "left") -> dict[str, object]:
    return {
        "current_side": side,
        "owner_id_before": 6,
        "captor_owner_id": 5,
    }


def test_next_ship_owner_matches_pre_capture_owner() -> None:
    raw_vcr = {
        "leftownerid": 5,
        "rightownerid": 6,
        "left": {"objectid": 27, "hullid": 56},
        "right": {"objectid": 119, "hullid": 20},
    }

    result = _opponent_projection(_capture_row(), raw_vcr)

    assert result["resolved"] is True
    assert result["opponent_owner_id"] == 6
    assert result["opponent_is_planet"] is False
    assert result["owner_relation"] == "pre_capture_owner"
    assert result["opponent_is_pre_capture_owner"] is True
    assert result["opponent_is_captor"] is False


def test_next_planet_owner_matches_pre_capture_owner() -> None:
    raw_vcr = {
        "leftownerid": 5,
        "rightownerid": 6,
        "left": {"objectid": 480, "hullid": 51},
        "right": {"objectid": 303, "hullid": 0},
    }

    result = _opponent_projection(_capture_row(), raw_vcr)

    assert result["resolved"] is True
    assert result["opponent_owner_id"] == 6
    assert result["opponent_is_planet"] is True
    assert result["owner_relation"] == "pre_capture_owner"


def test_third_party_owner_is_not_silently_folded_into_old_owner() -> None:
    raw_vcr = {
        "leftownerid": 5,
        "rightownerid": 9,
        "left": {"objectid": 27, "hullid": 56},
        "right": {"objectid": 88, "hullid": 20},
    }

    result = _opponent_projection(_capture_row(), raw_vcr)

    assert result["resolved"] is True
    assert result["owner_relation"] == "third_party"
    assert result["opponent_is_pre_capture_owner"] is False


def test_right_side_captured_ship_reads_left_opponent() -> None:
    raw_vcr = {
        "leftownerid": 6,
        "rightownerid": 5,
        "left": {"objectid": 119, "hullid": 20},
        "right": {"objectid": 27, "hullid": 56},
    }

    result = _opponent_projection(_capture_row(side="right"), raw_vcr)

    assert result["resolved"] is True
    assert result["opponent_side"] == "left"
    assert result["opponent_owner_id"] == 6
    assert result["owner_relation"] == "pre_capture_owner"


def test_vcr_index_filters_archives_by_explicit_selected_ids(tmp_path, monkeypatch) -> None:
    import combat_host_post_capture_opponent_audit as module

    (tmp_path / "game-1.zip").write_bytes(b"one")
    (tmp_path / "game-2.zip").write_bytes(b"two")
    seen_payloads: list[bytes] = []

    def fake_dedup(payload: bytes):
        seen_payloads.append(payload)
        game_id = 1 if payload == b"one" else 2
        return {
            (game_id, 7, 11): (
                "digest",
                {
                    "leftownerid": 1,
                    "rightownerid": 2,
                    "left": {"objectid": 10, "hullid": 20},
                    "right": {"objectid": 20, "hullid": 30},
                },
            )
        }, 0

    monkeypatch.setattr(module, "_dedup_vcrs", fake_dedup)

    rows, conflicts = _vcr_index(tmp_path, selected_ids={2})

    assert conflicts == 0
    assert seen_payloads == [b"two"]
    assert sorted(rows) == [(2, 7, 11)]


def test_vcr_index_without_scope_keeps_all_archives(tmp_path, monkeypatch) -> None:
    import combat_host_post_capture_opponent_audit as module

    (tmp_path / "game-1.zip").write_bytes(b"one")
    (tmp_path / "game-2.zip").write_bytes(b"two")

    def fake_dedup(payload: bytes):
        game_id = 1 if payload == b"one" else 2
        return {
            (game_id, 7, 11): (
                "digest",
                {
                    "leftownerid": 1,
                    "rightownerid": 2,
                    "left": {"objectid": 10, "hullid": 20},
                    "right": {"objectid": 20, "hullid": 30},
                },
            )
        }, 0

    monkeypatch.setattr(module, "_dedup_vcrs", fake_dedup)

    rows, conflicts = _vcr_index(tmp_path)

    assert conflicts == 0
    assert sorted(rows) == [(1, 7, 11), (2, 7, 11)]
