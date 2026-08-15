from __future__ import annotations

import duckdb

from planets_lab.corpus.columnar_io import write_rows_parquet_arrow


def test_arrow_parquet_writer_preserves_typed_nullable_columns(tmp_path) -> None:
    path = tmp_path / "rows.parquet"
    columns = (
        ("game_id", "BIGINT"),
        ("turn", "INTEGER"),
        ("distance", "DOUBLE"),
        ("sphere", "BOOLEAN"),
        ("category", "VARCHAR"),
    )
    rows = [
        {
            "game_id": 591478,
            "turn": 10,
            "distance": 81.0,
            "sphere": True,
            "category": "reachable_exact",
        },
        {
            "game_id": 680910,
            "turn": 11,
            "distance": None,
            "sphere": False,
            "category": None,
        },
    ]

    write_rows_parquet_arrow(rows=rows, columns=columns, path=path)

    connection = duckdb.connect(":memory:")
    try:
        result = connection.execute(
            "SELECT game_id, turn, distance, sphere, category "
            "FROM read_parquet(?) ORDER BY game_id",
            [str(path)],
        ).fetchall()
    finally:
        connection.close()

    assert result == [
        (591478, 10, 81.0, True, "reachable_exact"),
        (680910, 11, None, False, None),
    ]
