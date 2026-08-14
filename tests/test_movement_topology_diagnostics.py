import io
import json
import zipfile

from planets_lab.corpus.movement_topology_diagnostics import (
    extract_map_topology,
    sphere_adjusted_sample,
    wrapped_delta,
)
from planets_lab.validation.movement_geometry import MovementSample


def _payload(turn: int) -> dict:
    return {
        "game": {"id": 7, "turn": turn},
        "player": {"id": 1},
        "players": [{"id": 1}],
        "settings": {
            "sphere": True,
            "mapwidth": 2100,
            "mapheight": 2100,
            "mapshape": 1,
        },
    }


def test_extracts_stable_sphere_settings_from_archive() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("player1-turn0.trn", json.dumps(_payload(0)))
        archive.writestr("player1-turn1.trn", json.dumps(_payload(1)))

    topology = extract_map_topology(buffer.getvalue())
    assert topology.sphere is True
    assert topology.mapwidth == 2100
    assert topology.mapheight == 2100
    assert topology.mapshape == 1
    assert topology.stable is True


def test_wrapped_delta_uses_shortest_sphere_vector() -> None:
    assert wrapped_delta(938, 3084, 2100) == 46
    assert wrapped_delta(3058, 959, 2100) == 1
    assert wrapped_delta(100, 2090, 2000) == -10


def test_sphere_adjusts_target_and_observation_near_origin() -> None:
    sample = MovementSample(
        turn=10,
        ship_id=5,
        x=100,
        y=100,
        target_x=2090,
        target_y=100,
        warp=4,
        next_x=2090,
        next_y=100,
    )
    adjusted = sphere_adjusted_sample(sample, width=2000, height=2000)
    assert (adjusted.target_x, adjusted.target_y) == (90, 100)
    assert adjusted.observed_destination == (90, 100)
    assert adjusted.observed_distance == 10


def test_topology_diagnostics_cli_imports() -> None:
    from planets_lab.corpus.movement_topology_diagnostics_cli import main

    assert callable(main)
