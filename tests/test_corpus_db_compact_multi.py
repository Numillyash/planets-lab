from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import duckdb

from planets_lab.corpus.corpus_db_compact_multi import (
    CompactCorpusArchiveInput,
    compact_corpus_database_stats,
    import_archives_to_compact_database,
    validate_compact_corpus_parity,
)


def _payload(
    *,
    game_id: int,
    player_id: int,
    turn: int,
    mixed: int | float,
    include_nullable: bool,
    include_late: bool,
    scores_as_object: bool,
    ephemeral_empty: bool,
) -> dict:
    ship = {
        "id": 10 + player_id,
        "ownerid": player_id,
        "x": 1000 + turn,
        "y": 1200,
        "warp": 9,
        "mixed": mixed,
        "nested": {"a": 1},
    }
    if include_nullable:
        ship["nullable"] = None
    if include_late:
        ship["late_field"] = "late"

    return {
        "game": {"id": game_id, "turn": turn, "name": f"g{game_id}"},
        "player": {"id": player_id, "raceid": player_id},
        "settings": {"sphere": False},
        "ships": [ship],
        "planets": [],
        "vcrs": [
            {
                "id": 100 + turn,
                "x": 1000,
                "y": 1200,
                "seed": 7,
                "left": {"objectid": ship["id"], "damage": 0},
                "right": {"objectid": 99, "damage": 10},
            }
        ],
        "scores": (
            {"summary": 10}
            if scores_as_object
            else [{"id": player_id, "score": 10}]
        ),
        "ephemeral": (
            []
            if ephemeral_empty
            else [{"id": player_id, "value": 1}]
        ),
        "unknown_false": False,
    }


def _archive(path: Path, members: dict[str, dict]) -> Path:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", "fixture")
        for name, payload in members.items():
            archive.writestr(
                name,
                json.dumps(payload, ensure_ascii=False).encode(),
            )
    path.write_bytes(buffer.getvalue())
    return path


def test_compact_multi_resumes_and_preserves_global_semantics(tmp_path: Path) -> None:
    game1_payloads = {
        "player1-turn1.trn": _payload(
            game_id=101,
            player_id=1,
            turn=1,
            mixed=1,
            include_nullable=True,
            include_late=False,
            scores_as_object=False,
            ephemeral_empty=False,
        ),
        "player1-turn2.trn": _payload(
            game_id=101,
            player_id=1,
            turn=2,
            mixed=2,
            include_nullable=False,
            include_late=False,
            scores_as_object=False,
            ephemeral_empty=True,
        ),
    }
    game2_payloads = {
        "player2-turn1.trn": _payload(
            game_id=202,
            player_id=2,
            turn=1,
            mixed=1.5,
            include_nullable=False,
            include_late=True,
            scores_as_object=True,
            ephemeral_empty=True,
        )
    }

    archive1 = _archive(tmp_path / "game-101.zip", game1_payloads)
    archive2 = _archive(tmp_path / "game-202.zip", game2_payloads)
    archives = [
        CompactCorpusArchiveInput(101, str(archive1)),
        CompactCorpusArchiveInput(202, str(archive2)),
    ]
    database = tmp_path / "compact-public.duckdb"
    checkpoints = tmp_path / "schema-checkpoints"

    first = import_archives_to_compact_database(
        archives,
        database,
        checkpoints,
        commit_every_members=1,
        arrow_batch_rows=2,
        max_new_archives=1,
    )
    assert first.archive_count == 1
    assert first.game_ids == (101,)
    assert first.resumed_archives == 0

    # Simulate a hard crash after the next archive touched the DB but before it
    # was marked complete. Resume must remove this partial provenance.
    connection = duckdb.connect(str(database))
    try:
        connection.execute(
            """
            INSERT INTO zip_members VALUES
            (2, 999, 'partial.tmp', 0, 0, 0, false, false, ?)
            """,
            ["0" * 64],
        )
        connection.execute("CHECKPOINT")
    finally:
        connection.close()

    events: list[dict] = []
    second = import_archives_to_compact_database(
        archives,
        database,
        checkpoints,
        commit_every_members=1,
        arrow_batch_rows=2,
        progress=lambda value: events.append(dict(value)),
    )
    assert second.archive_count == 2
    assert second.game_ids == (101, 202)
    assert second.resumed_archives == 1
    assert any(
        event.get("status") == "cleanup-partial"
        and event.get("archive_id") == 2
        for event in events
    )

    connection = duckdb.connect(str(database), read_only=True)
    try:
        assert connection.execute(
            "SELECT count(*) FROM zip_members WHERE member_name='partial.tmp'"
        ).fetchone()[0] == 0

        tables = {
            row[0]
            for row in connection.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='main' AND table_type='BASE TABLE'"
            ).fetchall()
        }
        assert "entity_rows" not in tables
        assert "typed_scores" not in tables
        assert "typed_ephemeral" in tables

        source_columns = {
            row[0]
            for row in connection.execute("DESCRIBE source_members").fetchall()
        }
        assert "decoded_payload_zlib" not in source_columns
        assert connection.execute(
            "SELECT count(*) FROM duckdb_indexes()"
        ).fetchone()[0] == 0

        # int in one game + float in another must be a local JSON fallback
        # globally, preserving exact scalar identity.
        assert connection.execute(
            "SELECT typeof(data.mixed) FROM typed_ships LIMIT 1"
        ).fetchone()[0] == "VARCHAR"
        assert connection.execute(
            "SELECT typeof(data.late_field) FROM typed_ships LIMIT 1"
        ).fetchone()[0] == "VARCHAR"
    finally:
        connection.close()

    parity_events: list[dict] = []
    parity = validate_compact_corpus_parity(
        archives,
        database,
        validated_games={101: 2},
        progress=lambda value: parity_events.append(dict(value)),
    )
    assert parity.checked == 3
    assert parity.failed == 0
    assert any(
        event.get("phase") == "parity"
        and event.get("status") == "reused"
        and event.get("game_id") == 101
        for event in parity_events
    )

    stats = compact_corpus_database_stats(database)
    assert stats["source_archive_count"] == 2
    assert stats["source_members"] == 3
    assert stats["game_ids"] == [101, 202]
    assert stats["missing_residual_rows"] > 0

    # Schema discovery checkpoints are reusable and source-bound.
    assert (checkpoints / "schema-game-101.json").is_file()
    assert (checkpoints / "schema-game-202.json").is_file()
