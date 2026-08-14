from __future__ import annotations

import argparse
import json
from pathlib import Path

from .field_corpus import aggregate_field_games, summarize_field_game
from .indexer import CorpusIndexError, load_manifest_jsonl
from .normalizer import CorpusNormalizationError, load_archive_snapshots


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate privacy-safe field-level reconstruction quality across "
            "cached finished-game /loadall archives."
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
        default=Path("validation/corpus/index/accounts-field-games.jsonl"),
    )
    parser.add_argument(
        "--stats-output",
        type=Path,
        default=Path("validation/corpus/index/accounts-field-stats.json"),
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
            row = summarize_field_game(
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
                    "snapshots": row["snapshots"],
                    "entities": row["entities"],
                    "resolved_fields": row["resolved_fields"],
                    "total_fields": row["total_fields"],
                    "current_conflict": row["field_status_counts"].get("current_conflict", 0),
                    "no_current": row["field_status_counts"].get("no_current", 0),
                    "entities_with_conflicts": row["entities_with_conflicts"],
                },
                sort_keys=True,
            )
        )

    args.games_output.parent.mkdir(parents=True, exist_ok=True)
    with args.games_output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    stats = aggregate_field_games(rows, failed_game_ids=failures)
    args.stats_output.parent.mkdir(parents=True, exist_ok=True)
    args.stats_output.write_text(
        json.dumps(stats, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("===== FIELD CORPUS SUMMARY =====")
    print(f"games_indexed:       {stats['games_indexed']}")
    print(f"games_failed:        {stats['games_failed']}")
    print(f"settings_hashes:     {stats['settings_hashes']}")
    print(f"snapshots:           {stats['totals'].get('snapshots', 0)}")
    print(f"entities:            {stats['totals'].get('entities', 0)}")
    print(f"resolved_fields:     {stats['totals'].get('resolved_fields', 0)}")
    print(f"total_fields:        {stats['totals'].get('total_fields', 0)}")
    print(f"field_status_counts: {stats['field_status_counts']}")
    print(
        "entities_with_conflicts: "
        f"{stats['totals'].get('entities_with_conflicts', 0)}"
    )
    print(
        "entities_with_unresolved_dynamic: "
        f"{stats['totals'].get('entities_with_unresolved_dynamic', 0)}"
    )
    print("conflict_field_counts:")
    for key, count in sorted(
        stats["conflict_field_counts"].items(),
        key=lambda item: (-item[1], item[0]),
    ):
        print(f"  {key}: {count}")
    print("unresolved_dynamic_field_counts_top:")
    for key, count in sorted(
        stats["unresolved_dynamic_field_counts"].items(),
        key=lambda item: (-item[1], item[0]),
    )[:40]:
        print(f"  {key}: {count}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
