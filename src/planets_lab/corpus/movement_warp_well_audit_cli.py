from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .indexer import CorpusIndexError, load_manifest_jsonl
from .movement_warp_well_audit import audit_movement_warp_wells, extract_nowarpwells
from .normalizer import CorpusNormalizationError, load_archive_snapshots


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit historical Move Most warp-well matches against raw "
            "settings.nowarpwells and planet.debrisdisk state."
        )
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("validation/corpus/cache/loadall"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("validation/corpus/index/accounts-movement-warp-well-audit.json"),
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
    totals: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    debris_values: Counter[str] = Counter()

    for position, manifest in enumerate(manifests, start=1):
        game_id = int(manifest["game_id"])
        archive_path = args.cache_dir / f"game-{game_id}.zip"
        try:
            data = archive_path.read_bytes()
            snapshots = load_archive_snapshots(data)
            nowarpwells, setting_status = extract_nowarpwells(data)
            summary = audit_movement_warp_wells(
                snapshots,
                nowarpwells=nowarpwells,
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

        row = {
            "game_id": game_id,
            "settings_hash": str(manifest["settings_hash"]),
            "nowarpwells": nowarpwells,
            "setting_status": setting_status,
            "move_most_candidates": summary.move_most_candidates,
            "warp_well_matches": summary.warp_well_matches,
            "valid_ordinary_planet_matches": summary.valid_ordinary_planet_matches,
            "invalid_debris_planet_matches": summary.invalid_debris_planet_matches,
            "disabled_warp_well_matches": summary.disabled_warp_well_matches,
            "unknown_context_matches": summary.unknown_context_matches,
            "category_counts": dict(summary.category_counts),
            "debris_value_counts": {
                str(key): value for key, value in summary.debris_value_counts.items()
            },
        }
        rows.append(row)

        for key in (
            "move_most_candidates",
            "warp_well_matches",
            "valid_ordinary_planet_matches",
            "invalid_debris_planet_matches",
            "disabled_warp_well_matches",
            "unknown_context_matches",
        ):
            totals[key] += int(row[key])
        categories.update(row["category_counts"])
        debris_values.update(row["debris_value_counts"])

        print(
            json.dumps(
                {
                    "status": "ok",
                    "position": position,
                    "total": len(manifests),
                    "game_id": game_id,
                    "nowarpwells": nowarpwells,
                    "warp_well_matches": summary.warp_well_matches,
                    "valid": summary.valid_ordinary_planet_matches,
                    "invalid_debris": summary.invalid_debris_planet_matches,
                    "disabled": summary.disabled_warp_well_matches,
                    "unknown": summary.unknown_context_matches,
                },
                sort_keys=True,
            )
        )

    result = {
        "games_indexed": len(rows),
        "games_failed": len(failures),
        "failed_game_ids": sorted(set(failures)),
        "totals": dict(sorted(totals.items())),
        "category_counts": dict(sorted(categories.items())),
        "debris_value_counts": dict(
            sorted(debris_values.items(), key=lambda item: int(item[0]))
        ),
        "games": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("===== HISTORICAL WARP WELL AUDIT =====")
    print(f"games_indexed:                  {result['games_indexed']}")
    print(f"games_failed:                   {result['games_failed']}")
    for key in (
        "move_most_candidates",
        "warp_well_matches",
        "valid_ordinary_planet_matches",
        "invalid_debris_planet_matches",
        "disabled_warp_well_matches",
        "unknown_context_matches",
    ):
        print(f"{key + ':':32} {totals.get(key, 0)}")
    print("category_counts:")
    for category, count in sorted(categories.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {category}: {count}")
    print("debris_value_counts:")
    for value, count in sorted(debris_values.items(), key=lambda item: int(item[0])):
        print(f"  debrisdisk={value}: {count}")
    print("games_with_invalid_or_unknown:")
    for row in rows:
        if (
            row["invalid_debris_planet_matches"]
            or row["disabled_warp_well_matches"]
            or row["unknown_context_matches"]
        ):
            print(
                "  "
                f"game={row['game_id']} "
                f"matches={row['warp_well_matches']} "
                f"valid={row['valid_ordinary_planet_matches']} "
                f"invalid_debris={row['invalid_debris_planet_matches']} "
                f"disabled={row['disabled_warp_well_matches']} "
                f"unknown={row['unknown_context_matches']}"
            )

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
