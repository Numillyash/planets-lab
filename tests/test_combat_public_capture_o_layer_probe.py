from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_public_capture_o_layer_probe import (
    _appearance_mapping,
    _capture_projection,
    _targets_by_site,
)


def test_targets_by_site_groups_discovery_rows() -> None:
    rows = [
        {
            "game_id": 42,
            "turn": 7,
            "position": [100, 200],
            "captured_ship_id": 10,
        },
        {
            "game_id": 42,
            "turn": 7,
            "position": [100, 200],
            "captured_ship_id": 11,
        },
    ]
    grouped = _targets_by_site(rows)
    assert list(grouped) == [(42, 7, 100, 200)]
    assert [row["captured_ship_id"] for row in grouped[(42, 7, 100, 200)]] == [10, 11]


def test_appearance_mapping_uses_replay_identity() -> None:
    rows = [
        {
            "game_id": 42,
            "turn": 7,
            "vcr_id": 9,
            "ship_id": 11,
            "side": "left",
        }
    ]
    mapped = _appearance_mapping(rows)
    assert mapped[(42, 7, 9, 11)]["side"] == "left"


def test_capture_projection_keeps_only_probe_contract() -> None:
    row = {
        "captured_ship_id": 10,
        "captor_ship_id": 20,
        "captor_owner_id": 2,
        "next_opponent_ship_id": 30,
        "capture_vcr_id": 100,
        "next_vcr_id": 101,
        "captured_ship_side_next": "right",
    }
    assert _capture_projection(row) == {
        "ship_id": 10,
        "captor_ship_id": 20,
        "captor_owner_id": 2,
        "current_opponent_ship_id": 30,
        "from_vcr_id": 100,
        "to_vcr_id": 101,
        "current_side": "right",
    }


def test_o_layer_wrapper_is_main_guarded_and_discovery_only() -> None:
    root = Path(__file__).resolve().parents[1]
    wrapper = (
        root / "tools/run-public-capture-o-layer-discovery-with-evidence.sh"
    ).read_text(encoding="utf-8")
    runner = (
        root / "tools/run-public-capture-o-layer-discovery.sh"
    ).read_text(encoding="utf-8")

    assert 'PUBLIC_CAPTURE_O_LAYER_ALLOW_NON_MAIN="${PUBLIC_CAPTURE_O_LAYER_ALLOW_NON_MAIN:-0}"' in wrapper
    assert '"$SOURCE_BRANCH" != "main"' in wrapper
    assert "exit 64" in wrapper
    assert "discovery-capture-side.json" in runner
    assert "heldout" not in runner
    assert "--partition all" not in runner

def test_probe_supports_single_game_process_isolation() -> None:
    root = Path(__file__).resolve().parents[1]
    probe = (
        root / "tools/diagnostics/combat_public_capture_o_layer_probe.py"
    ).read_text(encoding="utf-8")
    runner = (
        root / "tools/run-public-capture-o-layer-discovery.sh"
    ).read_text(encoding="utf-8")

    assert 'parser.add_argument("--game-id", type=int)' in probe
    assert "full_scan_ids" in probe
    assert "probe_game_ids" in probe
    assert '--game-id "$game_id"' in runner
    assert "o-layer-parts" in runner
    assert "combat_public_capture_o_layer_merge.py" in runner

