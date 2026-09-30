from __future__ import annotations

import hashlib
import json
import math
import time
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import duckdb

from .archive import TURN_MEMBER_RE, TurnMember
from .corpus_db import (
    CorpusDbError,
    ParityMismatch,
    ParityResult,
    _first_int,
    _json_type,
    _peak_rss_bytes,
    _required_member_metadata,
    _sha256_path,
    _typed_number,
)
from .corpus_db_typed import (
    CORPUS_DB_TYPED_SCHEMA,
    _convert_value,
    _create_base_schema,
    _create_indexes_and_views,
    _flush,
    _learn_entity_specs,
    _merge_spec,
    _normalize_spec,
    reconstruct_typed_member,
)
from .normalizer import CorpusNormalizationError, _decode_member_json


@dataclass(frozen=True, slots=True)
class CorpusArchiveInput:
    game_id: int
    archive_path: str


@dataclass(frozen=True, slots=True)
class MultiImportResult:
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


def _learn_union_specs(
    archives: Sequence[CorpusArchiveInput],
    *,
    sample_members_per_archive: int = 128,
    sample_entities_per_section: int = 10_000,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for item in archives:
        specs = _learn_entity_specs(
            Path(item.archive_path),
            expected_game_id=item.game_id,
            sample_members=sample_members_per_archive,
            sample_entities_per_section=sample_entities_per_section,
        )
        for section, spec in specs.items():
            merged[section] = (
                spec if section not in merged else _merge_spec(merged[section], spec)
            )
    return {
        section: _normalize_spec(spec)
        for section, spec in merged.items()
    }


def _fingerprint_archives(rows: Sequence[tuple[int, str]]) -> str:
    digest = hashlib.sha256()
    for game_id, sha256 in rows:
        digest.update(f"{game_id}:{sha256}\n".encode("ascii"))
    return digest.hexdigest()


def import_archives_to_typed_database(
    archives: Sequence[CorpusArchiveInput],
    database_path: Path,
    *,
    commit_every_members: int = 128,
    arrow_batch_rows: int = 20_000,
    sample_members_per_archive: int = 128,
    sample_entities_per_section: int = 10_000,
) -> MultiImportResult:
    if not archives:
        raise CorpusDbError("typed corpus build requires at least one archive")
    if commit_every_members <= 0 or arrow_batch_rows <= 0:
        raise CorpusDbError("batch/commit parameters must be positive")
    if sample_members_per_archive <= 0 or sample_entities_per_section <= 0:
        raise CorpusDbError("schema sample limits must be positive")

    database_path = database_path.expanduser().resolve()
    if database_path.exists():
        raise CorpusDbError(f"database already exists: {database_path}")
    database_path.parent.mkdir(parents=True, exist_ok=True)

    normalized: list[CorpusArchiveInput] = []
    seen_games: set[int] = set()
    for item in archives:
        path = Path(item.archive_path).expanduser().resolve()
        if item.game_id <= 0:
            raise CorpusDbError(f"invalid game id: {item.game_id}")
        if item.game_id in seen_games:
            raise CorpusDbError(f"duplicate game id in corpus build: {item.game_id}")
        if not path.is_file():
            raise CorpusDbError(f"archive not found: {path}")
        seen_games.add(item.game_id)
        normalized.append(CorpusArchiveInput(item.game_id, str(path)))

    started = time.perf_counter()
    typed_specs = _learn_union_specs(
        normalized,
        sample_members_per_archive=sample_members_per_archive,
        sample_entities_per_section=sample_entities_per_section,
    )

    connection = duckdb.connect(str(database_path))
    member_id = 0
    turn_count = 0
    zip_count = 0
    entity_count = 0
    decoded_json_bytes = 0
    archive_bytes_total = 0
    archive_fingerprints: list[tuple[int, str]] = []
    field_rows: list[tuple[Any, ...]] = []
    entity_rows: list[tuple[Any, ...]] = []
    typed_rows: dict[str, list[tuple[Any, ...]]] = {
        section: [] for section in typed_specs
    }

    try:
        connection.execute("SET preserve_insertion_order = false")
        typed_schemas = _create_base_schema(connection, typed_specs)
        connection.execute("BEGIN TRANSACTION")

        for archive_id, item in enumerate(normalized, start=1):
            archive_path = Path(item.archive_path)
            archive_sha256 = _sha256_path(archive_path)
            archive_bytes = archive_path.stat().st_size
            archive_bytes_total += archive_bytes
            archive_fingerprints.append((item.game_id, archive_sha256))
            seen_turn_names: set[str] = set()

            with zipfile.ZipFile(archive_path, mode="r") as archive:
                infos = archive.infolist()
                zip_count += len(infos)
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
                    raw_sha256 = hashlib.sha256(raw).hexdigest()
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
                            raw_sha256,
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
                    decoded_json_bytes += len(decoded)
                    connection.execute(
                        """
                        INSERT INTO source_members VALUES
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                            and all(isinstance(entity, Mapping) for entity in value)
                            and (field_name in typed_specs or bool(value))
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
                        for ordinal, entity in enumerate(value):
                            assert isinstance(entity, Mapping)
                            entity_rows.append(
                                (
                                    member_id,
                                    game_id,
                                    member.player,
                                    member.turn,
                                    embedded_turn,
                                    field_name,
                                    ordinal,
                                    _first_int(entity, "id"),
                                    _first_int(entity, "ownerid", "owner_id"),
                                    _first_int(entity, "playerid", "player_id"),
                                    _typed_number(entity.get("x")),
                                    _typed_number(entity.get("y")),
                                )
                            )
                            if field_name in typed_specs:
                                typed_rows[field_name].append(
                                    (
                                        member_id,
                                        ordinal,
                                        _convert_value(
                                            entity,
                                            typed_specs[field_name],
                                            f"game-{game_id}/{member.name}.{field_name}[{ordinal}]",
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

            connection.execute(
                "INSERT INTO source_archives VALUES (?, ?, ?, ?, ?)",
                [
                    archive_id,
                    item.game_id,
                    str(archive_path),
                    archive_sha256,
                    archive_bytes,
                ],
            )

        _flush(connection, field_rows, entity_rows, typed_rows, typed_schemas)
        connection.execute("COMMIT")

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

    return MultiImportResult(
        schema=CORPUS_DB_TYPED_SCHEMA,
        database_path=str(database_path),
        archive_count=len(normalized),
        game_ids=tuple(item.game_id for item in normalized),
        archive_bytes=archive_bytes_total,
        zip_members=zip_count,
        turn_members=turn_count,
        decoded_json_bytes=decoded_json_bytes,
        entity_rows=entity_count,
        corpus_fingerprint=_fingerprint_archives(archive_fingerprints),
        import_wall_seconds=time.perf_counter() - started,
        peak_rss_bytes=_peak_rss_bytes(),
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


def validate_typed_corpus_parity(
    archives: Sequence[CorpusArchiveInput],
    database_path: Path,
    *,
    max_mismatches: int = 100,
) -> ParityResult:
    if max_mismatches <= 0:
        raise CorpusDbError("max_mismatches must be positive")

    started = time.perf_counter()
    mismatches: list[ParityMismatch] = []
    checked = 0

    def add(member: str, path: str, reason: str) -> bool:
        mismatches.append(ParityMismatch(member, path, reason))
        return len(mismatches) >= max_mismatches

    database_path = database_path.expanduser().resolve()
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        metadata = connection.execute(
            "SELECT schema_version FROM corpus_metadata"
        ).fetchone()
        if metadata is None or metadata[0] != CORPUS_DB_TYPED_SCHEMA:
            raise CorpusDbError(
                f"unexpected typed schema: {None if metadata is None else metadata[0]!r}"
            )

        db_archives = {
            int(row[1]): (
                int(row[0]),
                str(row[2]),
                int(row[3]),
            )
            for row in connection.execute(
                """
                SELECT archive_id, game_id, archive_sha256, archive_bytes
                FROM source_archives
                """
            ).fetchall()
        }
        expected_games = {item.game_id for item in archives}
        if set(db_archives) != expected_games:
            raise CorpusDbError(
                f"DB/source game set mismatch: db={sorted(db_archives)} "
                f"source={sorted(expected_games)}"
            )

        for item in archives:
            archive_path = Path(item.archive_path).expanduser().resolve()
            archive_id, db_sha, db_bytes = db_archives[item.game_id]
            if db_sha != _sha256_path(archive_path):
                raise CorpusDbError(f"game {item.game_id}: archive SHA256 mismatch")
            if db_bytes != archive_path.stat().st_size:
                raise CorpusDbError(f"game {item.game_id}: archive byte-size mismatch")

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
            entity_counts = {
                (int(row[0]), str(row[1])): int(row[2])
                for row in connection.execute(
                    """
                    SELECT member_id, section_name, count(*)
                    FROM entity_rows
                    WHERE member_id IN (
                        SELECT member_id FROM source_members WHERE archive_id = ?
                    )
                    GROUP BY member_id, section_name
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
                    if expected_game_id != item.game_id or int(db_game_id) != item.game_id:
                        problem = "game_id mismatch"
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

                    for field_name, value in expected.items():
                        if (
                            isinstance(value, list)
                            and all(isinstance(entity, Mapping) for entity in value)
                        ):
                            actual_count = entity_counts.get(
                                (int(member_id), field_name),
                                0,
                            )
                            if actual_count != len(value):
                                if add(
                                    f"game-{item.game_id}/{info.filename}",
                                    f"$.{field_name}",
                                    f"entity row count mismatch: {actual_count} != {len(value)}",
                                ):
                                    break
                    if len(mismatches) >= max_mismatches:
                        break

                    actual = reconstruct_typed_member(connection, int(member_id))
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

            extras = sorted(set(db_members) - seen_names)
            for name in extras:
                if add(
                    f"game-{item.game_id}/{name}",
                    "$",
                    "DB source member absent from archive",
                ):
                    break
            if len(mismatches) >= max_mismatches:
                break

            extra_ordinals = sorted(set(db_zip) - seen_ordinals)
            for ordinal in extra_ordinals:
                if add(
                    f"game-{item.game_id}/{db_zip[ordinal][0]}",
                    "$",
                    "DB ZIP member absent from archive",
                ):
                    break
            if len(mismatches) >= max_mismatches:
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
