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

from planets_lab.corpus.feature_scope import (
    DEFAULT_FEATURE_INDEX_PATH,
    load_feature_scope,
)
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.combat.order import orders_request_ship_combat

import combat_host_capture_continuation_audit as capture_module
import combat_host_post_capture_opponent_audit as opponent_module
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    _owner_raw,
)


SCHEMA = "planets-lab.combat-host-post-capture-initiator-population-audit.v2"
DEFAULT_EXAMPLE_LIMIT = 80
PLANET_ATTACK_FRIENDLY_CODES = frozenset({"nuk", "att"})


def _normalize_fc(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip().lower()


def _ship_request_projection(
    raw: Mapping[str, Any],
    *,
    target_owner_id: int,
) -> dict[str, Any]:
    mission = _intish(raw.get("mission"))
    enemy = _intish(raw.get("enemy"))
    return {
        "mission": mission,
        "enemy": enemy,
        "friendlycode": raw.get("friendlycode"),
        "requests_target_owner": orders_request_ship_combat(
            mission=mission,
            primary_enemy=enemy,
            opponent_owner_id=target_owner_id,
        ),
    }


def _planet_attack_projection(raw: Mapping[str, Any]) -> dict[str, Any]:
    fc = _normalize_fc(raw.get("friendlycode"))
    return {
        "friendlycode": raw.get("friendlycode"),
        "normalized_friendlycode": fc,
        "independent_attack_code": fc in PLANET_ATTACK_FRIENDLY_CODES,
    }


def _load_groups(
    *,
    archive_dir: Path,
    prepared_dir: Path,
    game_id: int,
) -> tuple[Mapping[Any, Any], Mapping[Any, Any]]:
    archive_path = archive_dir / f"game-{game_id}.zip"
    prepared, _ = load_or_build_prepared_game_cache(
        archive_path.read_bytes(),
        game_id=game_id,
        cache_path=prepared_dir / f"game-{game_id}.pickle",
    )
    return (
        group_perspective_records(prepared.snapshots, "ship"),
        group_perspective_records(prepared.snapshots, "planet"),
    )


REQUIRED_UNRESOLVED_KEYS = frozenset({
    "unresolved:next_vcr_missing",
    "unresolved:opponent_projection",
    "unresolved:opponent_object_id",
    "unresolved:opponent_ship_tminus1",
    "unresolved:opponent_planet_tminus1",
})


def _required_unresolved_total(counts: Mapping[str, int]) -> int:
    return sum(int(counts.get(key, 0)) for key in REQUIRED_UNRESOLVED_KEYS)


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
    vcrs, payload_conflicts = opponent_module._vcr_index(
        args.archive_dir,
        selected_ids=set(feature_scope.selected_ids),
    )
    rows = capture_report.get("examples")
    rows = rows if isinstance(rows, list) else []

    groups_by_game: dict[
        int,
        tuple[Mapping[Any, Any], Mapping[Any, Any]],
    ] = {}
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
        ship_id = int(capture_row["ship_id"])
        pre_capture_owner_id = int(capture_row["owner_id_before"])
        post_capture_owner_id = int(capture_row["owner_id_after"])
        counts["capture_continuations"] += 1

        raw_vcr = vcrs.get((game_id, battle_turn, to_vcr_id))
        if not isinstance(raw_vcr, Mapping):
            counts["unresolved:next_vcr_missing"] += 1
            continue

        opponent = opponent_module._opponent_projection(capture_row, raw_vcr)
        if opponent.get("resolved") is not True:
            counts["unresolved:opponent_projection"] += 1
            continue

        if game_id not in groups_by_game:
            groups_by_game[game_id] = _load_groups(
                archive_dir=args.archive_dir,
                prepared_dir=args.prepared_dir,
                game_id=game_id,
            )
        ship_groups, planet_groups = groups_by_game[game_id]
        before_turn = battle_turn - 1

        old_owner, old_ship_raw = _owner_raw(
            ship_groups,
            before_turn,
            ship_id,
        )
        old_order_projection: dict[str, Any] | None = None
        opponent_owner_id = int(opponent["opponent_owner_id"])
        if (
            old_owner == pre_capture_owner_id
            and isinstance(old_ship_raw, Mapping)
        ):
            old_order_projection = _ship_request_projection(
                old_ship_raw,
                target_owner_id=opponent_owner_id,
            )
        else:
            counts["unresolved:captured_ship_tminus1"] += 1

        opponent_object_id = opponent.get("opponent_object_id")
        if (
            isinstance(opponent_object_id, bool)
            or not isinstance(opponent_object_id, int)
            or opponent_object_id <= 0
        ):
            counts["unresolved:opponent_object_id"] += 1
            continue

        opponent_type = (
            "planet" if opponent.get("opponent_is_planet") is True else "ship"
        )
        independent_projection: dict[str, Any] | None = None

        if opponent_type == "ship":
            observed_owner, raw = _owner_raw(
                ship_groups,
                before_turn,
                opponent_object_id,
            )
            if observed_owner != opponent_owner_id or not isinstance(raw, Mapping):
                counts["unresolved:opponent_ship_tminus1"] += 1
            else:
                independent_projection = _ship_request_projection(
                    raw,
                    target_owner_id=post_capture_owner_id,
                )
                independent_projection["owner_id"] = observed_owner
                independent_projection["ship_id"] = opponent_object_id
                independent_projection["kind"] = "ship"
        else:
            observed_owner, raw = _owner_raw(
                planet_groups,
                before_turn,
                opponent_object_id,
            )
            if observed_owner != opponent_owner_id or not isinstance(raw, Mapping):
                counts["unresolved:opponent_planet_tminus1"] += 1
            else:
                independent_projection = _planet_attack_projection(raw)
                independent_projection["owner_id"] = observed_owner
                independent_projection["planet_id"] = opponent_object_id
                independent_projection["kind"] = "planet"

        if independent_projection is None:
            independent_attack = None
        elif opponent_type == "ship":
            independent_attack = bool(
                independent_projection.get("requests_target_owner")
            )
        else:
            independent_attack = bool(
                independent_projection.get("independent_attack_code")
            )

        old_orders_attack = (
            bool(old_order_projection.get("requests_target_owner"))
            if isinstance(old_order_projection, Mapping)
            else None
        )

        relation = str(opponent["owner_relation"])
        counts[f"owner_relation:{relation}"] += 1
        counts[f"opponent_type:{opponent_type}"] += 1

        if independent_attack is True:
            counts["independent_opponent_attack_candidate"] += 1
            counts[f"independent_attack:{opponent_type}"] += 1
        elif independent_attack is False:
            counts["no_independent_opponent_attack_candidate"] += 1
            counts[f"no_independent_attack:{opponent_type}"] += 1
        else:
            counts["independent_opponent_attack_unresolved"] += 1

        if old_orders_attack is True:
            counts["captured_old_orders_attack_candidate"] += 1
        elif old_orders_attack is False:
            counts["captured_old_orders_no_attack_candidate"] += 1
        else:
            counts["captured_old_orders_unresolved"] += 1

        if independent_attack is True and old_orders_attack is True:
            explanation = "both"
        elif independent_attack is True:
            explanation = "opponent_only"
        elif old_orders_attack is True:
            explanation = "captured_old_orders_only"
        elif independent_attack is False and old_orders_attack is False:
            explanation = "neither"
        else:
            explanation = "unresolved"
        counts[f"explanation:{explanation}"] += 1

        if (
            relation == "third_party"
            and independent_attack is True
        ):
            counts["third_party_independent_attack_exact"] += 1
        elif relation == "third_party":
            counts["third_party_without_independent_attack"] += 1

        if len(examples) < args.example_limit:
            examples.append(
                {
                    "game_id": game_id,
                    "battle_turn": battle_turn,
                    "ship_id": ship_id,
                    "from_vcr_id": int(capture_row["from_vcr_id"]),
                    "to_vcr_id": to_vcr_id,
                    "pre_capture_owner_id": pre_capture_owner_id,
                    "post_capture_owner_id": post_capture_owner_id,
                    "opponent": opponent,
                    "opponent_type": opponent_type,
                    "independent_opponent": independent_projection,
                    "captured_ship_old_orders": old_order_projection,
                    "independent_attack_candidate": independent_attack,
                    "old_orders_attack_candidate": old_orders_attack,
                    "explanation": explanation,
                }
            )

    population = int(counts["capture_continuations"])
    required_unresolved = _required_unresolved_total(counts)
    optional_old_order_unresolved = int(counts["unresolved:captured_ship_tminus1"])
    third_party = int(counts["owner_relation:third_party"])
    independent = int(counts["independent_opponent_attack_candidate"])
    acceptance = {
        "capture_continuation_population_present": population > 0,
        "payload_conflicts_absent": payload_conflicts == 0,
        "no_required_adapter_unresolved": required_unresolved == 0,
        "all_continuations_have_independent_opponent_attack": (
            population > 0
            and independent == population
            and int(counts["no_independent_opponent_attack_candidate"]) == 0
            and int(counts["independent_opponent_attack_unresolved"]) == 0
        ),
        "third_party_population_present": third_party > 0,
        "all_third_party_have_independent_attack": (
            third_party > 0
            and int(counts["third_party_independent_attack_exact"]) == third_party
            and int(counts["third_party_without_independent_attack"]) == 0
        ),
        "ship_and_planet_continuations_present": (
            int(counts["opponent_type:ship"]) > 0
            and int(counts["opponent_type:planet"]) > 0
        ),
    }
    acceptance["post_capture_initiator_gate_passed"] = all(acceptance.values())

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "feature_scope": feature_scope.to_dict(),
            "payload_conflicts": payload_conflicts,
            "counts": dict(sorted(counts.items())),
            "required_unresolved_total": required_unresolved,
            "optional_old_order_unresolved": optional_old_order_unresolved,
            "acceptance": acceptance,
        },
        "examples": examples,
        "evidence_boundary": (
            "Read-only initiator inventory across every production-validated "
            "same-turn post-capture continuation. Ship opponents are checked for "
            "an independent T-1 Kill!/Primary-Enemy request against the captured "
            "ship's new owner. Planet/base opponents are checked only for the "
            "documented NUK/ATT attack-code trigger. The captured ship's own T-1 "
            "orders are reported as a historical alternative but are never "
            "assumed to persist through capture. Missing old captured-ship T-1 "
            "orders are therefore informational and never block acceptance. "
            "Hard acceptance requires a resolved independent opponent initiator "
            "for every continuation. This diagnostic does not yet apply "
            "diplomacy or matching-FC suppression to the initiator "
            "candidates, nor infer the newly generated capture target list."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory independently attributable initiators for all observed "
            "post-capture combat continuations."
        )
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--feature-index", type=Path, default=DEFAULT_FEATURE_INDEX_PATH)
    parser.add_argument("--scope-profile", default="combat-planar-no-horwasp")
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT POST-CAPTURE INITIATOR POPULATION =====")
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
        "NOTE: initiator candidates only; capture target-list reconstruction, "
        "diplomacy suppression and specific target ordering remain separate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
