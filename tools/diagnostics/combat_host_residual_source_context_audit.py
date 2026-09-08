from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import PerspectiveRecord, group_perspective_records


RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")

SHIP_MECHANICAL_FIELDS = (
    "id",
    "ownerid",
    "hullid",
    "x",
    "y",
    "mission",
    "mission1target",
    "mission2target",
    "enemy",
    "friendlycode",
    "iscloaked",
    "warp",
    "targetx",
    "targety",
    "neutronium",
    "damage",
    "supplies",
    "beamid",
    "torpedoid",
    "beams",
    "torps",
    "bays",
    "ammo",
    "crew",
)

VCR_SIDE_MECHANICAL_FIELDS = (
    "objectid",
    "hullid",
    "raceid",
    "beamcount",
    "launchercount",
    "baycount",
    "beamid",
    "torpedoid",
    "shield",
    "damage",
    "crew",
    "mass",
    "torpedos",
    "fighters",
    "beamkillbonus",
    "beamchargerate",
    "torpchargerate",
    "torpmisspercent",
    "crewdefensepercent",
)

DEFAULT_CASE_TEXTS = (
    "511506:19:13:80:89",
    "621896:28:67:62:38",
)


@dataclass(frozen=True, slots=True)
class AuditCase:
    game_id: int
    battle_turn: int
    vcr_id: int
    ship_a: int
    ship_b: int

    @property
    def ship_ids(self) -> tuple[int, int]:
        return (self.ship_a, self.ship_b)


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


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


def _positive_int(value: Any) -> int | None:
    number = _intish(value)
    return number if number is not None and number > 0 else None


def _project_fields(raw: Mapping[str, Any], allowlist: Sequence[str]) -> dict[str, Any]:
    return {field: raw[field] for field in allowlist if field in raw}


def _project_ship_record(raw: Mapping[str, Any]) -> dict[str, Any]:
    fields = _project_fields(raw, SHIP_MECHANICAL_FIELDS)
    return {
        "fields": fields,
        "missing_fields": [field for field in SHIP_MECHANICAL_FIELDS if field not in raw],
    }


def _project_vcr_side(raw: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        return None
    fields = _project_fields(raw, VCR_SIDE_MECHANICAL_FIELDS)
    return {
        "fields": fields,
        "missing_fields": [field for field in VCR_SIDE_MECHANICAL_FIELDS if field not in raw],
    }


def _record_provenance(record: PerspectiveRecord) -> dict[str, Any]:
    raw_owner_id = _positive_int(record.raw.get("ownerid", record.raw.get("owner_id")))
    return {
        "perspective_player_id": record.player_id,
        "archive_turn": record.archive_turn,
        "embedded_turn": record.embedded_turn,
        "infoturn": record.infoturn,
        "freshness": "current" if record.is_current else "stale",
        "raw_owner_id": raw_owner_id,
        "owner_perspective": raw_owner_id == record.player_id,
    }


def _current_conflicts(records: Sequence[PerspectiveRecord]) -> dict[str, list[Any]]:
    current = [record for record in records if record.is_current]
    conflicts: dict[str, list[Any]] = {}
    for field in SHIP_MECHANICAL_FIELDS:
        values: dict[str, Any] = {}
        for record in current:
            if field not in record.raw:
                continue
            value = record.raw[field]
            if isinstance(value, (str, int, bool)) or value is None:
                values[repr(value)] = value
        if len(values) > 1:
            conflicts[field] = [values[key] for key in sorted(values)]
    return conflicts


def _snapshot_context(
    records: Sequence[PerspectiveRecord],
    *,
    ship_id: int,
    relative_turn: str,
    requested_archive_turn: int,
) -> dict[str, Any]:
    ordered = sorted(records, key=lambda record: (record.player_id, record.infoturn or -1))
    owner_visible: list[dict[str, Any]] = []
    for record in ordered:
        provenance = _record_provenance(record)
        if provenance["owner_perspective"]:
            owner_visible.append(
                {
                    **provenance,
                    **_project_ship_record(record.raw),
                }
            )

    current_owner_visible = [
        row for row in owner_visible if row["freshness"] == "current"
    ]
    return {
        "ship_id": ship_id,
        "relative_turn": relative_turn,
        "requested_archive_turn": requested_archive_turn,
        "perspective_count": len(ordered),
        "current_perspective_count": sum(record.is_current for record in ordered),
        "stale_perspective_count": sum(not record.is_current for record in ordered),
        "owner_visible_count": len(owner_visible),
        "current_owner_visible_count": len(current_owner_visible),
        "perspective_provenance": [_record_provenance(record) for record in ordered],
        "current_conflicts": _current_conflicts(ordered),
        "owner_visible_records": owner_visible,
    }


def _unique_current_owner_fields(snapshot: Mapping[str, Any]) -> Mapping[str, Any] | None:
    rows = [
        row
        for row in snapshot.get("owner_visible_records", [])
        if isinstance(row, Mapping) and row.get("freshness") == "current"
    ]
    if len(rows) != 1:
        return None
    fields = rows[0].get("fields")
    return fields if isinstance(fields, Mapping) else None


def _known_field_diff(
    before_snapshot: Mapping[str, Any],
    after_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    before = _unique_current_owner_fields(before_snapshot)
    after = _unique_current_owner_fields(after_snapshot)
    if before is None or after is None:
        return {
            "status": "not_comparable",
            "reason": "requires exactly one current owner-visible record on both archive turns",
        }

    overlap = sorted(set(before).intersection(after))
    changed = {
        field: {"before": before[field], "after": after[field]}
        for field in overlap
        if before[field] != after[field]
    }
    same = [field for field in overlap if before[field] == after[field]]
    return {
        "status": "comparable",
        "compared_fields": overlap,
        "changed": changed,
        "same_fields": same,
        "before_only": sorted(set(before).difference(after)),
        "after_only": sorted(set(after).difference(before)),
    }


def _member_provenance(member: Any, parsed: Mapping[str, Any]) -> dict[str, Any]:
    player = parsed.get("player")
    active_player_id = (
        _positive_int(player.get("id")) if isinstance(player, Mapping) else None
    )
    game = parsed.get("game")
    embedded_turn = _intish(game.get("turn")) if isinstance(game, Mapping) else None
    embedded_game_id = _intish(game.get("id")) if isinstance(game, Mapping) else None
    return {
        "archive_turn": int(member.turn),
        "member_player_id": int(member.player),
        "active_player_id": active_player_id,
        "embedded_turn": embedded_turn,
        "embedded_game_id": embedded_game_id,
    }


def _collect_factual_vcrs(
    archive_data: bytes,
    *,
    game_id: int,
    battle_turn: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    members = list(turn_members(archive_data))
    raw_members = read_archive_members(archive_data, [member.name for member in members])
    seen: dict[int, dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []

    for member in members:
        parsed = _decode_turn(raw_members[member.name], member.name)
        provenance = _member_provenance(member, parsed)
        if provenance["embedded_game_id"] != game_id:
            continue

        game_turn = provenance["embedded_turn"]
        for vcr in _objects(parsed, "vcrs"):
            vcr_id = _positive_int(vcr.get("id"))
            vcr_turn = _intish(vcr.get("turn")) or game_turn
            if vcr_id is None or vcr_turn != battle_turn:
                continue

            digest = _canonical_hash(vcr)
            existing = seen.get(vcr_id)
            if existing is None:
                seen[vcr_id] = {
                    "vcr_id": vcr_id,
                    "digest": digest,
                    "payload": vcr,
                    "provenance": [provenance],
                }
            elif existing["digest"] == digest:
                existing["provenance"].append(provenance)
            else:
                conflicts.append(
                    {
                        "vcr_id": vcr_id,
                        "first_digest": existing["digest"],
                        "conflicting_digest": digest,
                        "conflicting_provenance": provenance,
                    }
                )

    rows = [seen[key] for key in sorted(seen)]
    for row in rows:
        row["provenance"] = sorted(
            row["provenance"],
            key=lambda item: (
                item["member_player_id"],
                item["active_player_id"] or -1,
                item["embedded_turn"] or -1,
            ),
        )
    return rows, conflicts


def _side_ship_id(vcr: Mapping[str, Any], side: str) -> int | None:
    raw = vcr.get(side)
    if not isinstance(raw, Mapping):
        return None
    return _positive_int(raw.get("objectid"))


def _project_vcr_entry(row: Mapping[str, Any]) -> dict[str, Any]:
    vcr = row["payload"]
    assert isinstance(vcr, Mapping)
    return {
        "vcr_id": row["vcr_id"],
        "digest": row["digest"],
        "turn": _intish(vcr.get("turn")),
        "x": _intish(vcr.get("x")),
        "y": _intish(vcr.get("y")),
        "leftownerid": _positive_int(vcr.get("leftownerid")),
        "rightownerid": _positive_int(vcr.get("rightownerid")),
        "left": _project_vcr_side(vcr.get("left")),
        "right": _project_vcr_side(vcr.get("right")),
        "perspective_provenance": row["provenance"],
    }


def _ship_appearances(
    vcr_rows: Sequence[Mapping[str, Any]],
    *,
    ship_id: int,
    target_vcr_id: int,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in vcr_rows:
        vcr = row.get("payload")
        if not isinstance(vcr, Mapping):
            continue
        left_id = _side_ship_id(vcr, "left")
        right_id = _side_ship_id(vcr, "right")
        if ship_id not in {left_id, right_id}:
            continue
        side = "left" if left_id == ship_id else "right"
        other_side = "right" if side == "left" else "left"
        other_raw = vcr.get(other_side)
        other_id = (
            _positive_int(other_raw.get("objectid"))
            if isinstance(other_raw, Mapping)
            else None
        )
        vcr_id = int(row["vcr_id"])
        if vcr_id < target_vcr_id:
            position = "before_target_vcr"
        elif vcr_id == target_vcr_id:
            position = "target_vcr"
        else:
            position = "after_target_vcr"

        result.append(
            {
                "vcr_id": vcr_id,
                "relative_to_target": position,
                "x": _intish(vcr.get("x")),
                "y": _intish(vcr.get("y")),
                "side": side,
                "owner_id": _positive_int(
                    vcr.get("leftownerid" if side == "left" else "rightownerid")
                ),
                "opponent_side": other_side,
                "opponent_object_id": other_id,
                "opponent_owner_id": _positive_int(
                    vcr.get("rightownerid" if side == "left" else "leftownerid")
                ),
                "ship_combatant": _project_vcr_side(vcr.get(side)),
                "opponent_combatant": _project_vcr_side(other_raw),
                "perspective_provenance": row["provenance"],
            }
        )
    return sorted(result, key=lambda item: item["vcr_id"])


def _timeline_for_ship(
    ship_groups: Mapping[tuple[int, int], Sequence[PerspectiveRecord]],
    *,
    battle_turn: int,
    ship_id: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    turns = (
        ("T-2", battle_turn - 2),
        ("T-1", battle_turn - 1),
        ("T", battle_turn),
    )
    snapshots = [
        _snapshot_context(
            ship_groups.get((archive_turn, ship_id), ()),
            ship_id=ship_id,
            relative_turn=label,
            requested_archive_turn=archive_turn,
        )
        for label, archive_turn in turns
    ]
    diffs = [
        {
            "from": snapshots[index]["relative_turn"],
            "to": snapshots[index + 1]["relative_turn"],
            **_known_field_diff(snapshots[index], snapshots[index + 1]),
        }
        for index in range(len(snapshots) - 1)
    ]
    return snapshots, diffs


def _target_pair_matches(
    target_entry: Mapping[str, Any] | None,
    expected_ship_ids: Sequence[int],
) -> bool | None:
    if target_entry is None:
        return None
    payload = target_entry.get("payload")
    if not isinstance(payload, Mapping):
        return None
    actual = {_side_ship_id(payload, "left"), _side_ship_id(payload, "right")}
    actual.discard(None)
    return actual == set(expected_ship_ids)


def _audit_case(
    case: AuditCase,
    *,
    archive_dir: Path,
    prepared_dir: Path,
) -> dict[str, Any]:
    archive_path = archive_dir / f"game-{case.game_id}.zip"
    archive_data = archive_path.read_bytes()
    prepared, prepared_cache_status = load_or_build_prepared_game_cache(
        archive_data,
        game_id=case.game_id,
        cache_path=prepared_dir / f"game-{case.game_id}.pickle",
    )
    ship_groups = group_perspective_records(prepared.snapshots, "ship")
    vcr_rows, payload_conflicts = _collect_factual_vcrs(
        archive_data,
        game_id=case.game_id,
        battle_turn=case.battle_turn,
    )
    target_entry = next(
        (row for row in vcr_rows if int(row["vcr_id"]) == case.vcr_id),
        None,
    )

    ship_context: dict[str, Any] = {}
    relevant_vcr_ids: set[int] = set()
    relevant_locations: set[tuple[int | None, int | None]] = set()
    for ship_id in case.ship_ids:
        timeline, timeline_diffs = _timeline_for_ship(
            ship_groups,
            battle_turn=case.battle_turn,
            ship_id=ship_id,
        )
        appearances = _ship_appearances(
            vcr_rows,
            ship_id=ship_id,
            target_vcr_id=case.vcr_id,
        )
        for appearance in appearances:
            relevant_vcr_ids.add(int(appearance["vcr_id"]))
            relevant_locations.add((appearance["x"], appearance["y"]))
        ship_context[str(ship_id)] = {
            "timeline": timeline,
            "timeline_diffs": timeline_diffs,
            "same_turn_vcr_appearances": appearances,
        }

    target_projected = _project_vcr_entry(target_entry) if target_entry is not None else None
    relevant_vcrs = [
        _project_vcr_entry(row)
        for row in vcr_rows
        if int(row["vcr_id"]) in relevant_vcr_ids
    ]

    return {
        "case": {
            "game_id": case.game_id,
            "battle_turn": case.battle_turn,
            "target_vcr_id": case.vcr_id,
            "tracked_ship_ids": list(case.ship_ids),
        },
        "source": {
            "archive_path": str(archive_path),
            "prepared_cache_path": str(prepared_dir / f"game-{case.game_id}.pickle"),
            "prepared_cache_hit": prepared_cache_status,
        },
        "same_turn_vcr_summary": {
            "unique_vcrs": len(vcr_rows),
            "payload_conflicts": len(payload_conflicts),
            "target_vcr_found": target_entry is not None,
            "target_pair_matches_expected": _target_pair_matches(target_entry, case.ship_ids),
            "relevant_vcr_count": len(relevant_vcr_ids),
            "relevant_location_count": len(relevant_locations),
        },
        "payload_conflicts": payload_conflicts,
        "target_vcr": target_projected,
        "relevant_same_turn_vcrs": relevant_vcrs,
        "ships": ship_context,
    }


def _parse_case(text: str) -> AuditCase:
    parts = text.split(":")
    if len(parts) != 5:
        raise argparse.ArgumentTypeError(
            "case must be GAME:BATTLE_TURN:VCR_ID:SHIP_A:SHIP_B"
        )
    try:
        values = [int(part) for part in parts]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("case values must be integers") from exc
    if any(value <= 0 for value in values):
        raise argparse.ArgumentTypeError("case values must be positive")
    return AuditCase(*values)


def run(args: argparse.Namespace) -> dict[str, Any]:
    cases = args.case or [_parse_case(text) for text in DEFAULT_CASE_TEXTS]
    reports = [
        _audit_case(
            case,
            archive_dir=args.archive_dir,
            prepared_dir=args.prepared_dir,
        )
        for case in cases
    ]
    return {
        "schema": "planets-lab.combat-host-residual-source-context-audit.v1",
        "read_only": True,
        "summary": {
            "cases": len(reports),
            "target_vcrs_found": sum(
                bool(report["same_turn_vcr_summary"]["target_vcr_found"])
                for report in reports
            ),
            "payload_conflicts": sum(
                int(report["same_turn_vcr_summary"]["payload_conflicts"])
                for report in reports
            ),
        },
        "cases": reports,
        "evidence_boundary": (
            "Privacy-safe source-context diagnostic only. Ship snapshots are limited to an explicit mechanical "
            "allowlist and owner-visible records; non-owner perspectives contribute provenance/freshness and "
            "allowlisted current-conflict checks only. VCR payloads are limited to combat-mechanical fields. "
            "The report distinguishes archive turn, embedded turn and infoturn, and enumerates every same-turn "
            "VCR appearance of the tracked ships. It does not infer a Host rule, reinterpret Friendly Codes, "
            "or alter Priority Intercept eligibility."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect T-2/T-1/T owner-visible ship state and same-turn VCR context "
            "for the two ordinary non-PIA mission-7 residuals."
        )
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument(
        "--case",
        action="append",
        type=_parse_case,
        default=None,
        metavar="GAME:BATTLE_TURN:VCR_ID:SHIP_A:SHIP_B",
        help="repeat to override the two built-in residual cases",
    )
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT RESIDUAL SOURCE CONTEXT AUDIT =====")
    print(f"summary: {report['summary']}")
    for index, case in enumerate(report["cases"], start=1):
        meta = case["case"]
        summary = case["same_turn_vcr_summary"]
        print()
        print(
            f"CASE {index}: game={meta['game_id']} battle_turn={meta['battle_turn']} "
            f"target_vcr={meta['target_vcr_id']} ships={meta['tracked_ship_ids']}"
        )
        print(f"  vcr_summary: {summary}")
        target = case["target_vcr"]
        if target is not None:
            print(
                "  target_vcr: "
                f"pos=({target['x']},{target['y']}) "
                f"owners=({target['leftownerid']},{target['rightownerid']})"
            )
        for ship_id, context in case["ships"].items():
            print(f"  ship {ship_id}:")
            for snapshot in context["timeline"]:
                print(
                    "    "
                    f"{snapshot['relative_turn']} archive={snapshot['requested_archive_turn']} "
                    f"perspectives={snapshot['perspective_count']} "
                    f"current={snapshot['current_perspective_count']} "
                    f"owner_current={snapshot['current_owner_visible_count']} "
                    f"conflicts={snapshot['current_conflicts']}"
                )
                for owner_row in snapshot["owner_visible_records"]:
                    print(
                        "      owner-visible "
                        f"perspective={owner_row['perspective_player_id']} "
                        f"embedded={owner_row['embedded_turn']} infoturn={owner_row['infoturn']} "
                        f"freshness={owner_row['freshness']} fields={owner_row['fields']}"
                    )
            print(f"    timeline_diffs: {context['timeline_diffs']}")
            print(f"    same_turn_vcr_appearances: {context['same_turn_vcr_appearances']}")
        if case["payload_conflicts"]:
            print(f"  payload_conflicts: {case['payload_conflicts']}")

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print()
        print(f"output: {args.output}")

    print()
    print("NOTE: source-context audit only; no combat rule or evidence status is promoted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
