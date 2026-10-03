from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .api import CorpusApiError, PlanetsNuPublicApi
from .archive import archive_members
from .indexer import (
    INDEX_SCHEMA,
    CorpusIndexError,
    aggregate_corpus_index,
    index_game_archive,
    load_manifest_jsonl,
)
from .normalizer import CorpusNormalizationError


def _default_cache_path(cache_dir: Path, game_id: int) -> Path:
    return cache_dir / f"game-{game_id}.zip"


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    text = "".join(
        json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
        for record in records
    )
    _atomic_write_text(path, text)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(
        path,
        json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
    )


def _checkpoint_outputs(
    index_output: Path,
    stats_output: Path,
    records: list[dict[str, Any]],
    failed_game_ids: list[int],
    manifests: list[dict[str, Any]],
) -> dict[str, Any]:
    records_by_game = {int(record["game_id"]): record for record in records}
    ordered_records = [
        records_by_game[int(manifest["game_id"])]
        for manifest in manifests
        if int(manifest["game_id"]) in records_by_game
    ]
    stats = aggregate_corpus_index(
        ordered_records,
        failed_game_ids=failed_game_ids,
    )
    _write_jsonl(index_output, ordered_records)
    _write_json(stats_output, stats)
    return stats



def _load_previous_index_records(path: Path) -> dict[int, dict[str, Any]]:
    if not path.is_file():
        return {}

    records: dict[int, dict[str, Any]] = {}
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CorpusIndexError(
                f"previous index line {line_number} is not valid JSON"
            ) from exc
        if not isinstance(record, dict):
            raise CorpusIndexError(
                f"previous index line {line_number} must be an object"
            )
        game_id = record.get("game_id")
        if (
            record.get("schema") == INDEX_SCHEMA
            and isinstance(game_id, int)
            and not isinstance(game_id, bool)
            and game_id > 0
        ):
            records[game_id] = record
    return records


def _record_matches_immutable_cache(
    record: Mapping[str, Any],
    manifest: Mapping[str, Any],
    cache_path: Path,
) -> bool:
    if record.get("schema") != INDEX_SCHEMA:
        return False
    if record.get("game_id") != manifest.get("game_id"):
        return False
    if record.get("settings_hash") != manifest.get("settings_hash"):
        return False
    if not cache_path.is_file():
        return False

    archive = record.get("archive")
    if not isinstance(archive, Mapping):
        return False
    expected_bytes = archive.get("bytes")
    if (
        isinstance(expected_bytes, bool)
        or not isinstance(expected_bytes, int)
        or expected_bytes != cache_path.stat().st_size
    ):
        return False
    sha256 = archive.get("sha256")
    if not isinstance(sha256, str) or len(sha256) != 64:
        return False

    # The loadall cache is immutable by project policy. Matching game/settings
    # identity plus recorded byte size lets us reuse the derived record without
    # re-decompressing and re-normalizing the same archive on every backfill.
    return True


def _progress_payload(
    record: Mapping[str, Any],
    *,
    position: int,
    total: int,
    source: str,
) -> dict[str, Any]:
    canonical = record["canonical_import"]
    mechanics = record["candidate_mechanics"]
    return {
        "game_id": record["game_id"],
        "position": position,
        "total": total,
        "status": "ok",
        "source": source,
        "snapshots": record["snapshots"],
        "transitions": record["transitions"],
        "embedded_consecutive": record["embedded_consecutive"],
        "canonical_ok": canonical["ok"],
        "canonical_failed": canonical["failed"],
        "ghost_ship_records": mechanics.get("ghost_ship_records", 0),
        "ionstorm_records": mechanics.get("ionstorm_records", 0),
        "minefield_records": mechanics.get("minefield_records", 0),
    }

def _download_game_archive(
    *,
    client: PlanetsNuPublicApi,
    game_id: int,
    retries: int,
    retry_delay: float,
) -> bytes:
    attempts = retries + 1
    last_exc: BaseException | None = None

    for attempt in range(1, attempts + 1):
        try:
            info = client.load_info(game_id)
            game = info.get("game", {})
            if not isinstance(game, dict) or game.get("status") != 3:
                raise ValueError(
                    f"game {game_id}: /game/loadall requires finished status=3"
                )
            data = client.load_all_archive(game_id)
            # Validate ZIP structure before anything is written to immutable cache.
            archive_members(data)
            return data
        except (CorpusApiError, OSError) as exc:
            last_exc = exc
            if attempt >= attempts:
                raise
            print(
                json.dumps(
                    {
                        "game_id": game_id,
                        "status": "retry",
                        "attempt": attempt,
                        "max_attempts": attempts,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                    sort_keys=True,
                ),
                file=sys.stderr,
            )
            if retry_delay > 0:
                time.sleep(retry_delay * attempt)

    assert last_exc is not None
    raise last_exc



def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Ingest finished games from a corpus manifest, cache validated /game/loadall "
            "archives, and write privacy-minimized per-game index/statistics files."
        )
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("validation/corpus/cache/loadall"),
    )
    parser.add_argument(
        "--index-output",
        type=Path,
        default=Path("validation/corpus/index/games.jsonl"),
    )
    parser.add_argument(
        "--stats-output",
        type=Path,
        default=Path("validation/corpus/index/stats.json"),
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="redownload archives even when an immutable cache entry exists",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="never use the network; index only already cached archives",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="stop immediately after the first failed game",
    )
    parser.add_argument(
        "--no-reuse-index",
        action="store_true",
        help=(
            "ignore a compatible previous --index-output and rebuild every "
            "selected game from its archive"
        ),
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=0.0,
        help="sleep this many seconds after each network archive download",
    )
    parser.add_argument(
        "--network-timeout",
        type=float,
        default=180.0,
        help="per-request timeout in seconds for loadinfo/loadall",
    )
    parser.add_argument(
        "--download-retries",
        type=int,
        default=2,
        help="retry transient network failures this many additional times",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="base delay in seconds between download retries",
    )
    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        print("--limit must be positive", file=sys.stderr)
        return 2
    if args.offline and args.refresh:
        print("--offline and --refresh cannot be used together", file=sys.stderr)
        return 2
    if args.request_delay < 0:
        print("--request-delay must be non-negative", file=sys.stderr)
        return 2
    if args.network_timeout <= 0:
        print("--network-timeout must be positive", file=sys.stderr)
        return 2
    if args.download_retries < 0 or args.retry_delay < 0:
        print("--download-retries/retry-delay must be non-negative", file=sys.stderr)
        return 2

    try:
        manifests = list(load_manifest_jsonl(args.manifest.read_text(encoding="utf-8")))
    except (OSError, CorpusIndexError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.limit is not None:
        manifests = manifests[: args.limit]

    previous_records: dict[int, dict[str, Any]] = {}
    if not args.refresh and not args.no_reuse_index:
        try:
            previous_records = _load_previous_index_records(args.index_output)
        except (OSError, CorpusIndexError) as exc:
            print(
                f"WARNING: previous index cannot be reused: {exc}",
                file=sys.stderr,
            )

    records: list[dict[str, Any]] = []
    if previous_records:
        for manifest in manifests:
            game_id = int(manifest["game_id"])
            previous = previous_records.get(game_id)
            cache_path = _default_cache_path(args.cache_dir, game_id)
            if (
                previous is not None
                and _record_matches_immutable_cache(previous, manifest, cache_path)
            ):
                records.append(previous)

    failed_game_ids: list[int] = []
    client: PlanetsNuPublicApi | None = None

    for position, manifest in enumerate(manifests, start=1):
        game_id = int(manifest["game_id"])
        cache_path = _default_cache_path(args.cache_dir, game_id)
        source = "cache"
        try:
            previous = previous_records.get(game_id)
            if (
                previous is not None
                and not args.refresh
                and _record_matches_immutable_cache(previous, manifest, cache_path)
            ):
                print(
                    json.dumps(
                        _progress_payload(
                            previous,
                            position=position,
                            total=len(manifests),
                            source="index-cache",
                        ),
                        sort_keys=True,
                    )
                )
                _checkpoint_outputs(
                    args.index_output,
                    args.stats_output,
                    records,
                    failed_game_ids,
                    manifests,
                )
                continue

            if cache_path.exists() and not args.refresh:
                data = cache_path.read_bytes()
            else:
                if args.offline:
                    raise FileNotFoundError(f"game {game_id}: cache miss in offline mode")
                if client is None:
                    client = PlanetsNuPublicApi(timeout=args.network_timeout)
                data = _download_game_archive(
                    client=client,
                    game_id=game_id,
                    retries=args.download_retries,
                    retry_delay=args.retry_delay,
                )
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(data)
                source = "network"
                if args.request_delay > 0:
                    time.sleep(args.request_delay)

            record = index_game_archive(
                manifest,
                data,
                cache_path=str(cache_path),
                acquisition_source=source,
            )
            records.append(record)
            print(
                json.dumps(
                    _progress_payload(
                        record,
                        position=position,
                        total=len(manifests),
                        source=source,
                    ),
                    sort_keys=True,
                )
            )
            _checkpoint_outputs(
                args.index_output,
                args.stats_output,
                records,
                failed_game_ids,
            )
        except (
            CorpusApiError,
            CorpusIndexError,
            CorpusNormalizationError,
            OSError,
            ValueError,
        ) as exc:
            failed_game_ids.append(game_id)
            print(
                json.dumps(
                    {
                        "game_id": game_id,
                        "position": position,
                        "total": len(manifests),
                        "status": "failed",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                    sort_keys=True,
                ),
                file=sys.stderr,
            )
            _checkpoint_outputs(
                args.index_output,
                args.stats_output,
                records,
                failed_game_ids,
            )
            if args.fail_fast:
                break

    stats = _checkpoint_outputs(
        args.index_output,
        args.stats_output,
        records,
        failed_game_ids,
        manifests,
    )

    print("===== CORPUS INGEST SUMMARY =====")
    print(f"manifest_games:      {len(manifests)}")
    print(f"games_indexed:       {stats['games_indexed']}")
    print(f"games_failed:        {stats['games_failed']}")
    print(f"index_output:        {args.index_output}")
    print(f"stats_output:        {args.stats_output}")
    print(f"snapshots:           {stats['totals'].get('snapshots', 0)}")
    print(f"transitions:         {stats['totals'].get('transitions', 0)}")
    print(f"embedded_consecutive:{stats['totals'].get('embedded_consecutive', 0)}")
    print(f"canonical_ok:        {stats['totals'].get('canonical_ok', 0)}")
    print(f"canonical_failed:    {stats['totals'].get('canonical_failed', 0)}")
    print(f"settings_hashes:     {len(stats['games_by_settings_hash'])}")
    print(f"races:               {stats['player_slots_by_race']}")
    print(f"candidate_mechanics: {stats['candidate_mechanics']}")

    return 1 if failed_game_ids else 0


if __name__ == "__main__":
    raise SystemExit(main())
