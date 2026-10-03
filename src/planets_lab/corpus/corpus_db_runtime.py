from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import duckdb

from .archive import TurnMember
from .corpus_db import CorpusDbError, connect_current_read_only, resolve_current_generation
from .corpus_db_compact import (
    CORPUS_DB_COMPACT_SCHEMA,
    _load_specs,
    reconstruct_compact_member,
)


@dataclass(frozen=True, slots=True)
class CompactMemberRef:
    member_id: int
    game_id: int
    source_member_name: str
    perspective_player_id: int
    archive_turn: int
    embedded_turn: int
    decoded_payload_sha256: str

    @property
    def turn_member(self) -> TurnMember:
        return TurnMember(
            player=self.perspective_player_id,
            turn=self.archive_turn,
            name=self.source_member_name,
        )


def corpus_db_root_from_env() -> Path:
    value = os.environ.get("PLANETS_CORPUS_DB_ROOT")
    if not value:
        raise CorpusDbError("PLANETS_CORPUS_DB_ROOT is not set")
    return Path(value)


def connect_current_compact_read_only(
    root: Path | None = None,
) -> tuple[duckdb.DuckDBPyConnection, Path]:
    resolved_root = root if root is not None else corpus_db_root_from_env()
    generation = resolve_current_generation(resolved_root)
    connection = connect_current_read_only(resolved_root)
    row = connection.execute(
        "SELECT schema_version FROM corpus_metadata LIMIT 1"
    ).fetchone()
    if row is None or str(row[0]) != CORPUS_DB_COMPACT_SCHEMA:
        connection.close()
        observed = None if row is None else str(row[0])
        raise CorpusDbError(
            f"active corpus DB schema {observed!r} != "
            f"{CORPUS_DB_COMPACT_SCHEMA!r}"
        )
    return connection, generation


def _refs_from_rows(rows: Iterable[tuple[object, ...]]) -> list[CompactMemberRef]:
    return [
        CompactMemberRef(
            member_id=int(row[0]),
            game_id=int(row[1]),
            source_member_name=str(row[2]),
            perspective_player_id=int(row[3]),
            archive_turn=int(row[4]),
            embedded_turn=int(row[5]),
            decoded_payload_sha256=str(row[6]),
        )
        for row in rows
    ]


def member_refs_for_turns(
    connection: duckdb.DuckDBPyConnection,
    *,
    game_id: int,
    turns: set[int],
    include_embedded_turn: bool = True,
) -> list[CompactMemberRef]:
    if not turns:
        return []
    ordered = sorted(int(value) for value in turns)
    placeholders = ",".join("?" for _ in ordered)
    if include_embedded_turn:
        predicate = (
            f"(archive_turn IN ({placeholders}) "
            f"OR embedded_turn IN ({placeholders}))"
        )
        params: list[object] = [game_id, *ordered, *ordered]
    else:
        predicate = f"archive_turn IN ({placeholders})"
        params = [game_id, *ordered]
    rows = connection.execute(
        f"""
        SELECT member_id,
               game_id,
               source_member_name,
               perspective_player_id,
               archive_turn,
               embedded_turn,
               decoded_payload_sha256
        FROM source_members
        WHERE game_id = ?
          AND {predicate}
        ORDER BY archive_turn, perspective_player_id, member_ordinal
        """,
        params,
    ).fetchall()
    return _refs_from_rows(rows)


def first_last_member_refs(
    connection: duckdb.DuckDBPyConnection,
    *,
    game_id: int,
) -> tuple[CompactMemberRef, CompactMemberRef]:
    columns = """
        member_id,
        game_id,
        source_member_name,
        perspective_player_id,
        archive_turn,
        embedded_turn,
        decoded_payload_sha256
    """
    first = connection.execute(
        f"""
        SELECT {columns}
        FROM source_members
        WHERE game_id = ?
        ORDER BY member_ordinal ASC
        LIMIT 1
        """,
        [game_id],
    ).fetchone()
    last = connection.execute(
        f"""
        SELECT {columns}
        FROM source_members
        WHERE game_id = ?
        ORDER BY member_ordinal DESC
        LIMIT 1
        """,
        [game_id],
    ).fetchone()
    if first is None or last is None:
        raise CorpusDbError(f"game {game_id}: no source members in active DB")
    return _refs_from_rows([first])[0], _refs_from_rows([last])[0]


def reconstruct_members(
    connection: duckdb.DuckDBPyConnection,
    refs: Iterable[CompactMemberRef],
):
    specs = _load_specs(connection)
    for ref in refs:
        yield ref, reconstruct_compact_member(
            connection,
            ref.member_id,
            specs=specs,
        )
