from __future__ import annotations

import hashlib
import json
import math
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import duckdb

from .archive import TURN_MEMBER_RE, TurnMember
from .corpus_db import (
    CorpusDbError,
    ParityMismatch,
    ParityResult,
    _json_type,
    _peak_rss_bytes,
    _required_member_metadata,
    _sha256_path,
)
from .corpus_db_compact import (
    CORPUS_DB_COMPACT_SCHEMA,
    _collect_missing_paths,
    _compact_merge_spec,
    _convert_compact_value,
    _create_schema,
    _create_views,
    _flush,
    _load_specs,
    _normalize_spec,
    _observe_archive_entity_schema,
    _quote_ident,
    _restore_compact_value,
    _typed_table,
    reconstruct_compact_member,
)
from .corpus_db_typed import _canonical_json
from .normalizer import _decode_member_json


@dataclass(frozen=True, slots=True)
class CompactCorpusArchiveInput:
    game_id: int
    archive_path: str


@dataclass(frozen=True, slots=True)
class CompactCorpusImportResult:
    schema: str
    database_path: str
    archive_count: int
    game_ids: tuple[int, ...]
    archive_bytes: int
    zip_members: int
    turn_members: int
    decoded_json_bytes: int
    entity_rows: int
    corpus_fingerprint: str
    import_wall_seconds: float
    peak_rss_bytes: int
    resumed_archives: int


ProgressFn = Callable[[Mapping[str, Any]], None]


def _fingerprint(rows: Sequence[tuple[int, str]]) -> str:
    digest = hashlib.sha256()
    for game_id, sha256 in rows:
        digest.update(f"{game_id}:{sha256}\n".encode("ascii"))
    return digest.hexdigest()


def _checkpoint_path(checkpoint_dir: Path, game_id: int) -> Path:
    return checkpoint_dir / f"schema-game-{game_id}.json"


def _load_or_observe_archive(
    item: CompactCorpusArchiveInput,
    checkpoint_dir: Path,
    *,
    progress: ProgressFn | None = None,
) -> dict[str, Any]:
    archive_path = Path(item.archive_path).expanduser().resolve()
    archive_bytes = archive_path.stat().st_size
    archive_sha = _sha256_path(archive_path)
    checkpoint = _checkpoint_path(checkpoint_dir, item.game_id)

    if checkpoint.is_file():
        try:
            payload = json.loads(checkpoint.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = None
        if (
            isinstance(payload, dict)
            and payload.get("game_id") == item.game_id
            and payload.get("archive_sha256") == archive_sha
            and payload.get("archive_bytes") == archive_bytes
            and isinstance(payload.get("specs"), dict)
            and isinstance(payload.get("entity_candidates"), list)
            and isinstance(payload.get("non_entity_seen"), list)
        ):
            if progress is not None:
                progress(
                    {
                        "phase": "schema",
                        "status": "reused",
                        "game_id": item.game_id,
                    }
                )
            return payload

    if progress is not None:
        progress(
            {
                "phase": "schema",
                "status": "scan-start",
                "game_id": item.game_id,
            }
        )
    specs, candidates, non_entity = _observe_archive_entity_schema(
        archive_path,
        expected_game_id=item.game_id,
    )
    payload = {
        "game_id": item.game_id,
        "archive_path": str(archive_path),
        "archive_sha256": archive_sha,
        "archive_bytes": archive_bytes,
        "specs": specs,
        "entity_candidates": sorted(candidates),
        "non_entity_seen": sorted(non_entity),
    }
    tmp = checkpoint.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(checkpoint)
    if progress is not None:
        progress(
            {
                "phase": "schema",
                "status": "scan-complete",
                "game_id": item.game_id,
            }
        )
    return payload


def learn_compact_corpus_schema(
    archives: Sequence[CompactCorpusArchiveInput],
    checkpoint_dir: Path,
    *,
    progress: ProgressFn | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    observations: list[dict[str, Any]] = []
    merged_specs: dict[str, Any] = {}
    candidates: set[str] = set()
    non_entity: set[str] = set()

    for item in archives:
        observation = _load_or_observe_archive(
            item,
            checkpoint_dir,
            progress=progress,
        )
        observations.append(observation)
        candidates.update(str(value) for value in observation["entity_candidates"])
        non_entity.update(str(value) for value in observation["non_entity_seen"])
        for section, spec in observation["specs"].items():
            merged_specs[section] = (
                spec
                if section not in merged_specs
                else _compact_merge_spec(merged_specs[section], spec)
            )

    typed_fields = candidates - non_entity
    specs = {
        section: _normalize_spec(spec)
        for section, spec in merged_specs.items()
        if section in typed_fields
        and isinstance(spec, dict)
        and spec.get("kind") == "struct"
    }
    fingerprint = _fingerprint(
        [
            (int(observation["game_id"]), str(observation["archive_sha256"]))
            for observation in observations
        ]
    )
    return specs, observations, fingerprint


def _validate_archives(
    archives: Sequence[CompactCorpusArchiveInput],
) -> list[CompactCorpusArchiveInput]:
    if not archives:
        raise CorpusDbError("compact corpus build requires at least one archive")
    normalized: list[CompactCorpusArchiveInput] = []
    seen: set[int] = set()
    for item in archives:
        path = Path(item.archive_path).expanduser().resolve()
        if item.game_id <= 0:
            raise CorpusDbError(f"invalid game id: {item.game_id}")
        if item.game_id in seen:
            raise CorpusDbError(f"duplicate game id: {item.game_id}")
        if not path.is_file():
            raise CorpusDbError(f"archive not found: {path}")
        seen.add(item.game_id)
        normalized.append(
            CompactCorpusArchiveInput(
                game_id=item.game_id,
                archive_path=str(path),
            )
        )
    return normalized


def _verify_or_create_database(
    database_path: Path,
    specs: Mapping[str, Any],
    *,
    fingerprint: str,
    archive_count: int,
) -> duckdb.DuckDBPyConnection:
    if not database_path.exists():
        connection = duckdb.connect(str(database_path))
        connection.execute("SET preserve_insertion_order = false")
        _create_schema(connection, specs)
        connection.execute(
            """
            CREATE TABLE compact_build_state (
                corpus_fingerprint VARCHAR NOT NULL,
                expected_archive_count BIGINT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO compact_build_state VALUES (?, ?)",
            [fingerprint, archive_count],
        )
        connection.execute("CHECKPOINT")
        return connection

    connection = duckdb.connect(str(database_path))
    metadata = connection.execute(
        "SELECT schema_version FROM corpus_metadata"
    ).fetchone()
    if metadata is None or metadata[0] != CORPUS_DB_COMPACT_SCHEMA:
        connection.close()
        raise CorpusDbError(
            f"resume DB has unexpected schema: {None if metadata is None else metadata[0]!r}"
        )
    state = connection.execute(
        "SELECT corpus_fingerprint, expected_archive_count FROM compact_build_state"
    ).fetchone()
    if state is None:
        connection.close()
        raise CorpusDbError("resume DB has no compact_build_state")
    if str(state[0]) != fingerprint or int(state[1]) != archive_count:
        connection.close()
        raise CorpusDbError("resume DB corpus fingerprint/count mismatch")

    stored_specs = _load_specs(connection)
    if stored_specs != dict(specs):
        connection.close()
        raise CorpusDbError("resume DB typed schema differs from discovered corpus schema")
    connection.execute("SET preserve_insertion_order = false")
    return connection


def _cleanup_partial_archives(
    connection: duckdb.DuckDBPyConnection,
    specs: Mapping[str, Any],
    *,
    progress: ProgressFn | None = None,
) -> None:
    completed = {
        int(row[0])
        for row in connection.execute(
            "SELECT archive_id FROM source_archives"
        ).fetchall()
    }
    touched = {
        int(row[0])
        for row in connection.execute(
            """
            SELECT archive_id FROM source_members
            UNION
            SELECT archive_id FROM zip_members
            """
        ).fetchall()
    }
    partial = sorted(touched - completed)
    for archive_id in partial:
        game_row = connection.execute(
            "SELECT min(game_id) FROM source_members WHERE archive_id = ?",
            [archive_id],
        ).fetchone()
        game_id = (
            int(game_row[0])
            if game_row is not None and game_row[0] is not None
            else None
        )
        if progress is not None:
            progress(
                {
                    "phase": "import",
                    "status": "cleanup-partial",
                    "archive_id": archive_id,
                    "game_id": game_id,
                }
            )
        connection.execute("BEGIN TRANSACTION")
        for section in specs:
            connection.execute(
                f"""
                DELETE FROM {_quote_ident(_typed_table(section))}
                WHERE member_id IN (
                    SELECT member_id
                    FROM source_members
                    WHERE archive_id = ?
                )
                """,
                [archive_id],
            )
        connection.execute(
            """
            DELETE FROM member_fields
            WHERE member_id IN (
                SELECT member_id FROM source_members WHERE archive_id = ?
            )
            """,
            [archive_id],
        )
        connection.execute(
            "DELETE FROM source_members WHERE archive_id = ?",
            [archive_id],
        )
        connection.execute(
            "DELETE FROM zip_members WHERE archive_id = ?",
            [archive_id],
        )
        connection.execute("COMMIT")
    if partial:
        connection.execute("CHECKPOINT")


def _import_one_archive(
    connection: duckdb.DuckDBPyConnection,
    item: CompactCorpusArchiveInput,
    *,
    archive_id: int,
    specs: Mapping[str, Any],
    typed_schemas: Mapping[str, Any],
    member_id_start: int,
    commit_every_members: int,
    arrow_batch_rows: int,
) -> int:
    archive_path = Path(item.archive_path)
    archive_sha = _sha256_path(archive_path)
    archive_bytes = archive_path.stat().st_size
    member_id = member_id_start
    turn_count = 0
    seen_turn_names: set[str] = set()
    field_rows: list[tuple[Any, ...]] = []
    typed_rows: dict[str, list[tuple[Any, ...]]] = {
        section: [] for section in specs
    }

    connection.execute("BEGIN TRANSACTION")
    with zipfile.ZipFile(archive_path, mode="r") as archive:
        infos = archive.infolist()
        for member_ordinal, info in enumerate(infos):
            if info.is_dir():
                connection.execute(
                    "INSERT INTO zip_members VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        archive_id,
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
                    archive_id,
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
                    f"game {item.game_id}: duplicate turn member {info.filename}"
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
            if game_id != item.game_id:
                raise CorpusDbError(
                    f"{member.name}: manifest game {item.game_id}, payload game {game_id}"
                )

            member_id += 1
            turn_count += 1
            connection.execute(
                """
                INSERT INTO source_members VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    member_id,
                    archive_id,
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
                    if not (
                        isinstance(value, list)
                        and all(isinstance(entry, Mapping) for entry in value)
                    ):
                        raise CorpusDbError(
                            f"game {game_id}/{member.name}.{field_name}: "
                            "typed entity field changed shape"
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
                    for ordinal, entity in enumerate(value):
                        assert isinstance(entity, Mapping)
                        missing = _collect_missing_paths(entity, specs[field_name])
                        typed_rows[field_name].append(
                            (
                                member_id,
                                ordinal,
                                _convert_compact_value(
                                    entity,
                                    specs[field_name],
                                    (
                                        f"game-{game_id}/{member.name}."
                                        f"{field_name}[{ordinal}]"
                                    ),
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

    _flush(connection, field_rows, typed_rows, typed_schemas)
    connection.execute(
        "INSERT INTO source_archives VALUES (?, ?, ?, ?, ?)",
        [
            archive_id,
            item.game_id,
            str(archive_path),
            archive_sha,
            archive_bytes,
        ],
    )
    connection.execute("COMMIT")
    connection.execute("CHECKPOINT")
    return member_id


def import_archives_to_compact_database(
    archives: Sequence[CompactCorpusArchiveInput],
    database_path: Path,
    checkpoint_dir: Path,
    *,
    commit_every_members: int = 128,
    arrow_batch_rows: int = 10_000,
    progress: ProgressFn | None = None,
    max_new_archives: int | None = None,
) -> CompactCorpusImportResult:
    if commit_every_members <= 0 or arrow_batch_rows <= 0:
        raise CorpusDbError("batch/commit parameters must be positive")
    normalized = _validate_archives(archives)
    database_path = database_path.expanduser().resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = checkpoint_dir.expanduser().resolve()

    started = time.perf_counter()
    specs, observations, fingerprint = learn_compact_corpus_schema(
        normalized,
        checkpoint_dir,
        progress=progress,
    )

    connection = _verify_or_create_database(
        database_path,
        specs,
        fingerprint=fingerprint,
        archive_count=len(normalized),
    )
    resumed = 0
    imported_this_run = 0
    try:
        _cleanup_partial_archives(connection, specs, progress=progress)
        completed_rows = connection.execute(
            "SELECT archive_id, game_id, archive_sha256, archive_bytes "
            "FROM source_archives"
        ).fetchall()
        completed = {int(row[0]): row for row in completed_rows}
        resumed = len(completed)

        # _create_schema already created the real DuckDB tables from these
        # Arrow schemas. Reconstruct the Arrow schemas in-memory for batching.
        import pyarrow as pa
        from .corpus_db_compact import _pa_type

        typed_schemas = {
            section: pa.schema(
                [
                    pa.field("member_id", pa.int64(), nullable=False),
                    pa.field("ordinal", pa.int64(), nullable=False),
                    pa.field("data", _pa_type(spec), nullable=False),
                    pa.field("missing_json", pa.string(), nullable=True),
                ]
            )
            for section, spec in specs.items()
        }

        member_id = int(
            connection.execute(
                "SELECT coalesce(max(member_id), 0) FROM source_members"
            ).fetchone()[0]
        )

        for archive_id, (item, observation) in enumerate(
            zip(normalized, observations),
            start=1,
        ):
            if archive_id in completed:
                row = completed[archive_id]
                if (
                    int(row[1]) != item.game_id
                    or str(row[2]) != str(observation["archive_sha256"])
                    or int(row[3]) != int(observation["archive_bytes"])
                ):
                    raise CorpusDbError(
                        f"completed archive {archive_id} provenance mismatch"
                    )
                if progress is not None:
                    progress(
                        {
                            "phase": "import",
                            "status": "reused",
                            "archive_id": archive_id,
                            "game_id": item.game_id,
                        }
                    )
                continue

            if max_new_archives is not None and imported_this_run >= max_new_archives:
                break
            if progress is not None:
                progress(
                    {
                        "phase": "import",
                        "status": "archive-start",
                        "archive_id": archive_id,
                        "game_id": item.game_id,
                    }
                )
            member_id = _import_one_archive(
                connection,
                item,
                archive_id=archive_id,
                specs=specs,
                typed_schemas=typed_schemas,
                member_id_start=member_id,
                commit_every_members=commit_every_members,
                arrow_batch_rows=arrow_batch_rows,
            )
            imported_this_run += 1
            if progress is not None:
                progress(
                    {
                        "phase": "import",
                        "status": "archive-complete",
                        "archive_id": archive_id,
                        "game_id": item.game_id,
                    }
                )

        completed_count = int(
            connection.execute("SELECT count(*) FROM source_archives").fetchone()[0]
        )
        if completed_count == len(normalized):
            for section in specs:
                connection.execute(
                    f"DROP VIEW IF EXISTS {_quote_ident(section)}"
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

    read = duckdb.connect(str(database_path), read_only=True)
    try:
        archive_count = int(
            read.execute("SELECT count(*) FROM source_archives").fetchone()[0]
        )
        archive_bytes = int(
            read.execute(
                "SELECT coalesce(sum(archive_bytes), 0) FROM source_archives"
            ).fetchone()[0]
        )
        zip_members = int(
            read.execute("SELECT count(*) FROM zip_members").fetchone()[0]
        )
        turn_members = int(
            read.execute("SELECT count(*) FROM source_members").fetchone()[0]
        )
        decoded_json_bytes = int(
            read.execute(
                "SELECT coalesce(sum(decoded_json_bytes), 0) FROM source_members"
            ).fetchone()[0]
        )
        entity_rows = 0
        for section in specs:
            entity_rows += int(
                read.execute(
                    f"SELECT count(*) FROM {_quote_ident(_typed_table(section))}"
                ).fetchone()[0]
            )
    finally:
        read.close()

    return CompactCorpusImportResult(
        schema=CORPUS_DB_COMPACT_SCHEMA,
        database_path=str(database_path),
        archive_count=archive_count,
        game_ids=tuple(item.game_id for item in normalized[:archive_count]),
        archive_bytes=archive_bytes,
        zip_members=zip_members,
        turn_members=turn_members,
        decoded_json_bytes=decoded_json_bytes,
        entity_rows=entity_rows,
        corpus_fingerprint=fingerprint,
        import_wall_seconds=time.perf_counter() - started,
        peak_rss_bytes=_peak_rss_bytes(),
        resumed_archives=resumed,
    )


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


def validate_compact_corpus_parity(
    archives: Sequence[CompactCorpusArchiveInput],
    database_path: Path,
    *,
    max_mismatches: int = 100,
    progress: ProgressFn | None = None,
) -> ParityResult:
    if max_mismatches <= 0:
        raise CorpusDbError("max_mismatches must be positive")
    normalized = _validate_archives(archives)
    database_path = database_path.expanduser().resolve()

    started = time.perf_counter()
    checked = 0
    mismatches: list[ParityMismatch] = []

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
        db_archives = {
            int(row[1]): (
                int(row[0]),
                str(row[2]),
                int(row[3]),
            )
            for row in connection.execute(
                "SELECT archive_id, game_id, archive_sha256, archive_bytes "
                "FROM source_archives"
            ).fetchall()
        }
        expected_games = {item.game_id for item in normalized}
        if set(db_archives) != expected_games:
            raise CorpusDbError(
                f"DB/source game set mismatch: db={sorted(db_archives)} "
                f"source={sorted(expected_games)}"
            )
        specs = _load_specs(connection)

        for item in normalized:
            if progress is not None:
                progress(
                    {
                        "phase": "parity",
                        "status": "archive-start",
                        "game_id": item.game_id,
                    }
                )
            archive_path = Path(item.archive_path)
            archive_id, db_sha, db_bytes = db_archives[item.game_id]
            if db_sha != _sha256_path(archive_path):
                raise CorpusDbError(f"game {item.game_id}: archive SHA256 mismatch")
            if db_bytes != archive_path.stat().st_size:
                raise CorpusDbError(f"game {item.game_id}: archive size mismatch")

            db_zip = {
                int(row[0]): row[1:]
                for row in connection.execute(
                    """
                    SELECT member_ordinal, member_name, crc32, compressed_size,
                           uncompressed_size, is_directory, is_turn_member,
                           member_payload_sha256
                    FROM zip_members
                    WHERE archive_id = ?
                    ORDER BY member_ordinal
                    """,
                    [archive_id],
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
                    WHERE archive_id = ?
                    """,
                    [archive_id],
                ).fetchall()
            }
            seen_names: set[str] = set()
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
                        if add(
                            f"game-{item.game_id}/{info.filename}",
                            "$",
                            "ZIP member absent in DB provenance",
                        ):
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
                        if problem and add(
                            f"game-{item.game_id}/{info.filename}",
                            "$",
                            problem,
                        ):
                            break

                    if not is_turn:
                        continue
                    checked += 1
                    seen_names.add(info.filename)
                    db_row = db_members.get(info.filename)
                    if db_row is None:
                        if add(
                            f"game-{item.game_id}/{info.filename}",
                            "$",
                            "source member absent in DB",
                        ):
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
                        if add(
                            f"game-{item.game_id}/{info.filename}",
                            "$",
                            problem,
                        ):
                            break
                        continue

                    try:
                        actual = reconstruct_compact_member(
                            connection,
                            int(member_id),
                            specs=specs,
                        )
                    except Exception as exc:
                        if add(
                            f"game-{item.game_id}/{info.filename}",
                            "$",
                            f"reconstruction failed: {exc}",
                        ):
                            break
                        continue
                    mismatch = _first_semantic_mismatch(expected, actual)
                    if mismatch is not None:
                        if add(
                            f"game-{item.game_id}/{info.filename}",
                            mismatch[0],
                            mismatch[1],
                        ):
                            break

            if len(mismatches) >= max_mismatches:
                break
            for name in sorted(set(db_members) - seen_names):
                if add(
                    f"game-{item.game_id}/{name}",
                    "$",
                    "DB source member absent from archive",
                ):
                    break
            if len(mismatches) >= max_mismatches:
                break
            for ordinal in sorted(set(db_zip) - seen_ordinals):
                if add(
                    f"game-{item.game_id}/{db_zip[ordinal][0]}",
                    "$",
                    "DB ZIP member absent from archive",
                ):
                    break
            if len(mismatches) >= max_mismatches:
                break
            if progress is not None:
                progress(
                    {
                        "phase": "parity",
                        "status": "archive-complete",
                        "game_id": item.game_id,
                    }
                )
    finally:
        connection.close()

    return ParityResult(
        checked=checked,
        failed=len(mismatches),
        mismatches=tuple(mismatches),
        wall_seconds=time.perf_counter() - started,
        peak_rss_bytes=_peak_rss_bytes(),
    )


def compact_corpus_database_stats(database_path: Path) -> dict[str, Any]:
    database_path = database_path.expanduser().resolve()
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

        return {
            "schema": CORPUS_DB_COMPACT_SCHEMA,
            "database_path": str(database_path),
            "database_bytes": database_path.stat().st_size,
            "source_archive_count": int(
                connection.execute("SELECT count(*) FROM source_archives").fetchone()[0]
            ),
            "source_archive_bytes_total": int(
                connection.execute(
                    "SELECT coalesce(sum(archive_bytes),0) FROM source_archives"
                ).fetchone()[0]
            ),
            "game_ids": [
                int(row[0])
                for row in connection.execute(
                    "SELECT game_id FROM source_archives ORDER BY archive_id"
                ).fetchall()
            ],
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
