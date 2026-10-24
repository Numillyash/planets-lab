#!/usr/bin/env python3
"""Pre-reconstruction baseline cohort gate for public100 deep M2 runs.

The manifest is a SERVER-LOCAL export, absent from Git. A historical
manifest SHA is not an immutable trust anchor. Verify its exact GAME-ID
SET against the SHA-pinned public68 DuckDB metadata, and verify that
the approved baseline IDs are included in public100 metadata. No
heldout32 entity table is accessed, no raw IDs or source paths emitted.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only

BASELINE_GENERATION = "corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb"
BASELINE_DB_SHA256 = "5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a"
PUBLIC100_GENERATION = "corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
EXPECTED_BASELINE_GAMES = 68
EXPECTED_ALL_GAMES = 100
EXPECTED_BASELINE_MEMBERS = 169569
EXPECTED_ALL_MEMBERS = 224014
SCHEMA = "planets-lab.public100-baseline68-cohort-identity-guard.v3"


class CohortGateAbstain(ValueError):
    """Fail closed before any entity reconstruction."""


def digest_file(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            value.update(block)
    return value.hexdigest()


def manifest_ids(raw: bytes, *, expected_games: int = EXPECTED_BASELINE_GAMES) -> set[int]:
    if type(raw) is not bytes or not 1 <= len(raw) <= 1_000_000:
        raise CohortGateAbstain("ABSTAIN_INVALID_MANIFEST_SIZE")
    try:
        lines = raw.decode("utf-8-sig").splitlines()
        ids: set[int] = set()
        for line in lines:
            if not line.strip():
                continue
            item = json.loads(line)
            if type(item) is not dict or type(item.get("game_id")) is not int:
                raise CohortGateAbstain("ABSTAIN_INVALID_MANIFEST_GAME_ID")
            game_id = item["game_id"]
            if not 1 <= game_id <= 2_147_483_647 or game_id in ids:
                raise CohortGateAbstain("ABSTAIN_DUPLICATE_OR_INVALID_GAME_ID")
            ids.add(game_id)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CohortGateAbstain("ABSTAIN_MALFORMED_MANIFEST") from exc
    if len(ids) != expected_games:
        raise CohortGateAbstain("ABSTAIN_BASELINE_GAME_COUNT")
    return ids


def enforce_cohort_identity(
    manifest: set[int], baseline: set[int], universe: set[int],
    *, baseline_games: int = EXPECTED_BASELINE_GAMES,
    all_games: int = EXPECTED_ALL_GAMES,
) -> None:
    if not (
        len(manifest) == len(baseline) == baseline_games
        and len(universe) == all_games
        and manifest == baseline
        and baseline.issubset(universe)
    ):
        raise CohortGateAbstain("ABSTAIN_MANIFEST_NOT_APPROVED_PUBLIC68_COHORT")


def _source_ids(conn, *, game_count: int, member_count: int) -> set[int]:
    # Metadata table only. NEVER touch typed_<section> or JSON reconstruction.
    rows = conn.execute(
        "SELECT game_id FROM source_archives ORDER BY game_id"
    ).fetchall()
    values = [row[0] for row in rows]
    if (len(values) != game_count or any(type(v) is not int or v <= 0 for v in values)
            or len(set(values)) != game_count):
        raise CohortGateAbstain("ABSTAIN_ARCHIVE_GAME_METADATA")
    count = conn.execute("SELECT COUNT(*) FROM source_members").fetchone()[0]
    if type(count) is not int or count != member_count:
        raise CohortGateAbstain("ABSTAIN_MEMBER_COUNT")
    return set(values)


def validate(
    root: Path, manifest: Path, *, expected_baseline_sha: str = BASELINE_DB_SHA256,
    baseline_gen: str = BASELINE_GENERATION,
    all_gen: str = PUBLIC100_GENERATION,
    baseline_games: int = EXPECTED_BASELINE_GAMES,
    all_games: int = EXPECTED_ALL_GAMES,
    baseline_members: int = EXPECTED_BASELINE_MEMBERS,
    all_members: int = EXPECTED_ALL_MEMBERS,
) -> dict[str, object]:
    root = root.expanduser().resolve()
    marker = root / "CURRENT"
    if not marker.is_file() or marker.read_text(encoding="utf-8").strip() != (
        "generations/" + baseline_gen
    ):
        raise CohortGateAbstain("ABSTAIN_UNEXPECTED_CURRENT")
    baseline_path = (root / "generations" / baseline_gen).resolve()
    all_path = (root / "generations" / all_gen).resolve()
    approved_dir = (root / "generations").resolve()
    if (baseline_path.parent != approved_dir or all_path.parent != approved_dir
            or not baseline_path.is_file() or not all_path.is_file()):
        raise CohortGateAbstain("ABSTAIN_APPROVED_GENERATIONS_MISSING")
    before_stats = (
        baseline_path.stat().st_size, baseline_path.stat().st_mtime_ns,
        all_path.stat().st_size, all_path.stat().st_mtime_ns,
    )
    if digest_file(baseline_path) != expected_baseline_sha:
        raise CohortGateAbstain("ABSTAIN_BASELINE_DB_SHA256_MISMATCH")
    raw = manifest.read_bytes()
    supplied = manifest_ids(raw, expected_games=baseline_games)
    conn68, _ = connect_compact_generation_read_only("generations/" + baseline_gen, root)
    try:
        approved = _source_ids(
            conn68, game_count=baseline_games, member_count=baseline_members
        )
    finally:
        conn68.close()
    conn100, _ = connect_compact_generation_read_only("generations/" + all_gen, root)
    try:
        universe = _source_ids(
            conn100, game_count=all_games, member_count=all_members
        )
    finally:
        conn100.close()
    enforce_cohort_identity(
        supplied, approved, universe, baseline_games=baseline_games,
        all_games=all_games,
    )
    if (marker.read_text(encoding="utf-8").strip() != "generations/" + baseline_gen
            or (baseline_path.stat().st_size, baseline_path.stat().st_mtime_ns,
                all_path.stat().st_size, all_path.stat().st_mtime_ns) != before_stats
            or manifest.read_bytes() != raw):
        raise CohortGateAbstain("ABSTAIN_SOURCE_CHANGED_DURING_COHORT_GUARD")
    return {
        "schema": SCHEMA,
        "status": "PASS_EXACT_MANIFEST_GAME_IDS_MATCH_SHA_PINNED_PUBLIC68",
        "baseline_db_sha256": expected_baseline_sha,
        "manifest_sha256": sha256(raw).hexdigest(),
        "baseline_game_count": baseline_games,
        "all_metadata_game_count": all_games,
        "all_members_metadata_only": all_members,
        "heldout_entity_sampling": False,
        "current_modified": False,
        "host_diff_verified": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db-root", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    try:
        report = validate(args.db_root, args.manifest)
    except (CohortGateAbstain, OSError, ValueError, RuntimeError) as exc:
        # Exception messages can hold private disk paths, so publish a
        # fixed-status reason only (not raw exception/manifest contents).
        code = str(exc) if type(exc) is CohortGateAbstain else "ABSTAIN_SOURCE_READ_FAILURE"
        print("cohort_gate=" + code, flush=True)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("cohort_gate=PASS_EXACT_PUBLIC68_GAME_SET")
    print("baseline_games=68")
    print("public100_metadata_games=100")
    print("heldout32_entities_accessed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
