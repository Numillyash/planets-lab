from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import duckdb

from .corpus_db import CorpusDbError, _peak_rss_bytes


@dataclass(frozen=True, slots=True)
class TypedStorageStage:
    name: str
    database_bytes: int
    wall_seconds: float
    peak_rss_bytes: int


@dataclass(frozen=True, slots=True)
class TypedStorageAttribution:
    source_database_path: str
    source_database_bytes: int
    decoded_json_bytes: int
    compressed_member_blob_logical_bytes: int
    entity_rows: int
    base_tables: tuple[str, ...]
    typed_tables: tuple[str, ...]
    standalone_tables: tuple[TypedStorageStage, ...]
    source_member_variants: tuple[TypedStorageStage, ...]
    combined_stages: tuple[TypedStorageStage, ...]


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _connect_scratch(path: Path, source: Path, memory_limit: str, threads: int):
    con = duckdb.connect(str(path))
    con.execute(f"SET memory_limit={_sql_literal(memory_limit)}")
    con.execute(f"SET threads={int(threads)}")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"ATTACH {_sql_literal(str(source))} AS source_db (READ_ONLY)")
    return con


def _measure_query(
    source: Path,
    scratch: Path,
    *,
    name: str,
    statements: list[str],
    memory_limit: str,
    threads: int,
) -> TypedStorageStage:
    if scratch.exists():
        raise CorpusDbError(f"scratch DB already exists: {scratch}")
    started = time.perf_counter()
    con = _connect_scratch(scratch, source, memory_limit, threads)
    try:
        for statement in statements:
            con.execute(statement)
        con.execute("CHECKPOINT")
        size = scratch.stat().st_size
        return TypedStorageStage(
            name=name,
            database_bytes=size,
            wall_seconds=time.perf_counter() - started,
            peak_rss_bytes=_peak_rss_bytes(),
        )
    finally:
        con.close()
        try:
            scratch.unlink()
        except FileNotFoundError:
            pass


def attribute_typed_storage(
    database_path: Path,
    scratch_dir: Path,
    *,
    memory_limit: str = "4GB",
    threads: int = 2,
) -> TypedStorageAttribution:
    source = database_path.expanduser().resolve()
    scratch_dir = scratch_dir.expanduser().resolve()
    if not source.is_file():
        raise CorpusDbError(f"source database not found: {source}")
    if threads <= 0:
        raise CorpusDbError("threads must be positive")
    scratch_dir.mkdir(parents=True, exist_ok=True)

    ro = duckdb.connect(str(source), read_only=True)
    try:
        rows = ro.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main' AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        ).fetchall()
        tables = tuple(str(row[0]) for row in rows)
        typed_tables = tuple(name for name in tables if name.startswith("typed_") and name != "typed_entity_schema")
        base_tables = tuple(name for name in tables if name not in typed_tables)
        decoded_json_bytes = int(
            ro.execute(
                "SELECT coalesce(sum(decoded_json_bytes),0) FROM source_members"
            ).fetchone()[0]
        )
        compressed_blob_bytes = int(
            ro.execute(
                "SELECT coalesce(sum(octet_length(decoded_payload_zlib)),0) FROM source_members"
            ).fetchone()[0]
        )
        entity_rows = int(ro.execute("SELECT count(*) FROM entity_rows").fetchone()[0])
    finally:
        ro.close()

    standalone: list[TypedStorageStage] = []
    for table in tables:
        standalone.append(
            _measure_query(
                source,
                scratch_dir / f"typed-attrib-table-{table}.duckdb",
                name=table,
                statements=[f'CREATE TABLE "{table}" AS SELECT * FROM source_db."{table}"'],
                memory_limit=memory_limit,
                threads=threads,
            )
        )

    source_member_variants = (
        _measure_query(
            source,
            scratch_dir / "typed-attrib-source-members-no-blob.duckdb",
            name="source_members_without_blob",
            statements=[
                """
                CREATE TABLE source_members AS
                SELECT * EXCLUDE(decoded_payload_zlib)
                FROM source_db.source_members
                """
            ],
            memory_limit=memory_limit,
            threads=threads,
        ),
        _measure_query(
            source,
            scratch_dir / "typed-attrib-source-members-blob.duckdb",
            name="source_members_blob_only",
            statements=[
                """
                CREATE TABLE source_members_blob AS
                SELECT member_id, decoded_payload_zlib
                FROM source_db.source_members
                """
            ],
            memory_limit=memory_limit,
            threads=threads,
        ),
    )

    combined_path = scratch_dir / "typed-attrib-combined.duckdb"
    if combined_path.exists():
        raise CorpusDbError(f"scratch DB already exists: {combined_path}")
    combined: list[TypedStorageStage] = []
    con = _connect_scratch(combined_path, source, memory_limit, threads)
    try:
        started = time.perf_counter()
        for table in tables:
            con.execute(f'CREATE TABLE "{table}" AS SELECT * FROM source_db."{table}"')
        con.execute("CHECKPOINT")
        combined.append(
            TypedStorageStage(
                name="all_data_no_secondary_indexes",
                database_bytes=combined_path.stat().st_size,
                wall_seconds=time.perf_counter() - started,
                peak_rss_bytes=_peak_rss_bytes(),
            )
        )

        index_groups: tuple[tuple[str, tuple[str, ...]], ...] = (
            (
                "source_member_indexes",
                (
                    "CREATE INDEX idx_source_members_lookup ON source_members(game_id, perspective_player_id, archive_turn)",
                    "CREATE INDEX idx_source_members_name ON source_members(game_id, source_member_name)",
                ),
            ),
            (
                "member_field_index",
                (
                    "CREATE INDEX idx_member_fields_lookup ON member_fields(member_id, field_name)",
                ),
            ),
            (
                "entity_member_index",
                (
                    "CREATE INDEX idx_entity_member ON entity_rows(member_id, section_name, ordinal)",
                ),
            ),
            (
                "entity_id_index",
                (
                    "CREATE INDEX idx_entity_lookup ON entity_rows(game_id, section_name, archive_turn, source_entity_id)",
                ),
            ),
            (
                "entity_site_index",
                (
                    "CREATE INDEX idx_entity_site ON entity_rows(game_id, section_name, archive_turn, x, y)",
                ),
            ),
        )
        for name, statements in index_groups:
            started = time.perf_counter()
            for statement in statements:
                con.execute(statement)
            con.execute("CHECKPOINT")
            combined.append(
                TypedStorageStage(
                    name=name,
                    database_bytes=combined_path.stat().st_size,
                    wall_seconds=time.perf_counter() - started,
                    peak_rss_bytes=_peak_rss_bytes(),
                )
            )
    finally:
        con.close()
        try:
            combined_path.unlink()
        except FileNotFoundError:
            pass

    return TypedStorageAttribution(
        source_database_path=str(source),
        source_database_bytes=source.stat().st_size,
        decoded_json_bytes=decoded_json_bytes,
        compressed_member_blob_logical_bytes=compressed_blob_bytes,
        entity_rows=entity_rows,
        base_tables=base_tables,
        typed_tables=typed_tables,
        standalone_tables=tuple(standalone),
        source_member_variants=source_member_variants,
        combined_stages=tuple(combined),
    )
