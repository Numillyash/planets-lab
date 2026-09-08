from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records

RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
SPECIAL_GAME_ID = 591478
KILL_MISSION_ID = 3
INTERCEPT_MISSION_ID = 7


def _decode_turn(raw: bytes, member_name: str) -> dict[str, Any]:
    payload = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    parsed = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{member_name}: turn payload must be an object")
    return parsed


def _objects(record: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = record.get(key)
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _int(record: Mapping[str, Any] | None, key: str) -> int | None:
    if not isinstance(record, Mapping):
        return None
    return _intish(record.get(key))


def _ship_side(vcr: Mapping[str, Any], side: str) -> dict[str, Any] | None:
    raw = vcr.get(side)
    if not isinstance(raw, Mapping):
        return None
    hull_id = _int(raw, "hullid")
    ship_id = _int(raw, "objectid")
    if hull_id is None or hull_id <= 0 or ship_id is None:
        return None
    owner_key = "leftownerid" if side == "left" else "rightownerid"
    return {
        "ship_id": ship_id,
        "hull_id": hull_id,
        "owner_id": _int(vcr, owner_key),
    }


def _owner_raw(groups: Mapping[tuple[int, int], Any], turn: int, ship_id: int) -> tuple[int | None, Mapping[str, Any] | None]:
    owner_id, record = _owner_record(groups.get((turn, ship_id), ()))
    return owner_id, record.raw if record is not None else None


def _fc_kind(value: Any) -> tuple[str, int | None]:
    if not isinstance(value, str):
        return "missing", None
    if len(value) == 3 and value.isdigit() and 1 <= int(value) <= 999:
        return "strict_numeric", int(value)
    if value.isdigit():
        return "weird_numeric", None
    return "symbolic", None


def _priority_key(raw: Mapping[str, Any], ship_id: int) -> tuple[int, int, int]:
    kind, numeric = _fc_kind(raw.get("friendlycode"))
    if kind == "strict_numeric" and numeric is not None:
        return (0, numeric, ship_id)
    mission = _intish(raw.get("mission"))
    enemy = _intish(raw.get("enemy")) or 0
    kill = mission == KILL_MISSION_ID
    has_pe = enemy > 0
    if kill and has_pe:
        group = 1
    elif kill:
        group = 2
    elif has_pe:
        group = 3
    else:
        group = 4
    return (group, ship_id, 0)


def _can_initiate(raw: Mapping[str, Any], opponent_owner: int | None) -> bool:
    mission = _intish(raw.get("mission"))
    enemy = _intish(raw.get("enemy")) or 0
    return mission == KILL_MISSION_ID or (
        opponent_owner is not None and opponent_owner > 0 and enemy == opponent_owner
    )


def _priority_slice(left_raw: Mapping[str, Any], right_raw: Mapping[str, Any]) -> str:
    left_kind, _ = _fc_kind(left_raw.get("friendlycode"))
    right_kind, _ = _fc_kind(right_raw.get("friendlycode"))
    if left_kind == right_kind == "strict_numeric":
        return "numeric_vs_numeric"
    if "strict_numeric" in {left_kind, right_kind}:
        return "numeric_vs_standard"
    left_group = _priority_key(left_raw, 1)[0]
    right_group = _priority_key(right_raw, 1)[0]
    return "standard_same_group" if left_group == right_group else "standard_different_groups"


def _serialize(counter: Counter[Any]) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    }


def _scope(rows: list[dict[str, Any]], example_limit: int) -> dict[str, Any]:
    exclusions: Counter[str] = Counter()
    side_priority: Counter[str] = Counter()
    slices: dict[str, Counter[str]] = defaultdict(Counter)
    initiative: Counter[str] = Counter()
    single_initiator: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []

    for row in rows:
        reason = row.get("exclusion")
        if isinstance(reason, str):
            exclusions[reason] += 1
            continue
        left_raw = row["left_raw"]
        right_raw = row["right_raw"]
        left_id = int(row["left_ship_id"])
        right_id = int(row["right_ship_id"])
        left_key = _priority_key(left_raw, left_id)
        right_key = _priority_key(right_raw, right_id)
        if right_key < left_key:
            relation = "right_higher_priority"
        elif left_key < right_key:
            relation = "left_higher_priority"
        else:
            relation = "priority_tie"
        side_priority[relation] += 1
        slice_name = _priority_slice(left_raw, right_raw)
        slices[slice_name][relation] += 1

        left_can = _can_initiate(left_raw, row.get("right_owner"))
        right_can = _can_initiate(right_raw, row.get("left_owner"))
        if left_can and right_can:
            init = "both"
        elif left_can:
            init = "left_only"
            single_initiator["initiator_left"] += 1
        elif right_can:
            init = "right_only"
            single_initiator["initiator_right"] += 1
        else:
            init = "neither"
        initiative[init] += 1

        if (
            relation != "right_higher_priority"
            or init == "left_only"
        ) and len(examples) < example_limit:
            examples.append(
                {
                    "game_id": row["game_id"],
                    "turn": row["turn"],
                    "vcr_id": row["vcr_id"],
                    "left_ship_id": left_id,
                    "right_ship_id": right_id,
                    "left_owner": row["left_owner"],
                    "right_owner": row["right_owner"],
                    "left_mission": _intish(left_raw.get("mission")),
                    "right_mission": _intish(right_raw.get("mission")),
                    "left_enemy": _intish(left_raw.get("enemy")),
                    "right_enemy": _intish(right_raw.get("enemy")),
                    "left_fc": left_raw.get("friendlycode"),
                    "right_fc": right_raw.get("friendlycode"),
                    "left_priority": list(left_key),
                    "right_priority": list(right_key),
                    "priority_relation": relation,
                    "initiative": init,
                    "slice": slice_name,
                }
            )

    comparable = sum(side_priority.values())
    return {
        "candidate_single_ship_battles": len(rows),
        "exclusions": _serialize(exclusions),
        "comparable": comparable,
        "side_priority": _serialize(side_priority),
        "priority_slices": {key: _serialize(value) for key, value in sorted(slices.items())},
        "initiative": _serialize(initiative),
        "single_initiator_side": _serialize(single_initiator),
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
        members = turn_members(data)
        raw_members = read_archive_members(data, [member.name for member in members])
        seen: dict[tuple[int, int, int], dict[str, Any]] = {}

        for member in members:
            try:
                rst = _decode_turn(raw_members[member.name], member.name)
            except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            game = rst.get("game")
            game_id = _int(game, "id")
            game_turn = _int(game, "turn")
            if game_id is None or game_turn is None:
                continue
            for vcr in _objects(rst, "vcrs"):
                vcr_id = _int(vcr, "id")
                battle_turn = _int(vcr, "turn") or game_turn
                x = _int(vcr, "x")
                y = _int(vcr, "y")
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
            left = _ship_side(vcr, "left")
            right = _ship_side(vcr, "right")
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
            left_owner, left_raw = _owner_raw(ship_groups, before_turn, int(left["ship_id"]))
            right_owner, right_raw = _owner_raw(ship_groups, before_turn, int(right["ship_id"]))
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
            if _intish(left_raw.get("mission")) == INTERCEPT_MISSION_ID or _intish(right_raw.get("mission")) == INTERCEPT_MISSION_ID:
                row["exclusion"] = "priority_intercept_mission"
                all_rows.append(row)
                continue
            left_kind, _ = _fc_kind(left_raw.get("friendlycode"))
            right_kind, _ = _fc_kind(right_raw.get("friendlycode"))
            if "weird_numeric" in {left_kind, right_kind} or "missing" in {left_kind, right_kind}:
                row["exclusion"] = "noncanonical_numeric_or_missing_fc"
                all_rows.append(row)
                continue
            if left_raw.get("friendlycode") == right_raw.get("friendlycode"):
                row["exclusion"] = "matching_friendly_code"
                all_rows.append(row)
                continue
            row["left_raw"] = dict(left_raw)
            row["right_raw"] = dict(right_raw)
            all_rows.append(row)

    ordinary = [row for row in all_rows if row["game_id"] != SPECIAL_GAME_ID]
    special = [row for row in all_rows if row["game_id"] == SPECIAL_GAME_ID]
    return {
        "schema": "planets-lab.combat-host-single-battle-side-order-audit.v1",
        "read_only": True,
        "constants": {
            "kill_mission_id": KILL_MISSION_ID,
            "intercept_mission_id": INTERCEPT_MISSION_ID,
        },
        "scopes": {
            "ordinary": _scope(ordinary, args.example_limit),
            "game_591478": _scope(special, args.example_limit),
            "all": _scope(all_rows, args.example_limit),
        },
        "evidence_boundary": (
            "Single-VCR ship-only sites only. This compares factual left/right assignment with the documented "
            "standard battle-priority key and independently reports Kill/PE initiation. It does not model "
            "opponent selection, diplomacy, matching-FC exceptions, capture reinsertion or Priority Intercept."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit left/right side assignment against standard battle priority on isolated ship battles.")
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--example-limit", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST SINGLE-BATTLE SIDE / ORDER AUDIT =====")
    for name, scope in report["scopes"].items():
        print()
        print(f"===== {name} =====")
        for key in (
            "candidate_single_ship_battles",
            "exclusions",
            "comparable",
            "side_priority",
            "priority_slices",
            "initiative",
            "single_initiator_side",
        ):
            print(f"{key}: {scope[key]}")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: isolated side/order differential only; no full Host engagement queue is inferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
