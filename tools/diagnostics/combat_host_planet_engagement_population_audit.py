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

from planets_lab.rules.combat.order import orders_request_ship_combat

import combat_host_post_capture_opponent_audit as opponent_module
from combat_host_mixed_ship_planet_queue_batch_audit import (
    HORWASP_RACE_ID,
    _effective_planet_owner,
    _load_groups,
    _planet_pair,
    _planet_projection,
    _priority_projection,
    _resolved_owner_at_turn,
    _shape,
)
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
)


SCHEMA = "planets-lab.combat-host-planet-engagement-population-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 100


def run(args: argparse.Namespace) -> dict[str, Any]:
    vcrs, payload_conflicts = opponent_module._vcr_index(args.archive_dir)
    game_context: dict[int, tuple[Mapping[Any, Any], Mapping[Any, Any], Mapping[int, int]]] = {}
    counts: Counter[str] = Counter()
    residual_examples: list[dict[str, Any]] = []
    owner_repair_examples: list[dict[str, Any]] = []

    for (game_id, battle_turn, vcr_id), raw_vcr in sorted(vcrs.items()):
        if game_id == SPECIAL_GAME_ID or _shape(raw_vcr) != "ship_vs_planet":
            continue
        counts["ordinary_ship_vs_planet_vcrs"] += 1
        pair = _planet_pair(raw_vcr)
        if pair is None:
            counts["pair_projection_unresolved"] += 1
            continue
        ship, planet = pair
        ship_id = int(ship["object_id"])
        planet_id = int(planet["object_id"])

        if game_id not in game_context:
            game_context[game_id] = _load_groups(
                archive_dir=args.archive_dir,
                prepared_dir=args.prepared_dir,
                game_id=game_id,
            )
        ship_groups, planet_groups, race_owner_map = game_context[game_id]

        ship_projection = _priority_projection(
            ship_groups,
            battle_turn=battle_turn,
            ship_id=ship_id,
        )
        planet_projection = _planet_projection(
            planet_groups,
            battle_turn=battle_turn,
            planet_id=planet_id,
        )
        current_owner = _resolved_owner_at_turn(
            planet_groups,
            turn=battle_turn,
            entity_id=planet_id,
        )
        owner_resolution = _effective_planet_owner(
            ship_owner_id=int(ship["owner_id"]),
            vcr_planet_owner_id=int(planet["owner_id"]),
            planet_race_id=(
                int(planet["race_id"])
                if isinstance(planet.get("race_id"), int)
                else None
            ),
            race_owner_map=race_owner_map,
            tminus1_owner_id=(
                int(planet_projection["owner_id"])
                if planet_projection.get("resolved") is True
                else None
            ),
            current_owner_id=current_owner,
        )
        counts[f"owner_resolution:{owner_resolution['source']}"] += 1
        if owner_resolution.get("source") == "same_owner_vcr_repaired_by_race_map":
            counts["same_owner_vcr_rows"] += 1
            if owner_resolution.get("current_owner_confirms_race_map") is True:
                counts["same_owner_race_repairs_current_confirmed"] += 1
            if len(owner_repair_examples) < args.example_limit:
                owner_repair_examples.append({
                    "game_id": game_id,
                    "battle_turn": battle_turn,
                    "vcr_id": vcr_id,
                    "ship_id": ship_id,
                    "planet_id": planet_id,
                    "ship": {k: v for k, v in ship.items() if k != "raw"},
                    "planet": {k: v for k, v in planet.items() if k != "raw"},
                    "owner_resolution": owner_resolution,
                    "ship_tminus1": ship_projection,
                    "planet_tminus1": planet_projection,
                })

        effective_owner = owner_resolution.get("owner_id")
        ship_request: bool | None = None
        if ship_projection.get("resolved") is True and isinstance(effective_owner, int):
            ordinary_request = orders_request_ship_combat(
                mission=ship_projection.get("mission"),
                primary_enemy=ship_projection.get("enemy"),
                opponent_owner_id=effective_owner,
            )
            horwasp_request = (
                ship.get("race_id") == HORWASP_RACE_ID
                and int(ship["owner_id"]) != effective_owner
            )
            ship_request = bool(ordinary_request or horwasp_request)
            if horwasp_request and not ordinary_request:
                counts["ship_request:horwasp_kill_equivalent"] += 1
        elif ship_projection.get("resolved") is not True:
            counts["unresolved:ship_tminus1"] += 1
        elif not isinstance(effective_owner, int):
            counts["unresolved:planet_owner"] += 1

        planet_request: bool | None = None
        if planet_projection.get("resolved") is True:
            planet_request = bool(planet_projection.get("attack_code"))
        else:
            counts["unresolved:planet_tminus1"] += 1
        horwasp_planet_request = (
            planet.get("race_id") == HORWASP_RACE_ID
            and isinstance(effective_owner, int)
            and int(ship["owner_id"]) != effective_owner
        )
        if horwasp_planet_request:
            if planet_request is not True:
                counts["planet_request:horwasp_nuk_equivalent"] += 1
            planet_request = True

        if ship_request is True and planet_request is True:
            counts["explanation:both"] += 1
        elif ship_request is True:
            counts["explanation:ship_only"] += 1
        elif planet_request is True:
            counts["explanation:planet_only"] += 1
        elif ship_request is None or planet_request is None:
            counts["explanation:unresolved"] += 1
        else:
            counts["explanation:hard_residual"] += 1
            if len(residual_examples) < args.example_limit:
                residual_examples.append({
                    "game_id": game_id,
                    "battle_turn": battle_turn,
                    "vcr_id": vcr_id,
                    "ship_id": ship_id,
                    "planet_id": planet_id,
                    "ship": {k: v for k, v in ship.items() if k != "raw"},
                    "planet": {k: v for k, v in planet.items() if k != "raw"},
                    "owner_resolution": owner_resolution,
                    "ship_tminus1": ship_projection,
                    "planet_tminus1": planet_projection,
                    "ship_request": ship_request,
                    "planet_request": planet_request,
                })

    population = int(counts["ordinary_ship_vs_planet_vcrs"])
    explained = (
        int(counts["explanation:both"])
        + int(counts["explanation:ship_only"])
        + int(counts["explanation:planet_only"])
    )
    acceptance = {
        "ordinary_planet_population_present": population > 0,
        "payload_conflicts_absent": payload_conflicts == 0,
        "pair_projection_resolved": int(counts["pair_projection_unresolved"]) == 0,
        "owner_repair_population_if_observed_is_resolved": (
            int(counts["owner_resolution:same_owner_vcr_unresolved"]) == 0
        ),
        "explained_population_present": explained > 0,
        "no_hard_initiator_residuals": int(counts["explanation:hard_residual"]) == 0,
    }
    acceptance["planet_engagement_population_gate_passed"] = all(acceptance.values())

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "special_game_591478_excluded": True,
            "payload_conflicts": payload_conflicts,
            "counts": dict(sorted(counts.items())),
            "acceptance": acceptance,
        },
        "owner_repair_examples": owner_repair_examples,
        "hard_residual_examples": residual_examples,
        "evidence_boundary": (
            "All ordinary ship-vs-planet VCRs, not only mixed sites. The audit "
            "uses VCR race identity only to repair an otherwise impossible "
            "same-owner planet owner field when that race maps uniquely to a "
            "different player slot in normalized player metadata. T-1 and T "
            "planet owners are reported as independent context. The audit then "
            "tests attack initiation through ship Kill!/Primary Enemy, planet "
            "NUK/ATT, and Horwasp Kill!/NUK-equivalent behavior. It does not "
            "yet claim final targetability, diplomacy suppression, fuel, cloak, "
            "matching-FC exceptions, or capture-generated ordering."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit initiator coverage for all ordinary ship-vs-planet VCRs."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT ALL PLANET ENGAGEMENT POPULATION =====")
    print("summary:", report["summary"])
    if report["owner_repair_examples"]:
        print()
        print("OWNER REPAIR EXAMPLES:")
        for row in report["owner_repair_examples"]:
            print(row)
    if report["hard_residual_examples"]:
        print()
        print("HARD INITIATOR RESIDUALS:")
        for row in report["hard_residual_examples"]:
            print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("output:", args.output)
    print("NOTE: initiator population gate only; final planet targetability remains separate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
