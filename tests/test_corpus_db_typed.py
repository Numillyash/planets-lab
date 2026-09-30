from __future__ import annotations

import gzip
import io
import json
import zipfile
import zlib
from pathlib import Path

import duckdb

from planets_lab.corpus.corpus_db_typed import (
    CORPUS_DB_TYPED_SCHEMA,
    import_archive_to_typed_database,
    reconstruct_typed_member,
    validate_typed_semantic_parity,
)


def _payload(*, player_id: int, turn: int) -> dict:
    return {
        "game": {"id": 233558, "turn": turn, "name": "typed-fixture"},
        "player": {"id": player_id, "raceid": player_id},
        "players": [
            {"id": 1, "raceid": 1, "username": "one"},
            {"id": 2, "raceid": 7, "username": "two"},
        ],
        "settings": {"sphere": False, "nullable": None},
        "planets": [
            {
                "id": 4,
                "ownerid": 0,
                "x": 1686,
                "y": 2759,
                "mines": -1,
                "factories": -1,
                "buildingstarbase": False,
                "name": "Gothos",
            }
        ],
        "ships": [
            {
                "id": 17,
                "ownerid": player_id,
                "x": 1000 + turn,
                "y": 1200,
                "warp": 9,
                "damage": 0,
                "crew": 6,
                "friendlycode": "abc",
                "waypoints": [],
                "unknown_nested": {"flag": False, "value": None},
            }
        ],
        "starbases": [],
        "ionstorms": [
            {
                "id": 1,
                "x": 2396,
                "y": 834,
                "radius": 100,
                "voltage": 5,
                "warp": 6,
                "isgrowing": False,
            }
        ],
        "minefields": [
            {
                "id": 1,
                "ownerid": player_id,
                "x": 2855,
                "y": 1765,
                "units": 683,
                "isweb": False,
            }
        ],
        "vcrs": [
            {
                "id": 99,
                "x": 1000,
                "y": 1200,
                "seed": 83,
                "left": {
                    "objectid": 17,
                    "damage": 0,
                    "crew": 6,
                    "hasstarbase": False,
                },
                "right": {
                    "objectid": 33,
                    "damage": 20,
                    "crew": 100,
                    "hasstarbase": False,
                },
            }
        ],
        "relations": [{"id": 1, "playerid": player_id, "relationto": 0}],
        "messages": [{"id": 5, "body": "source semantic value"}],
        "unknown_zero": 0,
        "unknown_false": False,
        "unknown_array": [False, 0, "", None, [2, 1]],
    }


def _archive(path: Path) -> Path:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", "non-turn member")
        archive.writestr(
            "player1-turn10.trn",
            json.dumps(_payload(player_id=1, turn=10), ensure_ascii=False).encode(),
        )
        archive.writestr(
            "player2-turn10.trn",
            gzip.compress(
                json.dumps(
                    _payload(player_id=2, turn=10),
                    ensure_ascii=False,
                ).encode()
            ),
        )
        archive.writestr(
            "player1-turn11.trn",
            json.dumps(_payload(player_id=1, turn=11), ensure_ascii=False).encode(),
        )
    path.write_bytes(buffer.getvalue())
    return path


def test_typed_storage_removes_per_entity_json_and_keeps_native_types(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "game-233558.zip")
    database = tmp_path / "typed.duckdb"

    imported = import_archive_to_typed_database(
        archive,
        database,
        expected_game_id=233558,
        commit_every_members=1,
        arrow_batch_rows=10,
    )
    assert imported.schema == CORPUS_DB_TYPED_SCHEMA

    parity = validate_typed_semantic_parity(archive, database)
    assert parity.checked == 3
    assert parity.failed == 0

    connection = duckdb.connect(str(database), read_only=True)
    try:
        entity_columns = {
            row[0]: row[1]
            for row in connection.execute("DESCRIBE entity_rows").fetchall()
        }
        assert "payload_json" not in entity_columns
        assert entity_columns["source_entity_id"] == "BIGINT"
        assert entity_columns["x"] == "DOUBLE"

        ship_type = connection.execute(
            "SELECT typeof(data.warp), typeof(data.damage), "
            "typeof(data.friendlycode), typeof(data.unknown_nested.flag) "
            "FROM typed_ships LIMIT 1"
        ).fetchone()
        assert ship_type == ("BIGINT", "BIGINT", "VARCHAR", "BOOLEAN")

        ship = connection.execute(
            """
            SELECT e.perspective_player_id,
                   t.data.warp,
                   t.data.damage,
                   t.data.crew,
                   t.data.friendlycode,
                   t.data.unknown_nested.flag
            FROM entity_rows e
            JOIN typed_ships t USING (member_id, ordinal)
            WHERE e.section_name = 'ships'
              AND e.archive_turn = 10
            ORDER BY e.perspective_player_id
            """
        ).fetchall()
        assert ship == [
            (1, 9, 0, 6, "abc", False),
            (2, 9, 0, 6, "abc", False),
        ]

        vcr = connection.execute(
            "SELECT data.left.damage, data.right.damage, "
            "typeof(data.left.damage), typeof(data.left.hasstarbase) "
            "FROM typed_vcrs LIMIT 1"
        ).fetchone()
        assert vcr == (0, 20, "BIGINT", "BOOLEAN")

        member_id, blob, decoded_bytes = connection.execute(
            """
            SELECT member_id, decoded_payload_zlib, decoded_json_bytes
            FROM source_members
            WHERE perspective_player_id = 1 AND archive_turn = 10
            """
        ).fetchone()
        decoded = zlib.decompress(bytes(blob))
        assert len(decoded) == decoded_bytes
        assert len(blob) < decoded_bytes

        reconstructed = reconstruct_typed_member(connection, int(member_id))
        assert reconstructed == _payload(player_id=1, turn=10)
    finally:
        connection.close()


def test_typed_views_expose_struct_data_with_generic_provenance(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "game-233558.zip")
    database = tmp_path / "typed.duckdb"
    import_archive_to_typed_database(archive, database, expected_game_id=233558)

    connection = duckdb.connect(str(database), read_only=True)
    try:
        row = connection.execute(
            """
            SELECT archive_turn, perspective_player_id, source_entity_id,
                   data.warp, data.x, data.y
            FROM ships
            WHERE archive_turn = 10
            ORDER BY perspective_player_id
            LIMIT 1
            """
        ).fetchone()
        assert row == (10, 1, 17, 9, 1010, 1200)
    finally:
        connection.close()
