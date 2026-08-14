from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from .indexer import CorpusIndexError, load_manifest_jsonl
from .movement_horwasp_trajectory import diagnose_horwasp_trajectories
from .normalizer import CorpusNormalizationError, load_archive_snapshots


def _merge_nested_counts(rows: list[dict], key: str) -> dict[str, dict[str, int]]:
    merged: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        data = row.get(key, {})
        if not isinstance(data, dict):
            continue
        for hull_id, counts in data.items():
            if not isinstance(counts, dict):
                continue
            merged[str(hull_id)].update({str(k): int(v) for k, v in counts.items()})
    return {
        hull_id: dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))
        for hull_id, counter in sorted(merged.items(), key=lambda item: int(item[0]))
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect topology-aware Horwasp Pod/Mite trajectory state after ordinary, tow, "
            "gravitonic, ion-storm and observed Chunnel filters."
        )
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=Path("validation/corpus/cache/loadall"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--samples", type=int, default=40)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("validation/corpus/index/accounts-horwasp-trajectory-diagnostics.json"),
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
    remaining_samples = max(0, args.samples)
    for position, manifest in enumerate(manifests, start=1):
        game_id = int(manifest["game_id"])
        archive_path = args.cache_dir / f"game-{game_id}.zip"
        try:
            archive_data = archive_path.read_bytes()
            snapshots = load_archive_snapshots(archive_data)
            row = diagnose_horwasp_trajectories(
                archive_data,
                snapshots,
                sample_limit=remaining_samples,
            )
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
        remaining_samples = max(0, remaining_samples - len(row["samples"]))
        row["game_id"] = game_id
        row["settings_hash"] = str(manifest["settings_hash"])
        rows.append(row)
        print(json.dumps({
            "status": "ok",
            "position": position,
            "total": len(manifests),
            "game_id": game_id,
            "pod_like_residual": row["pod_like_residual"],
            "topology": row["topology"],
            "mite_link_counts": row["mite_link_counts"],
        }, sort_keys=True))

    hull_names: dict[str, str | None] = {}
    samples: list[dict] = []
    pod_like_residual = 0
    mite_links: Counter[str] = Counter()
    for row in rows:
        pod_like_residual += int(row.get("pod_like_residual", 0))
        hull_names.update({str(k): v for k, v in row.get("hull_names", {}).items()})
        mite_links.update({str(k): int(v) for k, v in row.get("mite_link_counts", {}).items()})
        samples.extend(row.get("samples", []))

    output = {
        "games_indexed": len(rows),
        "games_failed": len(failures),
        "failed_game_ids": sorted(failures),
        "pod_like_residual": pod_like_residual,
        "hull_names": dict(sorted(hull_names.items(), key=lambda item: int(item[0]))),
        "distance_class_counts": _merge_nested_counts(rows, "distance_class_counts"),
        "warp_distance_counts": _merge_nested_counts(rows, "warp_distance_counts"),
        "launch_age_counts": _merge_nested_counts(rows, "launch_age_counts"),
        "heading_target_error_counts": _merge_nested_counts(rows, "heading_target_error_counts"),
        "heading_observed_error_counts": _merge_nested_counts(rows, "heading_observed_error_counts"),
        "waypoint_count_counts": _merge_nested_counts(rows, "waypoint_count_counts"),
        "waypoint_key_counts": _merge_nested_counts(rows, "waypoint_key_counts"),
        "mite_link_counts": dict(sorted(mite_links.items())),
        "samples": samples[: max(0, args.samples)],
        "game_topologies": [
            {"game_id": row["game_id"], **row["topology"]} for row in rows
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("===== HORWASP TRAJECTORY DIAGNOSTICS =====")
    print(f"games_indexed:     {output['games_indexed']}")
    print(f"games_failed:      {output['games_failed']}")
    print(f"pod_like_residual: {pod_like_residual}")
    print("mite_link_counts:")
    for key, count in output["mite_link_counts"].items():
        print(f"  {key}: {count}")
    print("distance_classes_by_hull:")
    for hull_id, counts in output["distance_class_counts"].items():
        print(f"  hull={hull_id} name={hull_names.get(hull_id)}: {counts}")
    print("launch_age_by_hull:")
    for hull_id, counts in output["launch_age_counts"].items():
        print(f"  hull={hull_id} name={hull_names.get(hull_id)}: {list(counts.items())[:15]}")
    print("heading_target_error_by_hull:")
    for hull_id, counts in output["heading_target_error_counts"].items():
        print(f"  hull={hull_id} name={hull_names.get(hull_id)}: {counts}")
    print("heading_observed_error_by_hull:")
    for hull_id, counts in output["heading_observed_error_counts"].items():
        print(f"  hull={hull_id} name={hull_names.get(hull_id)}: {counts}")
    print("waypoint_counts_by_hull:")
    for hull_id, counts in output["waypoint_count_counts"].items():
        print(f"  hull={hull_id} name={hull_names.get(hull_id)}: {counts}")
    print("waypoint_keys_by_hull:")
    for hull_id, counts in output["waypoint_key_counts"].items():
        print(f"  hull={hull_id} name={hull_names.get(hull_id)}: {list(counts.items())[:20]}")
    print("top_warp_distance_pairs_by_hull:")
    for hull_id, counts in output["warp_distance_counts"].items():
        print(f"  hull={hull_id} name={hull_names.get(hull_id)}: {list(counts.items())[:20]}")
    print("samples:")
    for sample in output["samples"]:
        print("  " + json.dumps(sample, sort_keys=True))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
