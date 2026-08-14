from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .indexer import CorpusIndexError, load_manifest_jsonl
from .movement_horwasp_ballistic_context import (
    MOVEMENT_HORWASP_BALLISTIC_STATS_SCHEMA,
    evaluate_horwasp_ballistic_context,
)
from .normalizer import CorpusNormalizationError, load_archive_snapshots


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Measure topology-aware Horwasp ballistic movement closure after ordinary, tow, "
            "gravitonic, ion-storm and observed Chunnel filters."
        )
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=Path("validation/corpus/cache/loadall"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--games-output",
        type=Path,
        default=Path("validation/corpus/index/accounts-horwasp-ballistic-games.jsonl"),
    )
    parser.add_argument(
        "--stats-output",
        type=Path,
        default=Path("validation/corpus/index/accounts-horwasp-ballistic-stats.json"),
    )
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
            row = evaluate_horwasp_ballistic_context(archive_data, snapshots)
        except (OSError, ValueError, AssertionError, CorpusNormalizationError) as exc:
            failures.append(game_id)
            print(json.dumps({
                "status": "failed",
                "position": position,
                "total": len(manifests),
                "game_id": game_id,
                "error": f"{type(exc).__name__}: {exc}",
            }, sort_keys=True))
            continue
        row["game_id"] = game_id
        row["settings_hash"] = str(manifest["settings_hash"])
        rows.append(row)
        print(json.dumps({
            "status": "ok",
            "position": position,
            "total": len(manifests),
            "game_id": game_id,
            "residual_before": row["residual_before"],
            "ballistic_candidates": row["ballistic_candidates"],
            "mite_residual": row["mite_residual"],
            "strong_explained": row["strong_explained"],
            "observed_context_explained": row["observed_context_explained"],
            "ballistic_unresolved": row["ballistic_unresolved"],
        }, sort_keys=True))

    categories: Counter[str] = Counter()
    explained_hulls: Counter[str] = Counter()
    unresolved_hulls: Counter[str] = Counter()
    totals = Counter()
    settings_hashes: set[str] = set()
    for row in rows:
        settings_hashes.add(str(row["settings_hash"]))
        for key in (
            "residual_before",
            "ballistic_candidates",
            "mite_residual",
            "strong_explained",
            "observed_context_explained",
            "ballistic_unresolved",
            "residual_after_strong",
            "residual_after_observed",
        ):
            totals[key] += int(row.get(key, 0))
        categories.update({str(k): int(v) for k, v in row.get("category_counts", {}).items()})
        explained_hulls.update({str(k): int(v) for k, v in row.get("explained_hull_counts", {}).items()})
        unresolved_hulls.update({str(k): int(v) for k, v in row.get("unresolved_hull_counts", {}).items()})

    stats = {
        "schema": MOVEMENT_HORWASP_BALLISTIC_STATS_SCHEMA,
        "games_indexed": len(rows),
        "games_failed": len(failures),
        "failed_game_ids": sorted(failures),
        "settings_hashes": len(settings_hashes),
        **{key: int(value) for key, value in totals.items()},
        "category_counts": dict(sorted(categories.items(), key=lambda item: (-item[1], item[0]))),
        "explained_hull_counts": dict(sorted(explained_hulls.items(), key=lambda item: (-item[1], int(item[0])))),
        "unresolved_hull_counts": dict(sorted(unresolved_hulls.items(), key=lambda item: (-item[1], int(item[0])))),
    }

    args.games_output.parent.mkdir(parents=True, exist_ok=True)
    args.games_output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    args.stats_output.parent.mkdir(parents=True, exist_ok=True)
    args.stats_output.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("===== HORWASP BALLISTIC RESIDUAL SUMMARY =====")
    print(f"games_indexed:              {stats['games_indexed']}")
    print(f"games_failed:               {stats['games_failed']}")
    print(f"settings_hashes:            {stats['settings_hashes']}")
    print(f"residual_before:            {stats.get('residual_before', 0)}")
    print(f"ballistic_candidates:       {stats.get('ballistic_candidates', 0)}")
    print(f"mite_residual:              {stats.get('mite_residual', 0)}")
    print(f"strong_explained:           {stats.get('strong_explained', 0)}")
    print(f"observed_context_explained: {stats.get('observed_context_explained', 0)}")
    print(f"ballistic_unresolved:       {stats.get('ballistic_unresolved', 0)}")
    print(f"residual_after_strong:      {stats.get('residual_after_strong', 0)}")
    print(f"residual_after_observed:    {stats.get('residual_after_observed', 0)}")
    print("category_counts:")
    for key, count in stats["category_counts"].items():
        print(f"  {key}: {count}")
    print("explained_hulls_top:")
    for hull_id, count in list(stats["explained_hull_counts"].items())[:30]:
        print(f"  hull={hull_id}: {count}")
    print("unresolved_hulls_top:")
    for hull_id, count in list(stats["unresolved_hull_counts"].items())[:30]:
        print(f"  hull={hull_id}: {count}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
