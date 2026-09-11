from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.combat.order import standard_battle_priority_key

from combat_host_candidate_set_audit import _owner_rows_for_turn, _pair, _serialize
from combat_host_initial_standard_target_audit import _factual_queue_by_site
from combat_host_mission7_matched_control_audit import _dedup_vcrs
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR, SPECIAL_GAME_ID
from combat_host_privateer_rob_attack_opportunity_audit import run as run_attack_opportunities


SCHEMA = "planets-lab.combat-host-privateer-rob-initial-decision-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 100


def _priority_key(ship_id: int, raw: Mapping[str, Any]) -> tuple[int, int, int] | None:
    return standard_battle_priority_key(
        ship_id=ship_id,
        mission=_intish(raw.get("mission")),
        primary_enemy=_intish(raw.get("enemy")),
        friendly_code=raw.get("friendlycode"),
    )


def _opponent(pair: Sequence[int], ship_id: int) -> int | None:
    values = [int(value) for value in pair]
    if len(values) != 2 or ship_id not in values:
        return None
    return values[1] if values[0] == ship_id else values[0]


def _initial_context(
    *,
    row: Mapping[str, Any],
    owner_rows: Mapping[int, tuple[int, Mapping[str, Any]]],
    factual_queue: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    target_id = int(row["target_ship_id"])
    attacker_id = int(row["attacker_ship_id"])
    target_entry = owner_rows.get(target_id)
    if target_entry is None:
        return {"resolved": False, "reason": "target_owner_current_missing"}
    target_key = _priority_key(target_id, target_entry[1])
    if target_key is None:
        return {"resolved": False, "reason": "target_priority_unresolved"}

    attacker_appearances: list[tuple[int, Mapping[str, Any]]] = []
    for index, vcr in enumerate(factual_queue):
        pair_raw = vcr.get("pair")
        if not isinstance(pair_raw, Sequence):
            continue
        if attacker_id in [int(value) for value in pair_raw]:
            attacker_appearances.append((index, vcr))

    if not attacker_appearances:
        return {
            "resolved": True,
            "target_priority": list(target_key),
            "attacker_factual_appearance_count": 0,
            "initial_attacker": False,
            "classification": "attacker_no_factual_vcr",
        }

    first_index, first_vcr = attacker_appearances[0]
    first_pair_raw = first_vcr.get("pair")
    if not isinstance(first_pair_raw, Sequence):
        return {"resolved": False, "reason": "first_attacker_pair_missing"}
    first_pair = _pair(int(first_pair_raw[0]), int(first_pair_raw[1]))
    factual_opponent_id = _opponent(first_pair, attacker_id)
    if factual_opponent_id is None:
        return {"resolved": False, "reason": "first_attacker_opponent_missing"}
    factual_entry = owner_rows.get(factual_opponent_id)
    if factual_entry is None:
        return {"resolved": False, "reason": "factual_opponent_owner_current_missing"}
    factual_key = _priority_key(factual_opponent_id, factual_entry[1])
    if factual_key is None:
        return {"resolved": False, "reason": "factual_opponent_priority_unresolved"}

    opportunity_pair = _pair(target_id, attacker_id)
    initial_attacker = first_index == 0
    pair_is_first_for_attacker = first_pair == opportunity_pair
    target_outranks_factual = target_key < factual_key
    target_same_priority = target_key == factual_key

    if pair_is_first_for_attacker:
        classification = "initial_pair_vcr" if initial_attacker else "later_pair_vcr"
    elif initial_attacker and target_outranks_factual:
        classification = "initial_skip_target_outranks_factual"
    elif initial_attacker:
        classification = "initial_skip_target_not_above_factual"
    else:
        classification = "noninitial_attacker_context"

    return {
        "resolved": True,
        "target_priority": list(target_key),
        "attacker_factual_appearance_count": len(attacker_appearances),
        "attacker_first_vcr_index": first_index,
        "attacker_first_vcr_id": int(first_vcr["vcr_id"]),
        "attacker_first_pair": list(first_pair),
        "factual_first_opponent_ship_id": factual_opponent_id,
        "factual_first_opponent_priority": list(factual_key),
        "initial_attacker": initial_attacker,
        "pair_is_first_for_attacker": pair_is_first_for_attacker,
        "target_outranks_factual_first_opponent": target_outranks_factual,
        "target_same_priority_as_factual_first_opponent": target_same_priority,
        "classification": classification,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    base_args = SimpleNamespace(
        archive_dir=args.archive_dir,
        prepared_dir=args.prepared_dir,
        example_limit=100000,
        output=None,
    )
    base = run_attack_opportunities(base_args)
    opportunity_rows = list(base.get("examples", ()))

    rows_by_game: dict[int, list[dict[str, Any]]] = {}
    for raw in opportunity_rows:
        if not isinstance(raw, Mapping):
            continue
        game_id = int(raw["game_id"])
        rows_by_game.setdefault(game_id, []).append(dict(raw))

    totals: Counter[str] = Counter()
    by_cloak: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []

    for game_id, game_rows in sorted(rows_by_game.items()):
        if game_id == SPECIAL_GAME_ID:
            continue
        archive_path = args.archive_dir / f"game-{game_id}.zip"
        if not archive_path.exists():
            totals["missing_archives"] += 1
            continue
        archive_data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=args.prepared_dir / f"game-{game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        seen, conflicts = _dedup_vcrs(archive_data)
        totals["payload_conflicts"] += int(conflicts)
        queues = _factual_queue_by_site(game_id=game_id, seen=seen)
        owner_cache: dict[int, dict[int, tuple[int, Mapping[str, Any]]]] = {}

        for row in game_rows:
            before_turn = int(row["before_turn"])
            battle_turn = int(row["battle_turn"])
            site_raw = row["site"]
            site_key = (battle_turn, int(site_raw[0]), int(site_raw[1]))
            if before_turn not in owner_cache:
                owner_cache[before_turn] = _owner_rows_for_turn(ship_groups, before_turn)
            context = _initial_context(
                row=row,
                owner_rows=owner_cache[before_turn],
                factual_queue=queues.get(site_key, ()),
            )
            enriched = dict(row)
            enriched["initial_context"] = context
            rows.append(enriched)
            totals["opportunities"] += 1
            classification = str(context.get("classification") or "unresolved")
            totals[classification] += 1
            cloak = str(row.get("target_prior_cloak") or "unknown")
            by_cloak[f"{cloak}:{classification}"] += 1
            if context.get("resolved") is not True:
                totals["initial_context_unresolved"] += 1
            if row.get("is_target_residual") is True:
                target_rows.append(enriched)

    examples = sorted(
        rows,
        key=lambda row: (
            0 if row.get("is_target_residual") else 1,
            int(row["game_id"]),
            int(row["battle_turn"]),
            int(row["attacker_ship_id"]),
            int(row["target_ship_id"]),
        ),
    )[: args.example_limit]

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            **_serialize(totals),
            "by_prior_cloak": _serialize(by_cloak),
            "base_attack_opportunity_summary": base.get("summary"),
            "target_residual_rows": len(target_rows),
        },
        "target_residual": target_rows,
        "examples": examples,
        "evidence_boundary": (
            "Queue-aware refinement of the Privateer Rob attack-opportunity population. It uses only the factual VCR order "
            "after the independently reconstructed opportunity has been created. The target and the factual first opponent "
            "of the same attacker are compared using canonical standard_battle_priority_key. The strongest skip shape is an "
            "attacker in the first factual VCR at the site while the Rob target has strictly higher standard target priority "
            "than the factual opponent. This gate does not infer attacker survival after a prior fight and therefore labels "
            "later-attacker cases separately. It does not treat T-1 iscloaked as effective cloak and does not change combat rules."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify Privateer Rob attack opportunities by initial factual queue position and target priority."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT PRIVATEER ROB INITIAL-DECISION AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("TARGET RESIDUAL:")
    for row in report["target_residual"]:
        print(row)
    print()
    print("EXAMPLES:")
    for row in report["examples"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: initial queue/rank context only; later attacker survival is intentionally not inferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
