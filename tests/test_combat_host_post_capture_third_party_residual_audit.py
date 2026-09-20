from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools" / "diagnostics"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from combat_host_post_capture_third_party_residual_audit import (  # noqa: E402
    _request_matrix,
    _side_projection,
)


def test_side_projection_classifies_ship_and_owner() -> None:
    raw_vcr = {
        "leftownerid": 3,
        "rightownerid": 8,
        "left": {
            "objectid": 7,
            "hullid": 71,
            "raceid": 3,
            "shield": 0,
            "damage": 30,
            "crew": 10,
        },
        "right": {
            "objectid": 48,
            "hullid": 71,
            "raceid": 11,
            "shield": 100,
            "damage": 0,
            "crew": 100,
        },
    }

    left = _side_projection(raw_vcr, "left")
    right = _side_projection(raw_vcr, "right")

    assert left is not None
    assert right is not None
    assert left["object_id"] == 7
    assert left["owner_id"] == 3
    assert left["kind"] == "ship"
    assert right["object_id"] == 48
    assert right["owner_id"] == 8
    assert right["kind"] == "ship"


def test_request_matrix_detects_independent_third_party_attack() -> None:
    ships = {
        7: {
            "ship_id": 7,
            "found": True,
            "owner_id": 5,
            "mission": 0,
            "enemy": 0,
        },
        48: {
            "ship_id": 48,
            "found": True,
            "owner_id": 8,
            "mission": 3,
            "enemy": 3,
        },
    }

    rows = _request_matrix(ships, owners=(3, 5, 8))

    request = {
        (row["ship_id"], row["target_owner_id"]): row["requests_combat"]
        for row in rows
    }
    assert request[(48, 3)] is True
    assert request[(7, 8)] is False
