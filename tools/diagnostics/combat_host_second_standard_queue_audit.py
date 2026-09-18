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

from planets_lab.rules.combat.host_queue import (
    StandardQueueState,
    select_next_plain_standard,
)
from planets_lab.rules.combat.queue import InitialStandardPairInput
from planets_lab.rules.combat.selection import (
    ShipCombatSideInput,
    decide_ship_combat_pair,
)

import combat_host_repeated_pair_side_population_audit as repeated_module
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR


SCHEMA = "planets-lab.combat-host-second-standard-queue-audit.v1"


def _intish(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _side_from_group(
    row: Mapping[str, Any],
    *,
    ship_id: int,
) -> ShipCombatSideInput:
    tminus1 = row.get("tminus1")
    if not isinstance(tminus1, Mapping):
        raise ValueError("tminus1 map missing")
    raw = tminus1.get(str(ship_id))
    if not isinstance(raw, Mapping):
        raise ValueError(f"tminus1 ship {ship_id} missing")

    owner_id = _intish(raw.get("owner_tminus1"))
    if owner_id is None:
        owner_id = _intish(raw.get("factual_owner_id"))
    if owner_id is None or owner_id <= 0:
        raise ValueError(f"owner for ship {ship_id} unresolved")

    return ShipCombatSideInput(
        ship_id=ship_id,
        owner_id=owner_id,
        race_id=2,
        hull_id=20,
        mission=_intish(raw.get("mission")),
        mission_target_id=_intish(raw.get("mission1target")),
        primary_enemy=_intish(raw.get("enemy")),
        friendly_code=raw.get("friendlycode"),
        hull_can_cloak=False,
        has_fuel=True,
        diplomacy_allows_attack=True,
        harmonic_weapon_modulation_enabled=False,
        cloak_and_intercept_enabled=False,
        cloak_and_intercept_hull_eligible=False,
        active_cloak_at_intercept=False,
        intercept_interference_protected=False,
        galactic_power_enabled=False,
        standard_targetable_by_opponent=True,
    )


def _production_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    pair_raw = row.get("pair")
    left_sequence = row.get("left_ship_sequence")
    right_sequence = row.get("right_ship_sequence")
    if (
        not isinstance(pair_raw, list)
        or len(pair_raw) != 2
        or not isinstance(left_sequence, list)
        or len(left_sequence) != 2
        or not isinstance(right_sequence, list)
        or len(right_sequence) != 2
    ):
        return {"status": "adapter_error", "reason": "repeated_pair_shape_missing"}

    pair = tuple(sorted((int(pair_raw[0]), int(pair_raw[1]))))
    try:
        left = _side_from_group(row, ship_id=pair[0])
        right = _side_from_group(row, ship_id=pair[1])
        pair_input = InitialStandardPairInput(
            left=left,
            right=right,
            decision=decide_ship_combat_pair(
                left=left,
                right=right,
                same_location=True,
            ),
        )
        state = StandardQueueState(
            pair_occurrences={pair: 1},
            first_pass_sides={
                pair: (int(left_sequence[0]), int(right_sequence[0]))
            },
        )
        step = select_next_plain_standard(
            pair_inputs=[pair_input],
            active_ship_ids=set(pair),
            state=state,
        )
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "status": "adapter_error",
            "reason": f"{type(exc).__name__}:{exc}",
        }

    return {
        "status": (
            "resolved"
            if step.engagement_available is True
            else "unresolved"
        ),
        "engagement_available": step.engagement_available,
        "pair": list(step.pair) if step.pair is not None else None,
        "occurrence_index": step.occurrence_index,
        "left_ship_id": step.left_ship_id,
        "right_ship_id": step.right_ship_id,
        "expected_left_ship_id": int(left_sequence[1]),
        "expected_right_ship_id": int(right_sequence[1]),
        "unresolved_reasons": list(step.unresolved_reasons),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    baseline = repeated_module.run(
        argparse.Namespace(
            archive_dir=args.archive_dir,
            prepared_dir=args.prepared_dir,
            example_limit=args.example_limit,
            output=None,
        )
    )
    counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []

    baseline_rows = baseline.get("examples")
    baseline_rows = baseline_rows if isinstance(baseline_rows, list) else []

    seen_keys: set[tuple[int, int, int, int, int]] = set()
    for row in baseline_rows:
        if not isinstance(row, Mapping):
            continue
        if row.get("plain_static_comparable") is not True:
            continue
        if row.get("stable_owners") is not True:
            continue
        if int(row.get("occurrence_count") or 0) != 2:
            continue

        pair_raw = row.get("pair")
        if not isinstance(pair_raw, list) or len(pair_raw) != 2:
            counts["adapter_errors"] += 1
            continue
        key = (
            int(row["game_id"]),
            int(row["battle_turn"]),
            int(row["x"]),
            int(row["y"]),
            min(int(pair_raw[0]), int(pair_raw[1])),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        counts["comparable_repeated_groups"] += 1

        projection = _production_projection(row)
        if projection.get("status") == "adapter_error":
            counts["adapter_errors"] += 1
        elif projection.get("engagement_available") is not True:
            counts["production_unresolved"] += 1
        elif (
            projection.get("occurrence_index") == 2
            and projection.get("left_ship_id")
            == projection.get("expected_left_ship_id")
            and projection.get("right_ship_id")
            == projection.get("expected_right_ship_id")
        ):
            counts["production_second_occurrence_exact"] += 1
        else:
            counts["production_second_occurrence_mismatch"] += 1

        if (
            projection.get("status") != "resolved"
            or projection.get("left_ship_id")
            != projection.get("expected_left_ship_id")
            or projection.get("right_ship_id")
            != projection.get("expected_right_ship_id")
        ) and len(examples) < args.example_limit:
            examples.append(
                {
                    "game_id": row.get("game_id"),
                    "battle_turn": row.get("battle_turn"),
                    "x": row.get("x"),
                    "y": row.get("y"),
                    "pair": row.get("pair"),
                    "production": projection,
                }
            )

    comparable = int(counts["comparable_repeated_groups"])
    acceptance = {
        "ordinary_repeated_population_present": comparable > 0,
        "no_adapter_errors": int(counts["adapter_errors"]) == 0,
        "no_production_unresolved": int(counts["production_unresolved"]) == 0,
        "production_second_occurrence_exact": (
            int(counts["production_second_occurrence_exact"]) == comparable
            and int(counts["production_second_occurrence_mismatch"]) == 0
        ),
    }
    acceptance["second_standard_queue_gate_passed"] = all(
        acceptance.values()
    )

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "counts": dict(sorted(counts.items())),
            "baseline": baseline.get("summary"),
            "acceptance": acceptance,
        },
        "mismatch_examples": examples,
        "evidence_boundary": (
            "Production composition gate for occurrence-aware ordinary STANDARD "
            "queue sides. It reuses the independently mined repeated-pair "
            "population, which already excludes game 591478, and asks whether "
            "StandardQueueState plus select_next_plain_standard reproduces the "
            "factual second occurrence orientation. The adapter is intentionally "
            "restricted to stable-owner, exactly-two, plain-static-comparable "
            "groups. Factual repeated-pair membership is still the population "
            "selector for this gate; therefore this does not yet prove full "
            "post-mutation next-pair selection among a multi-pair stack."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate production ordinary STANDARD occurrence history against "
            "the repeated-pair corpus."
        )
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=80)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT SECOND STANDARD QUEUE =====")
    print("summary:", report["summary"])
    if report["mismatch_examples"]:
        print()
        print("MISMATCH EXAMPLES:")
        for row in report["mismatch_examples"]:
            print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("output:", args.output)
    print(
        "NOTE: occurrence-aware side composition gate only; full post-mutation "
        "multi-pair selection remains separate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
