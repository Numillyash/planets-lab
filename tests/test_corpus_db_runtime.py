from __future__ import annotations

import gzip
import io
import json
import zipfile
from pathlib import Path

import duckdb
import pytest

from planets_lab.corpus.corpus_db import CorpusDbError
from planets_lab.corpus.corpus_db_compact import import_archive_to_compact_database
from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only,
    connect_current_compact_read_only,
    first_last_member_refs,
    member_refs_for_turns,
    reconstruct_members,
)


def _payload(player: int, turn: int) -> dict:
    return {
        "game": {"id": 42, "turn": turn},
        "player": {"id": player, "raceid": player},
        "settings": {"sphere": False},
        "ships": [{"id": 10 + player, "ownerid": player, "x": 1, "y": 2}],
        "planets": [],
        "starbases": [],
        "ionstorms": [],
        "minefields": [],
        "vcrs": [],
        "relations": [],
    }


def _build_db(tmp_path: Path) -> tuple[Path, Path]:
    archive = tmp_path / "game-42.zip"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for player, turn in ((1, 10), (2, 10), (1, 11)):
            raw = json.dumps(_payload(player, turn)).encode()
            name = f"player{player}-turn{turn}.trn"
            zf.writestr(name, gzip.compress(raw) if player == 2 else raw)
    archive.write_bytes(buffer.getvalue())

    root = tmp_path / "corpus"
    (root / "generations").mkdir(parents=True)
    (root / "manifests").mkdir()
    (root / "staging").mkdir()
    database = root / "generations" / "fixture.duckdb"
    import_archive_to_compact_database(
        archive,
        database,
        expected_game_id=42,
        commit_every_members=1,
        arrow_batch_rows=4,
    )
    (root / "CURRENT").write_text("generations/fixture.duckdb\n")
    return root, database


def test_current_compact_reader_targets_only_requested_turns(tmp_path: Path) -> None:
    root, database = _build_db(tmp_path)
    connection, active = connect_current_compact_read_only(root)
    try:
        assert active == database.resolve()
        refs = member_refs_for_turns(
            connection,
            game_id=42,
            turns={10},
            include_embedded_turn=False,
        )
        assert [(ref.perspective_player_id, ref.archive_turn) for ref in refs] == [
            (1, 10),
            (2, 10),
        ]
        payloads = list(reconstruct_members(connection, refs))
        assert [payload["game"]["turn"] for _ref, payload in payloads] == [10, 10]

        first, last = first_last_member_refs(connection, game_id=42)
        assert first.source_member_name == "player1-turn10.trn"
        assert last.source_member_name == "player1-turn11.trn"
    finally:
        connection.close()


def test_current_compact_reader_rejects_wrong_schema(tmp_path: Path) -> None:
    root, _database = _build_db(tmp_path)
    target = root / "generations" / "wrong.duckdb"
    connection = duckdb.connect(str(target))
    connection.execute("CREATE TABLE corpus_metadata(schema_version VARCHAR)")
    connection.execute("INSERT INTO corpus_metadata VALUES ('wrong-schema')")
    connection.close()
    (root / "CURRENT").write_text("generations/wrong.duckdb\n")

    with pytest.raises(CorpusDbError, match="active corpus DB schema"):
        connect_current_compact_read_only(root)



def test_explicit_compact_reader_does_not_consult_current(tmp_path: Path) -> None:
    root, database = _build_db(tmp_path)
    other = root / "generations" / "other.duckdb"
    other.write_bytes(database.read_bytes())

    (root / "CURRENT").write_text("generations/fixture.duckdb\n")
    connection, explicit = connect_compact_generation_read_only(
        "generations/other.duckdb",
        root,
    )
    try:
        assert explicit == other.resolve()
        assert connection.execute(
            "SELECT count(*) FROM source_members"
        ).fetchone()[0] == 3
    finally:
        connection.close()

    assert (root / "CURRENT").read_text(encoding="utf-8").strip() == (
        "generations/fixture.duckdb"
    )


def test_explicit_compact_reader_rejects_escape(tmp_path: Path) -> None:
    root, _database = _build_db(tmp_path)
    with pytest.raises(CorpusDbError, match="outside generations"):
        connect_compact_generation_read_only("../escape.duckdb", root)
