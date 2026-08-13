import json

from planets_lab.validation.real_game import (
    SCHEMA,
    consecutive_transitions,
    latest_batches_by_stream_turn,
    load_jsonl,
    summarize,
)


def _record(turn: int, batch_id: int, *, x: int = 100) -> dict:
    return {
        "schema": SCHEMA,
        "game_id": 680933,
        "turn": turn,
        "batch_id": batch_id,
        "observer_planets_account_id": 10,
        "source_player_slot_id": 1,
        "source": "planets.nu/loadturn",
        "snapshot_hash": f"hash-{batch_id}",
        "players": [
            {
                "id": 1,
                "accountid": 100,
                "username": "observer",
                "raceid": 1,
                "status": 1,
            }
        ],
        "planets": [
            {
                "id": 1,
                "x": x,
                "y": 200,
                "ownerid": 1,
                "clans": 100,
            }
        ],
        "ships": [],
        "starbases": [],
    }


def test_real_game_jsonl_builds_consecutive_transition_and_imports(tmp_path) -> None:
    path = tmp_path / "game.jsonl"
    records = [_record(20, 1), _record(21, 2, x=101)]
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )

    batches = load_jsonl(path)
    summary = summarize(batches)
    transitions = consecutive_transitions(batches)

    assert summary.records == 2
    assert summary.streams == 1
    assert summary.consecutive_transitions == 1
    assert len(transitions) == 1
    assert transitions[0].before.turn == 20
    assert transitions[0].after.turn == 21

    state = transitions[0].before.import_state()
    assert state.game_id == 680933
    assert state.turn == 20
    assert state.players[1].race_id == 1
    assert state.planets[1].cargo.clans == 100


def test_latest_snapshot_wins_within_same_stream_turn() -> None:
    batches = tuple(
        __import__("planets_lab.validation.real_game", fromlist=["parse_record"]).parse_record(record)
        for record in [_record(20, 1, x=100), _record(20, 3, x=103)]
    )
    latest = latest_batches_by_stream_turn(batches)
    summary = summarize(batches)

    assert len(latest) == 1
    assert latest[0].batch_id == 3
    assert latest[0].planets[0]["x"] == 103
    assert summary.duplicate_turn_snapshots == 1
