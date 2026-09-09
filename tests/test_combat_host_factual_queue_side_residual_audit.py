from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


TOOL = (
    Path(__file__).parents[1]
    / "tools"
    / "diagnostics"
    / "combat_host_factual_queue_side_residual_audit.py"
)
spec = importlib.util.spec_from_file_location("combat_host_factual_queue_side_residual_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


def test_pair_occurrence_context_marks_second_same_pair() -> None:
    rows = [
        {"vcr_id": 4, "pair": (10, 20)},
        {"vcr_id": 5, "pair": (30, 40)},
        {"vcr_id": 6, "pair": (10, 20)},
        {"vcr_id": 7, "pair": (10, 50)},
    ]
    assert audit._pair_occurrence_context(
        rows,
        target_vcr_id=6,
        target_pair=(10, 20),
    ) == {
        "site_ship_vcr_ids": [4, 5, 6, 7],
        "same_pair_vcr_ids": [4, 6],
        "same_pair_count": 2,
        "same_pair_occurrence_index": 2,
        "prior_same_pair_vcr_ids": [4],
        "later_same_pair_vcr_ids": [],
        "is_repeated_pair": True,
        "is_second_or_later_same_pair": True,
    }


def test_pair_occurrence_context_marks_single_pair() -> None:
    rows = [
        {"vcr_id": 2, "pair": (11, 26)},
        {"vcr_id": 3, "pair": (12, 27)},
    ]
    result = audit._pair_occurrence_context(
        rows,
        target_vcr_id=2,
        target_pair=(11, 26),
    )
    assert result["same_pair_count"] == 1
    assert result["same_pair_occurrence_index"] == 1
    assert result["is_repeated_pair"] is False
    assert result["is_second_or_later_same_pair"] is False
