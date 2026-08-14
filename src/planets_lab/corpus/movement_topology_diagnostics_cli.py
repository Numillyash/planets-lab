from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .indexer import CorpusIndexError, load_manifest_jsonl
from .movement_topology_diagnostics import extract_map_topology, evaluate_sphere_geometry_effect
from .normalizer import CorpusNormalizationError, load_archive_snapshots


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect historical map topology and measure sphere-aware movement geometry closures."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--cache-dir", type=Path, default=Path("validation/corpus/cache/loadall")
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("validation/corpus/index/accounts-movement-topology-diagnostics.json"),
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
        path = args.cache_dir / f"game-{game_id}.zip"
        try:
            data = path.read_bytes()
            topology = extract_map_topology(data)
            row = {
                "game_id": game_id,
                "settings_hash": str(manifest["settings_hash"]),
                "sphere": topology.sphere,
                "mapwidth": topology.mapwidth,
                "mapheight": topology.mapheight,
                "mapshape": topology.mapshape,
                "topology_stable": topology.stable,
                "first_member": topology.first_member,
                "last_member": topology.last_member,
                "first_candidates": dict(topology.first_candidates),
                "last_candidates": dict(topology.last_candidates),
            }
            if topology.sphere is True and topology.mapwidth and topology.mapheight:
                snapshots = load_archive_snapshots(data)
                row["sphere_geometry"] = evaluate_sphere_geometry_effect(
                    snapshots,
                    width=topology.mapwidth,
                    height=topology.mapheight,
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
        rows.append(row)
        effect = row.get("sphere_geometry", {})
        print(json.dumps({
            "status": "ok",
            "position": position,
            "total": len(manifests),
            "game_id": game_id,
            "sphere": row["sphere"],
            "mapwidth": row["mapwidth"],
            "mapheight": row["mapheight"],
            "mapshape": row["mapshape"],
            "topology_stable": row["topology_stable"],
            "baseline_unresolved": effect.get("baseline_unresolved", 0),
            "sphere_explained": effect.get("sphere_explained", 0),
            "sphere_still_unresolved": effect.get("sphere_still_unresolved", 0),
        }, sort_keys=True))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "games_indexed": len(rows),
        "games_failed": len(failures),
        "failed_game_ids": sorted(failures),
        "rows": rows,
    }
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    sphere_games = [row for row in rows if row.get("sphere") is True]
    nonsphere_games = [row for row in rows if row.get("sphere") is False]
    unknown_games = [row for row in rows if row.get("sphere") is None]
    totals: Counter[str] = Counter()
    transitions: Counter[str] = Counter()
    hulls: Counter[str] = Counter()
    for row in sphere_games:
        effect = row.get("sphere_geometry", {})
        if not isinstance(effect, dict):
            continue
        for key in ("baseline_unresolved", "sphere_explained", "sphere_still_unresolved"):
            value = effect.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                totals[key] += value
        for key, value in effect.get("baseline_to_sphere_counts", {}).items():
            if isinstance(value, int) and not isinstance(value, bool):
                transitions[str(key)] += value
        for key, value in effect.get("sphere_explained_hull_counts", {}).items():
            if isinstance(value, int) and not isinstance(value, bool):
                hulls[str(key)] += value

    print("===== MOVEMENT MAP TOPOLOGY DIAGNOSTICS =====")
    print(f"games_indexed:          {len(rows)}")
    print(f"games_failed:           {len(failures)}")
    print(f"sphere_games:           {len(sphere_games)}")
    print(f"non_sphere_games:       {len(nonsphere_games)}")
    print(f"unknown_topology_games: {len(unknown_games)}")
    print("game_topologies:")
    for row in rows:
        print(
            f"  game={row['game_id']} sphere={row['sphere']} "
            f"size={row['mapwidth']}x{row['mapheight']} shape={row['mapshape']} "
            f"stable={row['topology_stable']}"
        )
    print(f"sphere_baseline_unresolved: {totals.get('baseline_unresolved', 0)}")
    print(f"sphere_geometry_explained:  {totals.get('sphere_explained', 0)}")
    print(f"sphere_still_unresolved:    {totals.get('sphere_still_unresolved', 0)}")
    print("baseline_to_sphere_counts:")
    for key, value in transitions.most_common(30):
        print(f"  {key}: {value}")
    print("sphere_explained_hulls_top:")
    for key, value in sorted(hulls.items(), key=lambda item: (-item[1], int(item[0])))[:30]:
        print(f"  hull={key}: {value}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
