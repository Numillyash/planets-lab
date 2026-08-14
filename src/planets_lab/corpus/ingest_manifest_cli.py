from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .api import CorpusApiError, PlanetsNuPublicApi
from .archive import archive_members
from .indexer import (
    CorpusIndexError,
    aggregate_corpus_index,
    index_game_archive,
    load_manifest_jsonl,
)
from .normalizer import CorpusNormalizationError


def _default_cache_path(cache_dir: Path, game_id: int) -> Path:
    return cache_dir / f"game-{game_id}.zip"


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(
        json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
        for record in records
    )
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


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
    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        print("--limit must be positive", file=sys.stderr)
        return 2
    if args.offline and args.refresh:
        print("--offline and --refresh cannot be used together", file=sys.stderr)
        return 2

    try:
        manifests = list(load_manifest_jsonl(args.manifest.read_text(encoding="utf-8")))
    except (OSError, CorpusIndexError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.limit is not None:
        manifests = manifests[: args.limit]

    records: list[dict[str, Any]] = []
    failed_game_ids: list[int] = []
    client: PlanetsNuPublicApi | None = None

    for position, manifest in enumerate(manifests, start=1):
        game_id = int(manifest["game_id"])
        cache_path = _default_cache_path(args.cache_dir, game_id)
        source = "cache"
        try:
            if cache_path.exists() and not args.refresh:
                data = cache_path.read_bytes()
            else:
                if args.offline:
                    raise FileNotFoundError(f"game {game_id}: cache miss in offline mode")
                if client is None:
                    client = PlanetsNuPublicApi()
                info = client.load_info(game_id)
                game = info.get("game", {})
                if not isinstance(game, dict) or game.get("status") != 3:
                    raise ValueError(f"game {game_id}: /game/loadall requires finished status=3")
                data = client.load_all_archive(game_id)
                # Validate before writing anything to the immutable cache.
                archive_members(data)
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(data)
                source = "network"

            record = index_game_archive(
                manifest,
                data,
                cache_path=str(cache_path),
                acquisition_source=source,
            )
            records.append(record)
            canonical = record["canonical_import"]
            mechanics = record["candidate_mechanics"]
            print(
                json.dumps(
                    {
                        "game_id": game_id,
                        "position": position,
                        "total": len(manifests),
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
                    },
                    sort_keys=True,
                )
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
            if args.fail_fast:
                break

    _write_jsonl(args.index_output, records)
    stats = aggregate_corpus_index(records, failed_game_ids=failed_game_ids)
    _write_json(args.stats_output, stats)

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
