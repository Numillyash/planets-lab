from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.combat.order import orders_request_ship_combat, standard_battle_priority_key

from combat_host_mission7_matched_control_audit import _dedup_vcrs
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR, _int, _owner_raw, _ship_side


TARGETS = {
    (620917, 7, 6),
    (621896, 25, 52),
}


def _pair(left_ship_id: int, right_ship_id: int) -> tuple[int, int]:
    return tuple(sorted((left_ship_id, right_ship_id)))


def _pair_occurrence_context(
    rows: Sequence[Mapping[str, Any]],
    *,
    target_vcr_id: int,
    target_pair: tuple[int, int],
) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: int(row["vcr_id"]))
    matching = [row for row in ordered if tuple(row["pair"]) == target_pair]
    ids = [int(row["vcr_id"]) for row in matching]
    index = ids.index(target_vcr_id)
    return {
        "site_ship_vcr_ids": [int(row["vcr_id"]) for row in ordered],
        "same_pair_vcr_ids": ids,
        "same_pair_count": len(ids),
        "same_pair_occurrence_index": index + 1,
        "prior_same_pair_vcr_ids": ids[:index],
        "later_same_pair_vcr_ids": ids[index + 1 :],
        "is_repeated_pair": len(ids) > 1,
        "is_second_or_later_same_pair": index > 0,
    }


def _side_projection(
    *,
    ship_id: int,
    owner_id: int,
    raw: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if raw is None:
        return {
            "ship_id": ship_id,
            "owner_id": owner_id,
            "tminus1_found": False,
            "battle_priority_key": None,
        }
    mission = _intish(raw.get("mission"))
    enemy = _intish(raw.get("enemy"))
    return {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "tminus1_found": True,
        "mission": mission,
        "mission1target": _intish(raw.get("mission1target")),
        "enemy": enemy,
        "friendlycode": raw.get("friendlycode") if isinstance(raw.get("friendlycode"), str) else None,
        "battle_priority_key": standard_battle_priority_key(
            ship_id=ship_id,
            mission=mission,
            primary_enemy=enemy,
            friendly_code=raw.get("friendlycode"),
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    target_games = {game_id for game_id, _turn, _vcr in TARGETS}
    result_rows: list[dict[str, Any]] = []
    payload_conflicts = 0

    for archive_path in sorted(args.archive_dir.glob("game-*.zip")):
        try:
            game_id = int(archive_path.stem.split("-")[-1])
        except ValueError:
            continue
        if game_id not in target_games:
            continue

        archive_data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=args.prepared_dir / f"game-{game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        seen, conflicts = _dedup_vcrs(archive_data)
        payload_conflicts += conflicts

        sites: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
        target_rows: dict[tuple[int, int, int], dict[str, Any]] = {}

        for (seen_game, battle_turn, vcr_id), (_digest, vcr) in sorted(seen.items()):
            if seen_game != game_id:
                continue
            left = _ship_side(vcr, "left")
            right = _ship_side(vcr, "right")
            x = _int(vcr, "x")
            y = _int(vcr, "y")
            if left is None or right is None or x is None or y is None:
                continue
            left_id = int(left["ship_id"])
            right_id = int(right["ship_id"])
            row = {
                "vcr_id": int(vcr_id),
                "left_ship_id": left_id,
                "right_ship_id": right_id,
                "pair": _pair(left_id, right_id),
            }
            sites[(int(battle_turn), int(x), int(y))].append(row)
            key = (game_id, int(battle_turn), int(vcr_id))
            if key in TARGETS:
                target_rows[key] = {
                    "vcr": vcr,
                    "left": left,
                    "right": right,
                    "x": int(x),
                    "y": int(y),
                }

        for key in sorted(TARGETS):
            if key[0] != game_id:
                continue
            target = target_rows.get(key)
            if target is None:
                result_rows.append({"game_id": key[0], "battle_turn": key[1], "vcr_id": key[2], "found": False})
                continue

            battle_turn = key[1]
            vcr_id = key[2]
            left = target["left"]
            right = target["right"]
            left_id = int(left["ship_id"])
            right_id = int(right["ship_id"])
            left_owner = int(left["owner_id"])
            right_owner = int(right["owner_id"])
            before_turn = battle_turn - 1
            left_owner_t1, left_raw = _owner_raw(ship_groups, before_turn, left_id)
            right_owner_t1, right_raw = _owner_raw(ship_groups, before_turn, right_id)
            site_rows = sites[(battle_turn, target["x"], target["y"])]
            occurrence = _pair_occurrence_context(
                site_rows,
                target_vcr_id=vcr_id,
                target_pair=_pair(left_id, right_id),
            )

            left_projection = _side_projection(
                ship_id=left_id,
                owner_id=left_owner,
                raw=left_raw if left_owner_t1 == left_owner else None,
            )
            right_projection = _side_projection(
                ship_id=right_id,
                owner_id=right_owner,
                raw=right_raw if right_owner_t1 == right_owner else None,
            )
            if left_raw is not None:
                left_projection["requests_factual_opponent"] = orders_request_ship_combat(
                    mission=_intish(left_raw.get("mission")),
                    primary_enemy=_intish(left_raw.get("enemy")),
                    opponent_owner_id=right_owner,
                )
            if right_raw is not None:
                right_projection["requests_factual_opponent"] = orders_request_ship_combat(
                    mission=_intish(right_raw.get("mission")),
                    primary_enemy=_intish(right_raw.get("enemy")),
                    opponent_owner_id=left_owner,
                )

            result_rows.append(
                {
                    "game_id": game_id,
                    "battle_turn": battle_turn,
                    "vcr_id": vcr_id,
                    "found": True,
                    "x": target["x"],
                    "y": target["y"],
                    "factual_pair": [left_id, right_id],
                    "left": left_projection,
                    "right": right_projection,
                    "site_queue": site_rows,
                    **occurrence,
                }
            )

    return {
        "schema": "planets-lab.combat-host-factual-queue-side-residual-audit.v1",
        "read_only": True,
        "payload_conflicts": payload_conflicts,
        "targets": result_rows,
        "evidence_boundary": (
            "Targeted follow-up for the two standard side residuals from the factual-positive queue audit. "
            "It inventories whether the same ship pair appears more than once in the same battle-turn/location "
            "queue, because repeated combat after timeout is queue-history dependent and cannot be inferred from "
            "a static pair priority key alone. No new side rule is inferred by this diagnostic."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect the two factual queue standard side residuals.")
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT FACTUAL QUEUE SIDE RESIDUAL AUDIT =====")
    print(f"payload_conflicts: {report['payload_conflicts']}")
    for row in report["targets"]:
        print()
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: targeted queue-history diagnostic only; no new universal side rule is inferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
