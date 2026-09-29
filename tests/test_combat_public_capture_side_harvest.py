from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_public_capture_side_harvest import (
    _order_side_controls,
    _pair_occurrence_index,
    _partition_for_game,
    _prior_same_pair_occurrences,
)


def test_partition_is_stable_and_binary() -> None:
    first = _partition_for_game(473010)
    second = _partition_for_game(473010)

    assert first == second
    assert first in {"discovery", "heldout"}


def test_partition_changes_only_with_explicit_salt() -> None:
    default = {
        game_id: _partition_for_game(game_id)
        for game_id in range(1, 50)
    }
    alternate = {
        game_id: _partition_for_game(game_id, salt="alternate")
        for game_id in range(1, 50)
    }

    assert default != alternate


def test_prior_same_pair_occurrences_count_only_earlier_vcrs() -> None:
    by_vcr = {
        (1, 10, 3): [
            {"ship_id": 7},
            {"ship_id": 20},
        ],
        (1, 10, 5): [
            {"ship_id": 20},
            {"ship_id": 7},
        ],
        (1, 10, 8): [
            {"ship_id": 7},
            {"ship_id": 20},
        ],
        (1, 10, 4): [
            {"ship_id": 7},
        ],
    }
    index = _pair_occurrence_index(by_vcr)

    count, vcr_ids = _prior_same_pair_occurrences(
        occurrence_index=index,
        game_id=1,
        turn=10,
        ship_a=20,
        ship_b=7,
        before_vcr_id=8,
    )

    assert count == 2
    assert vcr_ids == [3, 5]

def test_discovery_wrapper_is_main_guarded_and_heldout_sealed() -> None:
    root = Path(__file__).resolve().parents[1]
    wrapper = (
        root / "tools/run-public-capture-side-discovery-with-evidence.sh"
    ).read_text(encoding="utf-8")
    runner = (
        root / "tools/run-public-capture-side-discovery.sh"
    ).read_text(encoding="utf-8")

    assert 'PUBLIC_CAPTURE_SIDE_ALLOW_NON_MAIN="${PUBLIC_CAPTURE_SIDE_ALLOW_NON_MAIN:-0}"' in wrapper
    assert '"$SOURCE_BRANCH" != "main"' in wrapper
    assert "exit 64" in wrapper
    assert "--partition discovery" in runner
    assert "--partition heldout" not in runner
    assert "--partition all" not in runner

def test_order_side_controls_reuse_c5_priority_hypotheses() -> None:
    captured = {
        "mission": 0,
        "mission1target": 0,
        "enemy": 0,
        "friendlycode": "abc",
    }
    opponent = {
        "mission": 0,
        "mission1target": 0,
        "enemy": 0,
        "friendlycode": "001",
    }

    first = _order_side_controls(
        captured_ship_id=20,
        opponent_ship_id=10,
        captured_raw=captured,
        opponent_raw=opponent,
        prior_pair_occurrences=0,
        factual_side="left",
    )
    assert first["occurrence_index"] == 1
    assert first["side_controls"]["frozen_tminus1_priority"] == "left"
    assert first["side_control_exact"]["frozen_tminus1_priority"] is True
    assert first["side_controls"]["neutral_orders_preserve_fc"] == "left"
    assert first["side_controls"]["neutral_orders_fresh_fc"] == "left"

    repeated = _order_side_controls(
        captured_ship_id=20,
        opponent_ship_id=10,
        captured_raw=captured,
        opponent_raw=opponent,
        prior_pair_occurrences=1,
        factual_side="right",
    )
    assert repeated["occurrence_index"] == 2
    assert repeated["side_controls"]["frozen_tminus1_priority"] == "right"
    assert repeated["side_control_exact"]["frozen_tminus1_priority"] is True

