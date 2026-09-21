from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import PerspectiveRecord, group_perspective_records

RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
SPECIAL_GAME_ID = 591478
MISSION_ID = 20
RESIDUAL_GAME_ID = 621253
RESIDUAL_ARCHIVE_TURN = 9
RESIDUAL_SHIP_ID = 57
RESIDUAL_OPPONENT_SHIP_ID = 50


def _player_races(snapshots: Sequence[Any]) -> tuple[dict[int, int], dict[int, tuple[int, ...]]]:
    values: dict[int, set[int]] = {}
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
            values.setdefault(player_id, set()).add(race_id)

    resolved: dict[int, int] = {}
    conflicts: dict[int, tuple[int, ...]] = {}
    for player_id, races in sorted(values.items()):
        if len(races) == 1:
            resolved[player_id] = next(iter(races))
        else:
            conflicts[player_id] = tuple(sorted(races))
    return resolved, conflicts


def _owner_raw(
    ship_groups: Mapping[tuple[int, int], Sequence[PerspectiveRecord]],
    turn: int,
    ship_id: int,
) -> tuple[int | None, Mapping[str, Any] | None]:
    owner_id, record = _owner_record(ship_groups.get((turn, ship_id), ()))
    return owner_id, record.raw if record is not None else None


def _target_signature(
    *,
    ship_owner: int | None,
    enemy: int | None,
    target_id: int | None,
    target_owner: int | None,
) -> tuple[str, str, str]:
    if target_id is None or target_id <= 0:
        return "zero_or_missing", "not_applicable", "not_applicable"
    target_status = "resolved" if target_owner is not None and target_owner > 0 else "unresolved"
    if target_status == "unresolved":
        return "positive", target_status, "target_owner_unknown"

    ownership = "same_owner" if ship_owner == target_owner else "other_owner"
    if enemy is None or enemy <= 0:
        enemy_relation = "enemy_zero"
    elif enemy == target_owner:
        enemy_relation = "enemy_matches_target_owner"
    else:
        enemy_relation = "enemy_other"
    return "positive", ownership, enemy_relation


def _safe_row(
    *,
    game_id: int,
    turn: int,
    ship_id: int,
    owner_id: int | None,
    owner_race_id: int | None,
    raw: Mapping[str, Any],
    target_owner: int | None,
    target_hull: int | None,
) -> dict[str, Any]:
    target_id = _intish(raw.get("mission1target"))
    enemy = _intish(raw.get("enemy"))
    target_presence, target_relation, enemy_relation = _target_signature(
        ship_owner=owner_id,
        enemy=enemy,
        target_id=target_id,
        target_owner=target_owner,
    )
    return {
        "game_id": game_id,
        "archive_turn": turn,
        "ship_id": ship_id,
        "owner_id": owner_id,
        "owner_race_id": owner_race_id,
        "hull_id": _intish(raw.get("hullid", raw.get("hull_id"))),
        "mission": _intish(raw.get("mission")),
        "mission1target": target_id,
        "mission2target": _intish(raw.get("mission2target")),
        "enemy": enemy,
        "friendlycode": raw.get("friendlycode") if isinstance(raw.get("friendlycode"), str) else None,
        "iscloaked": raw.get("iscloaked") if isinstance(raw.get("iscloaked"), (bool, int)) else None,
        "target_owner_id": target_owner,
        "target_hull_id": target_hull,
        "target_presence": target_presence,
        "target_relation": target_relation,
        "enemy_relation": enemy_relation,
    }


def _serialize(counter: Counter[Any]) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    }


def _scope(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    games = Counter(int(row["game_id"]) for row in rows)
    races = Counter(row.get("owner_race_id") for row in rows)
    hulls = Counter(row.get("hull_id") for row in rows)
    targets = Counter(row.get("target_presence") for row in rows)
    target_relations = Counter(row.get("target_relation") for row in rows)
    enemy_relations = Counter(row.get("enemy_relation") for row in rows)
    cloaked = Counter(str(row.get("iscloaked")) for row in rows)
    return {
        "records": len(rows),
        "games": _serialize(games),
        "owner_races": _serialize(races),
        "owner_hulls": _serialize(hulls),
        "target_presence": _serialize(targets),
        "target_relation": _serialize(target_relations),
        "enemy_relation": _serialize(enemy_relations),
        "iscloaked": _serialize(cloaked),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    race_conflicts: dict[int, dict[str, list[int]]] = {}
    archives = sorted(args.archive_dir.glob("game-*.zip"))

    for archive_path in archives:
        try:
            game_id = int(archive_path.stem.split("-")[-1])
        except ValueError:
            continue
        data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            data,
            game_id=game_id,
            cache_path=args.prepared_dir / f"game-{game_id}.pickle",
        )
        races, conflicts = _player_races(prepared.snapshots)
        if conflicts:
            race_conflicts[game_id] = {str(player): list(values) for player, values in conflicts.items()}

        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        for (turn, ship_id), group in sorted(ship_groups.items()):
            owner_id, owner_record = _owner_record(group)
            if owner_record is None or _intish(owner_record.raw.get("mission")) != MISSION_ID:
                continue
            raw = owner_record.raw
            target_id = _intish(raw.get("mission1target"))
            target_owner: int | None = None
            target_hull: int | None = None
            if target_id is not None and target_id > 0:
                target_owner, target_raw = _owner_raw(ship_groups, turn, target_id)
                if target_raw is not None:
                    target_hull = _intish(target_raw.get("hullid", target_raw.get("hull_id")))
            rows.append(
                _safe_row(
                    game_id=game_id,
                    turn=turn,
                    ship_id=ship_id,
                    owner_id=owner_id,
                    owner_race_id=races.get(owner_id) if owner_id is not None else None,
                    raw=raw,
                    target_owner=target_owner,
                    target_hull=target_hull,
                )
            )

    ordinary = [row for row in rows if row["game_id"] != SPECIAL_GAME_ID]
    special = [row for row in rows if row["game_id"] == SPECIAL_GAME_ID]
    residual = [
        row
        for row in rows
        if row["game_id"] == RESIDUAL_GAME_ID
        and row["archive_turn"] == RESIDUAL_ARCHIVE_TURN
        and row["ship_id"] == RESIDUAL_SHIP_ID
    ]
    residual_signature = {
        "found": len(residual),
        "rows": residual,
        "targets_expected_opponent": bool(
            len(residual) == 1 and residual[0].get("mission1target") == RESIDUAL_OPPONENT_SHIP_ID
        ),
    }

    return {
        "schema": "planets-lab.combat-host-mission20-cloak-intercept-audit.v1",
        "read_only": True,
        "mission_id": MISSION_ID,
        "summary": {
            "archives": len(archives),
            "records": len(rows),
            "race_conflict_games": len(race_conflicts),
        },
        "race_conflicts": race_conflicts,
        "scopes": {
            "ordinary": _scope(ordinary),
            "game_591478": _scope(special),
            "all": _scope(rows),
        },
        "residual_621253_t9_ship57": residual_signature,
        "evidence_boundary": (
            "Mission 20 is not semantically renamed by this diagnostic. It inventories whether owner-visible "
            "mission-20 records exhibit the documented Cloak-and-Intercept signature: a ship target, target-owner "
            "Primary Enemy match, and concentration in the relevant race/hull population. Special game 591478 "
            "is reported separately."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit the corpus signature of numeric mission 20 against Cloak and Intercept.")
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST MISSION 20 / CLOAK-AND-INTERCEPT SIGNATURE AUDIT =====")
    print(f"summary: {report['summary']}")
    if report["race_conflicts"]:
        print(f"race_conflicts: {report['race_conflicts']}")
    for name, scope in report["scopes"].items():
        print()
        print(f"===== {name} =====")
        for key in (
            "records",
            "games",
            "owner_races",
            "owner_hulls",
            "target_presence",
            "target_relation",
            "enemy_relation",
            "iscloaked",
        ):
            print(f"{key}: {scope[key]}")
    print()
    print("===== RESIDUAL 621253 / T9 / SHIP57 =====")
    residual = report["residual_621253_t9_ship57"]
    print(f"found: {residual['found']}")
    print(f"targets_expected_opponent: {residual['targets_expected_opponent']}")
    for row in residual["rows"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: mission-20 signature only; numeric mission semantics are not promoted by this tool itself.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
