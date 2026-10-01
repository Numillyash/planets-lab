from __future__ import annotations

import gzip
import io
import json
import zipfile
from pathlib import Path

import duckdb

from planets_lab.corpus.corpus_db_compact import (
    CORPUS_DB_COMPACT_SCHEMA,
    benchmark_compact_query,
    compact_database_stats,
    import_archive_to_compact_database,
    reconstruct_compact_member,
    validate_compact_semantic_parity,
)


def _payload(
    *,
    player_id: int,
    turn: int,
    variant: int,
) -> dict:
    ship = {
        "id": 17,
        "ownerid": player_id,
        "x": 1000 + turn,
        "y": 1200,
        "warp": 9,
        "friendlycode": "abc",
        "nested": {"a": 1},
        "mixed_number": 1 if variant != 2 else 1.5,
    }
    if variant == 1:
        ship["nullable"] = None
    if variant == 2:
        ship["nested"]["b"] = None
        ship["late_field"] = "late"
    if variant == 3:
        ship["nullable"] = None
        ship["nested"]["b"] = 7

    return {
        "game": {"id": 233558, "turn": turn, "name": "compact-fixture"},
        "player": {"id": player_id, "raceid": player_id},
        "settings": {"sphere": False, "nullable": None},
        "ships": [ship],
        "planets": [],
        "starbases": [],
        "ionstorms": [],
        "minefields": [],
        "vcrs": [
            {
                "id": 99 + variant,
                "x": 1010,
                "y": 1200,
                "seed": 83,
                "left": {
                    "objectid": 17,
                    "damage": 0,
                    "hasstarbase": False,
                },
                "right": {
                    "objectid": 33,
                    "damage": 20,
                    "hasstarbase": False,
                },
            }
        ],
        "relations": [],
        "messages": [{"id": 5, "body": "text"}],
        "unknown_zero": 0,
        "unknown_false": False,
        "unknown_array": [False, 0, "", None, [2, 1]],
    }


def _archive(path: Path) -> tuple[Path, dict[str, dict]]:
    payloads = {
        "player1-turn10.trn": _payload(player_id=1, turn=10, variant=1),
        "player2-turn10.trn": _payload(player_id=2, turn=10, variant=2),
        "player1-turn11.trn": _payload(player_id=1, turn=11, variant=3),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", "compact fixture")
        for index, (name, payload) in enumerate(payloads.items()):
            raw = json.dumps(payload, ensure_ascii=False).encode()
            archive.writestr(name, gzip.compress(raw) if index == 1 else raw)
    path.write_bytes(buffer.getvalue())
    return path, payloads


def test_compact_roundtrip_uses_typed_state_plus_sparse_presence(tmp_path: Path) -> None:
    archive, payloads = _archive(tmp_path / "game-233558.zip")
    database = tmp_path / "compact.duckdb"

    imported = import_archive_to_compact_database(
        archive,
        database,
        expected_game_id=233558,
        commit_every_members=1,
        arrow_batch_rows=4,
    )
    assert imported.schema == CORPUS_DB_COMPACT_SCHEMA
    assert imported.turn_members == 3

    parity = validate_compact_semantic_parity(archive, database)
    assert parity.checked == 3
    assert parity.failed == 0
    assert parity.mismatches == ()

    connection = duckdb.connect(str(database), read_only=True)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='main' AND table_type='BASE TABLE'"
            ).fetchall()
        }
        assert "entity_rows" not in tables
        assert "typed_ships" in tables

        source_columns = {
            row[0]
            for row in connection.execute("DESCRIBE source_members").fetchall()
        }
        assert "decoded_payload_zlib" not in source_columns

        ship_type = connection.execute(
            "SELECT typeof(data.warp), typeof(data.mixed_number), "
            "typeof(data.late_field), typeof(data.nested.a) "
            "FROM typed_ships LIMIT 1"
        ).fetchone()
        # mixed int/float must remain a JSON fallback, never lossy DOUBLE.
        assert ship_type == ("BIGINT", "VARCHAR", "VARCHAR", "BIGINT")

        rows = connection.execute(
            """
            SELECT sm.source_member_name, s.missing_json
            FROM typed_ships s
            JOIN source_members sm USING (member_id)
            ORDER BY sm.source_member_name
            """
        ).fetchall()
        assert any(missing is not None for _name, missing in rows)

        member_ids = dict(
            connection.execute(
                "SELECT source_member_name, member_id FROM source_members"
            ).fetchall()
        )
        for name, expected in payloads.items():
            actual = reconstruct_compact_member(
                connection,
                int(member_ids[name]),
            )
            assert actual == expected

        first = reconstruct_compact_member(
            connection,
            int(member_ids["player1-turn10.trn"]),
        )["ships"][0]
        second = reconstruct_compact_member(
            connection,
            int(member_ids["player2-turn10.trn"]),
        )["ships"][0]
        assert "nullable" in first and first["nullable"] is None
        assert "nullable" not in second
        assert "b" not in first["nested"]
        assert "b" in second["nested"] and second["nested"]["b"] is None
        assert type(first["mixed_number"]) is int
        assert type(second["mixed_number"]) is float
        assert "late_field" not in first
        assert second["late_field"] == "late"
    finally:
        connection.close()

    stats = compact_database_stats(database)
    assert stats["decoded_json_bytes"] > stats["database_bytes"]
    assert stats["inline_json_bytes"] > 0
    assert stats["missing_residual_rows"] > 0
    assert stats["missing_residual_bytes"] > 0


def test_compact_benchmarks_without_generic_entity_indexes(tmp_path: Path) -> None:
    archive, _payloads = _archive(tmp_path / "game-233558.zip")
    database = tmp_path / "compact.duckdb"
    import_archive_to_compact_database(
        archive,
        database,
        expected_game_id=233558,
    )

    connection = duckdb.connect(str(database), read_only=True)
    try:
        indexes = connection.execute(
            """
            SELECT index_name
            FROM duckdb_indexes()
            WHERE database_name = current_database()
            """
        ).fetchall()
        assert indexes == []
    finally:
        connection.close()

    turn_pair = benchmark_compact_query(
        database,
        kind="turn-pair",
        game_id=233558,
    )
    assert turn_pair.result_rows > 0
    assert turn_pair.target["archive_turn_before"] == 10
    assert turn_pair.target["archive_turn_after"] == 11

    vcr_site = benchmark_compact_query(
        database,
        kind="vcr-site",
        game_id=233558,
    )
    assert vcr_site.result_rows > 0
    assert vcr_site.target["x"] == 1010
    assert vcr_site.target["y"] == 1200
