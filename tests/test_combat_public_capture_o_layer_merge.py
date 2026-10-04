from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_public_capture_o_layer_merge import merge_parts
from combat_public_capture_o_layer_probe import SCHEMA


def _part(
    game_id: int,
    *,
    left: int,
    right: int,
    partition: str = "discovery",
) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "partition": partition,
        "scanned_game_ids": [1, 2],
        "probe_game_ids": [game_id],
        "summary": {
            "counts": {
                "capture_ship_rows": left + right,
                "discovery_ship_rows": left + right,
                "o_pair_reachable": left + right,
                "o_pair_reachable:left": left,
                "o_pair_reachable:right": right,
                "split_candidate_exact": left + right,
                "resolved_dependency:qualified": left,
                "resolved_dependency:blocked": right,
                "split_candidate_exact:qualified": left,
                "split_candidate_exact:blocked": right,
                "identity_anchored_o_pair_reachable": left,
                "identity_anchored_o_pair_not_reachable": right,
                "identity_anchored_split_exact": left + right,
            }
        },
        "observations": [
            {
                "game_id": game_id,
                "turn": 10,
                "capture_vcr_id": game_id,
                "captured_ship_id": 100 + game_id,
            }
        ],
    }


def test_merge_parts_sums_counts_and_preserves_game_isolation() -> None:
    report = merge_parts([
        _part(1, left=2, right=1),
        _part(2, left=3, right=4),
    ])
    counts = report["summary"]["counts"]
    assert report["partition"] == "discovery"
    assert report["summary"]["game_passes"] == 2
    assert counts["capture_ship_rows"] == 10
    assert counts["discovery_ship_rows"] == 10
    assert counts["o_pair_reachable"] == 10
    assert counts["o_pair_reachable:left"] == 5
    assert counts["o_pair_reachable:right"] == 5
    assert counts["split_candidate_exact"] == 10
    assert counts["resolved_dependency:qualified"] == 5
    assert counts["resolved_dependency:blocked"] == 5
    assert counts["split_candidate_exact:qualified"] == 5
    assert counts["split_candidate_exact:blocked"] == 5
    assert counts["identity_anchored_o_pair_reachable"] == 5
    assert counts["identity_anchored_o_pair_not_reachable"] == 5
    assert counts["identity_anchored_split_exact"] == 10
    assert report["scanned_game_ids"] == [1, 2]
    assert [row["probe_game_ids"] for row in report["summary"]["per_game"]] == [[1], [2]]

def test_merge_parts_preserves_heldout_partition() -> None:
    report = merge_parts([
        _part(7, left=1, right=2, partition="heldout"),
        _part(8, left=2, right=1, partition="heldout"),
    ])
    assert report["partition"] == "heldout"
    assert report["evidence_status"] == "HELDOUT_VALIDATION_FROZEN_SIDE_CANDIDATE"




def test_merge_parts_preserves_independent_partition() -> None:
    report = merge_parts([
        _part(21, left=2, right=1, partition="independent"),
        _part(22, left=1, right=2, partition="independent"),
    ])
    assert report["partition"] == "independent"
    assert (
        report["evidence_status"]
        == "INDEPENDENT_VALIDATION_POSTHELDOUT_CANDIDATE"
    )
