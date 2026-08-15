import io
import json
import zipfile

import duckdb

from planets_lab.corpus.compiled_movement import (
    COMPILED_MOVEMENT_SCHEMA,
    MOVEMENT_COLUMNS,
    compile_movement_rows,
    create_compiled_catalog,
    movement_row_stats,
    query_compiled_stats,
    write_games_parquet,
    write_movement_parquet,
)
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import (
    PREPARED_GAME_CACHE_SCHEMA,
    build_prepared_game_cache,
)


def _turn_payload(
    turn: int,
    x: int,
    *,
    hull_id: int = 3,
    target_x: int = 125,
    friendly_code: str = "private-test-code",
) -> dict:
    return {
        "game": {"id": 7, "turn": turn},
        "player": {"id": 1, "raceid": 1},
        "players": [{"id": 1, "raceid": 1}],
        "settings": {
            "nowarpwells": False,
            "sphere": True,
            "mapwidth": 2150,
            "mapheight": 2150,
            "mapshape": 1,
        },
        "planets": [],
        "ships": [
            {
                "id": 10,
                "ownerid": 1,
                "hullid": hull_id,
                "x": x,
                "y": 100,
                "warp": 5,
                "targetx": target_x,
                "targety": 100,
                "mission": 0,
                "friendlycode": friendly_code,
                "infoturn": turn,
            }
        ],
        "starbases": [],
        "ionstorms": [],
        "minefields": [],
    }


def _archive(*, hull_id: int = 3, target_x: int = 125, final_x: int = 125) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "player1-turn10.trn",
            json.dumps(_turn_payload(10, 100, hull_id=hull_id, target_x=target_x)),
        )
        archive.writestr(
            "player1-turn11.trn",
            json.dumps(_turn_payload(11, final_x, hull_id=hull_id, target_x=target_x)),
        )
    return buffer.getvalue()


def _compiled_rows(data: bytes, *, hull_id: int | None = None):
    prepared = build_prepared_game_cache(data, game_id=7)
    topology = extract_map_topology(data)
    return prepared, compile_movement_rows(
        game_id=7,
        settings_hash="settings-7",
        prepared=prepared,
        topology=topology,
    )


def test_compiled_move_most_exact_row_omits_private_friendly_code() -> None:
    data = _archive()
    _, rows = _compiled_rows(data)

    assert len(rows) == 1
    row = rows[0]
    assert row["readiness_status"] == "ready"
    assert row["intent_class"] == "move_most_candidate"
    assert row["sphere"] is True
    assert row["map_width"] == 2150
    assert row["map_height"] == 2150
    assert row["map_shape"] == "1"
    assert row["topology_stable"] is True
    assert row["baseline_category"] == "reachable_exact"
    assert row["baseline_explained"] is True
    assert row["post_baseline_residual"] is False
    assert row["post_external_residual"] is False
    assert "friendlycode" not in {name for name, _ in MOVEMENT_COLUMNS}
    assert "private-test-code" not in repr(row)

    assert movement_row_stats(rows) == {
        "transition_rows": 1,
        "geometry_ready": 1,
        "move_most_candidates": 1,
        "baseline_explained": 1,
        "baseline_unresolved": 0,
        "external_context_explained": 0,
        "post_external_residual": 0,
    }


def test_compiled_gravitonic_transition_moves_from_baseline_to_external_context() -> None:
    data = _archive(hull_id=46, target_x=150, final_x=150)
    _, rows = _compiled_rows(data)

    row = rows[0]
    assert row["is_gravitonic_hull"] is True
    assert row["baseline_category"] == "above_nominal"
    assert row["post_baseline_residual"] is True
    assert row["external_context_category"] == "gravitonic_reachable_exact"
    assert row["external_context_explained"] is True
    assert row["post_external_residual"] is False


def test_parquet_and_duckdb_catalog_reproduce_compiled_accounting(tmp_path) -> None:
    data = _archive()
    prepared, rows = _compiled_rows(data)
    stats = movement_row_stats(rows)

    transition_path = (
        tmp_path
        / "mechanics"
        / "movement_transitions"
        / "game_id=7"
        / "part-000.parquet"
    )
    write_movement_parquet(rows, transition_path)
    games_path = tmp_path / "metadata" / "games.parquet"
    write_games_parquet(
        [
            {
                "game_id": 7,
                "settings_hash": "settings-7",
                "archive_sha256": prepared.archive_sha256,
                "prepared_schema": PREPARED_GAME_CACHE_SCHEMA,
                "compiled_schema": COMPILED_MOVEMENT_SCHEMA,
                "sphere": True,
                "map_width": 2150,
                "map_height": 2150,
                "map_shape": "1",
                "topology_stable": True,
                "snapshots": len(prepared.snapshots),
                **stats,
                "parquet_bytes": transition_path.stat().st_size,
            }
        ],
        games_path,
    )

    database_path = tmp_path / "corpus.duckdb"
    create_compiled_catalog(
        database_path=database_path,
        games_parquet=games_path,
        movement_glob=(
            tmp_path
            / "mechanics"
            / "movement_transitions"
            / "game_id=*"
            / "part-000.parquet"
        ),
    )

    assert query_compiled_stats(database_path) == stats
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        assert connection.execute("SELECT count(*) FROM move_most").fetchone() == (1,)
        assert connection.execute("SELECT count(*) FROM movement_residual").fetchone() == (0,)
        assert connection.execute(
            "SELECT sphere, map_width, map_height, map_shape FROM games WHERE game_id = 7"
        ).fetchone() == (True, 2150, 2150, "1")
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info('movement_transitions')").fetchall()
        }
        assert "friendlycode" not in columns
        assert {"sphere", "map_width", "map_height", "map_shape", "topology_stable"} <= columns
    finally:
        connection.close()
