from __future__ import annotations

import argparse
import json
from pathlib import Path

from .indexer import CorpusIndexError, load_manifest_jsonl
from .movement_residual_context import (
    aggregate_movement_residual_context_games,
    summarize_movement_residual_context_game,
)
from .normalizer import CorpusNormalizationError, load_archive_snapshots


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Classify unresolved Move Most movement geometry using observed tow-target, "
            "gravitonic, and resolved ion-storm context across cached finished games."
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
        default=Path("validation/corpus/index/accounts-movement-residual-context-games.jsonl"),
    )
    parser.add_argument(
        "--stats-output",
        type=Path,
        default=Path("validation/corpus/index/accounts-movement-residual-context-stats.json"),
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
            row = summarize_movement_residual_context_game(
                game_id=game_id,
                settings_hash=str(manifest["settings_hash"]),
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
                    "move_most_candidates": row["move_most_candidates"],
                    "baseline_unresolved": row["baseline_unresolved"],
                    "context_explained": row["context_explained"],
                    "residual_unresolved": row["residual_unresolved"],
                    "context_counts": row["context_counts"],
                },
                sort_keys=True,
            )
        )

    args.games_output.parent.mkdir(parents=True, exist_ok=True)
    with args.games_output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    stats = aggregate_movement_residual_context_games(rows, failed_game_ids=failures)
    args.stats_output.parent.mkdir(parents=True, exist_ok=True)
    args.stats_output.write_text(
        json.dumps(stats, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    totals = stats["totals"]
    print("===== MOVE MOST RESIDUAL CONTEXT SUMMARY =====")
    print(f"games_indexed:        {stats['games_indexed']}")
    print(f"games_failed:         {stats['games_failed']}")
    print(f"settings_hashes:      {stats['settings_hashes']}")
    print(f"snapshots:            {totals.get('snapshots', 0)}")
    print(f"valid_turn_pairs:     {totals.get('valid_turn_pairs', 0)}")
    print(f"skipped_turn_pairs:   {totals.get('skipped_turn_pairs', 0)}")
    print(f"move_most_candidates: {totals.get('move_most_candidates', 0)}")
    print(f"baseline_explained:   {totals.get('baseline_explained', 0)}")
    print(f"baseline_unresolved:  {totals.get('baseline_unresolved', 0)}")
    print(f"context_explained:    {totals.get('context_explained', 0)}")
    print(f"residual_unresolved:  {totals.get('residual_unresolved', 0)}")
    print("context_counts:")
    for key, count in sorted(stats["context_counts"].items(), key=lambda item: (-item[1], item[0])):
        print(f"  {key}: {count}")
    print("residual_category_counts:")
    for key, count in sorted(stats["residual_category_counts"].items(), key=lambda item: (-item[1], item[0])):
        print(f"  {key}: {count}")
    print("storm_context_counts:")
    for key, count in sorted(stats["storm_context_counts"].items(), key=lambda item: (-item[1], item[0])):
        print(f"  {key}: {count}")
    print("tow_context_counts:")
    for key, count in sorted(stats["tow_context_counts"].items(), key=lambda item: (-item[1], item[0])):
        print(f"  {key}: {count}")
    print("residual_hull_counts_top:")
    for key, count in sorted(
        stats["residual_hull_counts"].items(),
        key=lambda item: (-item[1], int(item[0])),
    )[:40]:
        print(f"  hull={key}: {count}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
