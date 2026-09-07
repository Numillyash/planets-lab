from __future__ import annotations

import importlib.util
import json
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "diagnostics" / "combat_host_single_battle_side_residual_audit.py"
spec = importlib.util.spec_from_file_location("combat_host_single_battle_side_residual_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_forced_side_candidate_classifies_gorbie_hull_70() -> None:
    assert audit._classify_forced_side(70, 20) == "left_gorbie"
    assert audit._classify_forced_side(20, 70) == "right_gorbie"
    assert audit._classify_forced_side(70, 70) == "both_gorbie"
    assert audit._classify_forced_side(20, 30) == "no_gorbie"


def test_load_targets_requires_all_left_higher_examples(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    path.write_text(
        json.dumps(
            {
                "scopes": {
                    "ordinary": {
                        "side_priority": {"right_higher_priority": 10, "left_higher_priority": 2},
                        "examples": [
                            {"priority_relation": "left_higher_priority", "game_id": 1},
                            {"priority_relation": "left_higher_priority", "game_id": 2},
                            {"priority_relation": "right_higher_priority", "game_id": 3},
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    rows = audit._load_targets(path)
    assert [row["game_id"] for row in rows] == [1, 2]


def test_load_targets_fails_closed_when_source_examples_are_truncated(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    path.write_text(
        json.dumps(
            {
                "scopes": {
                    "ordinary": {
                        "side_priority": {"left_higher_priority": 2},
                        "examples": [
                            {"priority_relation": "left_higher_priority", "game_id": 1},
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    try:
        audit._load_targets(path)
    except ValueError as exc:
        assert "rerun the source audit" in str(exc)
    else:
        raise AssertionError("expected truncated source report to fail closed")
