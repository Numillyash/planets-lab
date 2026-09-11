from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_initial_standard_directional_targetability_audit import (  # noqa: E402
    _opportunity_key,
    _profile_exact,
    _project_mismatch_repair,
)


def test_opportunity_key_is_directional() -> None:
    row = {
        "game_id": 1,
        "battle_turn": 2,
        "target_ship_id": 3,
        "attacker_ship_id": 4,
    }
    assert _opportunity_key(row) == (1, 2, 3, 4)


def test_profile_exact_requires_pair_and_right_exact() -> None:
    summary = {
        "strict": {
            "exact_set": {
                "sites": 2,
                "first_pair_exact": 2,
                "first_pair_mismatch": 0,
                "first_right_exact": 2,
                "first_right_mismatch": 0,
            }
        }
    }
    assert _profile_exact(summary, "strict") is True

    summary["strict"]["exact_set"]["first_right_exact"] = 1
    summary["strict"]["exact_set"]["first_right_mismatch"] = 1
    assert _profile_exact(summary, "strict") is False


def test_project_mismatch_repair_requires_exact_direction_and_rank2() -> None:
    mismatch = {
        "game_id": 360690,
        "battle_turn": 83,
        "profile": "conditional",
        "analysis": {
            "predicted_first": {
                "target_ship_id": 98,
                "active_ship_id": 264,
            },
            "factual_target_rank_within_top_active": 2,
        },
        "factual_first": {"right_ship_id": 264},
    }
    blocked = {(360690, 83, 98, 264)}
    result = _project_mismatch_repair(mismatch=mismatch, blocked_keys=blocked)
    assert result["supported_block_matches_prediction"] is True
    assert result["projected_fixed_by_directional_targetability"] is True

    wrong_direction = {(360690, 83, 264, 98)}
    result = _project_mismatch_repair(mismatch=mismatch, blocked_keys=wrong_direction)
    assert result["supported_block_matches_prediction"] is False
    assert result["projected_fixed_by_directional_targetability"] is False


def test_project_mismatch_repair_rejects_non_rank2() -> None:
    mismatch = {
        "game_id": 511506,
        "battle_turn": 94,
        "profile": "strict",
        "analysis": {
            "predicted_first": {
                "target_ship_id": 202,
                "active_ship_id": 496,
            },
            "factual_target_rank_within_top_active": 3,
        },
        "factual_first": {"right_ship_id": 496},
    }
    blocked = {(511506, 94, 202, 496)}
    result = _project_mismatch_repair(mismatch=mismatch, blocked_keys=blocked)
    assert result["supported_block_matches_prediction"] is True
    assert result["projected_fixed_by_directional_targetability"] is False
