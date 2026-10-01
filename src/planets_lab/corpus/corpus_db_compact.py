from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import uuid
import zipfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import duckdb
import pyarrow as pa

from .archive import TURN_MEMBER_RE, TurnMember
from .corpus_db import (
    CURRENT_FILE,
    KNOWN_ENTITY_SECTIONS,
    CorpusDbError,
    ImportResult,
    ParityMismatch,
    ParityResult,
    PublishResult,
    QueryBenchmarkResult,
    _json_type,
    _peak_rss_bytes,
    _required_member_metadata,
    _sha256_path,
    ensure_external_db_root,
)
from .corpus_db_typed import _canonical_json, _infer_spec, _normalize_spec, _pa_type
from .normalizer import CorpusNormalizationError, _decode_member_json


CORPUS_DB_COMPACT_SCHEMA = "planets-lab.corpus-db.v2.compact1"


def _quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _typed_table(section: str) -> str:
    return f"typed_{section}"


def _compact_merge_spec(left: Any, right: Any) -> Any:
    """Merge observed JSON types without losing semantic number types.

    Unlike typed1, int+float becomes JSON fallback rather than DOUBLE because
    compact2 reconstruction must preserve the original JSON scalar type.
    """
    if left == "null":
        return right
    if right == "null":
        return left
    if left == right:
        return left
    if isinstance(left, dict) and isinstance(right, dict):
        if left.get("kind") == "struct" and right.get("kind") == "struct":
            fields: dict[str, Any] = {}
            for key in left["fields"]:
                if key in right["fields"]:
                    fields[key] = _compact_merge_spec(
                        left["fields"][key],
                        right["fields"][key],
                    )
                else:
                    fields[key] = left["fields"][key]
            for key in right["fields"]:
                if key not in fields:
                    fields[key] = right["fields"][key]
            return {"kind": "struct", "fields": fields}
        if left.get("kind") == "list" and right.get("kind") == "list":
            return {
                "kind": "list",
                "element": _compact_merge_spec(
                    left["element"],
                    right["element"],
                ),
            }
    return "json"


def _infer_compact_spec(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            "kind": "struct",
            "fields": {
                str(key): _infer_compact_spec(item)
                for key, item in value.items()
            },
        }
    if isinstance(value, list):
        element: Any = "null"
        for item in value:
            element = _compact_merge_spec(element, _infer_compact_spec(item))
        return {"kind": "list", "element": element}
    return _infer_spec(value)


def _is_entity_array(field_name: str, value: Any) -> bool:
    if not isinstance(value, list):
        return False
    if field_name in KNOWN_ENTITY_SECTIONS:
        return not value or all(isinstance(item, Mapping) for item in value)
    return bool(value) and all(isinstance(item, Mapping) for item in value)


def _learn_full_entity_specs(
    archive_path: Path,
    *,
    expected_game_id: int | None,
) -> dict[str, Any]:
    specs: dict[str, Any] = {}
    entity_candidates: set[str] = set()
    non_entity_seen: set[str] = set()

    with zipfile.ZipFile(archive_path, mode="r") as archive:
        for info in archive.infolist():
            match = TURN_MEMBER_RE.fullmatch(info.filename)
            if match is None or info.is_dir():
                continue
            member = TurnMember(
                player=int(match.group("player")),
                turn=int(match.group("turn")),
                name=info.filename,
            )
            with archive.open(info, mode="r") as stream:
                raw = stream.read()
            parsed, _decoded = _decode_member_json(raw, member)
            game_id, _embedded_turn = _required_member_metadata(parsed, member)
            if expected_game_id is not None and game_id != expected_game_id:
                raise CorpusDbError(
                    f"{member.name}: expected game {expected_game_id}, got {game_id}"
                )

            for field_name, value in parsed.items():
                is_list = isinstance(value, list)
                all_objects = is_list and all(
                    isinstance(item, Mapping) for item in value
                )
                nonempty_object_array = bool(value) and all_objects

                if field_name in KNOWN_ENTITY_SECTIONS:
                    if not all_objects:
                        non_entity_seen.add(field_name)
                        continue
                    entity_candidates.add(field_name)
                else:
                    if nonempty_object_array:
                        entity_candidates.add(field_name)
                    elif not (is_list and not value):
                        # Empty arrays are shape-neutral for unknown fields:
                        # they may later prove to be an entity array. Any other
                        # observed shape makes the whole top-level field inline.
                        non_entity_seen.add(field_name)
                        continue

                if not nonempty_object_array:
                    continue
                for item in value:
                    assert isinstance(item, Mapping)
                    observed = _infer_compact_spec(item)
                    specs[field_name] = (
                        observed
                        if field_name not in specs
                        else _compact_merge_spec(specs[field_name], observed)
                    )

    typed_fields = entity_candidates - non_entity_seen
    return {
        section: _normalize_spec(spec)
        for section, spec in specs.items()
        if section in typed_fields
        and isinstance(spec, dict)
        and spec.get("kind") == "struct"
    }


def _convert_compact_value(value: Any, spec: Any, path: str) -> Any:
    if value is None:
        return None
    if spec == "json":
        return _canonical_json(value)
    if spec == "bool":
        if not isinstance(value, bool):
            raise CorpusDbError(f"{path}: expected bool, got {type(value).__name__}")
        return value
    if spec == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise CorpusDbError(f"{path}: expected int, got {type(value).__name__}")
        if not (-(2**63) <= value <= 2**63 - 1):
            raise CorpusDbError(f"{path}: int outside int64 range")
        return value
    if spec == "float":
        if not isinstance(value, float):
            raise CorpusDbError(f"{path}: expected float, got {type(value).__name__}")
        return value
    if spec == "string":
        if not isinstance(value, str):
            raise CorpusDbError(f"{path}: expected string, got {type(value).__name__}")
        return value
    if isinstance(spec, dict) and spec.get("kind") == "struct":
        if not isinstance(value, Mapping):
            raise CorpusDbError(f"{path}: expected object, got {type(value).__name__}")
        extras = set(value) - set(spec["fields"])
        if extras:
            raise CorpusDbError(
                f"{path}: fields absent from compact schema: {sorted(extras)!r}"
            )
        return {
            key: (
                _convert_compact_value(value[key], child, f"{path}.{key}")
                if key in value
                else None
            )
            for key, child in spec["fields"].items()
        }
    if isinstance(spec, dict) and spec.get("kind") == "list":
        if not isinstance(value, list):
            raise CorpusDbError(f"{path}: expected array, got {type(value).__name__}")
        return [
            _convert_compact_value(item, spec["element"], f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    raise CorpusDbError(f"{path}: unsupported compact schema spec {spec!r}")


def _collect_missing_paths(
    value: Any,
    spec: Any,
    *,
    path: tuple[str | int, ...] = (),
) -> list[list[str | int]]:
    missing: list[list[str | int]] = []
    if value is None or spec == "json":
        return missing
    if isinstance(spec, dict) and spec.get("kind") == "struct":
        if not isinstance(value, Mapping):
            return missing
        extras = set(value) - set(spec["fields"])
        if extras:
            raise CorpusDbError(
                f"{path!r}: fields absent from compact schema: {sorted(extras)!r}"
            )
        for key, child in spec["fields"].items():
            child_path = path + (key,)
            if key not in value:
                missing.append(list(child_path))
                continue
            child_value = value[key]
            if child_value is not None:
                missing.extend(
                    _collect_missing_paths(
                        child_value,
                        child,
                        path=child_path,
                    )
                )
        return missing
    if isinstance(spec, dict) and spec.get("kind") == "list":
        if not isinstance(value, list):
            return missing
        for index, item in enumerate(value):
            if item is not None:
                missing.extend(
                    _collect_missing_paths(
                        item,
                        spec["element"],
                        path=path + (index,),
                    )
                )
    return missing


def _restore_compact_value(value: Any, spec: Any) -> Any:
    if value is None:
        return None
    if spec == "json":
        if not isinstance(value, str):
            raise CorpusDbError(
                f"JSON fallback expected VARCHAR, got {type(value).__name__}"
            )
        return json.loads(value)
    if isinstance(spec, str) and spec in {"bool", "int", "float", "string"}:
        return value
    if isinstance(spec, dict) and spec.get("kind") == "struct":
        if not isinstance(value, Mapping):
            raise CorpusDbError(
                f"STRUCT reconstruction got {type(value).__name__}"
            )
        return {
            key: _restore_compact_value(value.get(key), child)
            for key, child in spec["fields"].items()
        }
    if isinstance(spec, dict) and spec.get("kind") == "list":
        if not isinstance(value, list):
            raise CorpusDbError(
                f"LIST reconstruction got {type(value).__name__}"
            )
        return [
            _restore_compact_value(item, spec["element"])
            for item in value
        ]
    raise CorpusDbError(f"unsupported compact reconstruction spec: {spec!r}")


def _drop_missing_path(root: Any, path: Sequence[str | int]) -> None:
    if not path:
        raise CorpusDbError("empty missing path")
    target = root
    for token in path[:-1]:
        if isinstance(token, int):
            if not isinstance(target, list) or token >= len(target):
                raise CorpusDbError(f"invalid missing path: {path!r}")
            target = target[token]
        else:
            if not isinstance(target, Mapping) or token not in target:
                raise CorpusDbError(f"invalid missing path: {path!r}")
            target = target[token]
    last = path[-1]
    if isinstance(last, int):
        raise CorpusDbError(f"compact missing path cannot remove array item: {path!r}")
    if not isinstance(target, dict) or last not in target:
        raise CorpusDbError(f"invalid missing path target: {path!r}")
    del target[last]


_MEMBER_FIELDS_SCHEMA = pa.schema(
    [
        pa.field("member_id", pa.int64(), nullable=False),
        pa.field("field_ordinal", pa.int64(), nullable=False),
        pa.field("field_name", pa.string(), nullable=False),
        pa.field("json_type", pa.string(), nullable=False),
        pa.field("storage_kind", pa.string(), nullable=False),
        pa.field("value_json", pa.string(), nullable=True),
    ]
)


def _insert_arrow(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    rows: list[tuple[Any, ...]],
    schema: pa.Schema,
) -> None:
    if not rows:
        return
    arrays = [
        pa.array((row[index] for row in rows), type=field.type)
        for index, field in enumerate(schema)
    ]
    table = pa.Table.from_arrays(arrays, schema=schema)
    relation = f"_compact_{uuid.uuid4().hex}"
    connection.register(relation, table)
    try:
        connection.execute(
            f"INSERT INTO {_quote_ident(table_name)} "
            f"SELECT * FROM {_quote_ident(relation)}"
        )
    finally:
        connection.unregister(relation)


def _create_schema(
    connection: duckdb.DuckDBPyConnection,
    specs: Mapping[str, Any],
) -> dict[str, pa.Schema]:
    connection.execute(
        """
        CREATE TABLE corpus_metadata (
            schema_version VARCHAR NOT NULL,
            created_at_utc VARCHAR NOT NULL
        );

        CREATE TABLE source_archives (
            archive_id BIGINT NOT NULL,
            game_id BIGINT NOT NULL,
            source_path VARCHAR NOT NULL,
            archive_sha256 VARCHAR NOT NULL,
            archive_bytes BIGINT NOT NULL
        );

        CREATE TABLE zip_members (
            archive_id BIGINT NOT NULL,
            member_ordinal BIGINT NOT NULL,
            member_name VARCHAR NOT NULL,
            crc32 UBIGINT,
            compressed_size BIGINT NOT NULL,
            uncompressed_size BIGINT NOT NULL,
            is_directory BOOLEAN NOT NULL,
            is_turn_member BOOLEAN NOT NULL,
            member_payload_sha256 VARCHAR
        );

        CREATE TABLE source_members (
            member_id BIGINT NOT NULL,
            archive_id BIGINT NOT NULL,
            game_id BIGINT NOT NULL,
            source_member_name VARCHAR NOT NULL,
            member_ordinal BIGINT NOT NULL,
            member_crc32 UBIGINT NOT NULL,
            member_compressed_size BIGINT NOT NULL,
            member_uncompressed_size BIGINT NOT NULL,
            member_payload_sha256 VARCHAR NOT NULL,
            decoded_payload_sha256 VARCHAR NOT NULL,
            transport VARCHAR NOT NULL,
            perspective_player_id BIGINT NOT NULL,
            archive_turn BIGINT NOT NULL,
            embedded_turn BIGINT NOT NULL,
            decoded_json_bytes BIGINT NOT NULL
        );

        CREATE TABLE member_fields (
            member_id BIGINT NOT NULL,
            field_ordinal BIGINT NOT NULL,
            field_name VARCHAR NOT NULL,
            json_type VARCHAR NOT NULL,
            storage_kind VARCHAR NOT NULL,
            value_json VARCHAR
        );

        CREATE TABLE typed_entity_schema (
            section_name VARCHAR NOT NULL,
            schema_json VARCHAR NOT NULL
        );
        """
    )
    connection.execute(
        "INSERT INTO corpus_metadata VALUES (?, current_timestamp::VARCHAR)",
        [CORPUS_DB_COMPACT_SCHEMA],
    )

    arrow_schemas: dict[str, pa.Schema] = {}
    for section in sorted(specs):
        schema = pa.schema(
            [
                pa.field("member_id", pa.int64(), nullable=False),
                pa.field("ordinal", pa.int64(), nullable=False),
                pa.field("data", _pa_type(specs[section]), nullable=False),
                pa.field("missing_json", pa.string(), nullable=True),
            ]
        )
        arrow_schemas[section] = schema
        empty = pa.Table.from_arrays(
            [pa.array([], type=field.type) for field in schema],
            schema=schema,
        )
        relation = f"_compact_schema_{uuid.uuid4().hex}"
        connection.register(relation, empty)
        try:
            connection.execute(
                f"CREATE TABLE {_quote_ident(_typed_table(section))} AS "
                f"SELECT * FROM {_quote_ident(relation)}"
            )
        finally:
            connection.unregister(relation)
        connection.execute(
            "INSERT INTO typed_entity_schema VALUES (?, ?)",
            [
                section,
                json.dumps(specs[section], ensure_ascii=False, sort_keys=True),
            ],
        )
    return arrow_schemas


def _flush(
    connection: duckdb.DuckDBPyConnection,
    field_rows: list[tuple[Any, ...]],
    typed_rows: dict[str, list[tuple[Any, ...]]],
    typed_schemas: Mapping[str, pa.Schema],
) -> None:
    _insert_arrow(connection, "member_fields", field_rows, _MEMBER_FIELDS_SCHEMA)
    field_rows.clear()
    for section, rows in typed_rows.items():
        if rows:
            _insert_arrow(
                connection,
                _typed_table(section),
                rows,
                typed_schemas[section],
            )
            rows.clear()


def _create_views(
    connection: duckdb.DuckDBPyConnection,
    specs: Mapping[str, Any],
) -> None:
    for section in sorted(KNOWN_ENTITY_SECTIONS):
        if section not in specs:
            continue
        connection.execute(
            f"""
            CREATE VIEW {_quote_ident(section)} AS
            SELECT sm.game_id,
                   sm.perspective_player_id,
                   sm.archive_turn,
                   sm.embedded_turn,
                   t.member_id,
                   t.ordinal,
                   t.data
            FROM {_quote_ident(_typed_table(section))} t
            JOIN source_members sm USING (member_id)
            """
        )
    connection.execute("ANALYZE")
    connection.execute("CHECKPOINT")


def import_archive_to_compact_database(
    archive_path: Path,
    database_path: Path,
    *,
    expected_game_id: int | None = None,
    commit_every_members: int = 128,
    arrow_batch_rows: int = 10_000,
) -> ImportResult:
    archive_path = archive_path.resolve()
    database_path = database_path.resolve()
    if not archive_path.is_file():
        raise CorpusDbError(f"archive not found: {archive_path}")
    if database_path.exists():
        raise CorpusDbError(f"database already exists: {database_path}")
    if commit_every_members <= 0 or arrow_batch_rows <= 0:
        raise CorpusDbError("batch/commit parameters must be positive")

    database_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    archive_sha256 = _sha256_path(archive_path)
    archive_bytes = archive_path.stat().st_size

    # Exact reconstruction requires a schema learned from the entire archive,
    # not an early bounded sample.
    specs = _learn_full_entity_specs(
        archive_path,
        expected_game_id=expected_game_id,
    )

    connection = duckdb.connect(str(database_path))
    observed_game_id: int | None = None
    zip_count = 0
    turn_count = 0
    entity_count = 0
    decoded_json_bytes = 0
    member_id = 0
    seen_turn_names: set[str] = set()
    field_rows: list[tuple[Any, ...]] = []
    typed_rows: dict[str, list[tuple[Any, ...]]] = {
        section: [] for section in specs
    }

    try:
        connection.execute("SET preserve_insertion_order = false")
        typed_schemas = _create_schema(connection, specs)
        connection.execute("BEGIN TRANSACTION")

        with zipfile.ZipFile(archive_path, mode="r") as archive:
            infos = archive.infolist()
            zip_count = len(infos)
            for member_ordinal, info in enumerate(infos):
                if info.is_dir():
                    connection.execute(
                        "INSERT INTO zip_members VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        [
                            1,
                            member_ordinal,
                            info.filename,
                            int(info.CRC),
                            int(info.compress_size),
                            int(info.file_size),
                            True,
                            False,
                            None,
                        ],
                    )
                    continue

                with archive.open(info, mode="r") as stream:
                    raw = stream.read()
                raw_sha = hashlib.sha256(raw).hexdigest()
                match = TURN_MEMBER_RE.fullmatch(info.filename)
                is_turn = match is not None
                connection.execute(
                    "INSERT INTO zip_members VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        1,
                        member_ordinal,
                        info.filename,
                        int(info.CRC),
                        int(info.compress_size),
                        int(info.file_size),
                        False,
                        is_turn,
                        raw_sha,
                    ],
                )
                if not is_turn:
                    continue
                if info.filename in seen_turn_names:
                    raise CorpusDbError(
                        f"duplicate canonical turn member name: {info.filename}"
                    )
                seen_turn_names.add(info.filename)

                assert match is not None
                member = TurnMember(
                    player=int(match.group("player")),
                    turn=int(match.group("turn")),
                    name=info.filename,
                )
                parsed, decoded = _decode_member_json(raw, member)
                game_id, embedded_turn = _required_member_metadata(parsed, member)
                if expected_game_id is not None and game_id != expected_game_id:
                    raise CorpusDbError(
                        f"{member.name}: expected game {expected_game_id}, got {game_id}"
                    )
                if observed_game_id is None:
                    observed_game_id = game_id
                elif observed_game_id != game_id:
                    raise CorpusDbError(
                        f"archive contains multiple game ids: {observed_game_id}, {game_id}"
                    )

                member_id += 1
                turn_count += 1
                decoded_json_bytes += len(decoded)
                connection.execute(
                    """
                    INSERT INTO source_members VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        member_id,
                        1,
                        game_id,
                        member.name,
                        member_ordinal,
                        int(info.CRC),
                        int(info.compress_size),
                        int(info.file_size),
                        raw_sha,
                        hashlib.sha256(decoded).hexdigest(),
                        "gzip" if raw[:2] == b"\x1f\x8b" else "plain",
                        member.player,
                        member.turn,
                        embedded_turn,
                        len(decoded),
                    ],
                )

                for field_ordinal, (field_name, value) in enumerate(parsed.items()):
                    if field_name in specs:
                        if not _is_entity_array(field_name, value):
                            raise CorpusDbError(
                                f"{member.name}.{field_name}: typed entity field changed shape"
                            )
                        field_rows.append(
                            (
                                member_id,
                                field_ordinal,
                                field_name,
                                "array",
                                "typed_entity",
                                None,
                            )
                        )
                        for ordinal, item in enumerate(value):
                            assert isinstance(item, Mapping)
                            missing = _collect_missing_paths(item, specs[field_name])
                            typed_rows[field_name].append(
                                (
                                    member_id,
                                    ordinal,
                                    _convert_compact_value(
                                        item,
                                        specs[field_name],
                                        f"{member.name}.{field_name}[{ordinal}]",
                                    ),
                                    (
                                        json.dumps(
                                            missing,
                                            ensure_ascii=False,
                                            separators=(",", ":"),
                                        )
                                        if missing
                                        else None
                                    ),
                                )
                            )
                            entity_count += 1
                    else:
                        field_rows.append(
                            (
                                member_id,
                                field_ordinal,
                                field_name,
                                _json_type(value),
                                "inline_json",
                                _canonical_json(value),
                            )
                        )

                buffered = len(field_rows) + sum(
                    len(rows) for rows in typed_rows.values()
                )
                if buffered >= arrow_batch_rows:
                    _flush(connection, field_rows, typed_rows, typed_schemas)

                if turn_count % commit_every_members == 0:
                    _flush(connection, field_rows, typed_rows, typed_schemas)
                    connection.execute("COMMIT")
                    connection.execute("BEGIN TRANSACTION")

        if turn_count == 0 or observed_game_id is None:
            raise CorpusDbError("archive has no canonical playerN-turnM.trn members")

        _flush(connection, field_rows, typed_rows, typed_schemas)
        connection.execute("COMMIT")
        connection.execute(
            "INSERT INTO source_archives VALUES (?, ?, ?, ?, ?)",
            [1, observed_game_id, str(archive_path), archive_sha256, archive_bytes],
        )
        _create_views(connection, specs)
    except BaseException:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        connection.close()

    return ImportResult(
        schema=CORPUS_DB_COMPACT_SCHEMA,
        database_path=str(database_path),
        game_id=int(observed_game_id),
        archive_path=str(archive_path),
        archive_sha256=archive_sha256,
        archive_bytes=archive_bytes,
        zip_members=zip_count,
        turn_members=turn_count,
        decoded_json_bytes=decoded_json_bytes,
        entity_rows=entity_count,
        import_wall_seconds=time.perf_counter() - started,
        peak_rss_bytes=_peak_rss_bytes(),
    )


def _load_specs(connection: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    return {
        str(section): json.loads(str(schema_json))
        for section, schema_json in connection.execute(
            "SELECT section_name, schema_json FROM typed_entity_schema"
        ).fetchall()
    }


def reconstruct_compact_member(
    connection: duckdb.DuckDBPyConnection,
    member_id: int,
    *,
    specs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    exists = connection.execute(
        "SELECT 1 FROM source_members WHERE member_id = ?",
        [member_id],
    ).fetchone()
    if exists is None:
        raise CorpusDbError(f"member not found: {member_id}")
    if specs is None:
        specs = _load_specs(connection)

    result: dict[str, Any] = {}
    fields = connection.execute(
        """
        SELECT field_name, storage_kind, value_json
        FROM member_fields
        WHERE member_id = ?
        ORDER BY field_ordinal
        """,
        [member_id],
    ).fetchall()

    for field_name_raw, storage_kind_raw, value_json in fields:
        field_name = str(field_name_raw)
        storage_kind = str(storage_kind_raw)
        if storage_kind == "inline_json":
            if value_json is None:
                raise CorpusDbError(
                    f"member {member_id}.{field_name}: inline JSON is NULL"
                )
            result[field_name] = json.loads(str(value_json))
            continue
        if storage_kind != "typed_entity":
            raise CorpusDbError(
                f"member {member_id}.{field_name}: unsupported storage kind {storage_kind!r}"
            )
        spec = specs.get(field_name)
        if spec is None:
            raise CorpusDbError(
                f"member {member_id}.{field_name}: typed schema missing"
            )
        rows = connection.execute(
            f"""
            SELECT data, missing_json
            FROM {_quote_ident(_typed_table(field_name))}
            WHERE member_id = ?
            ORDER BY ordinal
            """,
            [member_id],
        ).fetchall()
        entities: list[Any] = []
        for data, missing_json in rows:
            restored = _restore_compact_value(data, spec)
            if not isinstance(restored, dict):
                raise CorpusDbError(
                    f"member {member_id}.{field_name}: entity restored as non-object"
                )
            if missing_json is not None:
                paths = json.loads(str(missing_json))
                if not isinstance(paths, list):
                    raise CorpusDbError("missing_json must decode to a list")
                for path in paths:
                    if not isinstance(path, list):
                        raise CorpusDbError("missing path must be a list")
                    _drop_missing_path(restored, path)
            entities.append(restored)
        result[field_name] = entities

    return result


def _first_semantic_mismatch(
    expected: Any,
    actual: Any,
    path: str = "$",
) -> tuple[str, str] | None:
    if type(expected) is not type(actual):
        return path, f"type mismatch: {type(expected).__name__} != {type(actual).__name__}"
    if isinstance(expected, dict):
        expected_keys = set(expected)
        actual_keys = set(actual)
        missing = sorted(expected_keys - actual_keys)
        if missing:
            return f"{path}.{missing[0]}", "field absent in DB reconstruction"
        extra = sorted(actual_keys - expected_keys)
        if extra:
            return f"{path}.{extra[0]}", "extra field in DB reconstruction"
        for key in expected:
            mismatch = _first_semantic_mismatch(
                expected[key],
                actual[key],
                f"{path}.{key}",
            )
            if mismatch is not None:
                return mismatch
        return None
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return path, f"array length mismatch: {len(expected)} != {len(actual)}"
        for index, (left, right) in enumerate(zip(expected, actual)):
            mismatch = _first_semantic_mismatch(
                left,
                right,
                f"{path}[{index}]",
            )
            if mismatch is not None:
                return mismatch
        return None
    if isinstance(expected, float) and math.isnan(expected) and math.isnan(actual):
        return None
    if expected != actual:
        return path, "value mismatch"
    return None


def validate_compact_semantic_parity(
    archive_path: Path,
    database_path: Path,
    *,
    max_mismatches: int = 100,
) -> ParityResult:
    archive_path = archive_path.resolve()
    database_path = database_path.resolve()
    if max_mismatches <= 0:
        raise CorpusDbError("max_mismatches must be positive")

    started = time.perf_counter()
    mismatches: list[ParityMismatch] = []
    checked = 0

    def add(member: str, path: str, reason: str) -> bool:
        mismatches.append(ParityMismatch(member, path, reason))
        return len(mismatches) >= max_mismatches

    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        metadata = connection.execute(
            "SELECT schema_version FROM corpus_metadata"
        ).fetchone()
        if metadata is None or metadata[0] != CORPUS_DB_COMPACT_SCHEMA:
            raise CorpusDbError(
                f"unexpected compact schema: {None if metadata is None else metadata[0]!r}"
            )

        archive_row = connection.execute(
            """
            SELECT game_id, archive_sha256, archive_bytes
            FROM source_archives
            WHERE archive_id = 1
            """
        ).fetchone()
        if archive_row is None:
            raise CorpusDbError("source archive provenance missing")
        db_archive_game_id = int(archive_row[0])
        if str(archive_row[1]) != _sha256_path(archive_path):
            raise CorpusDbError("source archive SHA256 mismatch")
        if int(archive_row[2]) != archive_path.stat().st_size:
            raise CorpusDbError("source archive byte-size mismatch")

        db_zip = {
            int(row[0]): row[1:]
            for row in connection.execute(
                """
                SELECT member_ordinal, member_name, crc32, compressed_size,
                       uncompressed_size, is_directory, is_turn_member,
                       member_payload_sha256
                FROM zip_members
                WHERE archive_id = 1
                ORDER BY member_ordinal
                """
            ).fetchall()
        }
        db_members = {
            str(row[0]): row[1:]
            for row in connection.execute(
                """
                SELECT source_member_name, member_id, game_id, member_crc32,
                       member_uncompressed_size, member_payload_sha256,
                       decoded_payload_sha256, perspective_player_id,
                       archive_turn, embedded_turn
                FROM source_members
                WHERE archive_id = 1
                """
            ).fetchall()
        }
        specs = _load_specs(connection)
        seen_members: set[str] = set()
        seen_ordinals: set[int] = set()

        with zipfile.ZipFile(archive_path, mode="r") as archive:
            for ordinal, info in enumerate(archive.infolist()):
                seen_ordinals.add(ordinal)
                match = TURN_MEMBER_RE.fullmatch(info.filename)
                is_turn = match is not None
                raw: bytes | None = None
                raw_sha: str | None = None
                if not info.is_dir():
                    with archive.open(info, mode="r") as stream:
                        raw = stream.read()
                    raw_sha = hashlib.sha256(raw).hexdigest()

                zip_row = db_zip.get(ordinal)
                if zip_row is None:
                    if add(info.filename, "$", "ZIP member absent in DB provenance"):
                        break
                else:
                    (
                        db_name,
                        db_crc,
                        db_compressed,
                        db_uncompressed,
                        db_is_dir,
                        db_is_turn,
                        db_payload_sha,
                    ) = zip_row
                    problem: str | None = None
                    if db_name != info.filename:
                        problem = "ZIP member name mismatch"
                    elif int(db_crc) != int(info.CRC):
                        problem = "ZIP member CRC mismatch"
                    elif int(db_compressed) != int(info.compress_size):
                        problem = "ZIP compressed-size mismatch"
                    elif int(db_uncompressed) != int(info.file_size):
                        problem = "ZIP uncompressed-size mismatch"
                    elif bool(db_is_dir) != bool(info.is_dir()):
                        problem = "ZIP directory flag mismatch"
                    elif bool(db_is_turn) != is_turn:
                        problem = "ZIP turn-member flag mismatch"
                    elif db_payload_sha != raw_sha:
                        problem = "ZIP member payload SHA256 mismatch"
                    if problem and add(info.filename, "$", problem):
                        break

                if not is_turn:
                    continue
                checked += 1
                seen_members.add(info.filename)
                db_row = db_members.get(info.filename)
                if db_row is None:
                    if add(info.filename, "$", "source member absent in DB"):
                        break
                    continue

                assert match is not None and raw is not None and raw_sha is not None
                member = TurnMember(
                    player=int(match.group("player")),
                    turn=int(match.group("turn")),
                    name=info.filename,
                )
                expected, decoded = _decode_member_json(raw, member)
                expected_game_id, expected_embedded_turn = _required_member_metadata(
                    expected,
                    member,
                )
                (
                    member_id,
                    db_game_id,
                    db_crc,
                    db_uncompressed,
                    db_raw_sha,
                    db_decoded_sha,
                    db_perspective,
                    db_archive_turn,
                    db_embedded_turn,
                ) = db_row

                problem = None
                if int(db_game_id) != expected_game_id:
                    problem = "source member game_id mismatch"
                elif db_archive_game_id != expected_game_id:
                    problem = "source archive game_id mismatch"
                elif int(db_crc) != int(info.CRC):
                    problem = "member CRC mismatch"
                elif int(db_uncompressed) != int(info.file_size):
                    problem = "member size mismatch"
                elif db_raw_sha != raw_sha:
                    problem = "member payload SHA256 mismatch"
                elif db_decoded_sha != hashlib.sha256(decoded).hexdigest():
                    problem = "decoded payload SHA256 mismatch"
                elif int(db_perspective) != member.player:
                    problem = "perspective mismatch"
                elif int(db_archive_turn) != member.turn:
                    problem = "archive turn mismatch"
                elif int(db_embedded_turn) != expected_embedded_turn:
                    problem = "embedded turn mismatch"
                if problem is not None:
                    if add(info.filename, "$", problem):
                        break
                    continue

                try:
                    actual = reconstruct_compact_member(
                        connection,
                        int(member_id),
                        specs=specs,
                    )
                except Exception as exc:
                    if add(info.filename, "$", f"reconstruction failed: {exc}"):
                        break
                    continue
                mismatch = _first_semantic_mismatch(expected, actual)
                if mismatch is not None:
                    if add(info.filename, mismatch[0], mismatch[1]):
                        break

        if len(mismatches) < max_mismatches:
            for ordinal in sorted(set(db_zip) - seen_ordinals):
                if add(
                    str(db_zip[ordinal][0]),
                    "$",
                    "DB ZIP member absent from archive",
                ):
                    break
        if len(mismatches) < max_mismatches:
            for name in sorted(set(db_members) - seen_members):
                if add(name, "$", "DB source member absent from archive"):
                    break
    finally:
        connection.close()

    return ParityResult(
        checked=checked,
        failed=len(mismatches),
        mismatches=tuple(mismatches),
        wall_seconds=time.perf_counter() - started,
        peak_rss_bytes=_peak_rss_bytes(),
    )


def compact_database_stats(database_path: Path) -> dict[str, Any]:
    database_path = database_path.resolve()
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        sections = [
            str(row[0])
            for row in connection.execute(
                "SELECT section_name FROM typed_entity_schema ORDER BY section_name"
            ).fetchall()
        ]
        entity_rows = 0
        residual_rows = 0
        residual_bytes = 0
        per_section: dict[str, dict[str, int]] = {}
        for section in sections:
            table = _quote_ident(_typed_table(section))
            row = connection.execute(
                f"""
                SELECT count(*),
                       count(*) FILTER (WHERE missing_json IS NOT NULL),
                       coalesce(sum(octet_length(encode(missing_json))), 0)
                FROM {table}
                """
            ).fetchone()
            count = int(row[0])
            missing_count = int(row[1])
            missing_bytes = int(row[2])
            entity_rows += count
            residual_rows += missing_count
            residual_bytes += missing_bytes
            per_section[section] = {
                "rows": count,
                "missing_residual_rows": missing_count,
                "missing_residual_bytes": missing_bytes,
            }

        archive = connection.execute(
            "SELECT archive_sha256, archive_bytes FROM source_archives"
        ).fetchone()
        return {
            "schema": CORPUS_DB_COMPACT_SCHEMA,
            "database_path": str(database_path),
            "database_bytes": database_path.stat().st_size,
            "source_archive_sha256": archive[0] if archive else None,
            "source_archive_bytes": int(archive[1]) if archive else None,
            "decoded_json_bytes": int(
                connection.execute(
                    "SELECT coalesce(sum(decoded_json_bytes),0) FROM source_members"
                ).fetchone()[0]
            ),
            "source_members": int(
                connection.execute("SELECT count(*) FROM source_members").fetchone()[0]
            ),
            "member_fields": int(
                connection.execute("SELECT count(*) FROM member_fields").fetchone()[0]
            ),
            "inline_json_bytes": int(
                connection.execute(
                    "SELECT coalesce(sum(octet_length(encode(value_json))),0) "
                    "FROM member_fields WHERE value_json IS NOT NULL"
                ).fetchone()[0]
            ),
            "entity_rows": entity_rows,
            "missing_residual_rows": residual_rows,
            "missing_residual_bytes": residual_bytes,
            "typed_sections": per_section,
        }
    finally:
        connection.close()


def benchmark_compact_query(
    database_path: Path,
    *,
    kind: str,
    game_id: int,
) -> QueryBenchmarkResult:
    database_path = database_path.resolve()
    if kind not in {"turn-pair", "vcr-site"}:
        raise CorpusDbError(f"unsupported compact benchmark kind: {kind!r}")

    started = time.perf_counter()
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        if kind == "turn-pair":
            selected = connection.execute(
                """
                SELECT cur.perspective_player_id, cur.archive_turn
                FROM source_members cur
                JOIN source_members prev
                  ON prev.game_id = cur.game_id
                 AND prev.perspective_player_id = cur.perspective_player_id
                 AND prev.archive_turn = cur.archive_turn - 1
                WHERE cur.game_id = ?
                ORDER BY cur.archive_turn DESC, cur.perspective_player_id
                LIMIT 1
                """,
                [game_id],
            ).fetchone()
            if selected is None:
                raise CorpusDbError(f"game {game_id}: no consecutive T-1/T member pair")
            perspective, turn = map(int, selected)
            member_ids = [
                int(row[0])
                for row in connection.execute(
                    """
                    SELECT member_id
                    FROM source_members
                    WHERE game_id = ?
                      AND perspective_player_id = ?
                      AND archive_turn BETWEEN ? AND ?
                    """,
                    [game_id, perspective, turn - 1, turn],
                ).fetchall()
            ]
            if len(member_ids) != 2:
                raise CorpusDbError("turn-pair member lookup did not return exactly two rows")
            sections = [
                str(row[0])
                for row in connection.execute(
                    "SELECT section_name FROM typed_entity_schema"
                ).fetchall()
            ]
            rows: list[tuple[str, int]] = []
            for section in sections:
                count = int(
                    connection.execute(
                        f"SELECT count(*) FROM {_quote_ident(_typed_table(section))} "
                        "WHERE member_id IN (?, ?)",
                        member_ids,
                    ).fetchone()[0]
                )
                if count:
                    rows.append((section, count))
            target: Mapping[str, Any] = {
                "perspective_player_id": perspective,
                "archive_turn_before": turn - 1,
                "archive_turn_after": turn,
            }
        else:
            specs = _load_specs(connection)
            vcr_spec = specs.get("vcrs")
            if not (
                isinstance(vcr_spec, dict)
                and vcr_spec.get("kind") == "struct"
                and "x" in vcr_spec.get("fields", {})
                and "y" in vcr_spec.get("fields", {})
            ):
                raise CorpusDbError(f"game {game_id}: VCR x/y fields unavailable")
            selected = connection.execute(
                """
                SELECT sm.archive_turn, v.data.x, v.data.y, count(*) AS rows
                FROM typed_vcrs v
                JOIN source_members sm USING (member_id)
                WHERE sm.game_id = ?
                  AND v.data.x IS NOT NULL
                  AND v.data.y IS NOT NULL
                GROUP BY sm.archive_turn, v.data.x, v.data.y
                ORDER BY rows DESC, sm.archive_turn, v.data.x, v.data.y
                LIMIT 1
                """,
                [game_id],
            ).fetchone()
            if selected is None:
                raise CorpusDbError(f"game {game_id}: no VCR rows with a site")
            turn = int(selected[0])
            x = selected[1]
            y = selected[2]
            rows = connection.execute(
                """
                SELECT sm.perspective_player_id, count(*) AS rows
                FROM typed_vcrs v
                JOIN source_members sm USING (member_id)
                WHERE sm.game_id = ?
                  AND sm.archive_turn = ?
                  AND v.data.x = ?
                  AND v.data.y = ?
                GROUP BY sm.perspective_player_id
                ORDER BY sm.perspective_player_id
                """,
                [game_id, turn, x, y],
            ).fetchall()
            target = {
                "archive_turn": turn,
                "x": x,
                "y": y,
                "raw_vcr_rows_at_site": int(selected[3]),
            }
    finally:
        connection.close()

    return QueryBenchmarkResult(
        kind=kind,
        database_path=str(database_path),
        game_id=game_id,
        target=target,
        result_rows=len(rows),
        wall_seconds=time.perf_counter() - started,
        peak_rss_bytes=_peak_rss_bytes(),
    )


def publish_compact_generation(
    *,
    root: Path,
    staging_path: Path,
    build_id: str,
    import_result: ImportResult,
    parity_result: ParityResult,
    activate_current: bool = False,
) -> PublishResult:
    if parity_result.failed:
        raise CorpusDbError("refusing to publish compact generation with parity failures")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", build_id):
        raise CorpusDbError(f"unsafe build id: {build_id!r}")

    root = ensure_external_db_root(root)
    staging_path = staging_path.resolve()
    if staging_path.parent != (root / "staging").resolve():
        raise CorpusDbError("staging database must live directly under <root>/staging")
    if not staging_path.is_file():
        raise CorpusDbError(f"staging database not found: {staging_path}")

    generation_name = f"{build_id}.duckdb"
    generation_path = (root / "generations" / generation_name).resolve()
    if generation_path.exists():
        raise CorpusDbError(f"generation already exists: {generation_path}")

    os.replace(staging_path, generation_path)
    generation_sha = _sha256_path(generation_path)
    try:
        generation_path.chmod(0o444)
    except OSError:
        pass

    manifest = {
        "schema": import_result.schema,
        "build_id": build_id,
        "published_at_utc": datetime.now(timezone.utc).isoformat(),
        "activate_current": activate_current,
        "generation": {
            "path": f"generations/{generation_name}",
            "sha256": generation_sha,
            "bytes": generation_path.stat().st_size,
        },
        "import": asdict(import_result),
        "parity": {
            "checked": parity_result.checked,
            "failed": parity_result.failed,
            "wall_seconds": parity_result.wall_seconds,
            "peak_rss_bytes": parity_result.peak_rss_bytes,
        },
    }
    manifest_path = root / "manifests" / f"{build_id}.json"
    manifest_tmp = root / "manifests" / f".{build_id}.json.tmp"
    manifest_tmp.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(manifest_tmp, manifest_path)

    current_value = ""
    if activate_current:
        current_value = f"generations/{generation_name}"
        current_tmp = root / f".{CURRENT_FILE}.{os.getpid()}.tmp"
        current_tmp.write_text(current_value + "\n", encoding="utf-8")
        os.replace(current_tmp, root / CURRENT_FILE)

    return PublishResult(
        build_id=build_id,
        generation_path=str(generation_path),
        generation_sha256=generation_sha,
        current_value=current_value,
        manifest_path=str(manifest_path),
    )
