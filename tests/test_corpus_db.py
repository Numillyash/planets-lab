from __future__ import annotations

import gzip
import io
import json
import zipfile
from pathlib import Path

import duckdb
import pytest

from planets_lab.corpus.corpus_db import (
    CORPUS_DB_SCHEMA,
    attribute_storage,
    benchmark_query,
    connect_current_read_only,
    import_archive_to_database,
    publish_generation,
    reconstruct_member,
    resolve_current_generation,
    validate_semantic_parity,
)


def _payload(*, player_id: int, turn: int) -> dict:
    return {
        "game": {"id": 233558, "turn": turn, "name": "fixture"},
        "player": {"id": player_id, "raceid": player_id, "savekey": "local-secret"},
        "players": [
            {"id": 1, "raceid": 1, "username": "one"},
            {"id": 2, "raceid": 7, "username": "two"},
        ],
        "settings": {
            "sphere": False,
            "nullable": None,
            "ordered": [3, 1, 2],
        },
        "planets": [],
        "ships": [
            {
                "id": 17,
                "ownerid": player_id,
                "x": 1000 + turn,
                "y": 1200,
                "warp": 0,
                "unknown_nested": {"flag": False, "value": None},
            }
        ],
        "starbases": [],
        "ionstorms": [],
        "minefields": [],
        "vcrs": [
            {
                "id": 99,
                "x": 1000,
                "y": 1200,
                "participants": [17, 33],
                "result": None,
            }
        ],
        "relations": [{"id": 1, "playerid": player_id, "relationto": 0}],
        "messages": [{"id": 5, "body": "source semantic value"}],
        "unknown_null": None,
        "unknown_zero": 0,
        "unknown_false": False,
        "unknown_empty": "",
        "unknown_float": 0.0,
        "unknown_array": [False, 0, "", None, [2, 1]],
        "unknown_objects": [
            {"k": "a", "v": 1},
            {"k": "b", "v": 2},
        ],
    }


def _archive() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        first = json.dumps(_payload(player_id=1, turn=10), ensure_ascii=False).encode()
        second = json.dumps(_payload(player_id=2, turn=10), ensure_ascii=False).encode()
        archive.writestr("README.txt", "non-turn member")
        archive.writestr("player1-turn10.trn", first)
        archive.writestr("player2-turn10.trn", gzip.compress(second))
        archive.writestr(
            "player1-turn11.trn",
            json.dumps(_payload(player_id=1, turn=11), ensure_ascii=False).encode(),
        )
    return buffer.getvalue()


def _write_archive(path: Path) -> Path:
    path.write_bytes(_archive())
    return path


def test_import_is_lossless_and_keeps_same_entity_id_per_perspective(tmp_path: Path) -> None:
    archive = _write_archive(tmp_path / "game-233558.zip")
    database = tmp_path / "prototype.duckdb"

    imported = import_archive_to_database(
        archive,
        database,
        expected_game_id=233558,
        commit_every_members=1,
    )

    assert imported.schema == CORPUS_DB_SCHEMA
    assert imported.game_id == 233558
    assert imported.zip_members == 4
    assert imported.turn_members == 3
    assert imported.entity_rows > 0
    assert imported.decoded_json_bytes > 0

    parity = validate_semantic_parity(archive, database)
    assert parity.checked == 3
    assert parity.failed == 0
    assert parity.mismatches == ()

    connection = duckdb.connect(str(database), read_only=True)
    try:
        rows = connection.execute(
            """
            SELECT perspective_player_id, source_entity_id, owner_id
            FROM ships
            WHERE source_entity_id = 17 AND archive_turn = 10
            ORDER BY perspective_player_id
            """
        ).fetchall()
        assert rows == [(1, 17, 1), (2, 17, 2)]

        member_id = connection.execute(
            "SELECT member_id FROM source_members WHERE perspective_player_id = 1 ORDER BY archive_turn"
        ).fetchone()[0]
        reconstructed = reconstruct_member(connection, member_id)
        assert reconstructed == _payload(player_id=1, turn=10)
        assert reconstructed["unknown_null"] is None
        assert reconstructed["unknown_zero"] == 0
        assert type(reconstructed["unknown_zero"]) is int
        assert reconstructed["unknown_false"] is False
        assert reconstructed["unknown_empty"] == ""
        assert type(reconstructed["unknown_float"]) is float
        assert reconstructed["unknown_array"] == [False, 0, "", None, [2, 1]]
    finally:
        connection.close()


def test_parity_reports_exact_member_and_path_on_type_collapse(tmp_path: Path) -> None:
    archive = _write_archive(tmp_path / "game-233558.zip")
    database = tmp_path / "prototype.duckdb"
    import_archive_to_database(archive, database, expected_game_id=233558)

    connection = duckdb.connect(str(database))
    try:
        connection.execute(
            """
            UPDATE member_fields
            SET payload_json = 'false'
            WHERE member_id = 1 AND field_name = 'unknown_zero'
            """
        )
    finally:
        connection.close()

    parity = validate_semantic_parity(archive, database)
    assert parity.failed == 1
    mismatch = parity.mismatches[0]
    assert mismatch.member == "player1-turn10.trn"
    assert mismatch.path == "$.unknown_zero"
    assert "type mismatch" in mismatch.reason


def test_publish_updates_current_and_generation_is_opened_read_only(tmp_path: Path) -> None:
    archive = _write_archive(tmp_path / "game-233558.zip")
    root = tmp_path / "shared-corpus-db"
    staging_dir = root / "staging"
    staging_dir.mkdir(parents=True)
    staging = staging_dir / "prototype.duckdb"

    imported = import_archive_to_database(archive, staging, expected_game_id=233558)
    parity = validate_semantic_parity(archive, staging)
    assert parity.failed == 0

    published = publish_generation(
        root=root,
        staging_path=staging,
        build_id="corpus-v1-test",
        import_result=imported,
        parity_result=parity,
    )

    current = resolve_current_generation(root)
    assert current == Path(published.generation_path)
    assert current.is_file()
    assert not staging.exists()
    assert (root / "CURRENT").read_text(encoding="utf-8").strip() == (
        "generations/corpus-v1-test.duckdb"
    )
    assert (root / "manifests" / "corpus-v1-test.json").is_file()

    first = connect_current_read_only(root)
    second = connect_current_read_only(root)
    try:
        assert first.execute("SELECT count(*) FROM source_members").fetchone()[0] == 3
        assert second.execute("SELECT count(*) FROM source_members").fetchone()[0] == 3
        with pytest.raises(duckdb.Error):
            first.execute("CREATE TABLE forbidden_write(x INTEGER)")
    finally:
        first.close()
        second.close()



def test_bounded_query_benchmarks_use_indexed_member_and_site_keys(tmp_path: Path) -> None:
    archive = _write_archive(tmp_path / "game-233558.zip")
    database = tmp_path / "prototype.duckdb"
    import_archive_to_database(archive, database, expected_game_id=233558)

    pair = benchmark_query(database, kind="turn-pair", game_id=233558)
    site = benchmark_query(database, kind="vcr-site", game_id=233558)

    assert pair.kind == "turn-pair"
    assert pair.target["archive_turn_before"] == 10
    assert pair.target["archive_turn_after"] == 11
    assert pair.target["perspective_player_id"] == 1
    assert pair.result_rows >= 1
    assert pair.peak_rss_bytes > 0

    assert site.kind == "vcr-site"
    assert site.target["archive_turn"] in (10, 11)
    assert site.target["x"] == 1000.0
    assert site.target["y"] == 1200.0
    assert site.result_rows >= 1
    assert site.peak_rss_bytes > 0


def test_storage_attribution_uses_disposable_copy(tmp_path: Path) -> None:
    archive = _write_archive(tmp_path / "game-233558.zip")
    database = tmp_path / "prototype.duckdb"
    scratch = tmp_path / "storage-attribution.duckdb"
    import_archive_to_database(archive, database, expected_game_id=233558)
    before = database.read_bytes()

    result = attribute_storage(
        database,
        scratch,
        memory_limit="512MB",
        threads=1,
    )

    assert result.source_database_path == str(database.resolve())
    assert result.source_database_bytes == len(before)
    assert result.scratch_database_path == str(scratch.resolve())
    assert scratch.is_file()
    assert database.read_bytes() == before

    names = [stage.name for stage in result.stages]
    assert names == [
        "data_only",
        "source_member_indexes",
        "member_field_index",
        "entity_member_index",
        "entity_id_index",
        "entity_site_index",
        "analyze",
    ]
    assert all(stage.database_bytes > 0 for stage in result.stages)
    assert all(stage.delta_bytes >= 0 for stage in result.stages)
    assert all(stage.wall_seconds >= 0 for stage in result.stages)
    assert all(stage.process_peak_rss_bytes > 0 for stage in result.stages)

    connection = duckdb.connect(str(database), read_only=True)
    try:
        assert connection.execute("SELECT count(*) FROM source_members").fetchone()[0] == 3
    finally:
        connection.close()
