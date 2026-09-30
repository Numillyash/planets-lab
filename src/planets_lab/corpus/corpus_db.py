from __future__ import annotations

import hashlib
import json
import math
import os
import re
import resource
import time
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import duckdb
import pyarrow as pa

from .archive import TURN_MEMBER_RE, TurnMember
from .normalizer import CorpusNormalizationError, _decode_member_json


CORPUS_DB_SCHEMA = "planets-lab.corpus-db.v1"
CURRENT_FILE = "CURRENT"
KNOWN_ENTITY_SECTIONS = frozenset(
    {
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
        "nebulas",
        "stars",
        "stock",
        "hulls",
        "races",
        "advantages",
    }
)


class CorpusDbError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ImportResult:
    schema: str
    database_path: str
    game_id: int
    archive_path: str
    archive_sha256: str
    archive_bytes: int
    zip_members: int
    turn_members: int
    decoded_json_bytes: int
    entity_rows: int
    import_wall_seconds: float
    peak_rss_bytes: int


@dataclass(frozen=True, slots=True)
class ParityMismatch:
    member: str
    path: str
    reason: str


@dataclass(frozen=True, slots=True)
class ParityResult:
    checked: int
    failed: int
    mismatches: tuple[ParityMismatch, ...]
    wall_seconds: float
    peak_rss_bytes: int


@dataclass(frozen=True, slots=True)
class PublishResult:
    build_id: str
    generation_path: str
    generation_sha256: str
    current_value: str
    manifest_path: str


@dataclass(frozen=True, slots=True)
class QueryBenchmarkResult:
    kind: str
    database_path: str
    game_id: int
    target: Mapping[str, Any]
    result_rows: int
    wall_seconds: float
    peak_rss_bytes: int


def _peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    # Linux reports KiB; macOS reports bytes. The project runtime is Linux, but
    # retaining this guard makes local tests/reporting unsurprising elsewhere.
    if os.uname().sysname.lower() == "darwin":
        return value
    return value * 1024


def _sha256_path(path: Path, *, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=True,
    )


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, Mapping):
        return "object"
    raise CorpusDbError(f"unsupported decoded JSON value type: {type(value).__name__}")


def _typed_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _typed_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _first_int(record: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        if key in record:
            value = _typed_int(record[key])
            if value is not None:
                return value
    return None


def _is_entity_array(field_name: str, value: Any) -> bool:
    if not isinstance(value, list):
        return False
    if field_name in KNOWN_ENTITY_SECTIONS:
        return not value or all(isinstance(item, Mapping) for item in value)
    return bool(value) and all(isinstance(item, Mapping) for item in value)


def _required_member_metadata(parsed: Mapping[str, Any], member: TurnMember) -> tuple[int, int]:
    game = parsed.get("game")
    player = parsed.get("player")
    if not isinstance(game, Mapping):
        raise CorpusNormalizationError(f"{member.name}: game must be an object")
    if not isinstance(player, Mapping):
        raise CorpusNormalizationError(f"{member.name}: player must be an object")

    game_id = _typed_int(game.get("id"))
    embedded_turn = _typed_int(game.get("turn"))
    player_id = _typed_int(player.get("id"))
    if game_id is None:
        raise CorpusNormalizationError(f"{member.name}.game.id must be an integer")
    if embedded_turn is None:
        raise CorpusNormalizationError(f"{member.name}.game.turn must be an integer")
    if player_id is None:
        raise CorpusNormalizationError(f"{member.name}.player.id must be an integer")
    if player_id != member.player:
        raise CorpusNormalizationError(
            f"{member.name}: filename player {member.player} != payload player {player_id}"
        )
    return game_id, embedded_turn


def _create_schema(connection: duckdb.DuckDBPyConnection) -> None:
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
            payload_json VARCHAR
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
            y DOUBLE,
            payload_json VARCHAR NOT NULL
        );
        """
    )
    connection.execute(
        "INSERT INTO corpus_metadata VALUES (?, ?)",
        [CORPUS_DB_SCHEMA, datetime.now(timezone.utc).isoformat()],
    )


def _create_indexes_and_views(connection: duckdb.DuckDBPyConnection) -> None:
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
        connection.execute(
            f"CREATE VIEW {section} AS "
            f"SELECT * FROM entity_rows WHERE section_name = '{section}'"
        )

    for field in ("game", "player", "settings"):
        connection.execute(
            f"""
            CREATE VIEW {field}_fields AS
            SELECT m.game_id,
                   m.perspective_player_id,
                   m.archive_turn,
                   m.embedded_turn,
                   f.member_id,
                   f.payload_json
            FROM member_fields f
            JOIN source_members m USING (member_id)
            WHERE f.field_name = '{field}'
            """
        )

    connection.execute("ANALYZE")
    connection.execute("CHECKPOINT")


_MEMBER_FIELDS_ARROW_SCHEMA = pa.schema(
    [
        pa.field("member_id", pa.int64(), nullable=False),
        pa.field("field_ordinal", pa.int64(), nullable=False),
        pa.field("field_name", pa.string(), nullable=False),
        pa.field("json_type", pa.string(), nullable=False),
        pa.field("storage_kind", pa.string(), nullable=False),
        pa.field("payload_json", pa.string(), nullable=True),
    ]
)

_ENTITY_ROWS_ARROW_SCHEMA = pa.schema(
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
        pa.field("payload_json", pa.string(), nullable=False),
    ]
)


def _insert_arrow_rows(
    connection: duckdb.DuckDBPyConnection,
    *,
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
    relation_name = f"_{table_name}_arrow_batch"
    connection.register(relation_name, table)
    try:
        connection.execute(
            f"INSERT INTO {table_name} SELECT * FROM {relation_name}"
        )
    finally:
        connection.unregister(relation_name)


def _flush_import_rows(
    connection: duckdb.DuckDBPyConnection,
    field_rows: list[tuple[Any, ...]],
    entity_rows: list[tuple[Any, ...]],
) -> None:
    _insert_arrow_rows(
        connection,
        table_name="member_fields",
        rows=field_rows,
        schema=_MEMBER_FIELDS_ARROW_SCHEMA,
    )
    _insert_arrow_rows(
        connection,
        table_name="entity_rows",
        rows=entity_rows,
        schema=_ENTITY_ROWS_ARROW_SCHEMA,
    )
    field_rows.clear()
    entity_rows.clear()


def _entity_row(
    *,
    member_id: int,
    game_id: int,
    perspective_player_id: int,
    archive_turn: int,
    embedded_turn: int,
    section_name: str,
    ordinal: int,
    item: Mapping[str, Any],
) -> tuple[Any, ...]:
    return (
        member_id,
        game_id,
        perspective_player_id,
        archive_turn,
        embedded_turn,
        section_name,
        ordinal,
        _first_int(item, "id"),
        _first_int(item, "ownerid", "owner_id"),
        _first_int(item, "playerid", "player_id"),
        _typed_number(item.get("x")),
        _typed_number(item.get("y")),
        _canonical_json(dict(item)),
    )


def import_archive_to_database(
    archive_path: Path,
    database_path: Path,
    *,
    expected_game_id: int | None = None,
    commit_every_members: int = 128,
    arrow_batch_rows: int = 20_000,
) -> ImportResult:
    """Import one immutable loadall ZIP directly into a new DuckDB file.

    The importer keeps one decoded turn member plus a bounded Arrow row batch in
    Python memory. It never builds ``ArchiveTurnSnapshot`` objects for the whole
    game and never extracts the ZIP to disk.
    """

    archive_path = archive_path.resolve()
    database_path = database_path.resolve()
    if not archive_path.is_file():
        raise CorpusDbError(f"archive not found: {archive_path}")
    if database_path.exists():
        raise CorpusDbError(f"database already exists: {database_path}")
    if commit_every_members <= 0:
        raise CorpusDbError("commit_every_members must be positive")
    if arrow_batch_rows <= 0:
        raise CorpusDbError("arrow_batch_rows must be positive")

    database_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    archive_sha256 = _sha256_path(archive_path)
    archive_bytes = archive_path.stat().st_size

    connection = duckdb.connect(str(database_path))
    observed_game_id: int | None = None
    turn_count = 0
    entity_count = 0
    decoded_json_bytes = 0
    zip_count = 0
    member_id = 0
    seen_turn_names: set[str] = set()
    pending_field_rows: list[tuple[Any, ...]] = []
    pending_entity_rows: list[tuple[Any, ...]] = []

    try:
        connection.execute("SET preserve_insertion_order = false")
        _create_schema(connection)
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
                transport = "gzip" if raw[:2] == b"\x1f\x8b" else "plain"
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
                        raw_sha256,
                        hashlib.sha256(decoded).hexdigest(),
                        transport,
                        member.player,
                        member.turn,
                        embedded_turn,
                        len(decoded),
                    ],
                )

                field_rows: list[tuple[Any, ...]] = []
                entity_rows: list[tuple[Any, ...]] = []
                for field_ordinal, (field_name, value) in enumerate(parsed.items()):
                    if _is_entity_array(field_name, value):
                        field_rows.append(
                            (
                                member_id,
                                field_ordinal,
                                field_name,
                                "array",
                                "entity_rows",
                                None,
                            )
                        )
                        assert isinstance(value, list)
                        for ordinal, item in enumerate(value):
                            assert isinstance(item, Mapping)
                            entity_rows.append(
                                _entity_row(
                                    member_id=member_id,
                                    game_id=game_id,
                                    perspective_player_id=member.player,
                                    archive_turn=member.turn,
                                    embedded_turn=embedded_turn,
                                    section_name=field_name,
                                    ordinal=ordinal,
                                    item=item,
                                )
                            )
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

                pending_field_rows.extend(field_rows)
                pending_entity_rows.extend(entity_rows)
                entity_count += len(entity_rows)

                if (
                    len(pending_field_rows) >= arrow_batch_rows
                    or len(pending_entity_rows) >= arrow_batch_rows
                ):
                    _flush_import_rows(
                        connection, pending_field_rows, pending_entity_rows
                    )

                if turn_count % commit_every_members == 0:
                    _flush_import_rows(
                        connection, pending_field_rows, pending_entity_rows
                    )
                    connection.execute("COMMIT")
                    connection.execute("BEGIN TRANSACTION")

        if turn_count == 0 or observed_game_id is None:
            raise CorpusDbError("archive has no canonical playerN-turnM.trn members")

        _flush_import_rows(connection, pending_field_rows, pending_entity_rows)
        connection.execute("COMMIT")
        connection.execute(
            "INSERT INTO source_archives VALUES (?, ?, ?, ?, ?)",
            [1, observed_game_id, str(archive_path), archive_sha256, archive_bytes],
        )
        _create_indexes_and_views(connection)
    except BaseException:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        connection.close()

    return ImportResult(
        schema=CORPUS_DB_SCHEMA,
        database_path=str(database_path),
        game_id=observed_game_id,
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


def reconstruct_member(
    connection: duckdb.DuckDBPyConnection,
    member_id: int,
) -> dict[str, Any]:
    rows = connection.execute(
        """
        SELECT field_name, storage_kind, payload_json
        FROM member_fields
        WHERE member_id = ?
        ORDER BY field_ordinal
        """,
        [member_id],
    ).fetchall()
    entity_payloads: dict[str, list[str]] = {}
    for section_name, payload_json in connection.execute(
        """
        SELECT section_name, payload_json
        FROM entity_rows
        WHERE member_id = ?
        ORDER BY section_name, ordinal
        """,
        [member_id],
    ).fetchall():
        entity_payloads.setdefault(str(section_name), []).append(str(payload_json))

    result: dict[str, Any] = {}
    for field_name, storage_kind, payload_json in rows:
        if storage_kind == "inline_json":
            if payload_json is None:
                raise CorpusDbError(
                    f"member {member_id} field {field_name}: inline payload missing"
                )
            result[field_name] = json.loads(payload_json)
            continue
        if storage_kind != "entity_rows":
            raise CorpusDbError(
                f"member {member_id} field {field_name}: unknown storage {storage_kind!r}"
            )
        result[field_name] = [
            json.loads(value) for value in entity_payloads.get(str(field_name), [])
        ]
    return result


def _path_key(path: str, key: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        return f"{path}.{key}"
    return f"{path}[{json.dumps(key, ensure_ascii=False)}]"


def _scalar_fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()[:16]


def _first_semantic_mismatch(expected: Any, actual: Any, path: str = "$") -> tuple[str, str] | None:
    if type(expected) is not type(actual):
        return path, f"type mismatch: {type(expected).__name__} != {type(actual).__name__}"

    if isinstance(expected, dict):
        expected_keys = set(expected)
        actual_keys = set(actual)
        missing = sorted(expected_keys - actual_keys)
        if missing:
            return _path_key(path, missing[0]), "field absent in DB reconstruction"
        extra = sorted(actual_keys - expected_keys)
        if extra:
            return _path_key(path, extra[0]), "extra field in DB reconstruction"
        for key in expected:
            mismatch = _first_semantic_mismatch(
                expected[key], actual[key], _path_key(path, key)
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
        return (
            path,
            "value mismatch: "
            f"expected_sha={_scalar_fingerprint(expected)} "
            f"actual_sha={_scalar_fingerprint(actual)}",
        )
    return None


def validate_semantic_parity(
    archive_path: Path,
    database_path: Path,
    *,
    max_mismatches: int = 100,
) -> ParityResult:
    """Validate full ZIP provenance and semantic TRN round-trip parity.

    TRN comparison is type-sensitive: ``False``, ``0``, ``0.0``, ``null`` and
    an absent key are all different. Object key ordering is intentionally ignored;
    array ordering is strict. Every ZIP member is also CRC/size/SHA checked against
    the provenance rows before a staging generation can be published.
    """

    archive_path = archive_path.resolve()
    database_path = database_path.resolve()
    if max_mismatches <= 0:
        raise CorpusDbError("max_mismatches must be positive")
    started = time.perf_counter()
    mismatches: list[ParityMismatch] = []
    checked = 0

    def add_mismatch(member: str, path: str, reason: str) -> bool:
        mismatches.append(ParityMismatch(member, path, reason))
        return len(mismatches) >= max_mismatches

    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        db_archive = connection.execute(
            "SELECT game_id, archive_sha256, archive_bytes FROM source_archives"
        ).fetchall()
        if len(db_archive) != 1:
            raise CorpusDbError(f"expected one source archive row, got {len(db_archive)}")
        db_archive_game_id, db_archive_sha, db_archive_bytes = db_archive[0]
        actual_archive_sha = _sha256_path(archive_path)
        if db_archive_sha != actual_archive_sha:
            raise CorpusDbError("source archive SHA256 differs from DB provenance")
        if int(db_archive_bytes) != archive_path.stat().st_size:
            raise CorpusDbError("source archive byte size differs from DB provenance")

        db_zip_members = {
            int(row[0]): row[1:]
            for row in connection.execute(
                """
                SELECT member_ordinal,
                       member_name,
                       crc32,
                       compressed_size,
                       uncompressed_size,
                       is_directory,
                       is_turn_member,
                       member_payload_sha256
                FROM zip_members
                ORDER BY member_ordinal
                """
            ).fetchall()
        }
        db_members = {
            row[0]: row[1:]
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

        seen_turns: set[str] = set()
        seen_zip_ordinals: set[int] = set()
        with zipfile.ZipFile(archive_path, mode="r") as archive:
            infos = archive.infolist()
            for member_ordinal, info in enumerate(infos):
                seen_zip_ordinals.add(member_ordinal)
                match = TURN_MEMBER_RE.fullmatch(info.filename)
                is_turn = match is not None
                raw: bytes | None = None
                raw_sha256: str | None = None
                if not info.is_dir():
                    with archive.open(info, mode="r") as stream:
                        raw = stream.read()
                    raw_sha256 = hashlib.sha256(raw).hexdigest()

                zip_row = db_zip_members.get(member_ordinal)
                if zip_row is None:
                    if add_mismatch(info.filename, "$", "ZIP member absent in DB provenance"):
                        break
                else:
                    (
                        db_name,
                        db_crc32,
                        db_compressed_size,
                        db_uncompressed_size,
                        db_is_directory,
                        db_is_turn,
                        db_payload_sha256,
                    ) = zip_row
                    zip_problem: str | None = None
                    if db_name != info.filename:
                        zip_problem = f"ZIP member name mismatch at ordinal {member_ordinal}"
                    elif int(db_crc32) != int(info.CRC):
                        zip_problem = "ZIP member CRC mismatch"
                    elif int(db_compressed_size) != int(info.compress_size):
                        zip_problem = "ZIP member compressed size mismatch"
                    elif int(db_uncompressed_size) != int(info.file_size):
                        zip_problem = "ZIP member uncompressed size mismatch"
                    elif bool(db_is_directory) != bool(info.is_dir()):
                        zip_problem = "ZIP directory flag mismatch"
                    elif bool(db_is_turn) != is_turn:
                        zip_problem = "ZIP turn-member flag mismatch"
                    elif db_payload_sha256 != raw_sha256:
                        zip_problem = "ZIP member payload SHA256 mismatch"
                    if zip_problem is not None and add_mismatch(
                        info.filename, "$", zip_problem
                    ):
                        break

                if not is_turn:
                    continue
                if info.filename in seen_turns:
                    raise CorpusDbError(
                        f"duplicate canonical turn member name: {info.filename}"
                    )
                seen_turns.add(info.filename)
                checked += 1
                db_row = db_members.get(info.filename)
                if db_row is None:
                    if add_mismatch(info.filename, "$", "source member absent in DB"):
                        break
                    continue

                assert match is not None and raw is not None and raw_sha256 is not None
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
                member = TurnMember(
                    player=int(match.group("player")),
                    turn=int(match.group("turn")),
                    name=info.filename,
                )
                expected, decoded = _decode_member_json(raw, member)
                expected_game_id, expected_embedded_turn = _required_member_metadata(
                    expected, member
                )

                provenance_problem: str | None = None
                if int(db_game_id) != expected_game_id:
                    provenance_problem = "source member game_id mismatch"
                elif int(db_archive_game_id) != expected_game_id:
                    provenance_problem = "source archive game_id mismatch"
                elif int(crc32) != int(info.CRC):
                    provenance_problem = "member CRC mismatch"
                elif int(uncompressed_size) != int(info.file_size):
                    provenance_problem = "member size mismatch"
                elif payload_sha256 != raw_sha256:
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
                    if add_mismatch(info.filename, "$", provenance_problem):
                        break
                    continue

                actual = reconstruct_member(connection, int(member_id))
                mismatch = _first_semantic_mismatch(expected, actual)
                if mismatch is not None:
                    path, reason = mismatch
                    if add_mismatch(info.filename, path, reason):
                        break

        if len(mismatches) < max_mismatches:
            extra_zip_ordinals = sorted(set(db_zip_members) - seen_zip_ordinals)
            for ordinal in extra_zip_ordinals:
                member_name = str(db_zip_members[ordinal][0])
                if add_mismatch(member_name, "$", "DB ZIP member absent from archive"):
                    break

        if len(mismatches) < max_mismatches:
            extras = sorted(set(db_members) - seen_turns)
            for member_name in extras:
                if add_mismatch(member_name, "$", "DB source member absent from archive"):
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


def _find_checkout_root() -> Path | None:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src" / "planets_lab").is_dir():
            return parent
    return None


def ensure_external_db_root(root: Path) -> Path:
    resolved = root.expanduser().resolve()
    checkout = _find_checkout_root()
    if checkout is not None and (resolved == checkout or checkout in resolved.parents):
        raise CorpusDbError(
            f"PLANETS_CORPUS_DB_ROOT must be outside the planets-lab checkout: {resolved}"
        )
    for name in ("generations", "manifests", "staging"):
        (resolved / name).mkdir(parents=True, exist_ok=True)
    return resolved


def resolve_current_generation(root: Path) -> Path:
    root = root.expanduser().resolve()
    current = root / CURRENT_FILE
    if not current.is_file():
        raise CorpusDbError(f"CURRENT not found under {root}")
    value = current.read_text(encoding="utf-8").strip()
    if not value:
        raise CorpusDbError("CURRENT is empty")
    candidate = (root / value).resolve()
    generations = (root / "generations").resolve()
    if candidate.parent != generations or candidate.suffix != ".duckdb":
        raise CorpusDbError(f"CURRENT points outside generations: {value!r}")
    if not candidate.is_file():
        raise CorpusDbError(f"CURRENT generation does not exist: {candidate}")
    return candidate


def connect_current_read_only(root: Path) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(resolve_current_generation(root)), read_only=True)


def publish_generation(
    *,
    root: Path,
    staging_path: Path,
    build_id: str,
    import_result: ImportResult,
    parity_result: ParityResult,
) -> PublishResult:
    if parity_result.failed:
        raise CorpusDbError("refusing to publish a generation with parity failures")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", build_id):
        raise CorpusDbError(f"unsafe build id: {build_id!r}")

    root = ensure_external_db_root(root)
    staging_path = staging_path.resolve()
    staging_dir = (root / "staging").resolve()
    if staging_path.parent != staging_dir:
        raise CorpusDbError("staging database must live directly under <root>/staging")
    if not staging_path.is_file():
        raise CorpusDbError(f"staging database not found: {staging_path}")

    generation_name = f"{build_id}.duckdb"
    generation_path = (root / "generations" / generation_name).resolve()
    if generation_path.exists():
        raise CorpusDbError(f"generation already exists: {generation_path}")

    os.replace(staging_path, generation_path)
    generation_sha256 = _sha256_path(generation_path)
    try:
        generation_path.chmod(0o444)
    except OSError:
        pass

    manifest = {
        "schema": import_result.schema,
        "build_id": build_id,
        "published_at_utc": datetime.now(timezone.utc).isoformat(),
        "generation": {
            "path": f"generations/{generation_name}",
            "sha256": generation_sha256,
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

    current_value = f"generations/{generation_name}"
    current_tmp = root / f".{CURRENT_FILE}.{os.getpid()}.tmp"
    current_tmp.write_text(current_value + "\n", encoding="utf-8")
    os.replace(current_tmp, root / CURRENT_FILE)

    return PublishResult(
        build_id=build_id,
        generation_path=str(generation_path),
        generation_sha256=generation_sha256,
        current_value=current_value,
        manifest_path=str(manifest_path),
    )


def default_build_id(game_id: int, archive_sha256: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"corpus-v1-g{game_id}-{stamp}-{archive_sha256[:12]}"


def benchmark_query(
    database_path: Path,
    *,
    kind: str,
    game_id: int,
) -> QueryBenchmarkResult:
    """Run one bounded indexed query in a fresh caller process.

    The CLI exposes this one query per process so ``ru_maxrss`` is attributable
    to that query class rather than accumulated across a benchmark suite.
    """

    database_path = database_path.resolve()
    if kind not in {"turn-pair", "vcr-site"}:
        raise CorpusDbError(f"unsupported query benchmark kind: {kind!r}")
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
            perspective_player_id, archive_turn = map(int, selected)
            rows = connection.execute(
                """
                SELECT e.section_name, count(*) AS rows
                FROM entity_rows e
                WHERE e.game_id = ?
                  AND e.perspective_player_id = ?
                  AND e.archive_turn BETWEEN ? AND ?
                GROUP BY e.section_name
                ORDER BY e.section_name
                """,
                [game_id, perspective_player_id, archive_turn - 1, archive_turn],
            ).fetchall()
            target: Mapping[str, Any] = {
                "perspective_player_id": perspective_player_id,
                "archive_turn_before": archive_turn - 1,
                "archive_turn_after": archive_turn,
            }
        else:
            selected = connection.execute(
                """
                SELECT archive_turn, x, y, count(*) AS rows
                FROM entity_rows
                WHERE game_id = ?
                  AND section_name = 'vcrs'
                  AND x IS NOT NULL
                  AND y IS NOT NULL
                GROUP BY archive_turn, x, y
                ORDER BY rows DESC, archive_turn, x, y
                LIMIT 1
                """,
                [game_id],
            ).fetchone()
            if selected is None:
                raise CorpusDbError(f"game {game_id}: no VCR rows with an indexed site")
            archive_turn = int(selected[0])
            x = float(selected[1])
            y = float(selected[2])
            rows = connection.execute(
                """
                SELECT perspective_player_id, count(*) AS rows
                FROM entity_rows
                WHERE game_id = ?
                  AND section_name = 'vcrs'
                  AND archive_turn = ?
                  AND x = ?
                  AND y = ?
                GROUP BY perspective_player_id
                ORDER BY perspective_player_id
                """,
                [game_id, archive_turn, x, y],
            ).fetchall()
            target = {
                "archive_turn": archive_turn,
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


def database_stats(database_path: Path) -> dict[str, Any]:
    database_path = database_path.resolve()
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        game_ids = [row[0] for row in connection.execute(
            "SELECT DISTINCT game_id FROM source_members ORDER BY game_id"
        ).fetchall()]
        archive = connection.execute(
            "SELECT archive_sha256, archive_bytes FROM source_archives"
        ).fetchone()
        return {
            "database_path": str(database_path),
            "database_bytes": database_path.stat().st_size,
            "game_ids": game_ids,
            "source_archive_sha256": archive[0] if archive else None,
            "source_archive_bytes": int(archive[1]) if archive else None,
            "decoded_json_bytes": int(
                connection.execute(
                    "SELECT coalesce(sum(decoded_json_bytes), 0) FROM source_members"
                ).fetchone()[0]
            ),
            "source_members": connection.execute("SELECT count(*) FROM source_members").fetchone()[0],
            "entity_rows": connection.execute("SELECT count(*) FROM entity_rows").fetchone()[0],
            "member_fields": connection.execute("SELECT count(*) FROM member_fields").fetchone()[0],
        }
    finally:
        connection.close()


@dataclass(frozen=True, slots=True)
class StorageAttributionStage:
    name: str
    database_bytes: int
    delta_bytes: int
    wall_seconds: float
    process_peak_rss_bytes: int


@dataclass(frozen=True, slots=True)
class StorageAttributionResult:
    source_database_path: str
    source_database_bytes: int
    scratch_database_path: str
    memory_limit: str
    threads: int
    table_stages: tuple[StorageAttributionStage, ...]
    entity_layout_stages: tuple[StorageAttributionStage, ...]
    stages: tuple[StorageAttributionStage, ...]


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _measure_entity_layout_variant(
    source: Path,
    scratch: Path,
    *,
    name: str,
    select_list: str,
    memory_limit: str,
    threads: int,
) -> StorageAttributionStage:
    if scratch.exists():
        raise CorpusDbError(f"entity-layout scratch database already exists: {scratch}")

    started = time.perf_counter()
    connection = duckdb.connect(str(scratch))
    try:
        connection.execute(f"SET memory_limit = {_sql_literal(memory_limit)}")
        connection.execute(f"SET threads = {int(threads)}")
        connection.execute("SET preserve_insertion_order = false")
        connection.execute(
            f"ATTACH {_sql_literal(str(source))} AS source_db (READ_ONLY)"
        )
        connection.execute(
            f"CREATE TABLE entity_rows AS "
            f"SELECT {select_list} FROM source_db.entity_rows"
        )
        connection.execute("CHECKPOINT")
        size = scratch.stat().st_size
        return StorageAttributionStage(
            name=name,
            database_bytes=size,
            delta_bytes=size,
            wall_seconds=time.perf_counter() - started,
            process_peak_rss_bytes=_peak_rss_bytes(),
        )
    finally:
        connection.close()
        try:
            scratch.unlink()
        except FileNotFoundError:
            pass


def attribute_storage(
    database_path: Path,
    scratch_path: Path,
    *,
    memory_limit: str = "4GB",
    threads: int = 2,
) -> StorageAttributionResult:
    """Attribute physical DB size to base tables, entity layout and indexes.

    The source generation is attached READ_ONLY. The main disposable database
    copies the six v1 base tables one by one, checkpoints after each table, then
    adds the current secondary indexes in groups. Two additional disposable
    databases measure alternative entity-row layouts without publishing or
    changing CURRENT.
    """

    source = database_path.expanduser().resolve()
    scratch = scratch_path.expanduser().resolve()
    if not source.is_file():
        raise CorpusDbError(f"source database not found: {source}")
    if scratch == source:
        raise CorpusDbError("scratch database must differ from source generation")
    if scratch.exists():
        raise CorpusDbError(f"scratch database already exists: {scratch}")
    if threads <= 0:
        raise CorpusDbError("threads must be positive")

    scratch.parent.mkdir(parents=True, exist_ok=True)
    source_bytes = source.stat().st_size
    connection = duckdb.connect(str(scratch))
    table_stages: list[StorageAttributionStage] = []
    stages: list[StorageAttributionStage] = []
    previous_table_size = 0
    previous_size = 0

    try:
        connection.execute(f"SET memory_limit = {_sql_literal(memory_limit)}")
        connection.execute(f"SET threads = {int(threads)}")
        connection.execute("SET preserve_insertion_order = false")
        connection.execute(
            f"ATTACH {_sql_literal(str(source))} AS source_db (READ_ONLY)"
        )

        data_started = time.perf_counter()
        for table in (
            "corpus_metadata",
            "source_archives",
            "zip_members",
            "source_members",
            "member_fields",
            "entity_rows",
        ):
            started = time.perf_counter()
            connection.execute(
                f"CREATE TABLE {table} AS SELECT * FROM source_db.{table}"
            )
            connection.execute("CHECKPOINT")
            size = scratch.stat().st_size
            table_stages.append(
                StorageAttributionStage(
                    name=table,
                    database_bytes=size,
                    delta_bytes=size - previous_table_size,
                    wall_seconds=time.perf_counter() - started,
                    process_peak_rss_bytes=_peak_rss_bytes(),
                )
            )
            previous_table_size = size

        previous_size = scratch.stat().st_size
        stages.append(
            StorageAttributionStage(
                name="data_only",
                database_bytes=previous_size,
                delta_bytes=previous_size,
                wall_seconds=time.perf_counter() - data_started,
                process_peak_rss_bytes=_peak_rss_bytes(),
            )
        )

        index_stages = (
            (
                "source_member_indexes",
                (
                    "CREATE INDEX idx_source_members_lookup "
                    "ON source_members(game_id, perspective_player_id, archive_turn)",
                    "CREATE INDEX idx_source_members_name "
                    "ON source_members(game_id, source_member_name)",
                ),
            ),
            (
                "member_field_index",
                (
                    "CREATE INDEX idx_member_fields_lookup "
                    "ON member_fields(member_id, field_name)",
                ),
            ),
            (
                "entity_member_index",
                (
                    "CREATE INDEX idx_entity_member "
                    "ON entity_rows(member_id, section_name, ordinal)",
                ),
            ),
            (
                "entity_id_index",
                (
                    "CREATE INDEX idx_entity_lookup "
                    "ON entity_rows(game_id, section_name, archive_turn, source_entity_id)",
                ),
            ),
            (
                "entity_site_index",
                (
                    "CREATE INDEX idx_entity_site "
                    "ON entity_rows(game_id, section_name, archive_turn, x, y)",
                ),
            ),
        )
        for name, statements in index_stages:
            started = time.perf_counter()
            for statement in statements:
                connection.execute(statement)
            connection.execute("CHECKPOINT")
            size = scratch.stat().st_size
            stages.append(
                StorageAttributionStage(
                    name=name,
                    database_bytes=size,
                    delta_bytes=size - previous_size,
                    wall_seconds=time.perf_counter() - started,
                    process_peak_rss_bytes=_peak_rss_bytes(),
                )
            )
            previous_size = size

        started = time.perf_counter()
        connection.execute("ANALYZE")
        connection.execute("CHECKPOINT")
        size = scratch.stat().st_size
        stages.append(
            StorageAttributionStage(
                name="analyze",
                database_bytes=size,
                delta_bytes=size - previous_size,
                wall_seconds=time.perf_counter() - started,
                process_peak_rss_bytes=_peak_rss_bytes(),
            )
        )
    except BaseException:
        connection.close()
        try:
            scratch.unlink()
        except FileNotFoundError:
            pass
        raise
    else:
        connection.close()

    entity_variants = (
        (
            "entity_keys_only",
            "member_id, section_name, ordinal",
        ),
        (
            "entity_query_projection_only",
            (
                "member_id, section_name, ordinal, source_entity_id, owner_id, "
                "player_id, x, y"
            ),
        ),
        (
            "entity_all_context_no_payload",
            (
                "member_id, game_id, perspective_player_id, archive_turn, "
                "embedded_turn, section_name, ordinal, source_entity_id, "
                "owner_id, player_id, x, y"
            ),
        ),
        (
            "entity_payload_only",
            "payload_json",
        ),
        (
            "entity_semantic_min",
            "member_id, section_name, ordinal, payload_json",
        ),
        (
            "entity_query_slim",
            (
                "member_id, section_name, ordinal, source_entity_id, owner_id, "
                "player_id, x, y, payload_json"
            ),
        ),
    )
    entity_layout_stages = tuple(
        _measure_entity_layout_variant(
            source,
            scratch.with_name(f"{scratch.stem}-{name}.duckdb"),
            name=name,
            select_list=select_list,
            memory_limit=memory_limit,
            threads=threads,
        )
        for name, select_list in entity_variants
    )

    return StorageAttributionResult(
        source_database_path=str(source),
        source_database_bytes=source_bytes,
        scratch_database_path=str(scratch),
        memory_limit=memory_limit,
        threads=threads,
        table_stages=tuple(table_stages),
        entity_layout_stages=entity_layout_stages,
        stages=tuple(stages),
    )



@dataclass(frozen=True, slots=True)
class PayloadSectionProfile:
    section_name: str
    rows: int
    logical_payload_bytes: int
    average_payload_bytes: float
    max_payload_bytes: int
    approximate_distinct_payloads: int


@dataclass(frozen=True, slots=True)
class PayloadObjectProfile:
    section_name: str
    member_id: int
    source_entity_id: int | None
    payload_bytes: int
    keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PayloadProfileResult:
    database_path: str
    decoded_json_bytes: int
    entity_rows: int
    entity_payload_logical_bytes: int
    member_field_payload_logical_bytes: int
    entity_payload_vs_decoded_ratio: float
    sections: tuple[PayloadSectionProfile, ...]
    largest_objects: tuple[PayloadObjectProfile, ...]
    wall_seconds: float
    peak_rss_bytes: int


def profile_payloads(
    database_path: Path,
    *,
    largest_limit: int = 20,
) -> PayloadProfileResult:
    """Profile logical lossless payload contents without printing source values."""

    if largest_limit <= 0:
        raise CorpusDbError("largest_limit must be positive")

    database_path = database_path.expanduser().resolve()
    started = time.perf_counter()
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        length_expr = "octet_length(encode(payload_json))"
        decoded_json_bytes = int(
            connection.execute(
                "SELECT coalesce(sum(decoded_json_bytes), 0) FROM source_members"
            ).fetchone()[0]
        )
        entity_rows, entity_payload_bytes = connection.execute(
            f"""
            SELECT count(*), coalesce(sum({length_expr}), 0)
            FROM entity_rows
            """
        ).fetchone()
        member_field_payload_bytes = int(
            connection.execute(
                """
                SELECT coalesce(sum(octet_length(encode(payload_json))), 0)
                FROM member_fields
                WHERE payload_json IS NOT NULL
                """
            ).fetchone()[0]
        )

        section_rows = connection.execute(
            f"""
            SELECT section_name,
                   count(*) AS rows,
                   coalesce(sum({length_expr}), 0) AS payload_bytes,
                   avg({length_expr}) AS avg_payload_bytes,
                   max({length_expr}) AS max_payload_bytes,
                   approx_count_distinct(hash(payload_json)) AS approx_distinct
            FROM entity_rows
            GROUP BY section_name
            ORDER BY payload_bytes DESC, section_name
            """
        ).fetchall()
        sections = tuple(
            PayloadSectionProfile(
                section_name=str(row[0]),
                rows=int(row[1]),
                logical_payload_bytes=int(row[2]),
                average_payload_bytes=float(row[3]),
                max_payload_bytes=int(row[4]),
                approximate_distinct_payloads=int(row[5]),
            )
            for row in section_rows
        )

        largest_rows = connection.execute(
            f"""
            SELECT section_name,
                   member_id,
                   source_entity_id,
                   {length_expr} AS payload_bytes,
                   payload_json
            FROM entity_rows
            ORDER BY payload_bytes DESC
            LIMIT ?
            """,
            [largest_limit],
        ).fetchall()
        largest_objects: list[PayloadObjectProfile] = []
        for section_name, member_id, source_entity_id, payload_bytes, payload_json in largest_rows:
            parsed = json.loads(str(payload_json))
            keys = tuple(str(key) for key in parsed.keys()) if isinstance(parsed, dict) else ()
            largest_objects.append(
                PayloadObjectProfile(
                    section_name=str(section_name),
                    member_id=int(member_id),
                    source_entity_id=(
                        None if source_entity_id is None else int(source_entity_id)
                    ),
                    payload_bytes=int(payload_bytes),
                    keys=keys,
                )
            )
    finally:
        connection.close()

    logical_entity_bytes = int(entity_payload_bytes)
    return PayloadProfileResult(
        database_path=str(database_path),
        decoded_json_bytes=decoded_json_bytes,
        entity_rows=int(entity_rows),
        entity_payload_logical_bytes=logical_entity_bytes,
        member_field_payload_logical_bytes=member_field_payload_bytes,
        entity_payload_vs_decoded_ratio=(
            logical_entity_bytes / decoded_json_bytes if decoded_json_bytes else 0.0
        ),
        sections=sections,
        largest_objects=tuple(largest_objects),
        wall_seconds=time.perf_counter() - started,
        peak_rss_bytes=_peak_rss_bytes(),
    )
