from __future__ import annotations

import hashlib
import json
import math
import time
import zipfile
import zlib
from pathlib import Path
from typing import Any, Mapping

import duckdb
import pyarrow as pa

from .archive import TURN_MEMBER_RE, TurnMember
from .corpus_db import (
    KNOWN_ENTITY_SECTIONS,
    CorpusDbError,
    ImportResult,
    ParityMismatch,
    ParityResult,
    _first_int,
    _json_type,
    _peak_rss_bytes,
    _required_member_metadata,
    _sha256_path,
    _typed_number,
)
from .normalizer import CorpusNormalizationError, _decode_member_json


CORPUS_DB_TYPED_SCHEMA = "planets-lab.corpus-db.v1.typed1"
_TYPED_SAMPLE_MEMBERS = 256
_TYPED_SAMPLE_ENTITIES_PER_SECTION = 10_000


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=True,
    )


def _infer_spec(value: Any) -> Any:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        if -(2**63) <= value <= 2**63 - 1:
            return "int"
        return "json"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, Mapping):
        return {
            "kind": "struct",
            "fields": {str(key): _infer_spec(item) for key, item in value.items()},
        }
    if isinstance(value, list):
        element: Any = "null"
        for item in value:
            element = _merge_spec(element, _infer_spec(item))
        return {"kind": "list", "element": element}
    return "json"


def _merge_spec(left: Any, right: Any) -> Any:
    if left == "null":
        return right
    if right == "null":
        return left
    if left == right:
        return left
    if {left, right} == {"int", "float"}:
        return "float"
    if isinstance(left, dict) and isinstance(right, dict):
        if left.get("kind") == "struct" and right.get("kind") == "struct":
            fields: dict[str, Any] = {}
            for key in left["fields"]:
                if key in right["fields"]:
                    fields[key] = _merge_spec(left["fields"][key], right["fields"][key])
                else:
                    fields[key] = left["fields"][key]
            for key in right["fields"]:
                if key not in fields:
                    fields[key] = right["fields"][key]
            return {"kind": "struct", "fields": fields}
        if left.get("kind") == "list" and right.get("kind") == "list":
            return {
                "kind": "list",
                "element": _merge_spec(left["element"], right["element"]),
            }
    return "json"


def _normalize_spec(spec: Any) -> Any:
    if spec == "null":
        return "json"
    if isinstance(spec, dict):
        if spec.get("kind") == "struct":
            return {
                "kind": "struct",
                "fields": {
                    key: _normalize_spec(value)
                    for key, value in spec["fields"].items()
                },
            }
        if spec.get("kind") == "list":
            return {
                "kind": "list",
                "element": _normalize_spec(spec["element"]),
            }
    return spec


def _pa_type(spec: Any) -> pa.DataType:
    if spec == "bool":
        return pa.bool_()
    if spec == "int":
        return pa.int64()
    if spec == "float":
        return pa.float64()
    if spec in {"string", "json"}:
        return pa.string()
    if isinstance(spec, dict) and spec.get("kind") == "struct":
        return pa.struct(
            [
                pa.field(key, _pa_type(value), nullable=True)
                for key, value in spec["fields"].items()
            ]
        )
    if isinstance(spec, dict) and spec.get("kind") == "list":
        return pa.list_(_pa_type(spec["element"]))
    raise CorpusDbError(f"unsupported typed schema spec: {spec!r}")


def _convert_value(value: Any, spec: Any, path: str) -> Any:
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
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise CorpusDbError(f"{path}: expected number, got {type(value).__name__}")
        return float(value)
    if spec == "string":
        if not isinstance(value, str):
            raise CorpusDbError(f"{path}: expected string, got {type(value).__name__}")
        return value
    if isinstance(spec, dict) and spec.get("kind") == "struct":
        if not isinstance(value, Mapping):
            raise CorpusDbError(f"{path}: expected object, got {type(value).__name__}")
        return {
            key: (
                _convert_value(value[key], child, f"{path}.{key}")
                if key in value
                else None
            )
            for key, child in spec["fields"].items()
        }
    if isinstance(spec, dict) and spec.get("kind") == "list":
        if not isinstance(value, list):
            raise CorpusDbError(f"{path}: expected array, got {type(value).__name__}")
        return [
            _convert_value(item, spec["element"], f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    raise CorpusDbError(f"{path}: unsupported schema spec {spec!r}")


def _learn_entity_specs(
    archive_path: Path,
    *,
    expected_game_id: int | None,
    sample_members: int = _TYPED_SAMPLE_MEMBERS,
    sample_entities_per_section: int = _TYPED_SAMPLE_ENTITIES_PER_SECTION,
) -> dict[str, Any]:
    specs: dict[str, Any] = {}
    section_counts: dict[str, int] = {}
    sampled_members = 0

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

            for section in KNOWN_ENTITY_SECTIONS:
                value = parsed.get(section)
                if not isinstance(value, list):
                    continue
                count = section_counts.get(section, 0)
                if count >= sample_entities_per_section:
                    continue
                for item in value:
                    if count >= sample_entities_per_section:
                        break
                    if not isinstance(item, Mapping):
                        continue
                    spec = _infer_spec(item)
                    specs[section] = (
                        spec if section not in specs else _merge_spec(specs[section], spec)
                    )
                    count += 1
                section_counts[section] = count

            sampled_members += 1
            if sampled_members >= sample_members:
                break

    return {
        section: _normalize_spec(spec)
        for section, spec in specs.items()
        if isinstance(spec, dict) and spec.get("kind") == "struct"
    }


def _create_base_schema(
    connection: duckdb.DuckDBPyConnection,
    typed_specs: Mapping[str, Any],
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
            decoded_json_bytes BIGINT NOT NULL,
            decoded_payload_zlib BLOB NOT NULL
        );

        CREATE TABLE member_fields (
            member_id BIGINT NOT NULL,
            field_ordinal BIGINT NOT NULL,
            field_name VARCHAR NOT NULL,
            json_type VARCHAR NOT NULL,
            storage_kind VARCHAR NOT NULL
        );

        CREATE TABLE entity_rows (
            member_id BIGINT NOT NULL,
            game_id BIGINT NOT NULL,
            perspective_player_id BIGINT NOT NULL,
            archive_turn BIGINT NOT NULL,
            embedded_turn BIGINT NOT NULL,
            section_name VARCHAR NOT NULL,
            ordinal BIGINT NOT NULL,
            source_entity_id BIGINT,
            owner_id BIGINT,
            player_id BIGINT,
            x DOUBLE,
            y DOUBLE
        );

        CREATE TABLE typed_entity_schema (
            section_name VARCHAR NOT NULL,
            schema_json VARCHAR NOT NULL
        );
        """
    )
    connection.execute(
        "INSERT INTO corpus_metadata VALUES (?, current_timestamp::VARCHAR)",
        [CORPUS_DB_TYPED_SCHEMA],
    )

    arrow_schemas: dict[str, pa.Schema] = {}
    for section in sorted(typed_specs):
        schema = pa.schema(
            [
                pa.field("member_id", pa.int64(), nullable=False),
                pa.field("ordinal", pa.int64(), nullable=False),
                pa.field("data", _pa_type(typed_specs[section]), nullable=False),
            ]
        )
        arrow_schemas[section] = schema
        relation_name = f"_typed_schema_{section}"
        empty = pa.Table.from_arrays(
            [pa.array([], type=field.type) for field in schema],
            schema=schema,
        )
        connection.register(relation_name, empty)
        try:
            connection.execute(
                f'CREATE TABLE "typed_{section}" AS SELECT * FROM "{relation_name}"'
            )
        finally:
            connection.unregister(relation_name)
        connection.execute(
            "INSERT INTO typed_entity_schema VALUES (?, ?)",
            [
                section,
                json.dumps(typed_specs[section], ensure_ascii=False, sort_keys=True),
            ],
        )

    return arrow_schemas


_MEMBER_FIELDS_SCHEMA = pa.schema(
    [
        pa.field("member_id", pa.int64(), nullable=False),
        pa.field("field_ordinal", pa.int64(), nullable=False),
        pa.field("field_name", pa.string(), nullable=False),
        pa.field("json_type", pa.string(), nullable=False),
        pa.field("storage_kind", pa.string(), nullable=False),
    ]
)

_ENTITY_ROWS_SCHEMA = pa.schema(
    [
        pa.field("member_id", pa.int64(), nullable=False),
        pa.field("game_id", pa.int64(), nullable=False),
        pa.field("perspective_player_id", pa.int64(), nullable=False),
        pa.field("archive_turn", pa.int64(), nullable=False),
        pa.field("embedded_turn", pa.int64(), nullable=False),
        pa.field("section_name", pa.string(), nullable=False),
        pa.field("ordinal", pa.int64(), nullable=False),
        pa.field("source_entity_id", pa.int64(), nullable=True),
        pa.field("owner_id", pa.int64(), nullable=True),
        pa.field("player_id", pa.int64(), nullable=True),
        pa.field("x", pa.float64(), nullable=True),
        pa.field("y", pa.float64(), nullable=True),
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
    relation_name = f"_{table_name}_batch"
    connection.register(relation_name, table)
    try:
        connection.execute(f'INSERT INTO "{table_name}" SELECT * FROM "{relation_name}"')
    finally:
        connection.unregister(relation_name)


def _flush(
    connection: duckdb.DuckDBPyConnection,
    field_rows: list[tuple[Any, ...]],
    entity_rows: list[tuple[Any, ...]],
    typed_rows: dict[str, list[tuple[Any, ...]]],
    typed_schemas: Mapping[str, pa.Schema],
) -> None:
    _insert_arrow(connection, "member_fields", field_rows, _MEMBER_FIELDS_SCHEMA)
    _insert_arrow(connection, "entity_rows", entity_rows, _ENTITY_ROWS_SCHEMA)
    field_rows.clear()
    entity_rows.clear()
    for section, rows in typed_rows.items():
        if rows:
            _insert_arrow(
                connection,
                f"typed_{section}",
                rows,
                typed_schemas[section],
            )
            rows.clear()


def _create_indexes_and_views(
    connection: duckdb.DuckDBPyConnection,
    typed_specs: Mapping[str, Any],
) -> None:
    connection.execute(
        """
        CREATE INDEX idx_source_members_lookup
            ON source_members(game_id, perspective_player_id, archive_turn);
        CREATE INDEX idx_source_members_name
            ON source_members(game_id, source_member_name);
        CREATE INDEX idx_member_fields_lookup
            ON member_fields(member_id, field_name);
        CREATE INDEX idx_entity_member
            ON entity_rows(member_id, section_name, ordinal);
        CREATE INDEX idx_entity_lookup
            ON entity_rows(game_id, section_name, archive_turn, source_entity_id);
        CREATE INDEX idx_entity_site
            ON entity_rows(game_id, section_name, archive_turn, x, y);
        """
    )

    for section in (
        "players",
        "planets",
        "ships",
        "starbases",
        "ionstorms",
        "minefields",
        "vcrs",
        "relations",
        "messages",
        "notes",
    ):
        if section in typed_specs:
            connection.execute(
                f"""
                CREATE VIEW "{section}" AS
                SELECT e.*, t.data
                FROM entity_rows e
                JOIN "typed_{section}" t
                  ON t.member_id = e.member_id
                 AND t.ordinal = e.ordinal
                WHERE e.section_name = '{section}'
                """
            )
        else:
            connection.execute(
                f"CREATE VIEW \"{section}\" AS "
                f"SELECT * FROM entity_rows WHERE section_name = '{section}'"
            )

    connection.execute("ANALYZE")
    connection.execute("CHECKPOINT")


def import_archive_to_typed_database(
    archive_path: Path,
    database_path: Path,
    *,
    expected_game_id: int | None = None,
    commit_every_members: int = 128,
    arrow_batch_rows: int = 20_000,
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
    typed_specs = _learn_entity_specs(
        archive_path,
        expected_game_id=expected_game_id,
    )

    connection = duckdb.connect(str(database_path))
    observed_game_id: int | None = None
    turn_count = 0
    entity_count = 0
    decoded_json_bytes = 0
    zip_count = 0
    member_id = 0
    seen_turn_names: set[str] = set()
    field_rows: list[tuple[Any, ...]] = []
    entity_rows: list[tuple[Any, ...]] = []
    typed_rows: dict[str, list[tuple[Any, ...]]] = {
        section: [] for section in typed_specs
    }

    try:
        connection.execute("SET preserve_insertion_order = false")
        typed_schemas = _create_base_schema(connection, typed_specs)
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
                raw_sha256 = hashlib.sha256(raw).hexdigest()
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
                        raw_sha256,
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
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        raw_sha256,
                        hashlib.sha256(decoded).hexdigest(),
                        "gzip" if raw[:2] == b"\x1f\x8b" else "plain",
                        member.player,
                        member.turn,
                        embedded_turn,
                        len(decoded),
                        zlib.compress(decoded, level=6),
                    ],
                )

                for field_ordinal, (field_name, value) in enumerate(parsed.items()):
                    is_entity = (
                        isinstance(value, list)
                        and (
                            field_name in KNOWN_ENTITY_SECTIONS
                            or (value and all(isinstance(item, Mapping) for item in value))
                        )
                        and all(isinstance(item, Mapping) for item in value)
                    )
                    if not is_entity:
                        field_rows.append(
                            (
                                member_id,
                                field_ordinal,
                                field_name,
                                _json_type(value),
                                "member_blob",
                            )
                        )
                        continue

                    field_rows.append(
                        (
                            member_id,
                            field_ordinal,
                            field_name,
                            "array",
                            "typed_entity" if field_name in typed_specs else "entity_rows",
                        )
                    )
                    for ordinal, item in enumerate(value):
                        assert isinstance(item, Mapping)
                        entity_rows.append(
                            (
                                member_id,
                                game_id,
                                member.player,
                                member.turn,
                                embedded_turn,
                                field_name,
                                ordinal,
                                _first_int(item, "id"),
                                _first_int(item, "ownerid", "owner_id"),
                                _first_int(item, "playerid", "player_id"),
                                _typed_number(item.get("x")),
                                _typed_number(item.get("y")),
                            )
                        )
                        if field_name in typed_specs:
                            typed_rows[field_name].append(
                                (
                                    member_id,
                                    ordinal,
                                    _convert_value(
                                        item,
                                        typed_specs[field_name],
                                        f"{member.name}.{field_name}[{ordinal}]",
                                    ),
                                )
                            )
                        entity_count += 1

                buffered = len(field_rows) + len(entity_rows) + sum(
                    len(rows) for rows in typed_rows.values()
                )
                if buffered >= arrow_batch_rows:
                    _flush(
                        connection,
                        field_rows,
                        entity_rows,
                        typed_rows,
                        typed_schemas,
                    )

                if turn_count % commit_every_members == 0:
                    _flush(
                        connection,
                        field_rows,
                        entity_rows,
                        typed_rows,
                        typed_schemas,
                    )
                    connection.execute("COMMIT")
                    connection.execute("BEGIN TRANSACTION")

        if turn_count == 0 or observed_game_id is None:
            raise CorpusDbError("archive has no canonical playerN-turnM.trn members")

        _flush(connection, field_rows, entity_rows, typed_rows, typed_schemas)
        connection.execute("COMMIT")
        connection.execute(
            "INSERT INTO source_archives VALUES (?, ?, ?, ?, ?)",
            [1, observed_game_id, str(archive_path), archive_sha256, archive_bytes],
        )

        for section in typed_specs:
            generic_count = int(
                connection.execute(
                    "SELECT count(*) FROM entity_rows WHERE section_name = ?",
                    [section],
                ).fetchone()[0]
            )
            typed_count = int(
                connection.execute(
                    f'SELECT count(*) FROM "typed_{section}"'
                ).fetchone()[0]
            )
            if generic_count != typed_count:
                raise CorpusDbError(
                    f"{section}: generic/typed row-count mismatch "
                    f"{generic_count} != {typed_count}"
                )

        _create_indexes_and_views(connection, typed_specs)
    except BaseException:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        connection.close()

    return ImportResult(
        schema=CORPUS_DB_TYPED_SCHEMA,
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


def reconstruct_typed_member(
    connection: duckdb.DuckDBPyConnection,
    member_id: int,
) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT decoded_payload_zlib, decoded_payload_sha256
        FROM source_members
        WHERE member_id = ?
        """,
        [member_id],
    ).fetchone()
    if row is None:
        raise CorpusDbError(f"member not found: {member_id}")
    decoded = zlib.decompress(bytes(row[0]))
    if hashlib.sha256(decoded).hexdigest() != str(row[1]):
        raise CorpusDbError(f"member {member_id}: decoded payload hash mismatch")
    parsed = json.loads(decoded.decode("utf-8-sig"))
    if not isinstance(parsed, dict):
        raise CorpusDbError(f"member {member_id}: decoded payload is not an object")
    return parsed


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
                expected[key], actual[key], f"{path}.{key}"
            )
            if mismatch is not None:
                return mismatch
        return None
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return path, f"array length mismatch: {len(expected)} != {len(actual)}"
        for index, (left, right) in enumerate(zip(expected, actual)):
            mismatch = _first_semantic_mismatch(left, right, f"{path}[{index}]")
            if mismatch is not None:
                return mismatch
        return None
    if isinstance(expected, float) and math.isnan(expected) and math.isnan(actual):
        return None
    if expected != actual:
        return path, "value mismatch"
    return None


def validate_typed_semantic_parity(
    archive_path: Path,
    database_path: Path,
    *,
    max_mismatches: int = 100,
) -> ParityResult:
    archive_path = archive_path.resolve()
    database_path = database_path.resolve()
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
        if metadata is None or metadata[0] != CORPUS_DB_TYPED_SCHEMA:
            raise CorpusDbError(
                f"unexpected typed schema: {None if metadata is None else metadata[0]!r}"
            )

        archive_row = connection.execute(
            "SELECT game_id, archive_sha256, archive_bytes FROM source_archives"
        ).fetchone()
        if archive_row is None:
            raise CorpusDbError("missing source archive provenance")
        db_archive_game_id, db_archive_sha, db_archive_bytes = archive_row
        if db_archive_sha != _sha256_path(archive_path):
            raise CorpusDbError("source archive SHA256 differs from DB provenance")
        if int(db_archive_bytes) != archive_path.stat().st_size:
            raise CorpusDbError("source archive byte size differs from DB provenance")

        db_members = {
            str(row[0]): row[1:]
            for row in connection.execute(
                """
                SELECT source_member_name,
                       member_id,
                       game_id,
                       member_crc32,
                       member_uncompressed_size,
                       member_payload_sha256,
                       decoded_payload_sha256,
                       perspective_player_id,
                       archive_turn,
                       embedded_turn
                FROM source_members
                """
            ).fetchall()
        }
        entity_counts = {
            (int(row[0]), str(row[1])): int(row[2])
            for row in connection.execute(
                """
                SELECT member_id, section_name, count(*)
                FROM entity_rows
                GROUP BY member_id, section_name
                """
            ).fetchall()
        }

        seen: set[str] = set()
        with zipfile.ZipFile(archive_path, mode="r") as archive:
            for info in archive.infolist():
                match = TURN_MEMBER_RE.fullmatch(info.filename)
                if match is None or info.is_dir():
                    continue
                checked += 1
                seen.add(info.filename)
                with archive.open(info, mode="r") as stream:
                    raw = stream.read()
                member = TurnMember(
                    player=int(match.group("player")),
                    turn=int(match.group("turn")),
                    name=info.filename,
                )
                expected, decoded = _decode_member_json(raw, member)
                expected_game_id, expected_embedded_turn = _required_member_metadata(
                    expected, member
                )
                db_row = db_members.get(info.filename)
                if db_row is None:
                    if add(info.filename, "$", "source member absent in DB"):
                        break
                    continue
                (
                    member_id,
                    db_game_id,
                    crc32,
                    uncompressed_size,
                    payload_sha256,
                    decoded_payload_sha256,
                    perspective_player_id,
                    archive_turn,
                    embedded_turn,
                ) = db_row

                provenance_problem: str | None = None
                if int(db_game_id) != expected_game_id:
                    provenance_problem = "source member game_id mismatch"
                elif int(db_archive_game_id) != expected_game_id:
                    provenance_problem = "source archive game_id mismatch"
                elif int(crc32) != int(info.CRC):
                    provenance_problem = "member CRC mismatch"
                elif int(uncompressed_size) != int(info.file_size):
                    provenance_problem = "member size mismatch"
                elif payload_sha256 != hashlib.sha256(raw).hexdigest():
                    provenance_problem = "member payload SHA256 mismatch"
                elif decoded_payload_sha256 != hashlib.sha256(decoded).hexdigest():
                    provenance_problem = "decoded payload SHA256 mismatch"
                elif int(perspective_player_id) != member.player:
                    provenance_problem = "perspective_player_id mismatch"
                elif int(archive_turn) != member.turn:
                    provenance_problem = "archive_turn mismatch"
                elif int(embedded_turn) != expected_embedded_turn:
                    provenance_problem = "embedded_turn mismatch"
                if provenance_problem is not None:
                    if add(info.filename, "$", provenance_problem):
                        break
                    continue

                for field_name, value in expected.items():
                    if (
                        isinstance(value, list)
                        and all(isinstance(item, Mapping) for item in value)
                    ):
                        actual_count = entity_counts.get(
                            (int(member_id), field_name),
                            0,
                        )
                        if actual_count != len(value):
                            if add(
                                info.filename,
                                f"$.{field_name}",
                                f"entity row count mismatch: {actual_count} != {len(value)}",
                            ):
                                break
                if len(mismatches) >= max_mismatches:
                    break

                try:
                    actual = reconstruct_typed_member(connection, int(member_id))
                except Exception as exc:
                    if add(info.filename, "$", f"reconstruction failed: {exc}"):
                        break
                    continue
                mismatch = _first_semantic_mismatch(expected, actual)
                if mismatch is not None:
                    if add(info.filename, mismatch[0], mismatch[1]):
                        break

        if len(mismatches) < max_mismatches:
            for extra in sorted(set(db_members) - seen):
                if add(extra, "$", "DB source member absent from archive"):
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
