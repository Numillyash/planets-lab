from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.movement_differential import (
    aggregate_movement_differential_games,
    evaluate_movement_differential,
    summarize_movement_differential_game,
)
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot


def _snapshot(player: int, turn: int, *, ships=(), planets=()):
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
        },
    )


def _ship(turn: int, *, x=100, y=100, targetx=125, targety=100, warp=5, **extra):
    raw = {
        "id": 10,
        "ownerid": 1,
        "hullid": 3,
        "x": x,
        "y": y,
        "warp": warp,
        "targetx": targetx,
        "targety": targety,
        "mission": 0,
        "friendlycode": "abc",
        "infoturn": turn,
    }
    raw.update(extra)
    return raw


def test_reachable_exact_is_explained() -> None:
    summary = evaluate_movement_differential(
        (
            _snapshot(1, 10, ships=[_ship(10)]),
            _snapshot(1, 11, ships=[_ship(11, x=125, y=100)]),
        )
    )
    assert summary.geometry_ready == 1
    assert summary.move_most_candidates == 1
    assert summary.category_counts == {"reachable_exact": 1}
    assert summary.geometrically_explained == 1
    assert summary.unresolved == 0


def test_partial_host_major_minor_is_explained() -> None:
    summary = evaluate_movement_differential(
        (
            _snapshot(1, 10, ships=[_ship(10, targetx=200, targety=200)]),
            _snapshot(1, 11, ships=[_ship(11, x=118, y=118, targetx=200, targety=200)]),
        )
    )
    assert summary.category_counts == {"partial_host_major_minor": 1}
    assert summary.geometrically_explained == 1


def test_reachable_warp_well_match_is_explained() -> None:
    planet10 = {"id": 5, "ownerid": 0, "x": 120, "y": 100, "infoturn": 10}
    planet11 = {"id": 5, "ownerid": 0, "x": 120, "y": 100, "infoturn": 11}
    summary = evaluate_movement_differential(
        (
            _snapshot(
                1,
                10,
                ships=[_ship(10, targetx=122, targety=100)],
                planets=[planet10],
            ),
            _snapshot(
                1,
                11,
                ships=[_ship(11, x=120, y=100, targetx=122, targety=100)],
                planets=[planet11],
            ),
        )
    )
    assert summary.category_counts == {"reachable_warp_well_match": 1}
    assert summary.geometrically_explained == 1


def test_hyp_is_excluded_from_move_most_geometry() -> None:
    summary = evaluate_movement_differential(
        (
            _snapshot(1, 10, ships=[_ship(10, friendlycode="HYP")]),
            _snapshot(1, 11, ships=[_ship(11, x=125, y=100, friendlycode="HYP")]),
        )
    )
    assert summary.geometry_ready == 1
    assert summary.classified_context == 1
    assert summary.move_most_candidates == 0
    assert summary.evaluated_move_most == 0
    assert summary.excluded_intent_counts == {"hyp": 1}


def test_above_nominal_is_unresolved_and_grouped_by_hull() -> None:
    summary = evaluate_movement_differential(
        (
            _snapshot(1, 10, ships=[_ship(10, targetx=200, targety=100, hullid=99)]),
            _snapshot(1, 11, ships=[_ship(11, x=150, y=100, targetx=200, targety=100, hullid=99)]),
        )
    )
    assert summary.category_counts == {"above_nominal": 1}
    assert summary.geometrically_explained == 0
    assert summary.unresolved == 1
    assert summary.unresolved_hull_counts == {99: 1}


def test_movement_differential_game_and_corpus_aggregation() -> None:
    row = summarize_movement_differential_game(
        game_id=7,
        settings_hash="a" * 64,
        snapshots=(
            _snapshot(1, 10, ships=[_ship(10)]),
            _snapshot(1, 11, ships=[_ship(11, x=125, y=100)]),
        ),
    )
    stats = aggregate_movement_differential_games([row], failed_game_ids=[99, 99])
    assert stats["games_indexed"] == 1
    assert stats["games_failed"] == 1
    assert stats["failed_game_ids"] == [99]
    assert stats["totals"]["geometrically_explained"] == 1
    assert stats["category_counts"] == {"reachable_exact": 1}
    assert stats["category_counts_by_settings_hash"]["a" * 64] == {"reachable_exact": 1}


def test_movement_differential_cli_imports() -> None:
    from planets_lab.corpus.movement_differential_corpus_cli import main

    assert callable(main)
