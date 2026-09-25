from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_initial_standard_target_audit import _merge_prediction_overlay  # noqa: E402
from combat_host_post_capture_ship_candidate_audit import (  # noqa: E402
    _analyze_site,
    _candidate_acceptance,
    _capture_targets,
)


def _entry(ship_id: int, owner_id: int, *, mission: int, enemy: int, fc: str):
    return {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "raw": {
            "mission": mission,
            "enemy": enemy,
            "friendlycode": fc,
        },
    }


def test_post_capture_inventory_retargets_opponent_request_to_new_owner(monkeypatch) -> None:
    import combat_host_post_capture_ship_candidate_audit as module

    monkeypatch.setattr(module, "_relation_signature", lambda *args, **kwargs: ((0, 0, 0), (0, 0, 0)))
    monkeypatch.setattr(module, "_independent_permission", lambda **kwargs: True if kwargs["request"] else False)

    context = {
        "before_turn": 6,
        "site_ship_rows": {
            10: _entry(10, 5, mission=0, enemy=0, fc="900"),
            20: _entry(20, 5, mission=0, enemy=0, fc="800"),
            30: _entry(30, 8, mission=3, enemy=0, fc="100"),
        },
        "relations": {6: {}},
        "controls": {},
        "factual": {"pair_rows": {}},
    }
    capture = {
        "ship_id": 10,
        "captor_owner_id": 3,
        "current_opponent_ship_id": 30,
    }

    result = _analyze_site(context, capture)
    assert result["status"] == "resolved"
    assert result["factual_opponent_predicted_at_site"] is True
    assert result["factual_opponent_requests_new_owner"] is True
    assert result["factual_opponent_requester_rank"] == 1
    assert 20 in result["requester_order"] or result["requester_order"] == [30]


def test_post_capture_inventory_allows_capture_event_to_anchor_missing_prize_ship(monkeypatch) -> None:
    import combat_host_post_capture_ship_candidate_audit as module

    monkeypatch.setattr(module, "_relation_signature", lambda *args, **kwargs: ((0, 0, 0), (0, 0, 0)))
    monkeypatch.setattr(module, "_independent_permission", lambda **kwargs: True if kwargs["request"] else False)

    context = {
        "before_turn": 6,
        "site_ship_rows": {
            30: _entry(30, 8, mission=3, enemy=0, fc="100"),
        },
        "relations": {6: {}},
        "controls": {},
        "factual": {"pair_rows": {}},
    }
    capture = {
        "ship_id": 10,
        "captor_owner_id": 3,
        "current_opponent_ship_id": 30,
    }

    result = _analyze_site(context, capture)

    assert result["status"] == "resolved"
    assert result["captured_ship_predicted_at_site"] is False
    assert result["factual_opponent_predicted_at_site"] is True
    assert result["factual_opponent_requests_new_owner"] is True
    assert result["factual_opponent_requester_rank"] == 1


def test_capture_targets_preserve_multiple_capture_observations_at_same_site() -> None:
    report = {
        "examples": [
            {
                "status": "capture_continuation",
                "game_id": 1,
                "turn": 7,
                "position": [100, 200],
                "ship_id": 10,
                "current_opponent_is_planet": False,
                "from_vcr_id": 4,
                "to_vcr_id": 5,
            },
            {
                "status": "capture_continuation",
                "game_id": 1,
                "turn": 7,
                "position": [100, 200],
                "ship_id": 10,
                "current_opponent_is_planet": False,
                "from_vcr_id": 5,
                "to_vcr_id": 6,
            },
        ]
    }

    targets = _capture_targets(report)

    assert list(targets) == [(1, 7, 100, 200)]
    assert [row["from_vcr_id"] for row in targets[(1, 7, 100, 200)]] == [4, 5]


def test_prediction_overlay_replaces_fail_closed_position_with_special_prediction() -> None:
    rows = {
        10: {
            "ship_id": 10,
            "owner_id": 1,
            "position": None,
            "source": "intercept_movement",
        },
        20: {
            "ship_id": 20,
            "owner_id": 2,
            "position": (100, 100),
            "source": "normal_movement",
        },
    }

    _merge_prediction_overlay(
        rows,
        {
            10: {
                "ship_id": 10,
                "owner_id": 1,
                "position": (120, 100),
                "source": "special_intercept_movement_phase",
            }
        },
    )

    assert rows[10]["position"] == (120, 100)
    assert rows[10]["source"] == "special_intercept_movement_phase"
    assert rows[20]["position"] == (100, 100)


def test_candidate_acceptance_requires_all_eight_rank_one() -> None:
    counts = {
        "status:resolved": 8,
        "factual_opponent_predicted_at_site": 8,
        "factual_opponent_requests_new_owner": 8,
        "factual_opponent_strict_permission_true": 8,
        "requester_rank:1": 8,
        "strict_rank:1": 8,
    }

    acceptance = _candidate_acceptance(counts, observation_count=8)

    assert acceptance["post_capture_ship_candidate_gate_passed"] is True


def test_candidate_acceptance_fails_if_one_opponent_is_not_rank_one() -> None:
    counts = {
        "status:resolved": 8,
        "factual_opponent_predicted_at_site": 8,
        "factual_opponent_requests_new_owner": 8,
        "factual_opponent_strict_permission_true": 8,
        "requester_rank:1": 7,
        "requester_rank:2": 1,
        "strict_rank:1": 7,
        "strict_rank:2": 1,
    }

    acceptance = _candidate_acceptance(counts, observation_count=8)

    assert acceptance["post_capture_ship_candidate_gate_passed"] is False
    assert acceptance["all_factual_opponents_requester_rank_one"] is False
