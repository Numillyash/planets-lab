#!/usr/bin/env python3
"""M2: audit existing 26.65 GiB public100 DuckDB, without rewriting it.

From planets-lab checkout ON THE EXISTING CORPUS SERVER:
  python tools/diagnostics/m2_public_corpus_economy_coverage_v1.py \
    --output artifacts/planetary/m2-public100-coverage-v1/report.json

First SHA256-verifies the immutable explicit public100 generation.
Censuses metadata across ALL 100 games (224014 source members). Samples
entities ONLY from the user-supplied pre-existing 68-game BASELINE
manifest, never the sealed 32-game prospective holdout. It freezes
bounded adjacent T-1/T pairs before reconstructing any entity record.
No public web traffic, no game API calls, no data ingestion, no writes
to corpus DuckDB, no change to CURRENT, no player-order inference.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from planets_lab.corpus.corpus_db_runtime import (  # noqa: E402
    connect_compact_generation_read_only,
)
from planets_lab.corpus.corpus_db_compact import (  # noqa: E402
    _load_specs, reconstruct_compact_member,
)
from planets_lab.corpus.m2_economy_coverage import (  # noqa: E402
    analyze_corpus_coverage,
)

GENERATION = "generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
SHA256 = "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"


def _sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as source:
        while chunk := source.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-root", type=Path, default=None,
                        help="Defaults to PLANETS_CORPUS_DB_ROOT")
    parser.add_argument("--generation", default=GENERATION,
                        help="Explicit immutable generations/*.duckdb, never CURRENT")
    parser.add_argument("--expected-sha256", default=SHA256,
                        help="Published generation digest, required to match")
    parser.add_argument(
        "--baseline-manifest", required=True, type=Path,
        help="Baseline public68 JSONL IDs, never the sealed 32-game heldout set",
    )
    parser.add_argument("--expected-baseline-games", type=int, default=68)
    parser.add_argument("--max-games", type=int, default=100,
                        help="Spread selected samples across up to this many games")
    parser.add_argument("--pairs-per-game", type=int, default=2,
                        help="Up to this many adjacent T-1/T pairs per selected game")
    parser.add_argument("--output", type=Path,
                        help="Optional private aggregate JSON; must not overwrite")
    args = parser.parse_args(argv)

    root_value = args.db_root or (
        Path(os.environ["PLANETS_CORPUS_DB_ROOT"])
        if "PLANETS_CORPUS_DB_ROOT" in os.environ else None
    )
    if root_value is None:
        parser.error("set PLANETS_CORPUS_DB_ROOT or pass --db-root")
    root = root_value.expanduser().resolve()
    relative = Path(args.generation)
    if (relative.is_absolute() or len(relative.parts) != 2
            or relative.parts[0] != "generations"
            or relative.parts[1] in (".", "..")
            or relative.suffix != ".duckdb"):
        parser.error("generation must be an explicit generations/*.duckdb")
    path = (root / relative).resolve()
    if path.parent != (root / "generations").resolve() or not path.is_file():
        parser.error("published generation does not exist under DB root")
    expected = args.expected_sha256.lower()
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        parser.error("expected SHA256 must be 64 hex characters")

    digest = _sha256(path)
    if digest != expected:
        raise ValueError("CORPUS_GENERATION_SHA256_MISMATCH: refusing to open")

    manifest_raw = args.baseline_manifest.read_bytes()
    baseline_ids: set[int] = set()
    for line in manifest_raw.decode("utf-8-sig").splitlines():
        if not line.strip():
            continue
        game_id = json.loads(line).get("game_id")
        if type(game_id) is not int or game_id <= 0 or game_id in baseline_ids:
            raise ValueError("invalid or duplicated baseline manifest game ID")
        baseline_ids.add(game_id)
    if (args.expected_baseline_games < 1 or
            len(baseline_ids) != args.expected_baseline_games):
        raise ValueError("baseline manifest game count mismatch; stop before sampling")
    if not baseline_ids:
        raise ValueError("refusing unscoped heldout entity sampling")
    connection, actual = connect_compact_generation_read_only(
        relative, root=root,
    )
    try:
        specs = _load_specs(connection)
        def restore(member_id: int):
            return reconstruct_compact_member(
                connection, member_id, specs=specs,
            )
        report = analyze_corpus_coverage(
            connection,
            max_games=args.max_games, pairs_per_game=args.pairs_per_game,
            reconstruct=restore,
            allowed_games=baseline_ids,
        )
    finally:
        connection.close()

    report["baseline_sample_allowlist"] = {
        "manifest_sha256": sha256(manifest_raw).hexdigest(),
        "allowed_game_count": len(baseline_ids),
        "heldout_entity_sampling": False,
    }
    report["generation"] = {
        "name": actual.name,
        "verified_sha256": digest,
        "read_only": True,
        "CURRENT_modified": False,
    }
    print(f"status: {report['status']}")
    print(f"generation_sha256: {digest}")
    print(f"baseline_manifest_sha256: {sha256(manifest_raw).hexdigest()}")
    print(f"baseline_allowed_games: {len(baseline_ids)}")
    for key, value in report["metadata"].items():
        print(f"{key}: {value}")
    for key, value in report["sample"].items():
        print(f"{key}: {json.dumps(value, sort_keys=True)}")
    print("NuHost_order_execution_verified: False")
    if args.output:
        destination = args.output.expanduser().resolve()
        if destination == path:
            parser.error("cannot overwrite input DB")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8") as target:
            json.dump(report, target, ensure_ascii=False, indent=2, sort_keys=True)
            target.write("\n")
        print("aggregate_report_written: true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
