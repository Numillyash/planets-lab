from __future__ import annotations

import importlib.util
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_ship_chain_cluster_audit.py"
spec = importlib.util.spec_from_file_location("combat_ship_chain_cluster_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_problem_signature_combines_carry_and_shield() -> None:
    comparison = {
        "status": "mismatch",
        "carry_mismatches": ["damage", "crew"],
        "shield": {"model": "mismatch"},
    }
    assert audit._problem_signature(comparison) == "damage+crew+shield"


def test_problem_signature_keeps_reappearance_separate() -> None:
    assert audit._problem_signature(
        {"status": "reappearance_after_defeat"}
    ) == "reappearance_after_defeat"


def test_delta_and_gap_helpers() -> None:
    comparison = {
        "carry": {
            "fighters": {
                "terminal": 37,
                "next_start": 34,
            }
        }
    }
    assert audit._delta_from_carry(comparison, "fighters") == -3
    assert audit._gap_bucket(1) == "1"
    assert audit._gap_bucket(3) == "2-3"
    assert audit._gap_bucket(8) == "4-10"
    assert audit._gap_bucket(12) == ">10"


def test_scope_status_counts_follow_selected_game_ids() -> None:
    games = {
        "591478": {
            "same_location_transitions": 10,
            "match": 2,
            "mismatch": 7,
            "reappearance_after_defeat": 1,
        },
        "620694": {
            "same_location_transitions": 5,
            "match": 4,
            "mismatch": 1,
        },
    }
    excluded = audit._status_counts_for_games(games, {591478})
    selected = audit._status_counts_for_games(games, {620694})
    assert excluded["same_location_transitions"] == 10
    assert excluded["mismatch"] == 7
    assert selected["same_location_transitions"] == 5
    assert selected["match"] == 4


def test_scope_classification_has_no_special_game_constant() -> None:
    assert (
        audit._scope(
            620694,
            selected_ids={620694},
            unknown_ids=set(),
        )
        == "profile_selected"
    )
    assert (
        audit._scope(
            591478,
            selected_ids={620694},
            unknown_ids=set(),
        )
        == "profile_excluded"
    )
    assert (
        audit._scope(
            42,
            selected_ids={620694},
            unknown_ids={42},
        )
        == "profile_unknown"
    )
