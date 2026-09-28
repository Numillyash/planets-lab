from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import combat_host_post_capture_pair_recomposition_audit as module
from combat_host_post_capture_pair_recomposition_audit import (
    _c2ng_thost_sim_battle_value,
    _pair_recomposition,
    _side_from_priority_keys,
)


def _entry(
    ship_id: int,
    owner_id: int,
    *,
    race_id: int,
    mission: int,
    enemy: int,
    friendlycode: str,
) -> dict[str, object]:
    return {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "race_id": race_id,
        "hull_id": 20,
        "hull_can_cloak": False,
        "position": (100, 100),
        "source": "test",
        "raw": {
            "id": ship_id,
            "ownerid": owner_id,
            "hullid": 20,
            "mission": mission,
            "mission1target": 0,
            "enemy": enemy,
            "friendlycode": friendlycode,
            "neutronium": 50,
        },
    }


def test_priority_side_control_applies_second_occurrence_reversal() -> None:
    first = _side_from_priority_keys(
        prize_ship_id=10,
        opponent_ship_id=20,
        prize_key=(4, 10, 0),
        opponent_key=(3, 20, 0),
        occurrence_index=1,
    )
    second = _side_from_priority_keys(
        prize_ship_id=10,
        opponent_ship_id=20,
        prize_key=(4, 10, 0),
        opponent_key=(3, 20, 0),
        occurrence_index=2,
    )

    assert first == "left"
    assert second == "right"


def test_t26_shape_distinguishes_sticky_from_generic_initiator_side(monkeypatch) -> None:
    monkeypatch.setattr(module, "_interference_state", lambda **kwargs: False)

    context = {
        "game_id": 1,
        "battle_turn": 26,
        "before_turn": 25,
        "start_stacks": {},
        "predictions": {
            27: _entry(
                27,
                6,
                race_id=6,
                mission=2,
                enemy=5,
                friendlycode="mkt",
            ),
            119: _entry(
                119,
                6,
                race_id=6,
                mission=6,
                enemy=5,
                friendlycode="ona",
            ),
            102: _entry(
                102,
                5,
                race_id=5,
                mission=3,
                enemy=6,
                friendlycode="500",
            ),
        },
        "factual_queue": [
            {
                "vcr_id": 54,
                "pair": (27, 102),
                "left_ship_id": 102,
                "right_ship_id": 27,
            },
            {
                "vcr_id": 55,
                "pair": (27, 119),
                "left_ship_id": 119,
                "right_ship_id": 27,
            },
        ],
    }
    capture = {
        "ship_id": 27,
        "captor_ship_id": 102,
        "captor_owner_id": 5,
        "race_id_after": 5,
        "hull_id_after": 20,
        "current_opponent_ship_id": 119,
        "from_vcr_id": 54,
        "to_vcr_id": 55,
        "current_side": "right",
    }
    active_result = {
        "status": "resolved",
        "prize_owner_id_after_capture": 5,
        "candidates": [
            {
                "ship_id": 119,
                "requests_new_owner": True,
                "strict_permission": True,
            }
        ],
        "active_ship_ids": [27, 102, 119],
        "removed_ship_ids": [],
        "history_anchored_ship_ids": [27, 102, 119],
    }
    appearances = {
        (1, 26, 54, 27): {
            "side": "right",
        }
    }

    result = _pair_recomposition(
        context=context,
        capture=capture,
        active_result=active_result,
        appearances=appearances,
    )

    assert result["status"] == "resolved"
    assert result["pair_phase_invariant"] is True
    assert result["preserved_fc_decision"]["phase"] == "standard"
    assert result["fresh_fc_decision"]["phase"] == "standard"
    assert result["side_control_exact"]["sticky_capture_side"] is True
    assert result["side_control_exact"]["opponent_initiator_right"] is False
    assert result["side_control_exact"]["external_c2ng_captured_right"] is True
    assert result["side_control_exact"]["frozen_tminus1_priority"] is True
    external = result["external_c2ng_original_order"]
    assert external["status"] == "resolved"
    assert external["external_order"] == [102, 27, 119]
    assert external["predicted_opponent_ship_id"] == 119
    assert external["predicted_prize_side"] == "right"
    assert external["exact"] is True




def test_external_c2ng_thost_battle_value_isolated_from_canonical_priority() -> None:
    assert _c2ng_thost_sim_battle_value(
        ship_id=10,
        raw={"friendlycode": "001", "mission": 0, "enemy": 0, "neutronium": 50},
    ) == (1, 10)
    assert _c2ng_thost_sim_battle_value(
        ship_id=11,
        raw={"friendlycode": "abc", "mission": 3, "enemy": 0, "neutronium": 50},
    ) == (1000, 11)
    assert _c2ng_thost_sim_battle_value(
        ship_id=12,
        raw={"friendlycode": "abc", "mission": 2, "enemy": 5, "neutronium": 50},
    ) == (1010, 12)
    assert _c2ng_thost_sim_battle_value(
        ship_id=13,
        raw={"friendlycode": "abc", "mission": 0, "enemy": 0, "neutronium": 50},
    ) == (1015, 13)
    assert _c2ng_thost_sim_battle_value(
        ship_id=14,
        raw={"friendlycode": "001", "mission": 0, "enemy": 0, "neutronium": 0},
    ) == (1015, 14)

def test_pair_recomposition_fails_closed_when_fc_changes_eligibility(monkeypatch) -> None:
    monkeypatch.setattr(module, "_interference_state", lambda **kwargs: False)

    context = {
        "game_id": 1,
        "battle_turn": 7,
        "before_turn": 6,
        "start_stacks": {},
        "predictions": {
            10: _entry(
                10,
                1,
                race_id=1,
                mission=0,
                enemy=0,
                friendlycode="abc",
            ),
            20: _entry(
                20,
                2,
                race_id=2,
                mission=3,
                enemy=1,
                friendlycode="abc",
            ),
        },
        "factual_queue": [
            {
                "vcr_id": 1,
                "pair": (10, 30),
                "left_ship_id": 30,
                "right_ship_id": 10,
            },
            {
                "vcr_id": 2,
                "pair": (10, 20),
                "left_ship_id": 10,
                "right_ship_id": 20,
            },
        ],
    }
    capture = {
        "ship_id": 10,
        "captor_owner_id": 3,
        "race_id_after": 3,
        "hull_id_after": 20,
        "current_opponent_ship_id": 20,
        "from_vcr_id": 1,
        "to_vcr_id": 2,
        "current_side": "left",
    }
    active_result = {
        "status": "resolved",
        "prize_owner_id_after_capture": 3,
        "candidates": [{"ship_id": 20, "strict_permission": True}],
    }
    appearances = {(1, 7, 1, 10): {"side": "left"}}

    result = _pair_recomposition(
        context=context,
        capture=capture,
        active_result=active_result,
        appearances=appearances,
    )

    assert result["status"] == "unresolved"
    assert result["reason"] == "pair_phase_not_fc_invariant"
    assert result["factual_post_capture_side"] == "left"
    assert result["side_control_exact"]["opponent_initiator_right"] is True
    assert result["side_control_exact"]["external_c2ng_captured_right"] is False
