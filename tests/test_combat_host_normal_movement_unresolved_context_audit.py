from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_normal_movement_unresolved_context_audit import (  # noqa: E402
    RESIDUAL_SCHEMA,
    _matching_scaled_floor_hits,
    _unresolved_rows,
    _vcr_ship_starts,
)


def test_unresolved_rows_selects_only_unresolved_population() -> None:
    report = {
        "schema": RESIDUAL_SCHEMA,
        "rows": [
            {"ship_id": 1, "context_status": "unresolved"},
            {"ship_id": 2, "context_status": "single_exact_context_family"},
            {"ship_id": 3, "context_status": "unresolved"},
        ],
    }
    assert [row["ship_id"] for row in _unresolved_rows(report)] == [1, 3]


def test_unresolved_rows_rejects_wrong_schema() -> None:
    with pytest.raises(ValueError, match="residual report schema"):
        _unresolved_rows({"schema": "wrong", "rows": []})


def test_scaled_floor_one_hit_matches_super_star_destroyer_residual_geometry() -> None:
    matches = _matching_scaled_floor_hits(
        origin=(1744, 1460),
        target=(1783, 1437),
        factual_site=(1773, 1443),
        nominal_distance=49.0,
        regular_distance=45.27692569068709,
        max_hits=3,
    )
    assert matches == (
        {
            "slowdown_hits": 1,
            "endpoint": [1773, 1443],
            "major_axis_penalty": 10,
        },
    )


def test_scaled_floor_one_hit_matches_scorpius_residual_geometry() -> None:
    matches = _matching_scaled_floor_hits(
        origin=(2315, 1984),
        target=(2312, 1924),
        factual_site=(2313, 1937),
        nominal_distance=81.0,
        regular_distance=60.07495318350236,
        max_hits=3,
    )
    assert matches == (
        {
            "slowdown_hits": 1,
            "endpoint": [2313, 1937],
            "major_axis_penalty": 13,
        },
    )


def test_vcr_ship_starts_filters_ship_and_factual_site() -> None:
    rows = [
        {
            "vcr_id": 7,
            "payload": {
                "x": 100,
                "y": 200,
                "left": {
                    "objectid": 42,
                    "damage": 30,
                    "shield": 100,
                    "mass": 400,
                    "crew": 100,
                    "hullid": 69,
                    "raceid": 8,
                },
                "right": {"objectid": 9, "damage": 0},
            },
        },
        {
            "vcr_id": 8,
            "payload": {
                "x": 101,
                "y": 200,
                "left": {"objectid": 42, "damage": 60},
                "right": {"objectid": 10, "damage": 0},
            },
        },
    ]
    starts = _vcr_ship_starts(rows, ship_id=42, factual_site=(100, 200))
    assert starts == (
        {
            "vcr_id": 7,
            "side": "left",
            "damage": 30,
            "shield": 100,
            "mass": 400,
            "crew": 100,
            "hullid": 69,
            "raceid": 8,
        },
    )
