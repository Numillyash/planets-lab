from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.movement_context import (
    GHOST,
    HYP,
    INTERCEPT,
    MOVE_MOST_CANDIDATE,
    TOW_ATTEMPT,
    aggregate_movement_context_games,
    evaluate_movement_context,
    summarize_movement_context_game,
)
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot


def _snapshot(player: int, turn: int, *, ships=()):
    return ArchiveTurnSnapshot(
        member=TurnMember(player=player, turn=turn, name=f"player{player}-turn{turn}.trn"),
        game_id=7,
        player_id=player,
        embedded_turn=turn,
        snapshot_hash=f"{player}-{turn}",
        mechanics_payload={
            "planets": [],
            "starbases": [],
            "ships": list(ships),
        },
    )


def _ship(turn: int, *, owner: int = 1, mission=0, friendlycode="abc", x=100):
    return {
        "id": 10,
        "ownerid": owner,
        "hullid": 3,
        "x": x,
        "y": 200,
        "warp": 6,
        "targetx": 130,
        "targety": 240,
        "mission": mission,
        "friendlycode": friendlycode,
        "infoturn": turn,
    }


def test_context_uses_owner_perspective_not_other_observer_mission() -> None:
    snapshots = (
        _snapshot(1, 10, ships=[_ship(10, mission=6)]),
        _snapshot(2, 10, ships=[_ship(10, mission=7)]),
        _snapshot(1, 11, ships=[_ship(11, mission=0, x=130)]),
        _snapshot(2, 11, ships=[_ship(11, mission=0, x=130)]),
    )
    summary = evaluate_movement_context(snapshots)
    assert summary.geometry_ready == 1
    assert summary.classified == 1
    assert summary.intent_counts == {TOW_ATTEMPT: 1}
    assert summary.issue_counts == {}


def test_context_owner_hyp_and_intercept_match_simulator_precedence() -> None:
    hyp = (
        _snapshot(1, 10, ships=[_ship(10, mission=0, friendlycode="HYP")]),
        _snapshot(1, 11, ships=[_ship(11, x=130)]),
    )
    assert evaluate_movement_context(hyp).intent_counts == {HYP: 1}

    intercept = (
        _snapshot(1, 10, ships=[_ship(10, mission=7, friendlycode="HYP")]),
        _snapshot(1, 11, ships=[_ship(11, x=130)]),
    )
    assert evaluate_movement_context(intercept).intent_counts == {INTERCEPT: 1}


def test_context_ghost_ignores_stale_order_fields() -> None:
    snapshots = (
        _snapshot(4, 10, ships=[_ship(10, owner=0, mission=6)]),
        _snapshot(7, 10, ships=[_ship(10, owner=0, mission=7)]),
        _snapshot(4, 11, ships=[_ship(11, owner=0, x=100)]),
        _snapshot(7, 11, ships=[_ship(11, owner=0, x=100)]),
    )
    summary = evaluate_movement_context(snapshots)
    assert summary.intent_counts == {GHOST: 1}
    assert summary.classified == 1


def test_context_does_not_guess_orders_without_owner_perspective() -> None:
    snapshots = (
        _snapshot(2, 10, ships=[_ship(10, owner=1, mission=6)]),
        _snapshot(3, 10, ships=[_ship(10, owner=1, mission=7)]),
        _snapshot(2, 11, ships=[_ship(11, owner=1, x=130)]),
        _snapshot(3, 11, ships=[_ship(11, owner=1, x=130)]),
    )
    summary = evaluate_movement_context(snapshots)
    assert summary.geometry_ready == 1
    assert summary.classified == 0
    assert summary.issue_counts == {
        "before.ship.owner_context.owner_record_count": 1,
    }


def test_context_default_move_most_and_corpus_aggregation() -> None:
    snapshots = (
        _snapshot(1, 10, ships=[_ship(10)]),
        _snapshot(1, 11, ships=[_ship(11, x=130)]),
    )
    summary = evaluate_movement_context(snapshots)
    assert summary.intent_counts == {MOVE_MOST_CANDIDATE: 1}

    row = summarize_movement_context_game(
        game_id=7,
        settings_hash="a" * 64,
        snapshots=snapshots,
    )
    stats = aggregate_movement_context_games([row], failed_game_ids=[99, 99])
    assert stats["games_indexed"] == 1
    assert stats["games_failed"] == 1
    assert stats["intent_counts"] == {MOVE_MOST_CANDIDATE: 1}
    assert stats["intent_counts_by_settings_hash"]["a" * 64] == {
        MOVE_MOST_CANDIDATE: 1
    }


def test_movement_context_corpus_cli_imports() -> None:
    from planets_lab.corpus.movement_context_corpus_cli import main

    assert callable(main)
