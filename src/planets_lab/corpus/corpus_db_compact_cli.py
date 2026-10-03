from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .corpus_db import CorpusDbError, ensure_external_db_root
from .corpus_db_compact import (
    CORPUS_DB_COMPACT_SCHEMA,
    benchmark_compact_query,
    compact_database_stats,
    import_archive_to_compact_database,
    publish_compact_generation,
    validate_compact_semantic_parity,
)
from .normalizer import CorpusNormalizationError


def _db_root(value: str | None) -> Path:
    if value:
        return Path(value)
    env = os.environ.get("PLANETS_CORPUS_DB_ROOT")
    if env:
        return Path(env)
    return Path("/corpus-db")


def _json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def _build_id(game_id: int, archive_sha: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"corpus-v2compact-g{game_id}-{stamp}-{archive_sha[:12]}"


def _build(args: argparse.Namespace) -> int:
    try:
        root = ensure_external_db_root(_db_root(args.db_root))
        archive = args.archive.resolve()
        staging = root / "staging" / (
            f"compact-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-"
            f"{uuid.uuid4().hex[:12]}.duckdb"
        )
        imported = import_archive_to_compact_database(
            archive,
            staging,
            expected_game_id=args.game_id,
            commit_every_members=args.commit_every_members,
            arrow_batch_rows=args.arrow_batch_rows,
        )
        parity = validate_compact_semantic_parity(
            archive,
            staging,
            max_mismatches=args.max_mismatches,
        )
    except (OSError, ValueError, CorpusDbError, CorpusNormalizationError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    _json({"import": asdict(imported), "parity": asdict(parity)})
    if parity.failed:
        for mismatch in parity.mismatches:
            print(
                f"PARITY {mismatch.member} {mismatch.path}: {mismatch.reason}",
                file=sys.stderr,
            )
        print("compact parity failed; staging DB was not published", file=sys.stderr)
        return 1

    build_id = args.build_id or _build_id(
        imported.game_id,
        imported.archive_sha256,
    )
    try:
        published = publish_compact_generation(
            root=root,
            staging_path=staging,
            build_id=build_id,
            import_result=imported,
            parity_result=parity,
            activate_current=args.activate_current,
        )
        stats = compact_database_stats(Path(published.generation_path))
    except (OSError, ValueError, CorpusDbError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    _json(
        {
            "schema": CORPUS_DB_COMPACT_SCHEMA,
            "published": asdict(published),
            "database": stats,
        }
    )
    return 0


def _validate(args: argparse.Namespace) -> int:
    try:
        result = validate_compact_semantic_parity(
            args.archive.resolve(),
            args.database.resolve(),
            max_mismatches=args.max_mismatches,
        )
    except (OSError, ValueError, CorpusDbError, CorpusNormalizationError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _json(asdict(result))
    return 1 if result.failed else 0


def _stats(args: argparse.Namespace) -> int:
    try:
        result = compact_database_stats(args.database.resolve())
    except (OSError, ValueError, CorpusDbError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _json(result)
    return 0


def _benchmark(args: argparse.Namespace) -> int:
    try:
        result = benchmark_compact_query(
            args.database.resolve(),
            kind=args.kind,
            game_id=args.game_id,
        )
    except (OSError, ValueError, CorpusDbError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _json(asdict(result))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compact typed2 Planets.nu corpus DB prototype"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser(
        "build",
        help="build, exact-parity-check and publish one compact generation",
    )
    build.add_argument("archive", type=Path)
    build.add_argument("--game-id", type=int)
    build.add_argument("--db-root")
    build.add_argument("--build-id")
    build.add_argument("--commit-every-members", type=int, default=128)
    build.add_argument("--arrow-batch-rows", type=int, default=10_000)
    build.add_argument("--max-mismatches", type=int, default=100)
    build.add_argument(
        "--activate-current",
        action="store_true",
        help="switch CURRENT after publication; off by default for compact prototype",
    )
    build.set_defaults(func=_build)

    validate = sub.add_parser(
        "validate",
        help="validate an archive against an explicit compact generation",
    )
    validate.add_argument("archive", type=Path)
    validate.add_argument("--database", type=Path, required=True)
    validate.add_argument("--max-mismatches", type=int, default=100)
    validate.set_defaults(func=_validate)

    stats = sub.add_parser("stats", help="show compact generation statistics")
    stats.add_argument("--database", type=Path, required=True)
    stats.set_defaults(func=_stats)

    benchmark = sub.add_parser(
        "benchmark",
        help="run a no-global-entity-index compact query benchmark",
    )
    benchmark.add_argument("--database", type=Path, required=True)
    benchmark.add_argument("--kind", choices=("turn-pair", "vcr-site"), required=True)
    benchmark.add_argument("--game-id", type=int, default=233558)
    benchmark.set_defaults(func=_benchmark)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
