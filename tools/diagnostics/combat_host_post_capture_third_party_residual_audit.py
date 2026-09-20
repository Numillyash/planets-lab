from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.combat.order import (
    orders_request_ship_combat,
    standard_battle_priority_key,
)

from combat_host_matching_fc_suppression_audit import (
    _relation_inventory,
    _relation_signature,
    _safe_signature,
)
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_mission7_matched_control_audit import _dedup_vcrs
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    _int,
    _owner_raw,
)


SCHEMA = "planets-lab.combat-host-post-capture-third-party-residual-audit.v1"
TARGET_GAME_ID = 622476
TARGET_BATTLE_TURN = 17
TARGET_X = 1973
TARGET_Y = 1734
CAPTURED_SHIP_ID = 7
CAPTOR_SHIP_ID = 44
NEXT_OPPONENT_SHIP_ID = 48
PRE_CAPTURE_OWNER_ID = 5
POST_CAPTURE_OWNER_ID = 3
THIRD_PARTY_OWNER_ID = 8


def _side_projection(vcr: Mapping[str, Any], side: str) -> dict[str, Any] | None:
    raw = vcr.get(side)
    if not isinstance(raw, Mapping):
        return None
    owner_key = "leftownerid" if side == "left" else "rightownerid"
    object_id = _int(raw, "objectid")
    hull_id = _int(raw, "hullid")
    owner_id = _int(vcr, owner_key)
    if object_id is None or hull_id is None or owner_id is None:
        return None
    return {
        "side": side,
        "object_id": object_id,
        "owner_id": owner_id,
        "hull_id": hull_id,
        "kind": "ship" if hull_id > 0 else "planet",
        "race_id": _int(raw, "raceid"),
        "shield": _int(raw, "shield"),
        "damage": _int(raw, "damage"),
        "crew": _int(raw, "crew"),
    }


def _ship_tminus1(
    *,
    ship_groups: Mapping[Any, Any],
    races: Mapping[int, int],
    ship_id: int,
) -> dict[str, Any]:
    owner_id, raw = _owner_raw(
        ship_groups,
        TARGET_BATTLE_TURN - 1,
        ship_id,
    )
    if owner_id is None or raw is None:
        return {
            "ship_id": ship_id,
            "found": False,
        }
    mission = _intish(raw.get("mission"))
    enemy = _intish(raw.get("enemy"))
    friendly_code = (
        raw.get("friendlycode")
        if isinstance(raw.get("friendlycode"), str)
        else None
    )
    return {
        "ship_id": ship_id,
        "found": True,
        "owner_id": owner_id,
        "race_id": races.get(owner_id),
        "hull_id": _intish(raw.get("hullid", raw.get("hull_id"))),
        "x": _intish(raw.get("x")),
        "y": _intish(raw.get("y")),
        "mission": mission,
        "mission1target": _intish(raw.get("mission1target")),
        "enemy": enemy,
        "friendlycode": friendly_code,
        "neutronium": _intish(raw.get("neutronium")),
        "iscloaked": (
            raw.get("iscloaked")
            if isinstance(raw.get("iscloaked"), bool)
            else None
        ),
        "damage": _intish(raw.get("damage")),
        "battle_priority_key": list(
            standard_battle_priority_key(
                ship_id=ship_id,
                mission=mission,
                primary_enemy=enemy,
                friendly_code=friendly_code,
            )
        ),
    }


def _request_matrix(
    ships: Mapping[int, Mapping[str, Any]],
    *,
    owners: tuple[int, ...],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ship_id, ship in sorted(ships.items()):
        if ship.get("found") is not True:
            continue
        owner_id = ship.get("owner_id")
        for target_owner_id in owners:
            if target_owner_id == owner_id:
                continue
            rows.append(
                {
                    "ship_id": ship_id,
                    "owner_id": owner_id,
                    "target_owner_id": target_owner_id,
                    "requests_combat": orders_request_ship_combat(
                        mission=ship.get("mission"),
                        primary_enemy=ship.get("enemy"),
                        opponent_owner_id=target_owner_id,
                    ),
                }
            )
    return rows


def run(args: argparse.Namespace) -> dict[str, Any]:
    archive_path = args.archive_dir / f"game-{TARGET_GAME_ID}.zip"
    archive_data = archive_path.read_bytes()
    prepared, _ = load_or_build_prepared_game_cache(
        archive_data,
        game_id=TARGET_GAME_ID,
        cache_path=args.prepared_dir / f"game-{TARGET_GAME_ID}.pickle",
    )
    ship_groups = group_perspective_records(prepared.snapshots, "ship")
    races, race_conflicts = _player_races(prepared.snapshots)
    relations = _relation_inventory(archive_data)
    seen, payload_conflicts = _dedup_vcrs(archive_data)

    site_queue: list[dict[str, Any]] = []
    ship_ids: set[int] = set()
    for (game_id, battle_turn, vcr_id), (_digest, vcr) in sorted(seen.items()):
        if game_id != TARGET_GAME_ID or battle_turn != TARGET_BATTLE_TURN:
            continue
        x = _int(vcr, "x")
        y = _int(vcr, "y")
        if x != TARGET_X or y != TARGET_Y:
            continue
        left = _side_projection(vcr, "left")
        right = _side_projection(vcr, "right")
        if left is None or right is None:
            continue
        site_queue.append(
            {
                "vcr_id": int(vcr_id),
                "left": left,
                "right": right,
            }
        )
        if left["kind"] == "ship":
            ship_ids.add(int(left["object_id"]))
        if right["kind"] == "ship":
            ship_ids.add(int(right["object_id"]))

    site_queue.sort(key=lambda row: int(row["vcr_id"]))

    ships = {
        ship_id: _ship_tminus1(
            ship_groups=ship_groups,
            races=races,
            ship_id=ship_id,
        )
        for ship_id in sorted(ship_ids)
    }
    owners = tuple(
        sorted(
            {
                int(ship["owner_id"])
                for ship in ships.values()
                if ship.get("found") is True
                and isinstance(ship.get("owner_id"), int)
                and not isinstance(ship.get("owner_id"), bool)
            }
            | {
                PRE_CAPTURE_OWNER_ID,
                POST_CAPTURE_OWNER_ID,
                THIRD_PARTY_OWNER_ID,
            }
        )
    )

    relation_rows = relations.get(TARGET_BATTLE_TURN - 1, {})
    relation_signatures: dict[str, Any] = {}
    for index, owner_a in enumerate(owners):
        for owner_b in owners[index + 1 :]:
            relation_signatures[f"{owner_a}<->{owner_b}"] = _safe_signature(
                _relation_signature(relation_rows, owner_a, owner_b)
            )

    requests = _request_matrix(ships, owners=owners)

    def request(ship_id: int, target_owner_id: int) -> bool | None:
        for row in requests:
            if (
                row["ship_id"] == ship_id
                and row["target_owner_id"] == target_owner_id
            ):
                return bool(row["requests_combat"])
        return None

    factual_capture_vcr = next(
        (row for row in site_queue if int(row["vcr_id"]) == 37),
        None,
    )
    factual_next_vcr = next(
        (row for row in site_queue if int(row["vcr_id"]) == 38),
        None,
    )

    focus = {
        "captured_ship_id": CAPTURED_SHIP_ID,
        "captor_ship_id": CAPTOR_SHIP_ID,
        "next_opponent_ship_id": NEXT_OPPONENT_SHIP_ID,
        "pre_capture_owner_id": PRE_CAPTURE_OWNER_ID,
        "post_capture_owner_id": POST_CAPTURE_OWNER_ID,
        "third_party_owner_id": THIRD_PARTY_OWNER_ID,
        "captured_ship_old_orders_request_third_party": request(
            CAPTURED_SHIP_ID,
            THIRD_PARTY_OWNER_ID,
        ),
        "captor_orders_request_third_party": request(
            CAPTOR_SHIP_ID,
            THIRD_PARTY_OWNER_ID,
        ),
        "third_party_orders_request_post_capture_owner": request(
            NEXT_OPPONENT_SHIP_ID,
            POST_CAPTURE_OWNER_ID,
        ),
        "third_party_orders_request_pre_capture_owner": request(
            NEXT_OPPONENT_SHIP_ID,
            PRE_CAPTURE_OWNER_ID,
        ),
        "factual_capture_vcr": factual_capture_vcr,
        "factual_next_vcr": factual_next_vcr,
    }
    focus["third_party_independent_attack_candidate"] = (
        focus["third_party_orders_request_post_capture_owner"] is True
    )
    focus["old_orders_retained_attack_candidate"] = (
        focus["captured_ship_old_orders_request_third_party"] is True
    )

    acceptance = {
        "target_site_found": bool(site_queue),
        "capture_vcr_37_found": factual_capture_vcr is not None,
        "next_vcr_38_found": factual_next_vcr is not None,
        "payload_conflicts_absent": payload_conflicts == 0,
        "race_conflicts_absent": not race_conflicts,
        "focus_ships_have_tminus1_state": all(
            ships.get(ship_id, {}).get("found") is True
            for ship_id in (
                CAPTURED_SHIP_ID,
                CAPTOR_SHIP_ID,
                NEXT_OPPONENT_SHIP_ID,
            )
        ),
    }

    return {
        "schema": SCHEMA,
        "read_only": True,
        "target": {
            "game_id": TARGET_GAME_ID,
            "battle_turn": TARGET_BATTLE_TURN,
            "x": TARGET_X,
            "y": TARGET_Y,
        },
        "summary": {
            "payload_conflicts": payload_conflicts,
            "race_conflicts": race_conflicts,
            "site_vcr_count": len(site_queue),
            "site_ship_ids": sorted(ship_ids),
            "owners": list(owners),
            "acceptance": acceptance,
        },
        "site_queue": site_queue,
        "tminus1_ships": {
            str(ship_id): row for ship_id, row in sorted(ships.items())
        },
        "request_matrix": requests,
        "relation_signatures": relation_signatures,
        "focus": focus,
        "evidence_boundary": (
            "Targeted diagnostic for the sole third-party residual from the "
            "post-capture opponent population: game 622476 turn17 ship7, "
            "captured by ship44 and then fighting ship48. It inventories the "
            "full factual queue at the site, owner-current T-1 orders/PE/FC, "
            "static priorities and raw T-1 relation signatures. T-1 orders of "
            "the captured ship are reported as historical inputs only; this "
            "tool does not assume they survive capture. A positive independent "
            "attack request by ship48 against the new owner would explain the "
            "third-party continuation without requiring such an assumption. "
            "No production rule is promoted by this diagnostic."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect the sole third-party immediate opponent after combat capture."
        )
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT POST-CAPTURE THIRD-PARTY RESIDUAL =====")
    print("summary:", report["summary"])
    print()
    print("FOCUS:")
    print(report["focus"])
    print()
    print("SITE QUEUE:")
    for row in report["site_queue"]:
        print(row)
    print()
    print("T-1 SHIPS:")
    for ship_id, row in report["tminus1_ships"].items():
        print(ship_id, row)
    print()
    print("REQUEST MATRIX:")
    for row in report["request_matrix"]:
        print(row)
    print()
    print("RELATION SIGNATURES:")
    for key, value in report["relation_signatures"].items():
        print(key, value)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("output:", args.output)
    print(
        "NOTE: targeted residual only; no post-capture hostility/priority rule "
        "is promoted until this case is explained."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
