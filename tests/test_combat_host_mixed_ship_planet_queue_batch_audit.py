from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_mixed_ship_planet_queue_batch_audit import (  # noqa: E402
    _planet_pair,
    _same_planet_priority_group,
    _shape,
    _site_profile,
)


def _ship(object_id: int, owner_id: int) -> dict[str, object]:
    return {
        "objectid": object_id,
        "hullid": 20,
        "raceid": owner_id,
    }


def _planet(object_id: int) -> dict[str, object]:
    return {
        "objectid": object_id,
        "hullid": 0,
        "raceid": 2,
    }


def test_shape_and_planet_pair_classify_both_orientations() -> None:
    right_planet = {
        "leftownerid": 3,
        "rightownerid": 8,
        "left": _ship(10, 3),
        "right": _planet(50),
    }
    left_planet = {
        "leftownerid": 8,
        "rightownerid": 3,
        "left": _planet(50),
        "right": _ship(10, 3),
    }

    assert _shape(right_planet) == "ship_vs_planet"
    assert _shape(left_planet) == "ship_vs_planet"

    ship, planet = _planet_pair(right_planet) or ({}, {})
    assert ship["side"] == "left"
    assert ship["object_id"] == 10
    assert planet["side"] == "right"
    assert planet["object_id"] == 50

    ship, planet = _planet_pair(left_planet) or ({}, {})
    assert ship["side"] == "right"
    assert planet["side"] == "left"


def test_shape_classifies_ship_vs_ship() -> None:
    raw = {
        "leftownerid": 3,
        "rightownerid": 8,
        "left": _ship(10, 3),
        "right": _ship(11, 8),
    }

    assert _shape(raw) == "ship_vs_ship"
    assert _planet_pair(raw) is None


def test_site_profile_preserves_factual_mixed_order() -> None:
    rows = [
        {"shape": "ship_vs_ship"},
        {"shape": "ship_vs_ship"},
        {"shape": "ship_vs_planet"},
        {"shape": "ship_vs_planet"},
    ]

    assert _site_profile(rows) == "SSPP"


def test_repeated_planet_group_compares_standard_priority_order() -> None:
    rows = [
        {
            "ship": {"object_id": 20},
            "ship_tminus1": {
                "resolved": True,
                "priority_key": [0, 100, 20],
            },
        },
        {
            "ship": {"object_id": 30},
            "ship_tminus1": {
                "resolved": True,
                "priority_key": [3, 30, 0],
            },
        },
    ]

    result = _same_planet_priority_group(rows)

    assert result["comparable"] is True
    assert result["factual_ship_order"] == [20, 30]
    assert result["expected_standard_priority_order"] == [20, 30]
    assert result["exact"] is True


def test_repeated_planet_group_detects_priority_mismatch() -> None:
    rows = [
        {
            "ship": {"object_id": 30},
            "ship_tminus1": {
                "resolved": True,
                "priority_key": [3, 30, 0],
            },
        },
        {
            "ship": {"object_id": 20},
            "ship_tminus1": {
                "resolved": True,
                "priority_key": [0, 100, 20],
            },
        },
    ]

    result = _same_planet_priority_group(rows)

    assert result["comparable"] is True
    assert result["exact"] is False


def test_repeated_planet_group_fails_closed_on_unresolved_priority() -> None:
    rows = [
        {
            "ship": {"object_id": 20},
            "ship_tminus1": {
                "resolved": False,
                "reason": "priority_unresolved",
            },
        },
        {
            "ship": {"object_id": 30},
            "ship_tminus1": {
                "resolved": True,
                "priority_key": [3, 30, 0],
            },
        },
    ]

    result = _same_planet_priority_group(rows)

    assert result["comparable"] is False
    assert result["reason"] == "ship_priority_unresolved"
