from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from combat_public_capture_o_layer_probe import SCHEMA


MERGED_SCHEMA = "planets-lab.combat-public-capture-o-layer-probe-merged.v1"


def merge_parts(parts: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not parts:
        raise ValueError("no O-layer part reports found")

    counts: Counter[str] = Counter()
    observations: list[dict[str, Any]] = []
    per_game: list[dict[str, Any]] = []
    scanned_game_ids: set[int] = set()
    partitions: set[str] = set()

    for part in parts:
        if part.get("schema") != SCHEMA:
            raise ValueError(f"unexpected part schema: {part.get('schema')!r}")
        partition = part.get("partition")
        if partition not in {"discovery", "heldout"}:
            raise ValueError(f"unexpected part partition: {partition!r}")
        partitions.add(str(partition))
        part_summary = part.get("summary")
        if not isinstance(part_summary, Mapping):
            raise ValueError("part summary missing")
        part_counts = part_summary.get("counts")
        if not isinstance(part_counts, Mapping):
            raise ValueError("part counts missing")
        for key, value in part_counts.items():
            if isinstance(value, int) and not isinstance(value, bool):
                counts[str(key)] += int(value)

        part_observations = part.get("observations")
        if not isinstance(part_observations, list):
            raise ValueError("part observations missing")
        observations.extend(
            dict(row) for row in part_observations if isinstance(row, Mapping)
        )

        for value in part.get("scanned_game_ids", []):
            if isinstance(value, int) and not isinstance(value, bool):
                scanned_game_ids.add(int(value))
        probe_ids = [
            int(value)
            for value in part.get("probe_game_ids", [])
            if isinstance(value, int) and not isinstance(value, bool)
        ]
        per_game.append(
            {
                "probe_game_ids": probe_ids,
                "counts": dict(sorted(
                    (str(key), int(value))
                    for key, value in part_counts.items()
                    if isinstance(value, int) and not isinstance(value, bool)
                )),
            }
        )

    if len(partitions) != 1:
        raise ValueError(f"mixed O-layer partitions: {sorted(partitions)}")
    partition = next(iter(partitions))

    observations.sort(
        key=lambda row: (
            int(row.get("game_id", 0)),
            int(row.get("turn", 0)),
            int(row.get("capture_vcr_id", 0)),
            int(row.get("captured_ship_id", 0)),
        )
    )
    per_game.sort(key=lambda row: tuple(row["probe_game_ids"]))

    return {
        "schema": MERGED_SCHEMA,
        "evidence_status": (
            "DISCOVERY_ONLY_FROZEN_SIDE_CANDIDATE"
            if partition == "discovery"
            else "HELDOUT_VALIDATION_FROZEN_SIDE_CANDIDATE"
        ),
        "partition": partition,
        "scanned_game_ids": sorted(scanned_game_ids),
        "summary": {
            "counts": dict(sorted(counts.items())),
            "game_passes": len(parts),
            "per_game": per_game,
        },
        "observations": observations,
        "evidence_boundary": (
            f"Merged from process-isolated {partition} per-game O-layer "
            "reports. Each game is evaluated in a fresh Python/container process "
            "to bound peak memory. The external cursor remains reference-only. "
            "The held-out path validates the already frozen side candidate."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge per-game public O-layer reports.")
    parser.add_argument("--parts-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = sorted(args.parts_dir.glob("game-*.json"))
    if not paths:
        print(f"ERROR: no part reports in {args.parts_dir}")
        return 2
    try:
        parts = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
        report = merge_parts(parts)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    counts = report["summary"]["counts"]
    print(
        "===== PUBLIC CAPTURE O-LAYER "
        f"{str(report['partition']).upper()}: MERGED ====="
    )
    print(f"game_passes:          {report['summary']['game_passes']}")
    print(f"capture_ship_rows:    {counts.get('capture_ship_rows', 0)}")
    print(f"adjacent_rows:        {counts.get('adjacent_rows', 0)}")
    print(f"resolved:             {counts.get('status:resolved', 0)}")
    print(f"not_comparable:       {counts.get('status:not_comparable', 0)}")
    print(f"unresolved:           {counts.get('status:unresolved', 0)}")
    print(f"O pair reachable:     {counts.get('o_pair_reachable', 0)}")
    print(
        "  factual LEFT/RIGHT: "
        f"{counts.get('o_pair_reachable:left', 0)} / "
        f"{counts.get('o_pair_reachable:right', 0)}"
    )
    print(f"O pair not reachable: {counts.get('o_pair_not_reachable', 0)}")
    print(
        "  factual LEFT/RIGHT: "
        f"{counts.get('o_pair_not_reachable:left', 0)} / "
        f"{counts.get('o_pair_not_reachable:right', 0)}"
    )
    print(f"external O exact:     {counts.get('external_o_exact', 0)}")
    print(f"external O mismatch:  {counts.get('external_o_mismatch', 0)}")
    print(f"split candidate exact:{counts.get('split_candidate_exact', 0):>4}")
    print(f"split candidate mismatch:{counts.get('split_candidate_mismatch', 0):>2}")
    print(
        "resolved dependency qualified/blocked: "
        f"{counts.get('resolved_dependency:qualified', 0)} / "
        f"{counts.get('resolved_dependency:blocked', 0)}"
    )
    print(
        "split exact qualified/blocked: "
        f"{counts.get('split_candidate_exact:qualified', 0)} / "
        f"{counts.get('split_candidate_exact:blocked', 0)}"
    )
    print(
        "split mismatch qualified/blocked: "
        f"{counts.get('split_candidate_mismatch:qualified', 0)} / "
        f"{counts.get('split_candidate_mismatch:blocked', 0)}"
    )
    print(
        "identity-anchored O reachable/not: "
        f"{counts.get('identity_anchored_o_pair_reachable', 0)} / "
        f"{counts.get('identity_anchored_o_pair_not_reachable', 0)}"
    )
    print(
        "identity-anchored split exact/mismatch/unresolved: "
        f"{counts.get('identity_anchored_split_exact', 0)} / "
        f"{counts.get('identity_anchored_split_mismatch', 0)} / "
        f"{counts.get('identity_anchored_split_unresolved', 0)}"
    )
    print(
        "factual opponent active T/F/U: "
        f"{counts.get('active_dependency:factual_opponent_active:true', 0)} / "
        f"{counts.get('active_dependency:factual_opponent_active:false', 0)} / "
        f"{counts.get('active_dependency:factual_opponent_active:unknown', 0)}"
    )
    print(
        "strict permission T/F/U: "
        f"{counts.get('active_dependency:factual_opponent_strict_permission:true', 0)} / "
        f"{counts.get('active_dependency:factual_opponent_strict_permission:false', 0)} / "
        f"{counts.get('active_dependency:factual_opponent_strict_permission:unknown', 0)}"
    )
    for label, key in (
        ("blocked site predicted T/F/U", "factual_opponent_site_predicted"),
        ("blocked history anchored T/F/U", "factual_opponent_history_anchored"),
        ("blocked removed before next T/F/U", "factual_opponent_removed_before_next"),
        ("blocked owner changed T/F/U", "factual_opponent_owner_changed_before_next"),
    ):
        print(
            f"{label}: "
            f"{counts.get(f'blocked_dependency:{key}:true', 0)} / "
            f"{counts.get(f'blocked_dependency:{key}:false', 0)} / "
            f"{counts.get(f'blocked_dependency:{key}:unknown', 0)}"
        )
    print(f"output:               {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
