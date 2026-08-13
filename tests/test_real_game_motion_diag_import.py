from planets_lab.validation.real_game import ObservationBatch, ObservationStreamKey, RealGameTransition
from planets_lab.validation.real_game_motion_diag import diagnose


def _batch(turn: int, x1: int, x2: int) -> ObservationBatch:
    return ObservationBatch(
        game_id=680933,
        turn=turn,
        batch_id=turn,
        stream=ObservationStreamKey(10, 1, "planets.nu/loadturn"),
        snapshot_hash=f"diag-{turn}",
        players=({"id": 1, "username": "P1", "raceid": 1},),
        planets=(),
        ships=(
            {"id": 1, "ownerid": 1, "hullid": 16, "x": x1, "y": 100, "targetx": 110, "targety": 100, "warp": 9, "mission": 0, "neutronium": 20},
            {"id": 2, "ownerid": 1, "hullid": 16, "x": x2, "y": 200, "targetx": 220, "targety": 200, "warp": 9, "mission": 0, "neutronium": 0},
        ),
        starbases=(),
    )


def test_motion_diagnostics_classify_explained_cases() -> None:
    before = _batch(7, 100, 200)
    after = _batch(8, 110, 200)
    result = diagnose((RealGameTransition(before, after),))

    assert result["categories"]["reachable_exact"] == 1
    assert result["categories"]["reachable_stayed_no_fuel"] == 1
    assert result["total"] == 2
    assert result["explained"] == 2
    assert result["unresolved"] == 0
    assert result["rows"] == ()
