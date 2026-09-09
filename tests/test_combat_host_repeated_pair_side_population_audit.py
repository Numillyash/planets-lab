from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


TOOL = (
    Path(__file__).parents[1]
    / "tools"
    / "diagnostics"
    / "combat_host_repeated_pair_side_population_audit.py"
)
spec = importlib.util.spec_from_file_location("combat_host_repeated_pair_side_population_audit", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


def test_orientation_analysis_recognizes_two_pass_side_flip() -> None:
    rows = [
        {
            "vcr_id": 5,
            "left_ship_id": 20,
            "right_ship_id": 10,
            "pair": (10, 20),
        },
        {
            "vcr_id": 6,
            "left_ship_id": 10,
            "right_ship_id": 20,
            "pair": (10, 20),
        },
    ]
    result = audit._orientation_analysis(
        rows,
        priority_by_ship={10: (0, 10, 10), 20: (3, 20, 0)},
    )
    assert result["occurrence_count"] == 2
    assert result["right_ship_sequence"] == [10, 20]
    assert result["exactly_two_side_flip"] is True
    assert result["priority_comparable"] is True
    assert result["high_priority_ship_id"] == 10
    assert result["low_priority_ship_id"] == 20
    assert result["first_static_right_exact"] is True
    assert result["second_reversed_right_exact"] is True
    assert result["two_pass_static_pattern_exact"] is True


def test_orientation_analysis_detects_nonflipping_second_pass() -> None:
    rows = [
        {
            "vcr_id": 1,
            "left_ship_id": 20,
            "right_ship_id": 10,
            "pair": (10, 20),
        },
        {
            "vcr_id": 2,
            "left_ship_id": 20,
            "right_ship_id": 10,
            "pair": (10, 20),
        },
    ]
    result = audit._orientation_analysis(
        rows,
        priority_by_ship={10: (0, 10, 10), 20: (4, 20, 0)},
    )
    assert result["exactly_two_side_flip"] is False
    assert result["first_static_right_exact"] is True
    assert result["second_reversed_right_exact"] is False
    assert result["two_pass_static_pattern_exact"] is False


def test_orientation_analysis_keeps_unsupported_priority_unresolved() -> None:
    rows = [
        {
            "vcr_id": 1,
            "left_ship_id": 20,
            "right_ship_id": 10,
            "pair": (10, 20),
        },
        {
            "vcr_id": 2,
            "left_ship_id": 10,
            "right_ship_id": 20,
            "pair": (10, 20),
        },
    ]
    result = audit._orientation_analysis(
        rows,
        priority_by_ship={10: None, 20: (4, 20, 0)},
    )
    assert result["priority_comparable"] is False
    assert result["first_static_right_exact"] is None
    assert result["second_reversed_right_exact"] is None
    assert result["two_pass_static_pattern_exact"] is None


def test_exact_pair_special_order_only_binds_actual_target() -> None:
    assert audit._exact_pair_special_order(
        {"mission": 7, "mission1target": 20},
        20,
    ) is True
    assert audit._exact_pair_special_order(
        {"mission": 7, "mission1target": 99},
        20,
    ) is False
    assert audit._exact_pair_special_order(
        {"mission": 20, "mission1target": 20},
        20,
    ) is True
