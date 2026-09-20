from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_mixed_ship_planet_queue_batch_audit import (  # noqa: E402
    _capture_reset_priority_order,
    _effective_planet_owner,
    _planet_pair,
    _production_planet_order,
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



def test_production_planet_order_matches_ordinary_priority() -> None:
    rows = [
        {
            "ship": {"object_id": 20},
            "ship_tminus1": {
                "resolved": True,
                "mission": 3,
                "enemy": 0,
                "friendlycode": "100",
            },
            "post_capture": False,
        },
        {
            "ship": {"object_id": 30},
            "ship_tminus1": {
                "resolved": True,
                "mission": 0,
                "enemy": 7,
                "friendlycode": "abc",
            },
            "post_capture": False,
        },
    ]

    result = _production_planet_order(rows)

    assert result["comparable"] is True
    assert result["predicted_ship_order"] == [20, 30]
    assert result["exact"] is True


def test_production_planet_order_applies_capture_reset_priority() -> None:
    rows = [
        {
            "ship": {"object_id": 20},
            "ship_tminus1": {
                "resolved": True,
                "mission": 3,
                "enemy": 0,
                "friendlycode": "100",
            },
            "post_capture": False,
        },
        {
            "ship": {"object_id": 30},
            "ship_tminus1": {
                "resolved": True,
                "mission": 3,
                "enemy": 7,
                "friendlycode": "abc",
            },
            "post_capture": True,
        },
    ]

    result = _production_planet_order(rows)

    assert result["comparable"] is True
    assert result["predicted_ship_order"] == [20, 30]
    assert result["exact"] is True



def test_effective_planet_owner_repairs_impossible_same_owner_from_race_map() -> None:
    result = _effective_planet_owner(
        ship_owner_id=10,
        vcr_planet_owner_id=10,
        planet_race_id=4,
        race_owner_map={4: 7, 10: 10},
        tminus1_owner_id=10,
        current_owner_id=7,
    )

    assert result["resolved"] is True
    assert result["owner_id"] == 7
    assert result["source"] == "same_owner_vcr_repaired_by_race_map"
    assert result["current_owner_confirms_race_map"] is True


def test_effective_planet_owner_prefers_foreign_vcr_owner_without_repair() -> None:
    result = _effective_planet_owner(
        ship_owner_id=3,
        vcr_planet_owner_id=6,
        planet_race_id=8,
        race_owner_map={8: 6},
        tminus1_owner_id=6,
        current_owner_id=6,
    )

    assert result["resolved"] is True
    assert result["owner_id"] == 6
    assert result["source"] == "vcr_owner_foreign"


def test_capture_reset_priority_clears_old_aggression_but_keeps_numeric_fc() -> None:
    rows = [
        {
            "ship": {"object_id": 489},
            "ship_tminus1": {
                "resolved": True,
                "mission": 6,
                "enemy": 6,
                "friendlycode": "yis",
            },
            "post_capture": False,
        },
        {
            "ship": {"object_id": 480},
            "ship_tminus1": {
                "resolved": True,
                "mission": 3,
                "enemy": 3,
                "friendlycode": "ysD",
            },
            "post_capture": True,
        },
    ]

    result = _capture_reset_priority_order(rows)

    assert result["comparable"] is True
    assert result["predicted_ship_order"] == [489, 480]
    assert result["exact"] is True


def test_capture_reset_priority_preserves_numeric_fc_priority() -> None:
    rows = [
        {
            "ship": {"object_id": 34},
            "ship_tminus1": {
                "resolved": True,
                "mission": 8,
                "enemy": 0,
                "friendlycode": "999",
            },
            "post_capture": True,
        },
        {
            "ship": {"object_id": 67},
            "ship_tminus1": {
                "resolved": True,
                "mission": 2,
                "enemy": 6,
                "friendlycode": "md7",
            },
            "post_capture": False,
        },
    ]

    result = _capture_reset_priority_order(rows)

    assert result["comparable"] is True
    assert result["predicted_ship_order"] == [34, 67]
    assert result["exact"] is True


def test_capture_reset_priority_fails_closed_without_tminus1_fc() -> None:
    rows = [
        {
            "ship": {"object_id": 5},
            "ship_tminus1": {
                "resolved": True,
                "mission": 1,
                "enemy": 0,
                "friendlycode": "vcr",
            },
            "post_capture": True,
        },
        {
            "ship": {"object_id": 68},
            "ship_tminus1": {
                "resolved": False,
                "reason": "ship_tminus1_unresolved",
            },
            "post_capture": True,
        },
    ]

    result = _capture_reset_priority_order(rows)

    assert result["comparable"] is False
    assert result["reason"] == "ship_tminus1_unresolved"
