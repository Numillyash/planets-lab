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

import combat_host_capture_continuation_audit as capture_module
from combat_host_mission7_matched_control_audit import _dedup_vcrs
from combat_host_priority_intercept_audit import RAW_DIR, _int


SCHEMA = "planets-lab.combat-host-post-capture-opponent-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 80


def _vcr_index(
    archive_dir: Path,
) -> tuple[dict[tuple[int, int, int], dict[str, Any]], int]:
    result: dict[tuple[int, int, int], dict[str, Any]] = {}
    conflicts = 0
    for archive_path in sorted(archive_dir.glob("game-*.zip")):
        try:
            game_id = int(archive_path.stem.split("-")[-1])
        except ValueError:
            continue
        if selected_ids is not None and game_id not in selected_ids:
            continue
        seen, archive_conflicts = _dedup_vcrs(archive_path.read_bytes())
        conflicts += archive_conflicts
        for (seen_game, battle_turn, vcr_id), (_digest, raw) in seen.items():
            if seen_game != game_id:
                continue
            result[(game_id, int(battle_turn), int(vcr_id))] = dict(raw)
    return result, conflicts


def _opponent_projection(
    row: Mapping[str, Any],
    raw_vcr: Mapping[str, Any],
) -> dict[str, Any]:
    current_side = row.get("current_side")
    if current_side not in {"left", "right"}:
        return {"resolved": None, "reason": "captured_ship_side_unresolved"}

    opponent_side = "right" if current_side == "left" else "left"
    owner_key = f"{opponent_side}ownerid"
    opponent_owner_id = _int(raw_vcr, owner_key)
    raw_side = raw_vcr.get(opponent_side)
    if opponent_owner_id is None or opponent_owner_id <= 0 or not isinstance(raw_side, Mapping):
        return {
            "resolved": None,
            "reason": "opponent_owner_or_side_unresolved",
            "opponent_side": opponent_side,
        }

    hull_id = _int(raw_side, "hullid")
    object_id = _int(raw_side, "objectid")
    is_planet = hull_id is not None and hull_id <= 0

    old_owner_id = row.get("owner_id_before")
    captor_owner_id = row.get("captor_owner_id")
    if (
        isinstance(old_owner_id, bool)
        or not isinstance(old_owner_id, int)
        or old_owner_id <= 0
        or isinstance(captor_owner_id, bool)
        or not isinstance(captor_owner_id, int)
        or captor_owner_id <= 0
    ):
        return {
            "resolved": None,
            "reason": "capture_owner_attribution_unresolved",
            "opponent_owner_id": opponent_owner_id,
        }

    if opponent_owner_id == old_owner_id:
        owner_relation = "pre_capture_owner"
    elif opponent_owner_id == captor_owner_id:
        owner_relation = "captor"
    else:
        owner_relation = "third_party"

    return {
        "resolved": True,
        "opponent_side": opponent_side,
        "opponent_owner_id": opponent_owner_id,
        "opponent_hull_id": hull_id,
        "opponent_object_id": object_id,
        "opponent_is_planet": is_planet,
        "owner_relation": owner_relation,
        "opponent_is_pre_capture_owner": opponent_owner_id == old_owner_id,
        "opponent_is_captor": opponent_owner_id == captor_owner_id,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    feature_scope = load_feature_scope(
        args.feature_index,
        profile=args.scope_profile,
    )
    capture_report = capture_module.run(
        argparse.Namespace(
            archive_dir=args.archive_dir,
            feature_index=args.feature_index,
            scope_profile=args.scope_profile,
            example_limit=10000,
            output=None,
        )
    )
    vcrs, payload_conflicts = _vcr_index(
        args.archive_dir,
        selected_ids=set(feature_scope.selected_ids),
    )

    rows = capture_report.get("examples")
    rows = rows if isinstance(rows, list) else []

    counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []

    for capture_row in rows:
        if (
            not isinstance(capture_row, Mapping)
            or capture_row.get("status") != "capture_continuation"
        ):
            continue
        game_id = int(capture_row["game_id"])
        battle_turn = int(capture_row["turn"])
        to_vcr_id = int(capture_row["to_vcr_id"])
        counts["capture_continuations"] += 1

        raw_vcr = vcrs.get((game_id, battle_turn, to_vcr_id))
        if not isinstance(raw_vcr, Mapping):
            counts["next_vcr_missing"] += 1
            if len(examples) < args.example_limit:
                examples.append(
                    {
                        "game_id": game_id,
                        "battle_turn": battle_turn,
                        "ship_id": capture_row.get("ship_id"),
                        "to_vcr_id": to_vcr_id,
                        "status": "next_vcr_missing",
                    }
                )
            continue

        projection = _opponent_projection(capture_row, raw_vcr)
        if projection.get("resolved") is not True:
            counts["opponent_projection_unresolved"] += 1
        else:
            relation = str(projection["owner_relation"])
            counts[f"next_owner_relation:{relation}"] += 1
            if projection.get("opponent_is_planet") is True:
                counts["next_combat:planet"] += 1
            else:
                counts["next_combat:ship"] += 1
            side = capture_row.get("current_side")
            if side in {"left", "right"}:
                counts[f"captured_ship_side:{side}"] += 1

        enriched = {
            "game_id": game_id,
            "battle_turn": battle_turn,
            "ship_id": int(capture_row["ship_id"]),
            "from_vcr_id": int(capture_row["from_vcr_id"]),
            "to_vcr_id": to_vcr_id,
            "pre_capture_owner_id": int(capture_row["owner_id_before"]),
            "captor_owner_id": int(capture_row["captor_owner_id"]),
            "post_capture_owner_id": int(capture_row["owner_id_after"]),
            "captured_ship_side": capture_row.get("current_side"),
            "projection": projection,
        }
        if len(examples) < args.example_limit:
            examples.append(enriched)

    population = int(counts["capture_continuations"])
    old_owner = int(counts["next_owner_relation:pre_capture_owner"])
    acceptance = {
        "capture_continuation_population_present": population > 0,
        "payload_conflicts_absent": payload_conflicts == 0,
        "no_missing_next_vcrs": int(counts["next_vcr_missing"]) == 0,
        "no_opponent_projection_unresolved": int(
            counts["opponent_projection_unresolved"]
        ) == 0,
        "next_opponent_always_pre_capture_owner": (
            population > 0
            and old_owner == population
            and int(counts["next_owner_relation:captor"]) == 0
            and int(counts["next_owner_relation:third_party"]) == 0
        ),
        "ship_and_planet_continuations_both_present": (
            int(counts["next_combat:ship"]) > 0
            and int(counts["next_combat:planet"]) > 0
        ),
    }
    acceptance["post_capture_opponent_gate_passed"] = all(
        acceptance.values()
    )

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "feature_scope": feature_scope.to_dict(),
            "payload_conflicts": payload_conflicts,
            "counts": dict(sorted(counts.items())),
            "capture_state_acceptance": (
                capture_report.get("summary", {}).get("acceptance")
                if isinstance(capture_report.get("summary"), Mapping)
                else None
            ),
            "acceptance": acceptance,
        },
        "examples": examples,
        "evidence_boundary": (
            "Read-only post-capture opponent attribution. It starts only from "
            "capture continuations already established by the production capture "
            "state differential, then opens the factual next VCR solely to read "
            "the opposite combatant owner/type. The next opponent is not used to "
            "drive production selection. This gate tests whether the immediate "
            "post-capture combat remains directed against the captured ship's "
            "pre-capture owner across both ship and planet/base continuations. "
            "It does not yet determine which specific old-owner ship/planet is "
            "selected, nor does it infer mission/PE/diplomacy reset semantics."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit owner attribution of the immediate opponent after a captured "
            "ship re-enters the same Host combat sequence."
        )
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--feature-index", type=Path, default=DEFAULT_FEATURE_INDEX_PATH)
    parser.add_argument("--scope-profile", default="combat-planar-no-horwasp")
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT POST-CAPTURE OPPONENT AUDIT =====")
    print("summary:", report["summary"])
    if report["examples"]:
        print()
        print("EXAMPLES:")
        for row in report["examples"]:
            print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("output:", args.output)
    print(
        "NOTE: opponent-owner attribution only; specific target/order "
        "selection remains separate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
