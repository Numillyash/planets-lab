from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .corpus_db import (
    CorpusDbError,
    database_stats,
    ensure_external_db_root,
    publish_generation,
)
from .corpus_db_typed_multi import (
    CorpusArchiveInput,
    import_archives_to_typed_database,
    validate_typed_corpus_parity,
)
from .indexer import CorpusIndexError, load_manifest_jsonl
from .normalizer import CorpusNormalizationError


def _json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def _db_root(value: str | None) -> Path:
    if value:
        return Path(value)
    env = os.environ.get("PLANETS_CORPUS_DB_ROOT")
    if env:
        return Path(env)
    return Path("/corpus-db")


def _load_archives(manifest_path: Path, cache_dir: Path) -> list[CorpusArchiveInput]:
    try:
        records = list(load_manifest_jsonl(manifest_path.read_text(encoding="utf-8")))
    except (OSError, CorpusIndexError) as exc:
        raise CorpusDbError(str(exc)) from exc

    archives: list[CorpusArchiveInput] = []
    for record in records:
        game_id = record.get("game_id")
        if isinstance(game_id, bool) or not isinstance(game_id, int) or game_id <= 0:
            raise CorpusDbError("manifest game_id must be a positive integer")
        path = (cache_dir / f"game-{game_id}.zip").resolve()
        if not path.is_file():
            raise CorpusDbError(f"game {game_id}: cached archive not found: {path}")
        archives.append(CorpusArchiveInput(game_id=game_id, archive_path=str(path)))
    if not archives:
        raise CorpusDbError("manifest contains no games")
    return archives


def _default_build_id(result: object) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fingerprint = str(getattr(result, "corpus_fingerprint"))
    count = int(getattr(result, "archive_count"))
    return f"corpus-v1typed-public{count}-{stamp}-{fingerprint[:12]}"


def _build(args: argparse.Namespace) -> int:
    try:
        root = ensure_external_db_root(_db_root(args.db_root))
        manifest = args.manifest.resolve()
        cache_dir = args.cache_dir.resolve()
        archives = _load_archives(manifest, cache_dir)
        if args.expected_count is not None and len(archives) != args.expected_count:
            raise CorpusDbError(
                f"expected {args.expected_count} manifest games, got {len(archives)}"
            )

        staging = root / "staging" / (
            f"typed-corpus-{os.getpid()}-{hashlib.sha256(str(manifest).encode()).hexdigest()[:8]}.duckdb"
        )
        imported = import_archives_to_typed_database(
            archives,
            staging,
            commit_every_members=args.commit_every_members,
            arrow_batch_rows=args.arrow_batch_rows,
            sample_members_per_archive=args.sample_members_per_archive,
            sample_entities_per_section=args.sample_entities_per_section,
        )
        parity = validate_typed_corpus_parity(
            archives,
            staging,
            max_mismatches=args.max_mismatches,
        )
    except (OSError, ValueError, CorpusDbError, CorpusNormalizationError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    _json(
        {
            "manifest": str(manifest),
            "cache_dir": str(cache_dir),
            "import": asdict(imported),
            "parity": asdict(parity),
        }
    )
    if parity.failed:
        for mismatch in parity.mismatches:
            print(
                f"PARITY {mismatch.member} {mismatch.path}: {mismatch.reason}",
                file=sys.stderr,
            )
        print("typed corpus parity failed; staging DB was not published", file=sys.stderr)
        return 1

    build_id = args.build_id or _default_build_id(imported)
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
            "published": asdict(published),
            "database": database_stats(Path(published.generation_path)),
        }
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build one typed DuckDB generation from a corpus manifest/cache"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("validation/corpus/manifests/public-validation-selected.jsonl"),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("validation/corpus/cache/loadall"),
    )
    parser.add_argument("--db-root")
    parser.add_argument("--build-id")
    parser.add_argument("--expected-count", type=int, default=36)
    parser.add_argument("--commit-every-members", type=int, default=128)
    parser.add_argument("--arrow-batch-rows", type=int, default=20_000)
    parser.add_argument("--sample-members-per-archive", type=int, default=128)
    parser.add_argument("--sample-entities-per-section", type=int, default=10_000)
    parser.add_argument("--max-mismatches", type=int, default=100)
    args = parser.parse_args()
    return _build(args)


if __name__ == "__main__":
    raise SystemExit(main())
