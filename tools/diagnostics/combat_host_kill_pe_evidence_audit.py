from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
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
PLANET_ATTACK_FCS = frozenset({"att", "nuk"})


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


def _normalize_fc(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip().lower()


def _split_ship_planet(vcr: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    sides: list[dict[str, Any]] = []
    for side_name in ("left", "right"):
        raw = vcr.get(side_name)
        if not isinstance(raw, Mapping):
            return None
        hull_id = _int(raw, "hullid")
        object_id = _int(raw, "objectid")
        if hull_id is None or object_id is None:
            return None
        owner_key = "leftownerid" if side_name == "left" else "rightownerid"
        sides.append(
            {
                "side": side_name,
                "kind": "ship" if hull_id > 0 else "planet",
                "object_id": object_id,
                "hull_id": hull_id,
                "owner_id": _int(vcr, owner_key),
            }
        )
    kinds = {side["kind"] for side in sides}
    if kinds != {"ship", "planet"}:
        return None
    ship = next(side for side in sides if side["kind"] == "ship")
    planet = next(side for side in sides if side["kind"] == "planet")
    return ship, planet


def _owner_raw(groups: Mapping[tuple[int, int], Any], turn: int, object_id: int) -> tuple[int | None, Mapping[str, Any] | None]:
    owner_id, record = _owner_record(groups.get((turn, object_id), ()))
    return owner_id, record.raw if record is not None else None


def _classify_causal_row(row: Mapping[str, Any]) -> str:
    if not row.get("ship_aligned") or not row.get("planet_aligned"):
        return "alignment_excluded"
    ship_owner = row.get("ship_owner")
    planet_owner = row.get("planet_owner")
    if not isinstance(ship_owner, int) or not isinstance(planet_owner, int) or ship_owner == planet_owner:
        return "ownership_excluded"
    planet_fc = row.get("planet_fc")
    if planet_fc is None:
        return "planet_fc_missing"
    if planet_fc in PLANET_ATTACK_FCS:
        return "planet_attack_fc"
    enemy = row.get("enemy")
    if not isinstance(enemy, int):
        return "enemy_missing"
    if enemy <= 0:
        return "zero_enemy_nonhostile_planet"
    if enemy == planet_owner:
        return "enemy_matches_planet_owner_nonhostile_planet"
    return "enemy_other_nonhostile_planet"


def _serialize(counter: Counter[Any]) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    }


def _scope(rows: list[dict[str, Any]], example_limit: int) -> dict[str, Any]:
    classes: Counter[str] = Counter()
    zero_enemy_missions: Counter[int] = Counter()
    matching_enemy_missions: Counter[int] = Counter()
    other_enemy_missions: Counter[int] = Counter()
    examples: list[dict[str, Any]] = []

    for row in rows:
        causal = _classify_causal_row(row)
        classes[causal] += 1
        mission = row.get("mission")
        if causal == "zero_enemy_nonhostile_planet" and isinstance(mission, int):
            zero_enemy_missions[mission] += 1
        elif causal == "enemy_matches_planet_owner_nonhostile_planet" and isinstance(mission, int):
            matching_enemy_missions[mission] += 1
        elif causal == "enemy_other_nonhostile_planet" and isinstance(mission, int):
            other_enemy_missions[mission] += 1
        if causal in {
            "zero_enemy_nonhostile_planet",
            "enemy_matches_planet_owner_nonhostile_planet",
            "enemy_other_nonhostile_planet",
        } and len(examples) < example_limit:
            examples.append(
                {
                    key: row.get(key)
                    for key in (
                        "game_id",
                        "turn",
                        "vcr_id",
                        "ship_id",
                        "ship_owner",
                        "planet_id",
                        "planet_owner",
                        "mission",
                        "enemy",
                        "planet_fc",
                    )
                }
            )

    return {
        "ship_vs_planet_vcrs": len(rows),
        "causal_classes": _serialize(classes),
        "zero_enemy_nonhostile_mission_ids": _serialize(zero_enemy_missions),
        "enemy_matches_planet_owner_mission_ids": _serialize(matching_enemy_missions),
        "enemy_other_nonhostile_mission_ids": _serialize(other_enemy_missions),
        "examples": examples,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
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
        planet_groups = group_perspective_records(prepared.snapshots, "planet")

        members = turn_members(data)
        raw_members = read_archive_members(data, [member.name for member in members])
        seen: set[tuple[int, int, int]] = set()

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
                if vcr_id is None:
                    continue
                key = (game_id, battle_turn, vcr_id)
                if key in seen:
                    continue
                seen.add(key)

                split = _split_ship_planet(vcr)
                if split is None:
                    continue
                ship, planet = split
                before_turn = battle_turn - 1

                ship_owner, ship_raw = _owner_raw(ship_groups, before_turn, int(ship["object_id"]))
                planet_owner, planet_raw = _owner_raw(planet_groups, before_turn, int(planet["object_id"]))

                ship_hull = _intish(ship_raw.get("hullid", ship_raw.get("hull_id"))) if ship_raw is not None else None
                ship_aligned = (
                    ship_raw is not None
                    and ship_owner == ship.get("owner_id")
                    and ship_hull == ship.get("hull_id")
                )
                planet_aligned = (
                    planet_raw is not None
                    and planet_owner == planet.get("owner_id")
                )

                rows.append(
                    {
                        "game_id": game_id,
                        "turn": battle_turn,
                        "vcr_id": vcr_id,
                        "ship_id": ship["object_id"],
                        "ship_owner": ship.get("owner_id"),
                        "planet_id": planet["object_id"],
                        "planet_owner": planet.get("owner_id"),
                        "ship_aligned": ship_aligned,
                        "planet_aligned": planet_aligned,
                        "mission": _intish(ship_raw.get("mission")) if ship_raw is not None else None,
                        "enemy": _intish(ship_raw.get("enemy")) if ship_raw is not None else None,
                        "planet_fc": _normalize_fc(planet_raw.get("friendlycode")) if planet_raw is not None else None,
                    }
                )

    ordinary = [row for row in rows if row["game_id"] != SPECIAL_GAME_ID]
    special = [row for row in rows if row["game_id"] == SPECIAL_GAME_ID]
    return {
        "schema": "planets-lab.combat-host-kill-pe-evidence-audit.v1",
        "read_only": True,
        "summary": {"archives": len(archives), "ship_vs_planet_vcrs": len(rows)},
        "scopes": {
            "ordinary": _scope(ordinary, args.example_limit),
            "game_591478": _scope(special, args.example_limit),
            "all": _scope(rows, args.example_limit),
        },
        "evidence_boundary": (
            "The zero-enemy/non-ATT/NUK slice is a causal Kill-mission candidate, not a semantic mapping by itself. "
            "The enemy==planet-owner slice is independent corpus evidence for the raw Primary Enemy field."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mine ship-vs-planet VCRs for Kill-mission and Primary Enemy evidence.")
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--example-limit", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT KILL / PRIMARY ENEMY EVIDENCE AUDIT =====")
    print(f"summary: {report['summary']}")
    for name, scope in report["scopes"].items():
        print()
        print(f"===== {name} =====")
        for key in (
            "ship_vs_planet_vcrs",
            "causal_classes",
            "zero_enemy_nonhostile_mission_ids",
            "enemy_matches_planet_owner_mission_ids",
            "enemy_other_nonhostile_mission_ids",
        ):
            print(f"{key}: {scope[key]}")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: causal evidence mining only; no mission ID is promoted by this tool itself.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
