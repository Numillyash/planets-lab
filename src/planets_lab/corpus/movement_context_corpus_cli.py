from __future__ import annotations

import argparse
import json
from pathlib import Path

from .indexer import CorpusIndexError, load_manifest_jsonl
from .movement_context import (
    aggregate_movement_context_games,
    summarize_movement_context_game,
)
from .normalizer import CorpusNormalizationError, load_archive_snapshots


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Classify geometry-ready historical ship transitions by owner-perspective "
            "movement intent across cached finished-game /loadall archives. No network "
            "access is performed and raw order values are not written to derived indexes."
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
        default=Path("validation/corpus/index/accounts-movement-context-games.jsonl"),
    )
    parser.add_argument(
        "--stats-output",
        type=Path,
        default=Path("validation/corpus/index/accounts-movement-context-stats.json"),
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
            row = summarize_movement_context_game(
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
                    "classified": row["classified"],
                    "intent_counts": row["intent_counts"],
                    "issue_counts": row["issue_counts"],
                },
                sort_keys=True,
            )
        )

    args.games_output.parent.mkdir(parents=True, exist_ok=True)
    with args.games_output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    stats = aggregate_movement_context_games(rows, failed_game_ids=failures)
    args.stats_output.parent.mkdir(parents=True, exist_ok=True)
    args.stats_output.write_text(
        json.dumps(stats, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("===== OWNER-PERSPECTIVE MOVEMENT CONTEXT SUMMARY =====")
    print(f"games_indexed:       {stats['games_indexed']}")
    print(f"games_failed:        {stats['games_failed']}")
    print(f"settings_hashes:     {stats['settings_hashes']}")
    print(f"snapshots:           {stats['totals'].get('snapshots', 0)}")
    print(f"valid_turn_pairs:    {stats['totals'].get('valid_turn_pairs', 0)}")
    print(f"skipped_turn_pairs:  {stats['totals'].get('skipped_turn_pairs', 0)}")
    print(f"geometry_ready:      {stats['totals'].get('geometry_ready', 0)}")
    print(f"classified:          {stats['totals'].get('classified', 0)}")
    print(f"intent_counts:       {stats['intent_counts']}")
    print("issue_counts:")
    for issue, count in sorted(
        stats["issue_counts"].items(),
        key=lambda item: (-item[1], item[0]),
    ):
        print(f"  {issue}: {count}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
