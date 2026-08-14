from __future__ import annotations

import argparse
import json
from pathlib import Path

from .indexer import CorpusIndexError, load_manifest_jsonl
from .movement_differential import (
    aggregate_movement_differential_games,
    summarize_movement_differential_game,
)
from .normalizer import CorpusNormalizationError, load_archive_snapshots


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate owner-context-filtered Move Most geometry across cached "
            "finished-game /loadall archives. No network access is performed."
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
        default=Path("validation/corpus/index/accounts-movement-differential-games.jsonl"),
    )
    parser.add_argument(
        "--stats-output",
        type=Path,
        default=Path("validation/corpus/index/accounts-movement-differential-stats.json"),
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
            snapshots = load_archive_snapshots(archive_path.read_bytes())
            row = summarize_movement_differential_game(
                game_id=game_id,
                settings_hash=str(manifest["settings_hash"]),
                snapshots=snapshots,
            )
        except (OSError, ValueError, CorpusNormalizationError) as exc:
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
                    "geometry_ready": row["geometry_ready"],
                    "move_most_candidates": row["move_most_candidates"],
                    "geometrically_explained": row["geometrically_explained"],
                    "unresolved": row["unresolved"],
                    "category_counts": row["category_counts"],
                },
                sort_keys=True,
            )
        )

    args.games_output.parent.mkdir(parents=True, exist_ok=True)
    with args.games_output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    stats = aggregate_movement_differential_games(rows, failed_game_ids=failures)
    args.stats_output.parent.mkdir(parents=True, exist_ok=True)
    args.stats_output.write_text(
        json.dumps(stats, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("===== MOVE MOST GEOMETRY DIFFERENTIAL SUMMARY =====")
    print(f"games_indexed:            {stats['games_indexed']}")
    print(f"games_failed:             {stats['games_failed']}")
    print(f"settings_hashes:          {stats['settings_hashes']}")
    for key in (
        "snapshots",
        "valid_turn_pairs",
        "skipped_turn_pairs",
        "geometry_ready",
        "classified_context",
        "move_most_candidates",
        "evaluated_move_most",
        "geometrically_explained",
        "unresolved",
    ):
        print(f"{key + ':':27} {stats['totals'].get(key, 0)}")
    print(f"excluded_intent_counts:   {stats['excluded_intent_counts']}")
    print("category_counts:")
    for category, count in sorted(
        stats["category_counts"].items(),
        key=lambda item: (-item[1], item[0]),
    ):
        print(f"  {category}: {count}")
    print("unresolved_hull_counts_top:")
    for hull_id, count in sorted(
        stats["unresolved_hull_counts"].items(),
        key=lambda item: (-item[1], int(item[0])),
    )[:30]:
        print(f"  hull={hull_id}: {count}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
