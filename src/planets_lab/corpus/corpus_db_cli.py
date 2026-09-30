from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from .corpus_db import (
    CorpusDbError,
    attribute_storage,
    benchmark_query,
    database_stats,
    default_build_id,
    ensure_external_db_root,
    import_archive_to_database,
    profile_payloads,
    publish_generation,
    resolve_current_generation,
    validate_semantic_parity,
)
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


def _build(args: argparse.Namespace) -> int:
    root = ensure_external_db_root(_db_root(args.db_root))
    archive = args.archive.resolve()
    provisional = f"staging-{os.getpid()}-{archive.stem}.duckdb"
    staging = root / "staging" / provisional

    try:
        imported = import_archive_to_database(
            archive,
            staging,
            expected_game_id=args.game_id,
            commit_every_members=args.commit_every_members,
            arrow_batch_rows=args.arrow_batch_rows,
        )
        parity = validate_semantic_parity(
            archive,
            staging,
            max_mismatches=args.max_mismatches,
        )
    except (OSError, ValueError, CorpusDbError, CorpusNormalizationError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    _json({"import": asdict(imported), "parity": asdict(parity)})
    if parity.failed:
        print("semantic parity failed; staging database was not published", file=sys.stderr)
        for mismatch in parity.mismatches:
            print(
                f"PARITY {mismatch.member} {mismatch.path}: {mismatch.reason}",
                file=sys.stderr,
            )
        return 1

    build_id = args.build_id or default_build_id(imported.game_id, imported.archive_sha256)
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

    _json({"published": asdict(published), "database": database_stats(Path(published.generation_path))})
    return 0


def _validate(args: argparse.Namespace) -> int:
    database = args.database.resolve() if args.database else resolve_current_generation(_db_root(args.db_root))
    try:
        result = validate_semantic_parity(
            args.archive.resolve(),
            database,
            max_mismatches=args.max_mismatches,
        )
    except (OSError, ValueError, CorpusDbError, CorpusNormalizationError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _json(asdict(result))
    for mismatch in result.mismatches:
        print(f"PARITY {mismatch.member} {mismatch.path}: {mismatch.reason}", file=sys.stderr)
    return 1 if result.failed else 0


def _current(args: argparse.Namespace) -> int:
    try:
        path = resolve_current_generation(_db_root(args.db_root))
    except (OSError, CorpusDbError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _json(database_stats(path))
    return 0


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
    root = ensure_external_db_root(_db_root(args.db_root))
    try:
        database = (
            args.database.resolve()
            if args.database
            else resolve_current_generation(root)
        )
        scratch = (
            args.scratch.resolve()
            if args.scratch
            else root / "staging" / f"storage-attribution-{os.getpid()}.duckdb"
        )
        staging = (root / "staging").resolve()
        if scratch.parent.resolve() != staging:
            raise CorpusDbError(
                f"storage-attribution scratch DB must live directly under {staging}"
            )
        result = attribute_storage(
            database,
            scratch,
            memory_limit=args.memory_limit,
            threads=args.threads,
        )
        _json(asdict(result))
    except (OSError, ValueError, CorpusDbError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    finally:
        if "scratch" in locals() and not args.keep:
            try:
                scratch.unlink()
            except FileNotFoundError:
                pass
    return 0


def _payload_profile(args: argparse.Namespace) -> int:
    try:
        database = (
            args.database.resolve()
            if args.database
            else resolve_current_generation(_db_root(args.db_root))
        )
        result = profile_payloads(
            database,
            largest_limit=args.largest_limit,
        )
        _json(asdict(result))
    except (OSError, ValueError, CorpusDbError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Lossless Planets.nu TRN -> DuckDB corpus DB v1 tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="import, parity-validate and publish a new immutable generation")
    build.add_argument("archive", type=Path)
    build.add_argument("--game-id", type=int)
    build.add_argument("--db-root")
    build.add_argument("--build-id")
    build.add_argument("--commit-every-members", type=int, default=128)
    build.add_argument("--arrow-batch-rows", type=int, default=20_000)
    build.add_argument("--max-mismatches", type=int, default=100)
    build.set_defaults(func=_build)

    validate = sub.add_parser("validate", help="semantic parity-check an archive against a DB generation")
    validate.add_argument("archive", type=Path)
    validate.add_argument("--database", type=Path)
    validate.add_argument("--db-root")
    validate.add_argument("--max-mismatches", type=int, default=100)
    validate.set_defaults(func=_validate)

    current = sub.add_parser("current", help="show the published CURRENT generation and compact stats")
    current.add_argument("--db-root")
    current.set_defaults(func=_current)

    benchmark = sub.add_parser(
        "benchmark",
        help="run one bounded indexed query and report wall time / process peak RSS",
    )
    benchmark.add_argument("--kind", choices=("turn-pair", "vcr-site"), required=True)
    benchmark.add_argument("--game-id", type=int, default=233558)
    benchmark.add_argument("--database", type=Path)
    benchmark.add_argument("--db-root")
    benchmark.set_defaults(func=_benchmark)

    storage = sub.add_parser(
        "storage-attribution",
        help="copy CURRENT into staging and attribute physical size to data/index stages",
    )
    storage.add_argument("--database", type=Path)
    storage.add_argument("--db-root")
    storage.add_argument("--scratch", type=Path)
    storage.add_argument("--memory-limit", default="4GB")
    storage.add_argument("--threads", type=int, default=2)
    storage.add_argument("--keep", action="store_true")
    storage.set_defaults(func=_storage_attribution)

    payload = sub.add_parser(
        "payload-profile",
        help="profile logical entity payload sizes/cardinality without printing source values",
    )
    payload.add_argument("--database", type=Path)
    payload.add_argument("--db-root")
    payload.add_argument("--largest-limit", type=int, default=20)
    payload.set_defaults(func=_payload_profile)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())