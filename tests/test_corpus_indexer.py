from __future__ import annotations

import io
import json
import zipfile

import pytest

from planets_lab.corpus.indexer import (
    CorpusIndexError,
    aggregate_corpus_index,
    index_game_archive,
    load_manifest_jsonl,
)
from planets_lab.corpus.manifest import MANIFEST_SCHEMA


def _turn_payload(game_id: int, player_id: int, turn: int) -> dict:
    ships = [
        {
            "id": 10 + player_id,
            "ownerid": player_id,
            "hullid": 1,
            "x": 1000 + turn,
            "y": 1000,
            "warp": 0,
            "crew": -1,
            "mission": 6 if player_id == 1 else 7,
            "friendlycode": "HYP" if turn == 1 else "abc",
        }
    ]
    if player_id == 2 and turn == 1:
        ships.append(
            {
                "id": 99,
                "ownerid": 0,
                "hullid": 2,
                "x": 1200,
                "y": 1300,
                "warp": 0,
                "crew": 0,
            }
        )
    return {
        "game": {"id": game_id, "turn": turn},
        "player": {
            "id": player_id,
            "raceid": player_id,
            "username": "must-not-propagate",
            "email": "private@example.invalid",
            "savekey": "secret",
        },
        "players": [
            {"id": 1, "raceid": 1, "username": "private-one"},
            {"id": 2, "raceid": 7, "username": "private-two"},
        ],
        "planets": [],
        "ships": ships,
        "starbases": [],
        "ionstorms": (
            [{"id": 1, "x": 1, "y": 2, "radius": 3, "voltage": 4, "warp": 5, "heading": 6}]
            if turn == 1
            else []
        ),
        "minefields": ([{"id": 50, "ownerid": 2, "x": 5, "y": 6, "radius": 20}] if player_id == 2 else []),
        "messages": [{"body": "private"}],
    }


def _archive(game_id: int = 42) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for player_id in (1, 2):
            for turn in (0, 1):
                archive.writestr(
                    f"player{player_id}-turn{turn}.trn",
                    json.dumps(_turn_payload(game_id, player_id, turn)),
                )
    return buffer.getvalue()


def _manifest(game_id: int = 42) -> dict:
    return {
        "schema": MANIFEST_SCHEMA,
        "game_id": game_id,
        "tier": "B",
        "settings_hash": "a" * 64,
        "game": {
            "id": game_id,
            "turn": 2,
            "dateended": "8/14/2026 1:00:00 PM",
            "gametype": 2,
            "iscustom": False,
            "isprivate": False,
        },
        "settings": {},
        "player_slots": [
            {"id": 1, "raceid": 1},
            {"id": 2, "raceid": 7},
        ],
    }


def test_load_manifest_jsonl_validates_schema_and_duplicates() -> None:
    manifest = _manifest()
    text = json.dumps(manifest) + "\n"
    assert load_manifest_jsonl(text)[0]["game_id"] == 42

    with pytest.raises(CorpusIndexError, match="duplicate game_id"):
        load_manifest_jsonl(text + text)

    invalid = dict(manifest, schema="wrong")
    with pytest.raises(CorpusIndexError, match="unsupported schema"):
        load_manifest_jsonl(json.dumps(invalid))


def test_index_game_archive_counts_streams_races_and_candidate_mechanics() -> None:
    record = index_game_archive(
        _manifest(),
        _archive(),
        cache_path="validation/corpus/cache/loadall/game-42.zip",
        acquisition_source="cache",
    )

    assert record["game_id"] == 42
    assert record["ended_year"] == 2026
    assert record["snapshots"] == 4
    assert record["players"] == [1, 2]
    assert record["transitions"] == 2
    assert record["embedded_consecutive"] == 2
    assert record["missing_grid_cells"] == 0
    assert record["canonical_import"] == {
        "ok": 4,
        "failed": 0,
        "failure_types": {},
    }
    assert record["race_slots"] == {"1": 1, "7": 1}

    mechanics = record["candidate_mechanics"]
    assert mechanics["ghost_ship_records"] == 1
    assert mechanics["snapshots_with_ghost_ships"] == 1
    assert mechanics["ionstorm_records"] == 2
    assert mechanics["snapshots_with_ionstorms"] == 2
    assert mechanics["minefield_records"] == 2
    assert mechanics["snapshots_with_minefields"] == 2
    assert mechanics["tow_order_candidates"] == 2
    assert mechanics["intercept_order_candidates"] == 2
    assert mechanics["hyp_order_candidates"] == 2

    encoded = json.dumps(record, sort_keys=True)
    assert "must-not-propagate" not in encoded
    assert "private@example.invalid" not in encoded
    assert "secret" not in encoded
    assert "private-one" not in encoded


def test_aggregate_corpus_index_is_compact_and_deterministic() -> None:
    record = index_game_archive(
        _manifest(),
        _archive(),
        cache_path="cache/game-42.zip",
        acquisition_source="cache",
    )
    stats = aggregate_corpus_index([record], failed_game_ids=[99, 99])

    assert stats["games_indexed"] == 1
    assert stats["games_failed"] == 1
    assert stats["failed_game_ids"] == [99]
    assert stats["totals"]["snapshots"] == 4
    assert stats["totals"]["transitions"] == 2
    assert stats["totals"]["canonical_ok"] == 4
    assert stats["games_by_ended_year"] == {"2026": 1}
    assert stats["player_slots_by_race"] == {"1": 1, "7": 1}
    assert stats["candidate_mechanics"]["ghost_ship_records"] == 1
