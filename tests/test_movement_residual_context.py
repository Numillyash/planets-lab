from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.movement_residual_context import (
    aggregate_movement_residual_context_games,
    evaluate_movement_residual_context,
    summarize_movement_residual_context_game,
)
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot


def _snapshot(player: int, turn: int, *, ships=(), planets=(), ionstorms=()):
    return ArchiveTurnSnapshot(
        member=TurnMember(player=player, turn=turn, name=f"player{player}-turn{turn}.trn"),
        game_id=7,
        player_id=player,
        embedded_turn=turn,
        snapshot_hash=f"{player}-{turn}",
        mechanics_payload={
            "planets": list(planets),
            "ships": list(ships),
            "starbases": [],
            "ionstorms": list(ionstorms),
        },
    )


def _ship(
    turn: int,
    *,
    ship_id=10,
    owner=1,
    hullid=3,
    x=100,
    y=100,
    targetx=125,
    targety=100,
    warp=5,
    mission=0,
    mission1target=0,
):
    return {
        "id": ship_id,
        "ownerid": owner,
        "hullid": hullid,
        "x": x,
        "y": y,
        "warp": warp,
        "targetx": targetx,
        "targety": targety,
        "mission": mission,
        "mission1target": mission1target,
        "friendlycode": "abc",
        "infoturn": turn,
    }


def test_gravitonic_residual_is_explained() -> None:
    summary = evaluate_movement_residual_context(
        (
            _snapshot(1, 10, ships=[_ship(10, hullid=46, targetx=200)]),
            _snapshot(1, 11, ships=[_ship(11, hullid=46, x=150, targetx=200)]),
        )
    )
    assert summary.baseline_unresolved == 1
    assert summary.context_explained == 1
    assert summary.residual_unresolved == 0
    assert summary.context_counts == {"gravitonic_partial_host_major_minor": 1}


def test_observed_tow_target_match_explains_external_target_move() -> None:
    before = [
        _ship(10, ship_id=10, mission=6, mission1target=20, targetx=125),
        _ship(10, ship_id=20, warp=0, targetx=100),
    ]
    after = [
        _ship(11, ship_id=10, x=125, targetx=125, mission=6, mission1target=20),
        _ship(11, ship_id=20, x=125, warp=0, targetx=100),
    ]
    summary = evaluate_movement_residual_context(
        (
            _snapshot(1, 10, ships=before),
            _snapshot(1, 11, ships=after),
        )
    )
    assert summary.move_most_candidates == 1
    assert summary.baseline_unresolved == 1
    assert summary.context_counts == {"observed_tow_target_match": 1}
    assert summary.tow_context_counts["observed_tow_target_match"] == 1
    assert summary.residual_unresolved == 0


def test_resolved_next_turn_ion_storm_drag_explains_external_move() -> None:
    storm = {
        "id": 1,
        "x": 100,
        "y": 100,
        "radius": 100,
        "voltage": 200,
        "warp": 6,
        "heading": 90,
        "parentid": 0,
    }
    summary = evaluate_movement_residual_context(
        (
            _snapshot(1, 10, ships=[_ship(10, warp=0, targetx=100)], ionstorms=[]),
            _snapshot(
                1,
                11,
                ships=[_ship(11, x=127, warp=0, targetx=100)],
                ionstorms=[storm],
            ),
        )
    )
    assert summary.baseline_unresolved == 1
    assert summary.context_counts == {"ion_storm_drag": 1}
    assert summary.storm_context_counts["resolved_drag"] == 1
    assert summary.residual_unresolved == 0


def test_residual_context_game_and_corpus_aggregation() -> None:
    row = summarize_movement_residual_context_game(
        game_id=7,
        settings_hash="a" * 64,
        snapshots=(
            _snapshot(1, 10, ships=[_ship(10, hullid=46, targetx=200)]),
            _snapshot(1, 11, ships=[_ship(11, hullid=46, x=150, targetx=200)]),
        ),
    )
    stats = aggregate_movement_residual_context_games([row], failed_game_ids=[99, 99])
    assert stats["games_indexed"] == 1
    assert stats["games_failed"] == 1
    assert stats["failed_game_ids"] == [99]
    assert stats["totals"]["context_explained"] == 1
    assert stats["context_counts"] == {"gravitonic_partial_host_major_minor": 1}
    assert stats["context_counts_by_settings_hash"]["a" * 64] == {
        "gravitonic_partial_host_major_minor": 1
    }


def test_movement_residual_context_cli_imports() -> None:
    from planets_lab.corpus.movement_residual_context_corpus_cli import main

    assert callable(main)
