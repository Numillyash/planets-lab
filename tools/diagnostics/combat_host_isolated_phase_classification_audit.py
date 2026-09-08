from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import combat_host_single_battle_side_order_audit as base

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.data.nu_static import import_static_all
from planets_lab.rules.combat.order import (
    CLOAK_INTERCEPT_MISSION_ID,
    INTERCEPT_MISSION_ID,
    FriendlyCodePriorityKind,
    classify_battle_friendly_code,
    cloak_intercept_order_signature,
    standard_battle_priority_key,
)


RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
SPECIAL_GAME_ID = 591478


def _static_specs(data: bytes, members: Sequence[Any], raw_members: Mapping[str, bytes]) -> NuStaticSpecs:
    if not members:
        raise ValueError("archive contains no turn members")
    first = members[0]
    rst = base._decode_turn(raw_members[first.name], first.name)
    return NuStaticSpecs.from_catalog(import_static_all(rst))


def _player_races(snapshots: Sequence[Any]) -> dict[int, int]:
    values: dict[int, set[int]] = defaultdict(set)
    for snapshot in snapshots:
        players = snapshot.mechanics_payload.get("players", [])
        if not isinstance(players, list):
            continue
        for raw in players:
            if not isinstance(raw, Mapping):
                continue
            player_id = _intish(raw.get("id"))
            race_id = _intish(raw.get("raceid"))
            if player_id is None or player_id <= 0 or race_id is None or race_id <= 0:
                continue
            values[player_id].add(race_id)
    return {
        player_id: next(iter(races))
        for player_id, races in values.items()
        if len(races) == 1
    }


def _target_owner(
    ship_groups: Mapping[tuple[int, int], Any],
    turn: int,
    target_id: int | None,
) -> int | None:
    if target_id is None or target_id <= 0:
        return None
    owner_id, raw = base._owner_raw(ship_groups, turn, target_id)
    return owner_id if raw is not None else None


def _c_and_i_classification(
    *,
    raw: Mapping[str, Any],
    ship_id: int,
    opponent_ship_id: int,
    owner_race_id: int | None,
    hull_can_cloak: bool | None,
    target_owner_id: int | None,
) -> str:
    mission = _intish(raw.get("mission"))
    if mission != CLOAK_INTERCEPT_MISSION_ID:
        return "not_c_and_i"

    target_id = _intish(raw.get("mission1target"))
    signature = cloak_intercept_order_signature(
        mission=mission,
        owner_race_id=owner_race_id,
        mission_target_id=target_id,
        primary_enemy=_intish(raw.get("enemy")),
        target_owner_id=target_owner_id,
        hull_can_cloak=hull_can_cloak,
    )
    if signature is None:
        return "signature_unknown"
    if not signature:
        return "signature_false"
    if target_id == opponent_ship_id:
        return "targets_factual_opponent"
    if target_id == ship_id:
        return "targets_self"
    return "targets_other_ship"


def _standard_fc_supported(raw: Mapping[str, Any]) -> bool:
    return classify_battle_friendly_code(raw.get("friendlycode")).kind is not FriendlyCodePriorityKind.UNSUPPORTED


def _standard_relation(
    *,
    left_raw: Mapping[str, Any],
    right_raw: Mapping[str, Any],
    left_ship_id: int,
    right_ship_id: int,
) -> tuple[str, tuple[int, int, int] | None, tuple[int, int, int] | None]:
    left_key = standard_battle_priority_key(
        ship_id=left_ship_id,
        mission=_intish(left_raw.get("mission")),
        primary_enemy=_intish(left_raw.get("enemy")),
        friendly_code=left_raw.get("friendlycode"),
    )
    right_key = standard_battle_priority_key(
        ship_id=right_ship_id,
        mission=_intish(right_raw.get("mission")),
        primary_enemy=_intish(right_raw.get("enemy")),
        friendly_code=right_raw.get("friendlycode"),
    )
    if left_key is None or right_key is None:
        return "unsupported", left_key, right_key
    if right_key < left_key:
        return "right_higher_priority", left_key, right_key
    if left_key < right_key:
        return "left_higher_priority", left_key, right_key
    return "priority_tie", left_key, right_key


def _serialize(counter: Counter[Any]) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    }


def _scope(rows: Sequence[Mapping[str, Any]], example_limit: int) -> dict[str, Any]:
    exclusions: Counter[str] = Counter()
    phases: Counter[str] = Counter()
    standard_relations: Counter[str] = Counter()
    c_and_i_sides: Counter[str] = Counter()
    c_and_i_signatures: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []

    for row in rows:
        exclusion = row.get("exclusion")
        if isinstance(exclusion, str):
            exclusions[exclusion] += 1
            continue

        left_ci = str(row["left_c_and_i"])
        right_ci = str(row["right_c_and_i"])
        c_and_i_signatures[f"left:{left_ci}"] += 1
        c_and_i_signatures[f"right:{right_ci}"] += 1

        left_targets = left_ci == "targets_factual_opponent"
        right_targets = right_ci == "targets_factual_opponent"
        has_intercept = bool(row.get("has_intercept_mission"))

        if (left_targets or right_targets) and has_intercept:
            phases["mixed_prestandard_unresolved"] += 1
            exclusions["mixed_c_and_i_priority_intercept_unresolved"] += 1
            if len(examples) < example_limit:
                examples.append(
                    {
                        **row,
                        "classification": "mixed_prestandard_unresolved",
                        "relation": "c_and_i_and_mission7_present",
                    }
                )
            continue

        if left_targets or right_targets:
            phases["cloak_intercept_pre_standard"] += 1
            if left_targets and right_targets:
                side = "both_target_each_other"
            elif left_targets:
                side = "c_and_i_left"
            else:
                side = "c_and_i_right"
            c_and_i_sides[side] += 1
            if len(examples) < example_limit:
                examples.append({**row, "classification": "cloak_intercept_pre_standard", "relation": side})
            continue

        if has_intercept:
            phases["priority_intercept_unresolved"] += 1
            exclusions["priority_intercept_unresolved"] += 1
            continue

        if left_ci == "signature_unknown" or right_ci == "signature_unknown":
            phases["c_and_i_unknown"] += 1
            exclusions["c_and_i_signature_unknown"] += 1
            continue

        if not _standard_fc_supported(row["left_raw"]) or not _standard_fc_supported(row["right_raw"]):
            phases["standard_unsupported_fc"] += 1
            exclusions["unsupported_numeric_fc"] += 1
            continue

        if row["left_raw"].get("friendlycode") == row["right_raw"].get("friendlycode"):
            phases["matching_fc_unresolved"] += 1
            exclusions["matching_friendly_code"] += 1
            continue

        relation, left_key, right_key = _standard_relation(
            left_raw=row["left_raw"],
            right_raw=row["right_raw"],
            left_ship_id=int(row["left_ship_id"]),
            right_ship_id=int(row["right_ship_id"]),
        )
        phases["standard"] += 1
        standard_relations[relation] += 1
        if relation != "right_higher_priority" and len(examples) < example_limit:
            examples.append(
                {
                    **row,
                    "classification": "standard",
                    "relation": relation,
                    "left_priority": list(left_key) if left_key is not None else None,
                    "right_priority": list(right_key) if right_key is not None else None,
                }
            )

    return {
        "candidate_single_ship_battles": len(rows),
        "phases": _serialize(phases),
        "exclusions": _serialize(exclusions),
        "standard_side_priority": _serialize(standard_relations),
        "cloak_intercept_factual_side": _serialize(c_and_i_sides),
        "cloak_intercept_signatures": _serialize(c_and_i_signatures),
        "examples": examples,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    all_rows: list[dict[str, Any]] = []
    archives = sorted(args.archive_dir.glob("game-*.zip"))

    for archive_path in archives:
        try:
            archive_game_id = int(archive_path.stem.split("-")[-1])
        except ValueError:
            continue
        data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            data,
            game_id=archive_game_id,
            cache_path=args.prepared_dir / f"game-{archive_game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        races = _player_races(prepared.snapshots)
        members = turn_members(data)
        raw_members = read_archive_members(data, [member.name for member in members])
        specs = _static_specs(data, members, raw_members)

        seen: dict[tuple[int, int, int], dict[str, Any]] = {}
        for member in members:
            try:
                rst = base._decode_turn(raw_members[member.name], member.name)
            except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            game = rst.get("game")
            game_id = base._int(game, "id")
            game_turn = base._int(game, "turn")
            if game_id is None or game_turn is None:
                continue
            for vcr in base._objects(rst, "vcrs"):
                vcr_id = base._int(vcr, "id")
                battle_turn = base._int(vcr, "turn") or game_turn
                x = base._int(vcr, "x")
                y = base._int(vcr, "y")
                if vcr_id is None or x is None or y is None:
                    continue
                key = (game_id, battle_turn, vcr_id)
                if key not in seen:
                    seen[key] = {"vcr": vcr, "x": x, "y": y}

        sites: dict[tuple[int, int, int, int], list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
        for (game_id, turn, vcr_id), item in seen.items():
            sites[(game_id, turn, int(item["x"]), int(item["y"]))].append((vcr_id, item["vcr"]))

        for (game_id, turn, _x, _y), queue in sites.items():
            if len(queue) != 1:
                continue
            vcr_id, vcr = queue[0]
            left = base._ship_side(vcr, "left")
            right = base._ship_side(vcr, "right")
            if left is None or right is None:
                continue

            row: dict[str, Any] = {
                "game_id": game_id,
                "turn": turn,
                "vcr_id": vcr_id,
                "left_ship_id": left["ship_id"],
                "right_ship_id": right["ship_id"],
                "left_owner": left["owner_id"],
                "right_owner": right["owner_id"],
            }
            if left["owner_id"] is None or right["owner_id"] is None or left["owner_id"] == right["owner_id"]:
                row["exclusion"] = "same_or_missing_owner"
                all_rows.append(row)
                continue

            before_turn = turn - 1
            left_owner, left_raw = base._owner_raw(ship_groups, before_turn, int(left["ship_id"]))
            right_owner, right_raw = base._owner_raw(ship_groups, before_turn, int(right["ship_id"]))
            if left_raw is None or right_raw is None:
                row["exclusion"] = "t_minus_1_missing"
                all_rows.append(row)
                continue

            left_hull = _intish(left_raw.get("hullid", left_raw.get("hull_id")))
            right_hull = _intish(right_raw.get("hullid", right_raw.get("hull_id")))
            if (
                left_owner != left["owner_id"]
                or right_owner != right["owner_id"]
                or left_hull != left["hull_id"]
                or right_hull != right["hull_id"]
            ):
                row["exclusion"] = "t_minus_1_identity_mismatch"
                all_rows.append(row)
                continue

            left_target = _intish(left_raw.get("mission1target"))
            right_target = _intish(right_raw.get("mission1target"))
            left_target_owner = _target_owner(ship_groups, before_turn, left_target)
            right_target_owner = _target_owner(ship_groups, before_turn, right_target)
            left_spec = specs.hulls.get(int(left_hull)) if left_hull is not None else None
            right_spec = specs.hulls.get(int(right_hull)) if right_hull is not None else None

            row.update(
                {
                    "left_raw": dict(left_raw),
                    "right_raw": dict(right_raw),
                    "left_race": races.get(int(left_owner)) if left_owner is not None else None,
                    "right_race": races.get(int(right_owner)) if right_owner is not None else None,
                    "left_hull_can_cloak": left_spec.can_cloak if left_spec is not None else None,
                    "right_hull_can_cloak": right_spec.can_cloak if right_spec is not None else None,
                    "left_target_owner": left_target_owner,
                    "right_target_owner": right_target_owner,
                    "has_intercept_mission": (
                        _intish(left_raw.get("mission")) == INTERCEPT_MISSION_ID
                        or _intish(right_raw.get("mission")) == INTERCEPT_MISSION_ID
                    ),
                }
            )
            row["left_c_and_i"] = _c_and_i_classification(
                raw=left_raw,
                ship_id=int(left["ship_id"]),
                opponent_ship_id=int(right["ship_id"]),
                owner_race_id=row["left_race"],
                hull_can_cloak=row["left_hull_can_cloak"],
                target_owner_id=left_target_owner,
            )
            row["right_c_and_i"] = _c_and_i_classification(
                raw=right_raw,
                ship_id=int(right["ship_id"]),
                opponent_ship_id=int(left["ship_id"]),
                owner_race_id=row["right_race"],
                hull_can_cloak=row["right_hull_can_cloak"],
                target_owner_id=right_target_owner,
            )
            all_rows.append(row)

    ordinary = [row for row in all_rows if row["game_id"] != SPECIAL_GAME_ID]
    special = [row for row in all_rows if row["game_id"] == SPECIAL_GAME_ID]
    return {
        "schema": "planets-lab.combat-host-isolated-phase-classification-audit.v1",
        "read_only": True,
        "scopes": {
            "ordinary": _scope(ordinary, args.example_limit),
            "game_591478": _scope(special, args.example_limit),
            "all": _scope(all_rows, args.example_limit),
        },
        "evidence_boundary": (
            "Single-VCR ship-only sites only. C&I is classified as pre-standard only when owner-visible T-1 state "
            "has mission 20, Bird race, a cloak-capable hull, a positive target, Primary Enemy matching target owner, "
            "and the target is the factual opponent in this VCR. Mission 7 remains unresolved/excluded, and sites "
            "containing both a qualified C&I target and mission 7 are explicitly unresolved. Standard ordering uses "
            "canonical C5 Friendly Code parsing and does not model engagement eligibility, diplomacy, matching-FC "
            "exceptions, capture reinsertion or multi-ship opponent selection."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify isolated factual ship battles into C&I pre-standard vs standard order buckets.")
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--example-limit", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST ISOLATED PHASE CLASSIFICATION AUDIT =====")
    for name, scope in report["scopes"].items():
        print()
        print(f"===== {name} =====")
        for key in (
            "candidate_single_ship_battles",
            "phases",
            "exclusions",
            "standard_side_priority",
            "cloak_intercept_factual_side",
            "cloak_intercept_signatures",
        ):
            print(f"{key}: {scope[key]}")
        print(f"examples: {len(scope['examples'])}")
        for row in scope["examples"]:
            print(
                f"  game={row['game_id']} turn={row['turn']} vcr={row['vcr_id']} "
                f"left={row['left_ship_id']} right={row['right_ship_id']} "
                f"class={row['classification']} relation={row['relation']} "
                f"left_ci={row.get('left_c_and_i')} right_ci={row.get('right_c_and_i')}"
            )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: isolated phase classification only; no full Host engagement queue is inferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
