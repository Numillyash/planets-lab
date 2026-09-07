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


def _decode_turn(raw: bytes, member_name: str) -> dict[str, Any]:
    payload = raw
    if payload[:2] == b"\x1f\x8b":
        payload = gzip.decompress(payload)
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


def _side(vcr: Mapping[str, Any], side: str) -> dict[str, Any] | None:
    raw = vcr.get(side)
    if not isinstance(raw, Mapping):
        return None
    hull = _int(raw, "hullid")
    ship_id = _int(raw, "objectid")
    if hull is None or hull <= 0 or ship_id is None:
        return None
    owner_key = "leftownerid" if side == "left" else "rightownerid"
    return {
        "ship_id": ship_id,
        "hull_id": hull,
        "owner_id": _int(vcr, owner_key),
        "x": _int(vcr, "x"),
        "y": _int(vcr, "y"),
    }


def _raw_position(raw: Mapping[str, Any]) -> tuple[int, int] | None:
    x = _intish(raw.get("x"))
    y = _intish(raw.get("y"))
    if x is None or y is None:
        return None
    return x, y


def _target_id(raw: Mapping[str, Any]) -> int | None:
    return _intish(
        raw.get(
            "mission1target",
            raw.get("mission1_target_id", raw.get("mission1targetid")),
        )
    )


def _candidate(
    ship_groups: Mapping[tuple[int, int], Any],
    *,
    archive_turn: int,
    side: Mapping[str, Any],
) -> dict[str, Any]:
    owner_id, record = _owner_record(ship_groups.get((archive_turn, int(side["ship_id"])), ()))
    if owner_id is None or record is None:
        return {"present": False}
    raw = record.raw
    raw_hull = _intish(raw.get("hullid", raw.get("hull_id")))
    raw_pos = _raw_position(raw)
    vcr_pos = (side.get("x"), side.get("y"))
    position_match = (
        raw_pos == vcr_pos
        if raw_pos is not None and all(isinstance(value, int) for value in vcr_pos)
        else None
    )
    return {
        "present": True,
        "owner_match": owner_id == side.get("owner_id") if side.get("owner_id") is not None else None,
        "hull_match": raw_hull == side.get("hull_id") if raw_hull is not None else None,
        "position_match": position_match,
        "mission_present": _intish(raw.get("mission")) is not None,
        "mission": _intish(raw.get("mission")),
        "target_present": _target_id(raw) is not None,
        "friendlycode_present": isinstance(raw.get("friendlycode"), str),
    }


def _scope(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"ship_sides": len(rows)}
    for label in ("t_minus_1", "t"):
        present = Counter()
        owner = Counter()
        hull = Counter()
        position = Counter()
        private = Counter()
        identity = Counter()
        identity_and_position = Counter()
        for row in rows:
            candidate = row[label]
            if not candidate.get("present"):
                present["missing"] += 1
                continue
            present["present"] += 1
            owner[str(candidate.get("owner_match"))] += 1
            hull[str(candidate.get("hull_match"))] += 1
            position[str(candidate.get("position_match"))] += 1
            private["mission"] += int(candidate.get("mission_present") is True)
            private["mission1target"] += int(candidate.get("target_present") is True)
            private["friendlycode"] += int(candidate.get("friendlycode_present") is True)

            identity_match = (
                candidate.get("owner_match") is True
                and candidate.get("hull_match") is True
            )
            identity["match" if identity_match else "not_match"] += 1
            full_match = identity_match and candidate.get("position_match") is True
            identity_and_position["match" if full_match else "not_match"] += 1

        result[label] = {
            "presence": dict(present),
            "owner_match": dict(owner),
            "hull_match": dict(hull),
            "position_match": dict(position),
            "private_fields_present": dict(private),
            "owner_hull_identity": dict(identity),
            "owner_hull_position": dict(identity_and_position),
        }
    return result


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
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
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        members = turn_members(data)
        raw_members = read_archive_members(data, [member.name for member in members])
        seen_vcrs: set[tuple[int, int, int]] = set()
        for member in members:
            try:
                rst = _decode_turn(raw_members[member.name], member.name)
            except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            game = rst.get("game")
            if not isinstance(game, Mapping):
                continue
            embedded_game_id = _int(game, "id")
            game_turn = _int(game, "turn")
            if embedded_game_id is None or game_turn is None:
                continue
            for vcr in _objects(rst, "vcrs"):
                vcr_id = _int(vcr, "id")
                battle_turn = _int(vcr, "turn") or game_turn
                if vcr_id is None:
                    continue
                key = (embedded_game_id, battle_turn, vcr_id)
                if key in seen_vcrs:
                    continue
                seen_vcrs.add(key)
                for side_name in ("left", "right"):
                    side = _side(vcr, side_name)
                    if side is None:
                        continue
                    rows.append(
                        {
                            "game_id": embedded_game_id,
                            "turn": battle_turn,
                            "vcr_id": vcr_id,
                            "side": side_name,
                            "ship_id": side["ship_id"],
                            "owner_id": side["owner_id"],
                            "t_minus_1": _candidate(
                                ship_groups,
                                archive_turn=battle_turn - 1,
                                side=side,
                            ),
                            "t": _candidate(
                                ship_groups,
                                archive_turn=battle_turn,
                                side=side,
                            ),
                        }
                    )

    ordinary = [row for row in rows if row["game_id"] != SPECIAL_GAME_ID]
    special = [row for row in rows if row["game_id"] == SPECIAL_GAME_ID]
    return {
        "schema": "planets-lab.combat-host-snapshot-alignment-audit.v2",
        "read_only": True,
        "evidence_boundary": (
            "Owner+hull identity is the alignment criterion. Position is reported separately "
            "because T-1 snapshots precede movement while VCR positions are post-movement."
        ),
        "summary": {"archives": len(archives), "ship_sides": len(rows)},
        "scopes": {
            "ordinary": _scope(ordinary),
            "game_591478": _scope(special),
            "all": _scope(rows),
        },
        "examples": rows[: args.example_limit],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare candidate T-1 and T owner-visible ship snapshots to factual VCR ship sides."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--example-limit", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT SNAPSHOT ALIGNMENT AUDIT =====")
    print(f"summary: {report['summary']}")
    for scope_name, scope in report["scopes"].items():
        print()
        print(f"===== {scope_name} =====")
        print(f"ship_sides: {scope['ship_sides']}")
        for label in ("t_minus_1", "t"):
            print(f"{label}: {scope[label]}")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: alignment only; no mission/PE/FC combat causality is inferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
