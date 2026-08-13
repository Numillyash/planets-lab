from planets_lab.validation.real_game import ObservationBatch, ObservationStreamKey, RealGameTransition
from planets_lab.validation.real_game_motion import summarize_motion


def _batch(turn: int, x1: int, y1: int, x2: int, y2: int) -> ObservationBatch:
    ships = (
        {"id": 1, "ownerid": 1, "hullid": 16, "x": x1, "y": y1, "targetx": 110, "targety": 100, "warp": 9, "mission": 0},
        {"id": 2, "ownerid": 1, "hullid": 16, "x": x2, "y": y2, "targetx": 200, "targety": 200, "warp": 9, "mission": 0},
    )
    return ObservationBatch(
        game_id=680933,
        turn=turn,
        batch_id=turn,
        stream=ObservationStreamKey(10, 1, "planets.nu/loadturn"),
        snapshot_hash=f"hash-{turn}",
        players=({"id": 1, "username": "P1", "raceid": 1},),
        planets=(),
        ships=ships,
        starbases=(),
    )


def test_motion_summary_uses_observed_next_turn() -> None:
    before = _batch(7, 100, 100, 100, 100)
    after = _batch(8, 110, 100, 157, 157)
    summary = summarize_motion((RealGameTransition(before, after),))

    assert summary["source_ship_pairs"] == 2
    assert summary["moved"] == 2
    assert summary["ordinary_cases"] == 2
    assert summary["reachable_cases"] == 1
    assert summary["reachable_matches"] == 1
    assert summary["partial_cases"] == 1
    assert summary["rounding_scores"]["nearest"] == (1, 1)
    assert summary["rounding_scores"]["ceil"] == (0, 1)
