from __future__ import annotations

import argparse
import json
from pathlib import Path

from .indexer import CorpusIndexError, load_manifest_jsonl
from .movement_residual_profile import (
    aggregate_profile_rows,
    extract_hull_catalog,
    profile_residual_hulls,
)
from .normalizer import CorpusNormalizationError, load_archive_snapshots


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Profile unresolved Move Most residuals by category and the historical "
            "per-game hull catalog embedded in cached .trn archives."
        )
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("validation/corpus/cache/loadall"),
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--games-output",
        type=Path,
        default=Path("validation/corpus/index/accounts-movement-residual-profile-games.jsonl"),
    )
    parser.add_argument(
        "--stats-output",
        type=Path,
        default=Path("validation/corpus/index/accounts-movement-residual-profile-stats.json"),
    )
    parser.add_argument("--top", type=int, default=50)
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
        path = args.cache_dir / f"game-{game_id}.zip"
        try:
            data = path.read_bytes()
            snapshots = load_archive_snapshots(data)
            profile = profile_residual_hulls(snapshots)
            catalog = extract_hull_catalog(data)
            used_ids = {
                int(key.rsplit("|", 1)[1])
                for key in profile["category_hull_counts"]
            }
            safe_catalog = {
                str(hull_id): dict(catalog.hulls[hull_id])
                for hull_id in sorted(used_ids)
                if hull_id in catalog.hulls
            }
            row = {
                "game_id": game_id,
                "settings_hash": str(manifest["settings_hash"]),
                "residual_unresolved": profile["residual_unresolved"],
                "category_hull_counts": profile["category_hull_counts"],
                "storm_status_category_hull_counts": profile["storm_status_category_hull_counts"],
                "catalog_consistent": catalog.consistent,
                "catalog_first_member": catalog.first_member,
                "catalog_last_member": catalog.last_member,
                "catalog_first_hash": catalog.first_hash,
                "catalog_last_hash": catalog.last_hash,
                "hull_catalog": safe_catalog,
            }
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

        rows.append(row)
        top_local = sorted(
            row["category_hull_counts"].items(),
            key=lambda item: (-item[1], item[0]),
        )[:5]
        print(json.dumps({
            "status": "ok",
            "position": position,
            "total": len(manifests),
            "game_id": game_id,
            "residual_unresolved": row["residual_unresolved"],
            "catalog_consistent": row["catalog_consistent"],
            "top_category_hulls": top_local,
        }, sort_keys=True))

    args.games_output.parent.mkdir(parents=True, exist_ok=True)
    with args.games_output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")

    stats = aggregate_profile_rows(rows)
    stats["games_failed"] = len(failures)
    stats["failed_game_ids"] = sorted(set(failures))
    args.stats_output.parent.mkdir(parents=True, exist_ok=True)
    args.stats_output.write_text(
        json.dumps(stats, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("===== MOVE MOST RESIDUAL HULL PROFILE =====")
    print(f"games_indexed:        {stats['games']}")
    print(f"games_failed:         {stats['games_failed']}")
    print(f"residual_unresolved:  {stats['residual_unresolved']}")
    print(f"catalog_consistency:  {stats['catalog_consistency']}")
    print("top_category_hulls:")
    for item in stats["category_hull_name_counts"][: max(0, args.top)]:
        print(
            f"  {item['category']} | hull={item['hull_id']} | "
            f"name={item['hull_name']} | count={item['count']} | games={item['games']}"
        )

    print("top_hull_metadata:")
    seen: set[tuple[int, str]] = set()
    for item in stats["category_hull_name_counts"]:
        key = (item["hull_id"], item["hull_name"])
        if key in seen:
            continue
        seen.add(key)
        descriptor = None
        for row in rows:
            candidate = row.get("hull_catalog", {}).get(str(item["hull_id"]))
            if isinstance(candidate, dict) and candidate.get("name") == item["hull_name"]:
                descriptor = candidate
                break
        print(f"  hull={item['hull_id']} name={item['hull_name']}: {json.dumps(descriptor or {}, sort_keys=True, ensure_ascii=False)}")
        if len(seen) >= 30:
            break

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
