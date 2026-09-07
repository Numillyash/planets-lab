from __future__ import annotations

import argparse
import gzip
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

DEFAULT_REPORT = Path("logs/combat-host-single-battle-side-order.json")
RAW_DIR = Path("validation/corpus/cache/loadall")
GORBIE_HULL_ID = 70


def _intish(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _decode_member(raw: bytes) -> Mapping[str, Any] | None:
    payload = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    try:
        parsed = json.loads(payload.decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, Mapping) else None


def _vcr_turn(vcr: Mapping[str, Any], fallback: int | None) -> int | None:
    return _intish(vcr.get("turn")) or fallback


def _side_shape(vcr: Mapping[str, Any], side: str) -> dict[str, Any] | None:
    raw = vcr.get(side)
    if not isinstance(raw, Mapping):
        return None
    ship_id = _intish(raw.get("objectid"))
    hull_id = _intish(raw.get("hullid"))
    if ship_id is None or hull_id is None or hull_id <= 0:
        return None
    owner_key = "leftownerid" if side == "left" else "rightownerid"
    return {
        "ship_id": ship_id,
        "hull_id": hull_id,
        "owner_id": _intish(vcr.get(owner_key)),
    }


def _classify_forced_side(left_hull: int | None, right_hull: int | None) -> str:
    if left_hull == GORBIE_HULL_ID and right_hull == GORBIE_HULL_ID:
        return "both_gorbie"
    if left_hull == GORBIE_HULL_ID:
        return "left_gorbie"
    if right_hull == GORBIE_HULL_ID:
        return "right_gorbie"
    return "no_gorbie"


def _load_targets(report_path: Path) -> list[dict[str, Any]]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    ordinary = report.get("scopes", {}).get("ordinary", {})
    examples = ordinary.get("examples", [])
    if not isinstance(examples, list):
        raise ValueError("ordinary examples are missing from source report")
    rows = [
        dict(row)
        for row in examples
        if isinstance(row, Mapping) and row.get("priority_relation") == "left_higher_priority"
    ]
    expected = _intish((ordinary.get("side_priority") or {}).get("left_higher_priority")) or 0
    if len(rows) != expected:
        raise ValueError(
            f"source report retained {len(rows)} left-higher examples but summary says {expected}; "
            "rerun the source audit with a larger --example-limit"
        )
    return rows


def _factual_vcr_shapes(
    archive_path: Path,
    targets: set[tuple[int, int]],
) -> dict[tuple[int, int], dict[str, Any]]:
    found: dict[tuple[int, int], dict[str, Any]] = {}
    conflicts: set[tuple[int, int]] = set()
    with zipfile.ZipFile(archive_path) as archive:
        for name in archive.namelist():
            if not name.lower().endswith(".trn"):
                continue
            parsed = _decode_member(archive.read(name))
            if parsed is None:
                continue
            game = parsed.get("game")
            fallback_turn = _intish(game.get("turn")) if isinstance(game, Mapping) else None
            vcrs = parsed.get("vcrs")
            if not isinstance(vcrs, list):
                continue
            for raw_vcr in vcrs:
                if not isinstance(raw_vcr, Mapping):
                    continue
                vcr_id = _intish(raw_vcr.get("id"))
                turn = _vcr_turn(raw_vcr, fallback_turn)
                if vcr_id is None or turn is None or (turn, vcr_id) not in targets:
                    continue
                left = _side_shape(raw_vcr, "left")
                right = _side_shape(raw_vcr, "right")
                if left is None or right is None:
                    continue
                shape = {"left": left, "right": right}
                key = (turn, vcr_id)
                previous = found.get(key)
                if previous is None:
                    found[key] = shape
                elif previous != shape:
                    conflicts.add(key)
    if conflicts:
        raise ValueError(f"conflicting factual VCR shapes: {sorted(conflicts)}")
    return found


def run(report_path: Path, archive_dir: Path) -> dict[str, Any]:
    rows = _load_targets(report_path)
    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        game_id = _intish(row.get("game_id"))
        if game_id is None:
            continue
        by_game[game_id].append(row)

    enriched: list[dict[str, Any]] = []
    classification = Counter()
    missing = 0
    for game_id, game_rows in sorted(by_game.items()):
        archive_path = archive_dir / f"game-{game_id}.zip"
        targets = {
            (int(row["turn"]), int(row["vcr_id"]))
            for row in game_rows
        }
        shapes = _factual_vcr_shapes(archive_path, targets)
        for row in game_rows:
            key = (int(row["turn"]), int(row["vcr_id"]))
            shape = shapes.get(key)
            if shape is None:
                missing += 1
                continue
            left = shape["left"]
            right = shape["right"]
            if left["ship_id"] != int(row["left_ship_id"]) or right["ship_id"] != int(row["right_ship_id"]):
                raise ValueError(f"VCR ship identity mismatch for game={game_id} turn={key[0]} vcr={key[1]}")
            forced = _classify_forced_side(left["hull_id"], right["hull_id"])
            classification[forced] += 1
            enriched.append(
                {
                    **row,
                    "left_hull_id": left["hull_id"],
                    "right_hull_id": right["hull_id"],
                    "forced_side_candidate": forced,
                }
            )

    return {
        "schema": "planets-lab.combat-host-single-battle-side-residual-audit.v1",
        "source_report": str(report_path),
        "ordinary_left_higher_priority": len(rows),
        "resolved": len(enriched),
        "missing": missing,
        "forced_side_candidates": dict(sorted(classification.items())),
        "rows": enriched,
        "evidence_boundary": (
            "This residual audit only enriches already-observed ordinary left-higher-priority single battles "
            "with factual hull IDs. Hull 70 is labeled as a Gorbie candidate because current Planets.nu "
            "documentation lists Gorbie Class Battlecarrier as hull 70 and Galactic Power as a forced-left ability."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich ordinary side-order residuals with factual hull IDs.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args.report, args.archive_dir)
    print("===== HOST SINGLE-BATTLE SIDE RESIDUAL AUDIT =====")
    for key in ("ordinary_left_higher_priority", "resolved", "missing", "forced_side_candidates"):
        print(f"{key}: {report[key]}")
    for index, row in enumerate(report["rows"], start=1):
        print()
        print(
            f"CASE {index}: game={row['game_id']} turn={row['turn']} vcr={row['vcr_id']} "
            f"slice={row['slice']} initiative={row['initiative']}"
        )
        print(
            f"  left: ship={row['left_ship_id']} hull={row['left_hull_id']} owner={row['left_owner']} "
            f"mission={row['left_mission']} enemy={row['left_enemy']} fc={row['left_fc']!r} "
            f"priority={row['left_priority']}"
        )
        print(
            f"  right: ship={row['right_ship_id']} hull={row['right_hull_id']} owner={row['right_owner']} "
            f"mission={row['right_mission']} enemy={row['right_enemy']} fc={row['right_fc']!r} "
            f"priority={row['right_priority']}"
        )
        print(f"  forced_side_candidate: {row['forced_side_candidate']}")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: residual enrichment only; no forced-side mechanic is promoted by this tool alone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
