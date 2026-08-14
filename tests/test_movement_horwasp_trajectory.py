import pytest

from planets_lab.corpus.movement_horwasp_trajectory import (
    _bearing,
    _distance_class,
    _safe_waypoints,
    _vector,
)
from planets_lab.corpus.movement_topology_diagnostics import MapTopologyEvidence


def _sphere() -> MapTopologyEvidence:
    return MapTopologyEvidence(
        sphere=True,
        mapwidth=2150,
        mapheight=2150,
        mapshape=1,
        first_member="first.trn",
        last_member="last.trn",
        stable=True,
        first_candidates={},
        last_candidates={},
    )


def test_sphere_vector_uses_shortest_wrapped_delta() -> None:
    assert _vector((938, 2986), (3084, 3012), _sphere()) == (-4, 26)
    assert _vector((1143, 3058), (1183, 959), _sphere()) == (40, 51)


def test_planets_compass_bearing_matches_heading_convention() -> None:
    assert _bearing(-108, 115) == pytest.approx(316.8, abs=0.2)
    assert _bearing(10, 0) == pytest.approx(90.0)
    assert _bearing(0, -10) == pytest.approx(180.0)


def test_safe_waypoints_only_keeps_numeric_navigation_fields() -> None:
    raw = {
        "waypoints": [
            {"x": 100, "y": 200, "planetid": 7, "name": "secret", "friendlycode": "abc"},
            {"targetx": 300, "targety": 400, "heading": 90, "note": "private"},
        ]
    }
    assert _safe_waypoints(raw) == (
        {"planetid": 7, "x": 100, "y": 200},
        {"heading": 90, "targetx": 300, "targety": 400},
    )


def test_documented_horwasp_speed_buckets_are_diagnostic_only() -> None:
    assert _distance_class(36.0, 6) == "near_normal_max"
    assert _distance_class(54.0, 6) == "near_accelerated_max"
    assert _distance_class(45.0, 6) == "between_normal_and_accelerated"
    assert _distance_class(60.0, 6) == "above_accelerated_max"


def test_trajectory_cli_imports() -> None:
    from planets_lab.corpus.movement_horwasp_trajectory_cli import main

    assert callable(main)
