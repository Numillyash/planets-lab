from planets_lab.corpus.movement_horwasp_state_linkage import (
    safe_history_entries,
    sign_step_toward,
)
from planets_lab.corpus.movement_topology_diagnostics import MapTopologyEvidence


def _topology(*, sphere: bool, width: int, height: int) -> MapTopologyEvidence:
    return MapTopologyEvidence(
        sphere=sphere,
        mapwidth=width,
        mapheight=height,
        mapshape=1 if sphere else 0,
        first_member="first.trn",
        last_member="last.trn",
        stable=True,
        first_candidates={},
        last_candidates={},
    )


def test_sign_step_toward_uses_wrapped_shortest_vector() -> None:
    topology = _topology(sphere=True, width=2150, height=2150)
    assert sign_step_toward((938, 2986), (830, 3101), topology) == (-1, 1)
    assert sign_step_toward((3074, 3043), (3013, 3124), topology) == (-1, 1)


def test_sign_step_toward_handles_cardinal_and_stationary_axes() -> None:
    topology = _topology(sphere=False, width=800, height=800)
    assert sign_step_toward((10, 10), (10, 15), topology) == (0, 1)
    assert sign_step_toward((10, 10), (4, 10), topology) == (-1, 0)
    assert sign_step_toward((10, 10), (10, 10), topology) == (0, 0)


def test_safe_history_entries_only_keeps_navigation_numeric_values() -> None:
    raw = {
        "history": [
            {
                "x": 100,
                "y": 200,
                "turn": 7,
                "heading": 303,
                "name": "do not expose",
                "friendlycode": "abc",
                "ownerid": 8,
            },
            {"targetx": 300, "targety": 400, "warp": 6, "note": "secret"},
        ]
    }
    assert safe_history_entries(raw) == (
        {"heading": 303, "turn": 7, "x": 100, "y": 200},
        {"targetx": 300, "targety": 400, "warp": 6},
    )


def test_safe_history_entries_handles_mapping_container() -> None:
    raw = {
        "history": {
            "first": {"x": 1, "y": 2, "turn": 3, "text": "drop"},
            "second": [{"x": 4, "y": 5, "heading": 90}],
        }
    }
    assert safe_history_entries(raw) == (
        {"turn": 3, "x": 1, "y": 2},
        {"heading": 90, "x": 4, "y": 5},
    )
