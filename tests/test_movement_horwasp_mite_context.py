from __future__ import annotations

from planets_lab.corpus.movement_horwasp_mite_context import (
    classify_scoped_mite_fallback_transition,
    discover_scoped_mite_fallback_runs,
)
from planets_lab.corpus.reconstruction import PerspectiveRecord


MITE_HULLS = frozenset({213})


def _record(*, player_id: int, turn: int, raw: dict[str, object]) -> PerspectiveRecord:
    payload = dict(raw)
    payload.setdefault("ownerid", player_id)
    payload.setdefault("infoturn", turn)
    return PerspectiveRecord(
        player_id=player_id,
        archive_turn=turn,
        embedded_turn=turn,
        infoturn=turn,
        raw=payload,
    )


def _clean_groups() -> dict[tuple[int, int], tuple[PerspectiveRecord, ...]]:
    target_common = {
        "id": 329,
        "ownerid": 3,
        "hullid": 46,
        "name": "TARGET",
        "turn": 10,
    }
    mite_common = {
        "id": 1185,
        "ownerid": 6,
        "hullid": 213,
        "name": "RED MITE",
        "turn": 51,
        "warp": 6,
    }
    return {
        (50, 329): (_record(player_id=3, turn=50, raw={**target_common, "x": 0, "y": 0}),),
        (51, 329): (_record(player_id=3, turn=51, raw={**target_common, "x": 100, "y": 0}),),
        (52, 329): (_record(player_id=3, turn=52, raw={**target_common, "x": 120, "y": 0}),),
        (51, 1185): (
            _record(
                player_id=6,
                turn=51,
                raw={
                    **mite_common,
                    "x": 108,
                    "y": 0,
                    "targetx": 100,
                    "targety": 0,
                    "mission": 7,
                    "mission1target": 329,
                },
            ),
        ),
        (52, 1185): (
            _record(
                player_id=6,
                turn=52,
                raw={
                    **mite_common,
                    "x": 72,
                    "y": 0,
                    "targetx": 0,
                    "targety": 0,
                    "mission": 0,
                    "mission1target": 0,
                },
            ),
        ),
        (53, 1185): (
            _record(
                player_id=6,
                turn=53,
                raw={
                    **mite_common,
                    "x": 36,
                    "y": 0,
                    "targetx": 0,
                    "targety": 0,
                    "mission": 0,
                    "mission1target": 0,
                },
            ),
        ),
    }


def test_discovers_clean_scoped_fallback_origin() -> None:
    runs = discover_scoped_mite_fallback_runs(
        game_id=591478,
        ship_groups=_clean_groups(),
        mite_hulls=MITE_HULLS,
    )

    assert tuple(runs) == (1185,)
    assert len(runs[1185]) == 1
    run = runs[1185][0]
    assert run.tracking_start == 51
    assert run.tracking_end == 51
    assert run.target_id == 329
    assert run.anchor == (0, 0)
    assert run.identity == (6, 213, "RED MITE", 51)


def test_classifies_clean_warp2_fallback_transition() -> None:
    groups = _clean_groups()
    runs = discover_scoped_mite_fallback_runs(
        game_id=591478,
        ship_groups=groups,
        mite_hulls=MITE_HULLS,
    )
    raw = groups[(52, 1185)][0].raw

    category, strong = classify_scoped_mite_fallback_transition(
        game_id=591478,
        before_turn=52,
        ship_id=1185,
        owner_id=6,
        raw=raw,
        origin=(72, 0),
        observed=(36, 0),
        warp=6,
        runs_by_ship=runs,
    )

    assert category == "mite_fallback_navigation_g591478"
    assert strong is True


def test_rejects_same_shape_outside_evidence_scoped_game() -> None:
    groups = _clean_groups()
    runs = discover_scoped_mite_fallback_runs(
        game_id=591478,
        ship_groups=groups,
        mite_hulls=MITE_HULLS,
    )

    category, strong = classify_scoped_mite_fallback_transition(
        game_id=123456,
        before_turn=52,
        ship_id=1185,
        owner_id=6,
        raw=groups[(52, 1185)][0].raw,
        origin=(72, 0),
        observed=(36, 0),
        warp=6,
        runs_by_ship=runs,
    )

    assert category is None
    assert strong is False


def test_rejects_self_waypoint_stop_variant_as_normal_fallback() -> None:
    groups = _clean_groups()
    runs = discover_scoped_mite_fallback_runs(
        game_id=591478,
        ship_groups=groups,
        mite_hulls=MITE_HULLS,
    )
    raw = dict(groups[(52, 1185)][0].raw)
    raw["targetx"] = 72
    raw["targety"] = 0

    category, strong = classify_scoped_mite_fallback_transition(
        game_id=591478,
        before_turn=52,
        ship_id=1185,
        owner_id=6,
        raw=raw,
        origin=(72, 0),
        observed=(72, 0),
        warp=6,
        runs_by_ship=runs,
    )

    assert category is None
    assert strong is False
