from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import combat_host_post_capture_opponent_audit as opponent_module
from combat_host_mixed_ship_planet_queue_batch_audit import (
    _load_groups,
    _planet_pair,
    _resolved_owner_at_turn,
    _shape,
)
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
)


SCHEMA = "planets-lab.combat-host-planet-ownership-timeline-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 80


def _owner_at(
    groups: Mapping[Any, Any],
    *,
    turn: int,
    entity_id: int,
) -> int | None:
    owner = _resolved_owner_at_turn(groups, turn=turn, entity_id=entity_id)
    return owner if isinstance(owner, int) and not isinstance(owner, bool) else None


def run(args: argparse.Namespace) -> dict[str, Any]:
    vcrs, payload_conflicts = opponent_module._vcr_index(args.archive_dir)
    contexts: dict[int, tuple[Mapping[Any, Any], Mapping[Any, Any], Mapping[int, int]]] = {}
    counts: Counter[str] = Counter()
    unique_timelines: dict[tuple[int, int, int], dict[str, Any]] = {}
    changed_examples: list[dict[str, Any]] = []

    for (game_id, battle_turn, vcr_id), raw_vcr in sorted(vcrs.items()):
        if game_id == SPECIAL_GAME_ID or _shape(raw_vcr) != "ship_vs_planet":
            continue
        pair = _planet_pair(raw_vcr)
        if pair is None:
            counts["pair_projection_unresolved"] += 1
            continue
        ship, planet = pair
        ship_owner = int(ship["owner_id"])
        planet_id = int(planet["object_id"])
        vcr_owner = int(planet["owner_id"])

        if game_id not in contexts:
            contexts[game_id] = _load_groups(
                archive_dir=args.archive_dir,
                prepared_dir=args.prepared_dir,
                game_id=game_id,
            )
        _ship_groups, planet_groups, race_owner_map = contexts[game_id]

        tminus1_owner = _owner_at(
            planet_groups,
            turn=battle_turn - 1,
            entity_id=planet_id,
        )
        current_owner = _owner_at(
            planet_groups,
            turn=battle_turn,
            entity_id=planet_id,
        )
        race_id = planet.get("race_id")
        race_mapped_owner = (
            race_owner_map.get(int(race_id))
            if isinstance(race_id, int)
            else None
        )

        counts["ordinary_ship_vs_planet_vcrs"] += 1
        if vcr_owner != ship_owner:
            counts["vcr_defender_foreign_to_ship"] += 1
        else:
            counts["vcr_same_owner_anomaly"] += 1
        if race_mapped_owner == vcr_owner:
            counts["vcr_race_owner_exact"] += 1
        elif race_mapped_owner is None:
            counts["vcr_race_owner_unresolved"] += 1
        else:
            counts["vcr_race_owner_mismatch"] += 1

        if tminus1_owner is None:
            counts["tminus1_owner_unresolved"] += 1
            precombat_class = "tminus1_unresolved"
        elif tminus1_owner == vcr_owner:
            counts["precombat_owner_unchanged"] += 1
            precombat_class = "unchanged"
        else:
            counts["precombat_owner_changed"] += 1
            precombat_class = "changed"
            if tminus1_owner == ship_owner:
                counts["precombat_changed_from_attacker_to_defender"] += 1
            elif vcr_owner == ship_owner:
                counts["precombat_changed_to_attacker"] += 1
            else:
                counts["precombat_changed_between_third_parties"] += 1

        if current_owner is None:
            counts["current_owner_unresolved"] += 1
            postcombat_class = "current_unresolved"
        elif current_owner == vcr_owner:
            counts["postcombat_defender_retained"] += 1
            postcombat_class = "defender_retained"
        elif current_owner == ship_owner:
            counts["postcombat_attacker_owns_planet"] += 1
            postcombat_class = "attacker_owns"
        elif current_owner == 0:
            counts["postcombat_neutral"] += 1
            postcombat_class = "neutral"
        else:
            counts["postcombat_other_owner"] += 1
            postcombat_class = "other_owner"

        timeline_key = (game_id, battle_turn, planet_id)
        timeline = unique_timelines.setdefault(
            timeline_key,
            {
                "game_id": game_id,
                "battle_turn": battle_turn,
                "planet_id": planet_id,
                "tminus1_owner_id": tminus1_owner,
                "vcr_defender_owner_id": vcr_owner,
                "vcr_planet_race_id": race_id,
                "race_mapped_owner_id": race_mapped_owner,
                "current_owner_id": current_owner,
                "ship_owner_ids": set(),
                "vcr_ids": [],
                "precombat_class": precombat_class,
                "postcombat_class": postcombat_class,
            },
        )
        timeline["ship_owner_ids"].add(ship_owner)
        timeline["vcr_ids"].append(vcr_id)

    for timeline in unique_timelines.values():
        counts["unique_planet_turn_timelines"] += 1
        if timeline["precombat_class"] == "changed":
            counts["unique_precombat_owner_changed"] += 1
            if timeline["tminus1_owner_id"] in timeline["ship_owner_ids"]:
                counts["unique_changed_from_attacker_to_defender"] += 1
            if len(changed_examples) < args.example_limit:
                changed_examples.append(
                    {
                        **{
                            key: value
                            for key, value in timeline.items()
                            if key not in {"ship_owner_ids", "vcr_ids"}
                        },
                        "ship_owner_ids": sorted(timeline["ship_owner_ids"]),
                        "vcr_ids": sorted(timeline["vcr_ids"]),
                    }
                )

    acceptance = {
        "ordinary_planet_population_present": counts["ordinary_ship_vs_planet_vcrs"] > 0,
        "payload_conflicts_absent": payload_conflicts == 0,
        "pair_projection_resolved": counts["pair_projection_unresolved"] == 0,
        "all_vcr_defenders_foreign": counts["vcr_same_owner_anomaly"] == 0,
        "vcr_race_owner_consistent": counts["vcr_race_owner_mismatch"] == 0,
        "timeline_population_present": counts["unique_planet_turn_timelines"] > 0,
    }
    acceptance["ownership_timeline_gate_passed"] = all(acceptance.values())

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "special_game_591478_excluded": True,
            "payload_conflicts": payload_conflicts,
            "counts": dict(sorted(counts.items())),
            "acceptance": acceptance,
        },
        "changed_examples": changed_examples,
        "evidence_boundary": (
            "Factual VCR defender ownership is comparator/attribution evidence, "
            "not a production precombat input. T is post-Host and is used only "
            "to classify the later ownership outcome. This audit measures the "
            "size and shape of ownership changes that production must reconstruct "
            "before ship-vs-planet engagement selection."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit T-1 -> VCR defender -> T planet ownership timelines."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT PLANET OWNERSHIP TIMELINE =====")
    print("summary:", report["summary"])
    if report["changed_examples"]:
        print()
        print("PRECOMBAT OWNER-CHANGE EXAMPLES:")
        for row in report["changed_examples"]:
            print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("output:", args.output)
    print(
        "NOTE: VCR/T ownership is attribution evidence only; "
        "production precombat ownership reconstruction remains separate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
