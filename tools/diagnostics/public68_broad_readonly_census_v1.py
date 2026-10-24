#!/usr/bin/env python3
"""Maximal read-only public68 corpus census with sanitized aggregate output.

NO reconstructed member JSON, game IDs, player IDs, source paths, orders,
raw entities or holdout/private data are exported. This is descriptive
CORPUS_OBSERVED source coverage, NOT Host phase/order DIFF_VERIFIED.

Only pinned CURRENT public68 is allowed; public100 and other generations
are not opened. All tables are read-only, including in tests.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import time

import duckdb

from planets_lab.corpus.corpus_db import KNOWN_ENTITY_SECTIONS
from planets_lab.corpus.corpus_db_compact import CORPUS_DB_COMPACT_SCHEMA
from planets_lab.corpus.corpus_db_runtime import (
    connect_current_compact_read_only,
)

SCHEMA = "planets-lab.public68-readonly-broad-census.v1"
PINNED_GENERATION = "corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb"
PINNED_SHA256 = "5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a"
EXPECTED_GAMES = 68
EXPECTED_MEMBERS = 169569
SAFE_SECTIONS = frozenset(KNOWN_ENTITY_SECTIONS)
DEEP_MEMBER_SECTIONS = frozenset({
    "minefields", "ships", "starbases", "planets", "vcrs", "ionstorms", "nebulas",
})
SOURCE_CATEGORIES = {
    "movement": ("ships", "planets", "ionstorms", "minefields"),
    "combat": ("ships", "planets", "starbases", "vcrs"),
    "economy": ("planets", "starbases", "ships"),
    "shipyard_pq_ppq": ("ships", "starbases", "planets"),
    "mine_placement_decay": ("minefields", "ships", "nebulas"),
    "ship_sweeping": ("minefields", "ships", "ionstorms"),
    "starbase_sweeping": ("minefields", "starbases", "planets"),
    "web_drain": ("minefields", "ships"),
}
ABSTAIN = "ABSTAIN_NO_AUTHENTICATED_HOST_PHASE_OR_ACCEPTED_ORDERS"
BATCH_LIMIT = 3  # low, memory-bounded DuckDB reading thread count


class ReadOnlyCensusAbstain(ValueError):
    """Safety precondition not met; no other database/generation is opened."""


def pinned_public68(root: Path) -> Path:
    root = root.expanduser().resolve()
    marker = root / "CURRENT"
    if not marker.is_file():
        raise ReadOnlyCensusAbstain("CURRENT_MISSING")
    # Never publish the marker text; malicious paths/other generations fail.
    if marker.read_text(encoding="utf-8").strip() != (
        "generations/" + PINNED_GENERATION
    ):
        raise ReadOnlyCensusAbstain("CURRENT_NOT_PINNED_PUBLIC68")
    gen = (root / "generations" / PINNED_GENERATION).resolve()
    if gen.parent != (root / "generations").resolve() or not gen.is_file():
        raise ReadOnlyCensusAbstain("PINNED_GENERATION_MISSING_OR_UNSAFE")
    return gen


def file_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        while block := stream.read(16 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()


def table_sections(connection: duckdb.DuckDBPyConnection) -> tuple[str, ...]:
    rows = connection.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' AND table_type = 'BASE TABLE'"
    ).fetchall()
    names = {str(r[0]) for r in rows}
    required = {"corpus_metadata", "source_archives", "source_members",
                "zip_members", "member_fields", "typed_entity_schema"}
    if not required.issubset(names):
        raise ReadOnlyCensusAbstain("COMPACT_TABLE_SET_INCOMPLETE")
    # Critically: section names used in SQL are from an allowlist, not source
    # content; never print dynamic names or raw schema strings.
    return tuple(sorted(
        s for s in SAFE_SECTIONS if f"typed_{s}" in names
    ))


def metadata_census(connection: duckdb.DuckDBPyConnection) -> dict[str, int]:
    row = connection.execute(
        "SELECT COUNT(*), COUNT(DISTINCT game_id), "
        "COUNT(DISTINCT archive_id), "
        "COALESCE(SUM(archive_bytes),0) FROM source_archives"
    ).fetchone()
    ar, games, unique_ar, encoded_bytes = (int(v) for v in row)
    members = connection.execute(
        "SELECT COUNT(*), COUNT(DISTINCT member_id), "
        "COUNT(DISTINCT game_id), "
        "COALESCE(SUM(decoded_json_bytes),0), "
        "SUM(CASE WHEN archive_turn=embedded_turn THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN archive_turn!=embedded_turn THEN 1 ELSE 0 END) "
        "FROM source_members"
    ).fetchone()
    member_count, unique_ids, member_games, json_bytes, offsets_equal, offsets_different = (
        int(v or 0) for v in members
    )
    zip_members = int(connection.execute("SELECT COUNT(*) FROM zip_members").fetchone()[0])
    member_fields = int(connection.execute("SELECT COUNT(*) FROM member_fields").fetchone()[0])
    if ar != EXPECTED_GAMES or games != EXPECTED_GAMES or member_games != EXPECTED_GAMES:
        raise ReadOnlyCensusAbstain("PUBLIC68_EXPECTED_GAME_COUNT_MISMATCH")
    if member_count != EXPECTED_MEMBERS or unique_ids != member_count:
        raise ReadOnlyCensusAbstain("PUBLIC68_MEMBER_IDENTITY_COUNT_MISMATCH")
    if unique_ar != ar:
        raise ReadOnlyCensusAbstain("DUPLICATE_ARCHIVE_IDENTIFIER")
    return {
        "source_archives": ar,
        "distinct_games": games,
        "source_members": member_count,
        "zip_members": zip_members,
        "member_fields": member_fields,
        "source_archive_bytes": encoded_bytes,
        "decoded_semantic_json_bytes": json_bytes,
        "archive_turn_equals_embedded": offsets_equal,
        "archive_turn_differs_from_embedded": offsets_different,
    }


def temporal_census(connection: duckdb.DuckDBPyConnection) -> dict[str, int]:
    # Full public68 member scan, but only aggregate totals ever cross Python.
    row = connection.execute(
        """
        WITH ordered AS (
            SELECT game_id, perspective_player_id, embedded_turn,
                   LAG(embedded_turn) OVER (
                       PARTITION BY game_id, perspective_player_id
                       ORDER BY embedded_turn, member_id
                   ) AS previous_turn
            FROM source_members
        )
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE previous_turn IS NULL),
               COUNT(*) FILTER (WHERE embedded_turn-previous_turn=1),
               COUNT(*) FILTER (WHERE embedded_turn=previous_turn),
               COUNT(*) FILTER (WHERE embedded_turn-previous_turn>1),
               COUNT(*) FILTER (WHERE embedded_turn-previous_turn<0)
        FROM ordered
        """
    ).fetchone()
    names = (
        "snapshots_scanned", "perspective_timelines",
        "consecutive_archival_observation_pairs",
        "duplicate_embedded_turn_observations",
        "nonconsecutive_archival_gaps", "out_of_order_turn_pairs",
    )
    return dict(zip(names, (int(v or 0) for v in row)))


def section_census(
    connection: duckdb.DuckDBPyConnection,
    sections: tuple[str, ...],
    *,
    progress=None,
) -> dict[str, dict[str, int]]:
    output: dict[str, dict[str, int]] = {}
    for section in sections:
        # Never query public100; access ONLY the pinned CURRENT public68
        # DuckDB connection. Identifiers strictly allowlisted above.
        table = f"typed_{section}"
        total = int(connection.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()[0])
        value: dict[str, int] = {"typed_entity_rows": total}
        if section in DEEP_MEMBER_SECTIONS:
            members = int(connection.execute(
                f'SELECT COUNT(DISTINCT member_id) FROM "{table}"'
            ).fetchone()[0])
            value["members_with_nonempty_section"] = members
        output[section] = value
        if progress:
            progress(section, value)
    return output


def observed_family_matrix(
    census: dict[str, dict[str, int]],
) -> dict[str, dict[str, object]]:
    results: dict[str, dict[str, object]] = {}
    for family, sections in SOURCE_CATEGORIES.items():
        missing = tuple(s for s in sections if s not in census)
        results[family] = {
            "required_observational_sections": list(sections),
            "available_sections": len(sections) - len(missing),
            "missing_sections": list(missing),
            "observational_source_sections_present": not missing,
            "independently_authenticated_host_orders": False,
            "independently_authenticated_phase_boundary": False,
            "host_diff_verified_by_this_run": False,
            "conditional_new_mechanics_host_audit": ABSTAIN,
        }
    return results


def audit(root: Path, *, verify_sha256: bool, progress=None) -> dict[str, object]:
    generation = pinned_public68(root)
    size = generation.stat().st_size
    before_stat = (size, generation.stat().st_mtime_ns)
    summary: dict[str, object] = {
        "schema": SCHEMA,
        "status": "RUNNING",
        "corpus_scope": "CURRENT_PINNED_PUBLIC68_ONLY",
        "no_public100_access": True,
        "no_m2_sealed_holdout_entity_sampling": True,
        "no_reconstruction_of_raw_members": True,
        "no_server_order_or_host_phase_accepted_evidence": True,
        "no_db_write_or_current_activation": True,
        "source_generation": PINNED_GENERATION,  # public basename, no local path
        "source_generation_bytes": size,
        "source_generation_sha256_expected": PINNED_SHA256,
        "source_generation_sha256_checked": False,
        "evidence_level": "CORPUS_OBSERVED_DESCRIPTIVE_SOURCE_COVERAGE_ONLY",
    }
    if verify_sha256:
        digest = file_sha256(generation)
        if digest != PINNED_SHA256:
            raise ReadOnlyCensusAbstain("PINNED_PUBLIC68_SHA256_MISMATCH")
        summary["source_generation_sha256_checked"] = True
    if progress:
        progress("generation_integrity", {"sha256_checked": bool(verify_sha256)})
    conn, opened = connect_current_compact_read_only(root)
    try:
        if opened.resolve() != generation:
            raise ReadOnlyCensusAbstain("ACTIVE_GENERATION_RACE_DETECTED")
        conn.execute(f"SET threads={BATCH_LIMIT}")
        conn.execute("SET memory_limit='4GB'")
        names = table_sections(conn)
        if progress:
            progress("schema", {"typed_section_count": len(names)})
        source = metadata_census(conn)
        if progress:
            progress("metadata", {"members": source["source_members"],
                                   "games": source["distinct_games"]})
        timing = temporal_census(conn)
        if progress:
            progress("temporal", {"pairs": timing["consecutive_archival_observation_pairs"]})
        sections = section_census(conn, names, progress=lambda s, v: (
            progress("typed_section", {"section": s, **v})
            if progress else None
        ))
        summary.update({
            "metadata_census": source,
            "temporal_census": timing,
            "typed_section_census": sections,
            "family_readiness": observed_family_matrix(sections),
            "source_sections_checked": len(sections),
            "status": "PASS_DESCRIPTIVE_CENSUS_NO_HOST_PHASE_PROMOTION",
        })
    finally:
        conn.close()
    after = pinned_public68(root)
    if after != generation or (after.stat().st_size, after.stat().st_mtime_ns) != before_stat:
        raise ReadOnlyCensusAbstain("CURRENT_OR_GENERATION_CHANGED_DURING_AUDIT")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--db-root", type=Path, default=Path(
        os.environ.get("PLANETS_CORPUS_DB_ROOT", "/corpus-db")
    ))
    parser.add_argument("--skip-hash", action="store_true",
                        help="faster audit; no full-file SHA validation")
    args = parser.parse_args()
    # Fixed path below artifacts only: wrapper can safely include this.
    target = args.report
    if str(target) != "artifacts/corpus/public68-broad-readonly-v1/report.json":
        print("ABSTAIN_UNSUPPORTED_REPORT_DESTINATION", flush=True)
        return 64
    target.parent.mkdir(parents=True, exist_ok=True)

    def progress(stage, numbers):
        # Only aggregate safe literals here. No raw source values, IDs, paths.
        encoded = json.dumps(numbers, sort_keys=True)
        print(f"stage={stage} summary={encoded}", flush=True)

    started = time.monotonic()
    try:
        payload = audit(args.db_root, verify_sha256=not args.skip_hash, progress=progress)
        exit_code = 0
    except ReadOnlyCensusAbstain as exc:
        payload = {
            "schema": SCHEMA, "status": "ABSTAIN",
            "reason_code": str(exc), "no_host_verification": True,
            "no_raw_entities_published": True,
        }
        exit_code = 2
    except (duckdb.Error, OSError, ValueError, RuntimeError) as exc:
        # DO NOT include exception str: it may expose a path or source value.
        payload = {
            "schema": SCHEMA, "status": "ABSTAIN_OPERATIONAL_ERROR",
            "exception_category": type(exc).__name__,
            "no_host_verification": True,
            "no_raw_entities_published": True,
        }
        exit_code = 2
    payload["elapsed_seconds"] = round(time.monotonic() - started, 2)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print("audit_status=" + str(payload["status"]), flush=True)
    print("output=artifacts/corpus/public68-broad-readonly-v1/report.json", flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
