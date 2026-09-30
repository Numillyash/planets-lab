from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .corpus_db import (
    CorpusDbError,
    benchmark_query,
    database_stats,
    ensure_external_db_root,
    publish_generation,
    resolve_current_generation,
)
from .corpus_db_typed import (
    CORPUS_DB_TYPED_SCHEMA,
    import_archive_to_typed_database,
    validate_typed_semantic_parity,
)
from .corpus_db_typed_attribution import attribute_typed_storage
from .normalizer import CorpusNormalizationError


def _db_root(value: str | None) -> Path:
    if value:
        return Path(value)
    env = os.environ.get("PLANETS_CORPUS_DB_ROOT")
    if env:
        return Path(env)
    return Path("/corpus-db")


def _json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))


def _default_build_id(game_id: int, archive_sha256: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"corpus-v1typed-g{game_id}-{stamp}-{archive_sha256[:12]}"


def _build(args: argparse.Namespace) -> int:
    root = ensure_external_db_root(_db_root(args.db_root))
    archive = args.archive.resolve()
    staging = root / "staging" / f"typed-{os.getpid()}-{archive.stem}.duckdb"

    try:
        imported = import_archive_to_typed_database(
            archive,
            staging,
            expected_game_id=args.game_id,
            commit_every_members=args.commit_every_members,
            arrow_batch_rows=args.arrow_batch_rows,
        )
        parity = validate_typed_semantic_parity(
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
        return 1

    build_id = args.build_id or _default_build_id(
        imported.game_id,
        imported.archive_sha256,
    )
    try:
        published = publish_generation(
            root=root,
            staging_path=staging,
            build_id=build_id,
            import_result=imported,
            parity_result=parity,
        )
    except (OSError, CorpusDbError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    _json(
        {
            "schema": CORPUS_DB_TYPED_SCHEMA,
            "published": asdict(published),
            "database": database_stats(Path(published.generation_path)),
        }
    )
    return 0


def _validate(args: argparse.Namespace) -> int:
    try:
        database = (
            args.database.resolve()
            if args.database
            else resolve_current_generation(_db_root(args.db_root))
        )
        result = validate_typed_semantic_parity(
            args.archive.resolve(),
            database,
            max_mismatches=args.max_mismatches,
        )
    except (OSError, ValueError, CorpusDbError, CorpusNormalizationError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    _json(asdict(result))
    return 1 if result.failed else 0


def _benchmark(args: argparse.Namespace) -> int:
    try:
        database = (
            args.database.resolve()
            if args.database
            else resolve_current_generation(_db_root(args.db_root))
        )
        result = benchmark_query(
            database,
            kind=args.kind,
            game_id=args.game_id,
        )
    except (OSError, CorpusDbError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _json(asdict(result))
    return 0


def _storage_attribution(args: argparse.Namespace) -> int:
    try:
        root = ensure_external_db_root(_db_root(args.db_root))
        database = (
            args.database.resolve()
            if args.database
            else resolve_current_generation(root)
        )
        scratch_dir = (root / "staging").resolve()
        result = attribute_typed_storage(
            database,
            scratch_dir,
            memory_limit=args.memory_limit,
            threads=args.threads,
        )
        _json(asdict(result))
    except (OSError, ValueError, CorpusDbError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Typed Planets.nu corpus DB v1 prototype"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser(
        "build",
        help="build, parity-check and publish a typed corpus generation",
    )
    build.add_argument("archive", type=Path)
    build.add_argument("--game-id", type=int)
    build.add_argument("--db-root")
    build.add_argument("--build-id")
    build.add_argument("--commit-every-members", type=int, default=128)
    build.add_argument("--arrow-batch-rows", type=int, default=20_000)
    build.add_argument("--max-mismatches", type=int, default=100)
    build.set_defaults(func=_build)

    validate = sub.add_parser(
        "validate",
        help="validate source archive against a typed generation",
    )
    validate.add_argument("archive", type=Path)
    validate.add_argument("--database", type=Path)
    validate.add_argument("--db-root")
    validate.add_argument("--max-mismatches", type=int, default=100)
    validate.set_defaults(func=_validate)

    benchmark = sub.add_parser(
        "benchmark",
        help="run existing bounded indexed benchmark against typed generation",
    )
    benchmark.add_argument("--kind", choices=("turn-pair", "vcr-site"), required=True)
    benchmark.add_argument("--game-id", type=int, default=233558)
    benchmark.add_argument("--database", type=Path)
    benchmark.add_argument("--db-root")
    benchmark.set_defaults(func=_benchmark)

    attribution = sub.add_parser(
        "storage-attribution",
        help="attribute typed-generation storage to tables, member fallback and indexes",
    )
    attribution.add_argument("--database", type=Path)
    attribution.add_argument("--db-root")
    attribution.add_argument("--memory-limit", default="4GB")
    attribution.add_argument("--threads", type=int, default=2)
    attribution.set_defaults(func=_storage_attribution)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
