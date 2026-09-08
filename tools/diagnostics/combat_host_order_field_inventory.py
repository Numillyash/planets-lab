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


def _decode_turn(raw: bytes, member_name: str) -> dict[str, Any]:
    payload = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    parsed = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{member_name}: turn payload must be an object")
    return parsed


def _candidate_order_key(key: str) -> bool:
    lowered = key.lower()
    return (
        "mission" in lowered
        or "enemy" in lowered
        or "primary" in lowered
        or "friendly" in lowered
        or lowered in {"pe", "fc"}
    )


def _value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def _friendlycode_shape(value: Any) -> str:
    if not isinstance(value, str):
        return "missing_or_non_string"
    if value == "000":
        return "000"
    if len(value) == 3 and value.isdigit() and 1 <= int(value) <= 999:
        return "numeric_001_999"
    if value.isdigit():
        return f"numeric_other_len_{len(value)}"
    return "non_numeric"


def _serialize_counter(counter: Counter[Any], limit: int | None = None) -> dict[str, int]:
    items = sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    if limit is not None:
        items = items[:limit]
    return {str(key): int(value) for key, value in items}


def _catalog_inventory(rst: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, value in sorted(rst.items()):
        if "mission" not in key.lower():
            continue
        row: dict[str, Any] = {"key": key, "type": _value_type(value)}
        if isinstance(value, list):
            row["length"] = len(value)
            row["sample"] = value[:5]
        elif isinstance(value, dict):
            row["length"] = len(value)
            row["sample"] = list(value.items())[:5]
        else:
            row["sample"] = value
        rows.append(row)
    return rows


def run(args: argparse.Namespace) -> dict[str, Any]:
    archives = sorted(args.archive_dir.glob("game-*.zip"))
    raw_ship_records = 0
    owner_ship_records = 0
    mission_ids: Counter[int] = Counter()
    mission_targets: Counter[str] = Counter()
    fc_shapes: Counter[str] = Counter()
    numeric_fc_values: Counter[int] = Counter()
    candidate_presence: Counter[str] = Counter()
    candidate_types: dict[str, Counter[str]] = defaultdict(Counter)
    candidate_values: dict[str, Counter[str]] = defaultdict(Counter)
    catalog_rows: list[dict[str, Any]] = []
    catalog_seen: set[str] = set()

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
        raw_ship_records += sum(len(records) for records in ship_groups.values())

        for records in ship_groups.values():
            owner_id, owner_record = _owner_record(records)
            if owner_id is None or owner_record is None:
                continue
            owner_ship_records += 1
            raw = owner_record.raw

            mission = _intish(raw.get("mission"))
            if mission is not None:
                mission_ids[mission] += 1

            target = _intish(
                raw.get(
                    "mission1target",
                    raw.get("mission1_target_id", raw.get("mission1targetid")),
                )
            )
            mission_targets["positive"] += int(target is not None and target > 0)
            mission_targets["zero_or_negative"] += int(target is not None and target <= 0)
            mission_targets["missing"] += int(target is None)

            fc = raw.get("friendlycode")
            fc_shapes[_friendlycode_shape(fc)] += 1
            if isinstance(fc, str) and len(fc) == 3 and fc.isdigit() and 1 <= int(fc) <= 999:
                numeric_fc_values[int(fc)] += 1

            for key, value in raw.items():
                if not _candidate_order_key(str(key)):
                    continue
                key = str(key)
                candidate_presence[key] += 1
                candidate_types[key][_value_type(value)] += 1
                if value is None or isinstance(value, (bool, int, float, str)):
                    candidate_values[key][repr(value)] += 1

        members = turn_members(data)
        if members:
            raw_members = read_archive_members(data, [members[0].name])
            try:
                rst = _decode_turn(raw_members[members[0].name], members[0].name)
            except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
                rst = {}
            for row in _catalog_inventory(rst):
                signature = json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)
                if signature not in catalog_seen:
                    catalog_seen.add(signature)
                    catalog_rows.append({"game_id": game_id, **row})

    candidate_fields: dict[str, Any] = {}
    for key in sorted(candidate_presence):
        candidate_fields[key] = {
            "presence": int(candidate_presence[key]),
            "types": _serialize_counter(candidate_types[key]),
            "top_values": _serialize_counter(candidate_values[key], args.value_limit),
        }

    return {
        "schema": "planets-lab.combat-host-order-field-inventory.v1",
        "read_only": True,
        "summary": {
            "archives": len(archives),
            "raw_perspective_ship_records": raw_ship_records,
            "owner_ship_records": owner_ship_records,
        },
        "mission_ids": _serialize_counter(mission_ids),
        "mission_target_presence": _serialize_counter(mission_targets),
        "friendlycode_shapes": _serialize_counter(fc_shapes),
        "numeric_friendlycode_values_top": _serialize_counter(numeric_fc_values, args.value_limit),
        "candidate_order_fields": candidate_fields,
        "mission_catalog_candidates": catalog_rows[: args.catalog_limit],
        "evidence_boundary": (
            "Schema inventory only. Numeric mission IDs are not assigned semantic names unless a factual "
            "catalog or other explicit evidence establishes that mapping."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inventory owner-visible pre-combat order fields and mission catalogs.")
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--value-limit", type=int, default=20)
    parser.add_argument("--catalog-limit", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT ORDER FIELD INVENTORY =====")
    print(f"summary: {report['summary']}")
    print(f"mission_ids: {report['mission_ids']}")
    print(f"mission_target_presence: {report['mission_target_presence']}")
    print(f"friendlycode_shapes: {report['friendlycode_shapes']}")
    print(f"numeric_friendlycode_values_top: {report['numeric_friendlycode_values_top']}")
    print("candidate_order_fields:")
    for key, value in report["candidate_order_fields"].items():
        print(f"  {key}: {value}")
    print("mission_catalog_candidates:")
    for row in report["mission_catalog_candidates"]:
        print(f"  {row}")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: schema inventory only; mission/PE/FC causality is not inferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
