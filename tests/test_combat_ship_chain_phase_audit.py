from __future__ import annotations

import importlib.util
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_ship_chain_phase_audit.py"
spec = importlib.util.spec_from_file_location("combat_ship_chain_phase_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_battle_shape_distinguishes_ship_and_planet() -> None:
    assert audit._battle_shape(
        {
            "left": {"hullid": 10},
            "right": {"hullid": 20},
        }
    ) == "ship_vs_ship"
    assert audit._battle_shape(
        {
            "left": {"hullid": 10},
            "right": {"hullid": 0},
        }
    ) == "ship_vs_planet"
    assert audit._battle_shape(
        {
            "left": {"hullid": 0},
            "right": {"hullid": 0},
        }
    ) == "planet_vs_planet"


def test_terminal_kind_separates_capture_and_destroy() -> None:
    assert audit._terminal_kind({"terminal": {"captured": True}}) == "captured"
    assert audit._terminal_kind({"terminal": {"destroyed": True}}) == "destroyed"
    assert audit._terminal_kind(
        {"terminal": {"captured": False, "destroyed": False}}
    ) == "survived"


def test_problem_signature_keeps_capture_destroy_distinct() -> None:
    comparison = {
        "status": "reappearance_after_defeat",
        "carry_mismatches": [],
        "shield": {"model": "unknown"},
    }
    assert audit._problem_signature(comparison, "captured") == "reappearance_after_capture"
    assert audit._problem_signature(comparison, "destroyed") == "reappearance_after_destroyed"


def test_scope_summary_reports_field_deltas() -> None:
    rows = [
        {
            "comparison": {
                "status": "mismatch",
                "carry_mismatches": ["crew"],
                "carry": {
                    "damage": {"terminal": 10, "next_start": 10},
                    "crew": {"terminal": 100, "next_start": 103},
                    "torpedoes": {"terminal": 4, "next_start": 4},
                    "fighters": {"terminal": 8, "next_start": 8},
                },
                "shield": {"model": "exact_carry"},
            },
            "terminal_kind": "survived",
            "race_id": 3,
            "hull_id": 17,
            "gap": 1,
            "from_side": "left",
            "to_side": "left",
        }
    ]
    summary = audit._scope_summary(rows)
    assert summary["transitions"] == 1
    assert summary["status"] == {"mismatch": 1}
    assert summary["problem_signatures"] == {"crew": 1}
    assert summary["field_deltas_next_minus_terminal"]["crew"] == {"3": 1}
    assert summary["field_deltas_next_minus_terminal"]["damage"] == {"0": 1}
