from __future__ import annotations

import argparse
import json
from pathlib import Path

from .indexer import CorpusIndexError, load_manifest_jsonl
from .movement_chunnel_context import (
    aggregate_chunnel_residual_games,
    summarize_chunnel_residual_game,
)
from .normalizer import CorpusNormalizationError, load_archive_snapshots


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Explain remaining Move Most residuals with observed historical Chunnel events "
            "derived from stable hull abilities, owner Friendly Codes, and N+1 endpoints."
        )
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("validation/corpus/cache/loadall"),
    )
    parser.add_argument(
        "--games-output",
        type=Path,
        default=Path("validation/corpus/index/accounts-movement-chunnel-context-games.jsonl"),
    )
    parser.add_argument(
        "--stats-output",
        type=Path,
        default=Path("validation/corpus/index/accounts-movement-chunnel-context-stats.json"),
    )
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    try:
        manifests = load_manifest_jsonl(args.manifest.read_text(encoding="utf-8"))
    except (OSError, CorpusIndexError) as exc:
        print(str(exc))
        return 2

    if args.limit is not None:
        manifests = manifests[: max(0, args.limit)]

    rows: list[dict] = []
    failures: list[int] = []
    for position, manifest in enumerate(manifests, start=1):
        game_id = int(manifest["game_id"])
        archive_path = args.cache_dir / f"game-{game_id}.zip"
        try:
            archive_data = archive_path.read_bytes()
            snapshots = load_archive_snapshots(archive_data)
            row = summarize_chunnel_residual_game(
                game_id=game_id,
                settings_hash=str(manifest["settings_hash"]),
                archive_data=archive_data,
                snapshots=snapshots,
            )
        except (OSError, ValueError, AssertionError, CorpusNormalizationError) as exc:
            failures.append(game_id)
            print(
                json.dumps(
                    {
                        "status": "failed",
                        "position": position,
                        "total": len(manifests),
                        "game_id": game_id,
                        "error": f"{type(exc).__name__}: {exc}",
                    },
                    sort_keys=True,
                )
            )
            continue

        rows.append(row)
        print(
            json.dumps(
                {
                    "status": "ok",
                    "position": position,
                    "total": len(manifests),
                    "game_id": game_id,
                    "residual_before_chunnel": row["residual_before_chunnel"],
                    "observed_chunnel_events": row["observed_chunnel_events"],
                    "chunnel_explained": row["chunnel_explained"],
                    "residual_after_chunnel": row["residual_after_chunnel"],
                    "chunnel_counts": row["chunnel_counts"],
                    "ability_catalog": row["ability_catalog"],
                },
                sort_keys=True,
            )
        )

    args.games_output.parent.mkdir(parents=True, exist_ok=True)
    with args.games_output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    stats = aggregate_chunnel_residual_games(rows, failed_game_ids=failures)
    args.stats_output.parent.mkdir(parents=True, exist_ok=True)
    args.stats_output.write_text(
        json.dumps(stats, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    totals = stats["totals"]
    print("===== OBSERVED CHUNNEL RESIDUAL SUMMARY =====")
    print(f"games_indexed:          {stats['games_indexed']}")
    print(f"games_failed:           {stats['games_failed']}")
    print(f"settings_hashes:        {stats['settings_hashes']}")
    print(f"snapshots:              {totals.get('snapshots', 0)}")
    print(f"valid_turn_pairs:       {totals.get('valid_turn_pairs', 0)}")
    print(f"skipped_turn_pairs:     {totals.get('skipped_turn_pairs', 0)}")
    print(f"residual_before:        {totals.get('residual_before_chunnel', 0)}")
    print(f"observed_chunnel_events:{totals.get('observed_chunnel_events', 0)}")
    print(f"chunnel_explained:      {totals.get('chunnel_explained', 0)}")
    print(f"residual_after:         {totals.get('residual_after_chunnel', 0)}")
    print("chunnel_counts:")
    for key, count in sorted(stats["chunnel_counts"].items(), key=lambda item: (-item[1], item[0])):
        print(f"  {key}: {count}")
    print("explained_category_counts:")
    for key, count in sorted(stats["explained_category_counts"].items(), key=lambda item: (-item[1], item[0])):
        print(f"  {key}: {count}")
    print("explained_hull_counts_top:")
    for key, count in sorted(
        stats["explained_hull_counts"].items(),
        key=lambda item: (-item[1], int(item[0])),
    )[:40]:
        print(f"  hull={key}: {count}")
    print("residual_category_counts:")
    for key, count in sorted(stats["residual_category_counts"].items(), key=lambda item: (-item[1], item[0])):
        print(f"  {key}: {count}")
    print("event_counts:")
    for key, count in sorted(stats["event_counts"].items(), key=lambda item: (-item[1], item[0])):
        print(f"  {key}: {count}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
