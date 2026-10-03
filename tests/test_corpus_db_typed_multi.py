from __future__ import annotations

import gzip
import io
import json
import zipfile
from pathlib import Path

import duckdb

from planets_lab.corpus.corpus_db_typed_multi import (
    CorpusArchiveInput,
    import_archives_to_typed_database,
    validate_typed_corpus_parity,
)


def _payload(*, game_id: int, player_id: int, turn: int, extra_ship: bool) -> dict:
    ship = {
        "id": 17,
        "ownerid": player_id,
        "x": 1000 + game_id % 100 + turn,
        "y": 1200,
        "warp": 9,
        "damage": 0,
        "crew": 6,
        "friendlycode": "abc",
    }
    if extra_ship:
        ship["iscloaked"] = False
    return {
        "game": {"id": game_id, "turn": turn, "name": f"game-{game_id}"},
        "player": {"id": player_id, "raceid": player_id},
        "players": [{"id": player_id, "raceid": player_id}],
        "settings": {"sphere": False},
        "planets": [],
        "ships": [ship],
        "starbases": [],
        "ionstorms": [],
        "minefields": [],
        "vcrs": [],
        "relations": [],
        "messages": [],
        "unknown_zero": 0,
    }


def _archive(path: Path, *, game_id: int, extra_ship: bool, gzip_second: bool) -> Path:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        first = json.dumps(
            _payload(
                game_id=game_id,
                player_id=1,
                turn=10,
                extra_ship=extra_ship,
            ),
            ensure_ascii=False,
        ).encode()
        second = json.dumps(
            _payload(
                game_id=game_id,
                player_id=2,
                turn=10,
                extra_ship=extra_ship,
            ),
            ensure_ascii=False,
        ).encode()
        archive.writestr("README.txt", f"fixture {game_id}")
        archive.writestr("player1-turn10.trn", first)
        archive.writestr(
            "player2-turn10.trn",
            gzip.compress(second) if gzip_second else second,
        )
    path.write_bytes(buffer.getvalue())
    return path


def test_multi_game_typed_generation_keeps_global_identity_and_union_schema(
    tmp_path: Path,
) -> None:
    first = _archive(
        tmp_path / "game-111.zip",
        game_id=111,
        extra_ship=False,
        gzip_second=False,
    )
    second = _archive(
        tmp_path / "game-222.zip",
        game_id=222,
        extra_ship=True,
        gzip_second=True,
    )
    database = tmp_path / "corpus.duckdb"
    inputs = [
        CorpusArchiveInput(111, str(first)),
        CorpusArchiveInput(222, str(second)),
    ]

    result = import_archives_to_typed_database(
        inputs,
        database,
        commit_every_members=1,
        arrow_batch_rows=4,
        sample_members_per_archive=2,
        sample_entities_per_section=10,
    )

    assert result.archive_count == 2
    assert result.game_ids == (111, 222)
    assert result.turn_members == 4
    assert result.entity_rows > 0

    parity = validate_typed_corpus_parity(inputs, database)
    assert parity.checked == 4
    assert parity.failed == 0
    assert parity.mismatches == ()

    connection = duckdb.connect(str(database), read_only=True)
    try:
        assert connection.execute(
            "SELECT count(*) FROM source_archives"
        ).fetchone()[0] == 2
        assert connection.execute(
            "SELECT count(DISTINCT member_id) FROM source_members"
        ).fetchone()[0] == 4

        rows = connection.execute(
            """
            SELECT e.game_id,
                   e.perspective_player_id,
                   t.data.warp,
                   t.data.damage,
                   t.data.iscloaked
            FROM entity_rows e
            JOIN typed_ships t USING (member_id, ordinal)
            WHERE e.section_name = 'ships'
            ORDER BY e.game_id, e.perspective_player_id
            """
        ).fetchall()
        assert rows == [
            (111, 1, 9, 0, None),
            (111, 2, 9, 0, None),
            (222, 1, 9, 0, False),
            (222, 2, 9, 0, False),
        ]

        member_names = connection.execute(
            """
            SELECT game_id, source_member_name
            FROM source_members
            WHERE source_member_name = 'player1-turn10.trn'
            ORDER BY game_id
            """
        ).fetchall()
        assert member_names == [
            (111, "player1-turn10.trn"),
            (222, "player1-turn10.trn"),
        ]
    finally:
        connection.close()
