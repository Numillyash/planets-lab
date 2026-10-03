from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from .corpus_db import CorpusDbError, ensure_external_db_root
from .corpus_db_compact import publish_compact_generation
from .corpus_db_compact_multi import (
    CompactCorpusArchiveInput,
    compact_corpus_database_stats,
    import_archives_to_compact_database,
    validate_compact_corpus_parity,
)
from .indexer import CorpusIndexError, load_manifest_jsonl
from .normalizer import CorpusNormalizationError


PARITY_CHECKPOINT_VERSION = 1


def _json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def _progress(value: object) -> None:
    print(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        flush=True,
    )


def _db_root(value: str | None) -> Path:
    if value:
        return Path(value)
    env = os.environ.get("PLANETS_CORPUS_DB_ROOT")
    if env:
        return Path(env)
    return Path("/corpus-db")


def _load_archives(manifest_path: Path, cache_dir: Path) -> list[CompactCorpusArchiveInput]:
    try:
        records = list(load_manifest_jsonl(manifest_path.read_text(encoding="utf-8")))
    except (OSError, CorpusIndexError) as exc:
        raise CorpusDbError(str(exc)) from exc

    archives: list[CompactCorpusArchiveInput] = []
    for record in records:
        game_id = record.get("game_id")
        if isinstance(game_id, bool) or not isinstance(game_id, int) or game_id <= 0:
            raise CorpusDbError("manifest game_id must be a positive integer")
        path = (cache_dir / f"game-{game_id}.zip").resolve()
        if not path.is_file():
            raise CorpusDbError(f"game {game_id}: cached archive not found: {path}")
        archives.append(
            CompactCorpusArchiveInput(
                game_id=game_id,
                archive_path=str(path),
            )
        )
    if not archives:
        raise CorpusDbError("manifest contains no games")
    return archives


def _default_build_id(count: int, fingerprint: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"corpus-v2compact-public{count}-{stamp}-{fingerprint[:12]}"


def _load_parity_checkpoint(
    path: Path,
    *,
    fingerprint: str,
    database: Path,
    source_members: int,
) -> dict[int, int]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    if payload.get("version") != PARITY_CHECKPOINT_VERSION:
        return {}
    if payload.get("corpus_fingerprint") != fingerprint:
        return {}
    if payload.get("database_bytes") != database.stat().st_size:
        return {}
    if payload.get("source_members") != source_members:
        return {}
    games = payload.get("validated_games")
    if not isinstance(games, dict):
        return {}
    result: dict[int, int] = {}
    for key, value in games.items():
        try:
            game_id = int(key)
            checked = int(value)
        except (TypeError, ValueError):
            return {}
        if game_id <= 0 or checked < 0:
            return {}
        result[game_id] = checked
    return result


def _write_parity_checkpoint(
    path: Path,
    *,
    fingerprint: str,
    database: Path,
    source_members: int,
    validated_games: dict[int, int],
) -> None:
    payload = {
        "version": PARITY_CHECKPOINT_VERSION,
        "corpus_fingerprint": fingerprint,
        "database_bytes": database.stat().st_size,
        "source_members": source_members,
        "validated_games": {
            str(game_id): int(checked)
            for game_id, checked in sorted(validated_games.items())
        },
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


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

        state_name = args.state_name
        staging = root / "staging" / f"{state_name}.duckdb"
        schema_dir = root / "staging" / f"{state_name}-schema"
        parity_checkpoint = root / "staging" / f"{state_name}-parity.json"

        imported = import_archives_to_compact_database(
            archives,
            staging,
            schema_dir,
            commit_every_members=args.commit_every_members,
            arrow_batch_rows=args.arrow_batch_rows,
            progress=_progress,
        )
        if imported.archive_count != len(archives):
            raise CorpusDbError(
                f"compact import incomplete: {imported.archive_count}/{len(archives)} archives"
            )

        validated_games = _load_parity_checkpoint(
            parity_checkpoint,
            fingerprint=imported.corpus_fingerprint,
            database=staging,
            source_members=imported.turn_members,
        )

        def checkpoint_game(game_id: int, checked: int) -> None:
            validated_games[game_id] = checked
            _write_parity_checkpoint(
                parity_checkpoint,
                fingerprint=imported.corpus_fingerprint,
                database=staging,
                source_members=imported.turn_members,
                validated_games=validated_games,
            )

        parity = validate_compact_corpus_parity(
            archives,
            staging,
            max_mismatches=args.max_mismatches,
            progress=_progress,
            validated_games=validated_games,
            on_archive_validated=checkpoint_game,
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
        print(
            "compact corpus parity failed; resumable staging DB was not published",
            file=sys.stderr,
        )
        return 1

    expected_checked = imported.turn_members
    if parity.checked != expected_checked:
        print(
            f"parity checked {parity.checked} members, expected {expected_checked}",
            file=sys.stderr,
        )
        return 2

    build_id = args.build_id or _default_build_id(
        len(archives),
        imported.corpus_fingerprint,
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
        stats = compact_corpus_database_stats(Path(published.generation_path))
        parity_checkpoint.unlink(missing_ok=True)
        if args.clear_schema_checkpoints:
            shutil.rmtree(schema_dir, ignore_errors=True)
    except (OSError, ValueError, CorpusDbError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    _json(
        {
            "published": asdict(published),
            "database": stats,
        }
    )
    return 0


def _stats(args: argparse.Namespace) -> int:
    try:
        result = compact_corpus_database_stats(args.database.resolve())
    except (OSError, ValueError, CorpusDbError, duckdb.Error) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _json(result)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build one resumable compact DuckDB generation for a corpus"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser(
        "build",
        help="resume/build, exact-parity-check and publish a compact corpus generation",
    )
    build.add_argument(
        "--manifest",
        type=Path,
        default=Path("validation/corpus/manifests/public-validation-selected.jsonl"),
    )
    build.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("validation/corpus/cache/loadall"),
    )
    build.add_argument("--db-root")
    build.add_argument("--build-id")
    build.add_argument("--expected-count", type=int, default=36)
    build.add_argument("--state-name", default="compact-public36-resume")
    build.add_argument("--commit-every-members", type=int, default=128)
    build.add_argument("--arrow-batch-rows", type=int, default=10_000)
    build.add_argument("--max-mismatches", type=int, default=100)
    build.add_argument(
        "--activate-current",
        action="store_true",
        help="switch CURRENT after publication; off by default for public compact gate",
    )
    build.add_argument(
        "--clear-schema-checkpoints",
        action="store_true",
        help="delete reusable schema checkpoints after successful publication",
    )
    build.set_defaults(func=_build)

    stats = sub.add_parser("stats", help="show compact corpus generation statistics")
    stats.add_argument("--database", type=Path, required=True)
    stats.set_defaults(func=_stats)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
