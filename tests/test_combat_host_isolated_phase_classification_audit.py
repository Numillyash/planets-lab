from __future__ import annotations

import importlib.util
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_host_isolated_phase_classification_audit.py"
spec = importlib.util.spec_from_file_location("combat_host_isolated_phase_classification_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_c_and_i_classification_matches_621253_residual_signature() -> None:
    assert audit._c_and_i_classification(
        raw={"mission": 20, "mission1target": 50, "enemy": 4},
        ship_id=57,
        opponent_ship_id=50,
        owner_race_id=3,
        hull_can_cloak=True,
        target_owner_id=4,
    ) == "targets_factual_opponent"


def test_c_and_i_classification_distinguishes_other_target_and_unknown() -> None:
    assert audit._c_and_i_classification(
        raw={"mission": 20, "mission1target": 99, "enemy": 4},
        ship_id=57,
        opponent_ship_id=50,
        owner_race_id=3,
        hull_can_cloak=True,
        target_owner_id=4,
    ) == "targets_other_ship"
    assert audit._c_and_i_classification(
        raw={"mission": 20, "mission1target": 50, "enemy": 4},
        ship_id=57,
        opponent_ship_id=50,
        owner_race_id=3,
        hull_can_cloak=None,
        target_owner_id=4,
    ) == "signature_unknown"


def test_signed_fc_standard_relation_fixes_two_prior_residual_shapes() -> None:
    relation, left_key, right_key = audit._standard_relation(
        left_raw={"mission": 8, "enemy": 0, "friendlycode": "125"},
        right_raw={"mission": 3, "enemy": 0, "friendlycode": "-54"},
        left_ship_id=105,
        right_ship_id=108,
    )
    assert relation == "right_higher_priority"
    assert left_key == (0, 125, 105)
    assert right_key == (0, -54, 108)

    relation, left_key, right_key = audit._standard_relation(
        left_raw={"mission": 9, "enemy": 5, "friendlycode": "mkt"},
        right_raw={"mission": 1, "enemy": 3, "friendlycode": "-52"},
        left_ship_id=262,
        right_ship_id=448,
    )
    assert relation == "right_higher_priority"
    assert left_key == (3, 262, 0)
    assert right_key == (0, -52, 448)


def test_prior_final_residual_is_left_higher_if_misclassified_as_standard() -> None:
    relation, left_key, right_key = audit._standard_relation(
        left_raw={"mission": 0, "enemy": 3, "friendlycode": "wxd"},
        right_raw={"mission": 20, "enemy": 4, "friendlycode": "osq"},
        left_ship_id=50,
        right_ship_id=57,
    )
    assert relation == "left_higher_priority"
    assert left_key == (3, 50, 0)
    assert right_key == (3, 57, 0)


def test_scope_removes_qualified_c_and_i_from_standard_bucket() -> None:
    rows = [
        {
            "game_id": 621253,
            "turn": 10,
            "vcr_id": 8,
            "left_ship_id": 50,
            "right_ship_id": 57,
            "left_raw": {"mission": 0, "enemy": 3, "friendlycode": "wxd"},
            "right_raw": {"mission": 20, "enemy": 4, "friendlycode": "osq"},
            "left_c_and_i": "not_c_and_i",
            "right_c_and_i": "targets_factual_opponent",
            "has_intercept_mission": False,
        },
        {
            "game_id": 620694,
            "turn": 89,
            "vcr_id": 592,
            "left_ship_id": 105,
            "right_ship_id": 108,
            "left_raw": {"mission": 8, "enemy": 0, "friendlycode": "125"},
            "right_raw": {"mission": 3, "enemy": 0, "friendlycode": "-54"},
            "left_c_and_i": "not_c_and_i",
            "right_c_and_i": "not_c_and_i",
            "has_intercept_mission": False,
        },
    ]
    scope = audit._scope(rows, example_limit=10)
    assert scope["phases"] == {
        "cloak_intercept_pre_standard": 1,
        "standard": 1,
    }
    assert scope["standard_side_priority"] == {"right_higher_priority": 1}
    assert scope["cloak_intercept_factual_side"] == {"c_and_i_right": 1}


def test_scope_keeps_mixed_c_and_i_and_mission7_unresolved() -> None:
    rows = [
        {
            "game_id": 1,
            "turn": 2,
            "vcr_id": 1,
            "left_ship_id": 10,
            "right_ship_id": 20,
            "left_raw": {"mission": 20, "enemy": 2, "friendlycode": "abc"},
            "right_raw": {"mission": 7, "enemy": 1, "friendlycode": "def"},
            "left_c_and_i": "targets_factual_opponent",
            "right_c_and_i": "not_c_and_i",
            "has_intercept_mission": True,
        }
    ]
    scope = audit._scope(rows, example_limit=10)
    assert scope["phases"] == {"mixed_prestandard_unresolved": 1}
    assert scope["exclusions"] == {"mixed_c_and_i_priority_intercept_unresolved": 1}
    assert scope["standard_side_priority"] == {}


def test_scope_keeps_mission7_unresolved() -> None:
    rows = [
        {
            "game_id": 1,
            "turn": 2,
            "vcr_id": 1,
            "left_ship_id": 10,
            "right_ship_id": 20,
            "left_raw": {"mission": 7, "enemy": 2, "friendlycode": "abc"},
            "right_raw": {"mission": 0, "enemy": 1, "friendlycode": "def"},
            "left_c_and_i": "not_c_and_i",
            "right_c_and_i": "not_c_and_i",
            "has_intercept_mission": True,
        }
    ]
    scope = audit._scope(rows, example_limit=10)
    assert scope["phases"] == {"priority_intercept_unresolved": 1}
    assert scope["exclusions"] == {"priority_intercept_unresolved": 1}
