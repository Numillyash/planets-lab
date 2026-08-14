from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from .indexer import CorpusIndexError, load_manifest_jsonl
from .movement_horwasp_state_linkage import diagnose_horwasp_state_linkage
from .normalizer import CorpusNormalizationError, load_archive_snapshots


def _merge_nested_counts(rows: list[dict], key: str) -> dict[str, dict[str, int]]:
    merged: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        data = row.get(key, {})
        if not isinstance(data, dict):
            continue
        for hull_id, counts in data.items():
            if isinstance(counts, dict):
                merged[str(hull_id)].update({str(k): int(v) for k, v in counts.items()})
    return {
        hull_id: dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))
        for hull_id, counter in sorted(merged.items(), key=lambda item: int(item[0]))
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect cross-turn authoritative Horwasp Pod/Mite wire-state linkage."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=Path("validation/corpus/cache/loadall"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--samples", type=int, default=40)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("validation/corpus/index/accounts-horwasp-state-linkage.json"),
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
            row = diagnose_horwasp_state_linkage(
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
        remaining_samples = max(0, remaining_samples - len(row.get("samples", [])))
        row["game_id"] = game_id
        row["settings_hash"] = str(manifest["settings_hash"])
        rows.append(row)
        print(json.dumps({
            "status": "ok",
            "position": position,
            "total": len(manifests),
            "game_id": game_id,
            "topology": row["topology"],
            "pod_transitions": sum(int(v) for v in row.get("transitions_by_hull", {}).values()),
            "mite_linkage_counts": row.get("mite_linkage_counts", {}),
        }, sort_keys=True))

    hull_names: dict[str, str | None] = {}
    transitions: Counter[str] = Counter()
    mite_counts: Counter[str] = Counter()
    samples: list[dict] = []
    for row in rows:
        hull_names.update({str(k): v for k, v in row.get("hull_names", {}).items()})
        transitions.update({str(k): int(v) for k, v in row.get("transitions_by_hull", {}).items()})
        mite_counts.update({str(k): int(v) for k, v in row.get("mite_linkage_counts", {}).items()})
        samples.extend(row.get("samples", []))

    nested_keys = (
        "heading_before_observed_error_counts",
        "heading_after_observed_error_counts",
        "heading_change_counts",
        "launch_turn_change_counts",
        "target_change_counts",
        "history_type_counts",
        "history_length_counts",
        "history_key_counts",
    )
    output = {
        "games_indexed": len(rows),
        "games_failed": len(failures),
        "failed_game_ids": sorted(failures),
        "hull_names": dict(sorted(hull_names.items(), key=lambda item: int(item[0]))),
        "transitions_by_hull": dict(sorted(transitions.items(), key=lambda item: int(item[0]))),
        "mite_linkage_counts": dict(sorted(mite_counts.items())),
        "samples": samples[: max(0, args.samples)],
        "game_topologies": [{"game_id": row["game_id"], **row["topology"]} for row in rows],
    }
    for key in nested_keys:
        output[key] = _merge_nested_counts(rows, key)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("===== HORWASP STATE LINKAGE DIAGNOSTICS =====")
    print(f"games_indexed: {output['games_indexed']}")
    print(f"games_failed:  {output['games_failed']}")
    print(f"pod_transitions: {sum(transitions.values())}")
    print("transitions_by_hull:")
    for hull_id, count in output["transitions_by_hull"].items():
        print(f"  hull={hull_id} name={hull_names.get(hull_id)}: {count}")
    print("mite_linkage_counts:")
    for key, count in output["mite_linkage_counts"].items():
        print(f"  {key}: {count}")
    print("heading_before_vs_observed:")
    for hull_id, counts in output["heading_before_observed_error_counts"].items():
        print(f"  hull={hull_id} name={hull_names.get(hull_id)}: {counts}")
    print("heading_after_vs_observed:")
    for hull_id, counts in output["heading_after_observed_error_counts"].items():
        print(f"  hull={hull_id} name={hull_names.get(hull_id)}: {counts}")
    print("state_change_counts:")
    for hull_id in sorted(output["transitions_by_hull"], key=int):
        print(
            f"  hull={hull_id} name={hull_names.get(hull_id)} "
            f"heading={output['heading_change_counts'].get(hull_id, {})} "
            f"turn={output['launch_turn_change_counts'].get(hull_id, {})} "
            f"target={output['target_change_counts'].get(hull_id, {})}"
        )
    print("history_shapes:")
    for hull_id, counts in output["history_type_counts"].items():
        print(
            f"  hull={hull_id} name={hull_names.get(hull_id)} "
            f"types={counts} lengths={list(output['history_length_counts'].get(hull_id, {}).items())[:12]} "
            f"keys={list(output['history_key_counts'].get(hull_id, {}).items())[:20]}"
        )
    print("samples:")
    for sample in output["samples"]:
        print("  " + json.dumps(sample, sort_keys=True))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
