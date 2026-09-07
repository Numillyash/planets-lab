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


def test_scope_status_counts_separate_special_game() -> None:
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
    special = audit._status_counts_for_scope(games, include_special=True)
    ordinary = audit._status_counts_for_scope(games, include_special=False)
    assert special["same_location_transitions"] == 10
    assert special["mismatch"] == 7
    assert ordinary["same_location_transitions"] == 5
    assert ordinary["match"] == 4
