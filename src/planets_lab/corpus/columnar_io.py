from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


_ARROW_TYPES: dict[str, pa.DataType] = {
    "BIGINT": pa.int64(),
    "INTEGER": pa.int32(),
    "DOUBLE": pa.float64(),
    "BOOLEAN": pa.bool_(),
    "VARCHAR": pa.string(),
}


def _arrow_schema(columns: Sequence[tuple[str, str]]) -> pa.Schema:
    fields: list[pa.Field] = []
    for name, sql_type in columns:
        try:
            arrow_type = _ARROW_TYPES[sql_type.upper()]
        except KeyError as exc:
            raise ValueError(f"unsupported compiled column type: {sql_type}") from exc
        fields.append(pa.field(name, arrow_type, nullable=True))
    return pa.schema(fields)


def write_rows_parquet_arrow(
    *,
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[tuple[str, str]],
    path: Path,
) -> None:
    """Write typed compiled rows directly through Arrow, without row SQL INSERTs.

    The previous DuckDB ``executemany`` path crossed Python/SQL once per row and
    dominated first-build time for the historical corpus.  Arrow constructs the
    table column-wise and Parquet writes it in vectorized batches.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    schema = _arrow_schema(columns)

    arrays = [
        pa.array((row.get(field.name) for row in rows), type=field.type)
        for field in schema
    ]
    table = pa.Table.from_arrays(arrays, schema=schema)

    try:
        pq.write_table(
            table,
            temporary,
            compression="zstd",
            use_dictionary=True,
            write_statistics=True,
        )
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
