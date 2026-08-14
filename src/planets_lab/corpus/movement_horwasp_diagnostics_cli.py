from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from .indexer import CorpusIndexError, load_manifest_jsonl
from .movement_horwasp_diagnostics import diagnose_horwasp_residuals
from .normalizer import CorpusNormalizationError, load_archive_snapshots


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect privacy-safe wire-state fields for pod-like Horwasp hulls that remain "
            "unresolved after ordinary, tow, gravitonic, ion-storm and observed Chunnel filters."
        )
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=Path("validation/corpus/cache/loadall"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("validation/corpus/index/accounts-horwasp-residual-diagnostics.json"),
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
            row = diagnose_horwasp_residuals(
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
            "residual_after_chunnel": row["residual_after_chunnel"],
            "pod_like_residual": row["pod_like_residual"],
            "top_category_hulls": list(row["category_hull_counts"].items())[:8],
        }, sort_keys=True))

    category_hulls: Counter[str] = Counter()
    hull_names: dict[str, str | None] = {}
    raw_keys: dict[str, Counter[str]] = defaultdict(Counter)
    field_values: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    samples: list[dict] = []
    residual_after_chunnel = 0
    pod_like_residual = 0
    for row in rows:
        residual_after_chunnel += int(row["residual_after_chunnel"])
        pod_like_residual += int(row["pod_like_residual"])
        category_hulls.update({str(k): int(v) for k, v in row["category_hull_counts"].items()})
        hull_names.update({str(k): v for k, v in row["hull_names"].items()})
        for hull_id, counts in row["raw_key_counts"].items():
            raw_keys[str(hull_id)].update({str(k): int(v) for k, v in counts.items()})
        for hull_id, fields in row["interesting_field_values"].items():
            for field, values in fields.items():
                field_values[str(hull_id)][str(field)].update({str(k): int(v) for k, v in values.items()})
        samples.extend(row["samples"])

    output = {
        "games_indexed": len(rows),
        "games_failed": len(failures),
        "failed_game_ids": sorted(failures),
        "residual_after_chunnel": residual_after_chunnel,
        "pod_like_residual": pod_like_residual,
        "category_hull_counts": dict(sorted(category_hulls.items(), key=lambda item: (-item[1], item[0]))),
        "hull_names": dict(sorted(hull_names.items(), key=lambda item: int(item[0]))),
        "raw_key_counts": {
            hull_id: dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))
            for hull_id, counter in sorted(raw_keys.items(), key=lambda item: int(item[0]))
        },
        "interesting_field_values": {
            hull_id: {
                field: dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))
                for field, counter in sorted(fields.items())
            }
            for hull_id, fields in sorted(field_values.items(), key=lambda item: int(item[0]))
        },
        "samples": samples[: max(0, args.samples)],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("===== HORWASP RESIDUAL WIRE DIAGNOSTICS =====")
    print(f"games_indexed:          {output['games_indexed']}")
    print(f"games_failed:           {output['games_failed']}")
    print(f"residual_after_chunnel: {residual_after_chunnel}")
    print(f"pod_like_residual:      {pod_like_residual}")
    print("top_category_hulls:")
    for key, count in list(output["category_hull_counts"].items())[:30]:
        category, hull_id = key.rsplit("|", 1)
        print(f"  {category} | hull={hull_id} | name={hull_names.get(hull_id)} | count={count}")
    print("interesting_fields_by_hull:")
    for hull_id, fields in output["interesting_field_values"].items():
        name = hull_names.get(hull_id)
        print(f"  hull={hull_id} name={name}")
        for field, values in fields.items():
            top = list(values.items())[:12]
            print(f"    {field}: {top}")
    print("samples:")
    for sample in output["samples"]:
        print("  " + json.dumps(sample, sort_keys=True))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
