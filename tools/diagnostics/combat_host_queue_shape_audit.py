from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from planets_lab.corpus.archive import read_archive_members, turn_members


DEFAULT_ARCHIVE_DIR = Path("validation/corpus/cache/loadall")
SPECIAL_GAME_ID = 591478


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
    payload = raw
    if payload[:2] == b"\x1f\x8b":
        try:
            payload = gzip.decompress(payload)
        except OSError as exc:
            raise ValueError(f"{member_name}: invalid gzip payload") from exc
    try:
        parsed = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{member_name}: turn payload is not UTF-8 JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{member_name}: turn payload must be an object")
    return parsed


def _int(record: Mapping[str, Any] | None, key: str) -> int | None:
    if not isinstance(record, Mapping):
        return None
    value = record.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _objects(record: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = record.get(key)
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _archive_paths(args: argparse.Namespace) -> list[Path]:
    explicit = [Path(value) for value in args.archive]
    paths = explicit or sorted(Path(args.archive_dir).glob("game-*.zip"))
    if not paths:
        raise ValueError("no loadall archives found")
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise ValueError(f"archive paths do not exist: {missing}")
    return paths


def _shape(vcr: Mapping[str, Any]) -> str:
    left = vcr.get("left")
    right = vcr.get("right")
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        return "unknown"
    left_hull = _int(left, "hullid")
    right_hull = _int(right, "hullid")
    if left_hull is None or right_hull is None:
        return "unknown"
    left_planet = left_hull <= 0
    right_planet = right_hull <= 0
    if left_planet and right_planet:
        return "planet_vs_planet"
    if left_planet or right_planet:
        return "ship_vs_planet"
    return "ship_vs_ship"


def _side(vcr: Mapping[str, Any], name: str) -> dict[str, Any]:
    raw = vcr.get(name)
    if not isinstance(raw, Mapping):
        return {"object_id": None, "hull_id": None, "owner_id": None, "kind": "unknown"}
    hull_id = _int(raw, "hullid")
    owner_key = "leftownerid" if name == "left" else "rightownerid"
    return {
        "object_id": _int(raw, "objectid"),
        "hull_id": hull_id,
        "owner_id": _int(vcr, owner_key),
        "kind": "planet" if hull_id is not None and hull_id <= 0 else "ship" if hull_id is not None else "unknown",
    }


def _counter(counter: Counter[Any]) -> dict[str, int]:
    return {
        str(key): value
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    }


def _queue_profile(queue: list[Mapping[str, Any]]) -> str:
    tokens = {
        "ship_vs_ship": "S",
        "ship_vs_planet": "P",
        "planet_vs_planet": "PP",
        "unknown": "?",
    }
    return "".join(tokens.get(str(item.get("shape")), "?") for item in queue)


def _site_summary(queue: list[dict[str, Any]]) -> dict[str, Any]:
    queue.sort(key=lambda item: int(item["vcr_id"]))
    shape_counts = Counter(str(item["shape"]) for item in queue)
    vcr_gaps = Counter(
        int(current["vcr_id"]) - int(previous["vcr_id"])
        for previous, current in zip(queue, queue[1:])
    )

    first_planet_index: int | None = None
    phase_order_violation = False
    ship_ids: set[int] = set()
    planet_ids: set[int] = set()
    ship_appearances = Counter()
    pair_counts: Counter[tuple[int, int]] = Counter()

    for index, item in enumerate(queue):
        shape = str(item["shape"])
        if shape == "ship_vs_planet" and first_planet_index is None:
            first_planet_index = index
        elif shape == "ship_vs_ship" and first_planet_index is not None:
            phase_order_violation = True

        sides = item.get("sides")
        if not isinstance(sides, Mapping):
            continue
        for name in ("left", "right"):
            side = sides.get(name)
            if not isinstance(side, Mapping):
                continue
            object_id = side.get("object_id")
            if not isinstance(object_id, int) or isinstance(object_id, bool):
                continue
            if side.get("kind") == "planet":
                planet_ids.add(object_id)
            elif side.get("kind") == "ship":
                ship_ids.add(object_id)
                ship_appearances[object_id] += 1

        if shape == "ship_vs_ship":
            left = sides.get("left")
            right = sides.get("right")
            if isinstance(left, Mapping) and isinstance(right, Mapping):
                a = left.get("object_id")
                b = right.get("object_id")
                if (
                    isinstance(a, int)
                    and not isinstance(a, bool)
                    and isinstance(b, int)
                    and not isinstance(b, bool)
                    and a != b
                ):
                    pair_counts[tuple(sorted((a, b)))] += 1

    max_pair_fights = max(pair_counts.values(), default=0)
    repeated_pairs = sum(1 for count in pair_counts.values() if count > 1)
    pair_over_two = sum(1 for count in pair_counts.values() if count > 2)
    max_ship_appearances = max(ship_appearances.values(), default=0)

    return {
        "vcr_count": len(queue),
        "profile": _queue_profile(queue),
        "shape_counts": dict(shape_counts),
        "vcr_gaps": dict(vcr_gaps),
        "phase_order_violation": phase_order_violation,
        "ship_count": len(ship_ids),
        "planet_count": len(planet_ids),
        "max_ship_appearances": max_ship_appearances,
        "repeated_ship_pairs": repeated_pairs,
        "max_pair_fights": max_pair_fights,
        "pairs_over_two_fights": pair_over_two,
    }


def _scope(sites: list[dict[str, Any]]) -> dict[str, Any]:
    queue_lengths = Counter()
    profiles = Counter()
    shape_counts = Counter()
    gaps = Counter()
    ship_counts = Counter()
    planet_counts = Counter()
    max_ship_appearances = Counter()
    max_pair_fights = Counter()
    phase_violations = 0
    repeated_pair_sites = 0
    pair_over_two_sites = 0
    multi_vcr_sites = 0
    ship_only_sites = 0
    planet_phase_sites = 0

    for site in sites:
        summary = site["summary"]
        queue_lengths[int(summary["vcr_count"])] += 1
        profiles[str(summary["profile"])] += 1
        ship_counts[int(summary["ship_count"])] += 1
        planet_counts[int(summary["planet_count"])] += 1
        max_ship_appearances[int(summary["max_ship_appearances"])] += 1
        max_pair_fights[int(summary["max_pair_fights"])] += 1
        if int(summary["vcr_count"]) > 1:
            multi_vcr_sites += 1
        if summary["shape_counts"].get("ship_vs_planet", 0):
            planet_phase_sites += 1
        else:
            ship_only_sites += 1
        if bool(summary["phase_order_violation"]):
            phase_violations += 1
        if int(summary["repeated_ship_pairs"]) > 0:
            repeated_pair_sites += 1
        if int(summary["pairs_over_two_fights"]) > 0:
            pair_over_two_sites += 1
        for key, value in summary["shape_counts"].items():
            shape_counts[str(key)] += int(value)
        for key, value in summary["vcr_gaps"].items():
            gaps[int(key)] += int(value)

    return {
        "sites": len(sites),
        "multi_vcr_sites": multi_vcr_sites,
        "ship_only_sites": ship_only_sites,
        "planet_phase_sites": planet_phase_sites,
        "phase_order_violations": phase_violations,
        "sites_with_repeated_ship_pair": repeated_pair_sites,
        "sites_with_pair_over_two_fights": pair_over_two_sites,
        "queue_lengths": _counter(queue_lengths),
        "profiles": _counter(profiles),
        "battle_shapes": _counter(shape_counts),
        "vcr_gap_distribution": _counter(gaps),
        "ship_counts_per_site": _counter(ship_counts),
        "planet_counts_per_site": _counter(planet_counts),
        "max_ship_appearances_per_site": _counter(max_ship_appearances),
        "max_pair_fights_per_site": _counter(max_pair_fights),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    archives = _archive_paths(args)
    raw_observations = 0
    malformed_members = 0
    payload_conflicts: set[tuple[int, int, int]] = set()
    cases: dict[tuple[int, int, int], dict[str, Any]] = {}

    for archive_path in archives:
        data = archive_path.read_bytes()
        members = turn_members(data)
        raw_members = read_archive_members(data, [member.name for member in members])
        for member in members:
            try:
                rst = _decode_turn(raw_members[member.name], member.name)
            except ValueError:
                malformed_members += 1
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
                raw_observations += 1
                key = (game_id, battle_turn, vcr_id)
                payload_hash = _canonical_hash(vcr)
                previous = cases.get(key)
                if previous is None:
                    cases[key] = {
                        "game_id": game_id,
                        "turn": battle_turn,
                        "vcr_id": vcr_id,
                        "payload_hash": payload_hash,
                        "x": _int(vcr, "x"),
                        "y": _int(vcr, "y"),
                        "shape": _shape(vcr),
                        "sides": {
                            "left": _side(vcr, "left"),
                            "right": _side(vcr, "right"),
                        },
                    }
                elif previous["payload_hash"] != payload_hash:
                    payload_conflicts.add(key)

    sites_map: dict[tuple[int, int, int, int], list[dict[str, Any]]] = defaultdict(list)
    missing_position = 0
    for key, case in sorted(cases.items()):
        if key in payload_conflicts:
            continue
        x = case.get("x")
        y = case.get("y")
        if not isinstance(x, int) or isinstance(x, bool) or not isinstance(y, int) or isinstance(y, bool):
            missing_position += 1
            continue
        sites_map[(int(case["game_id"]), int(case["turn"]), x, y)].append(case)

    sites: list[dict[str, Any]] = []
    for (game_id, turn, x, y), queue in sorted(sites_map.items()):
        summary = _site_summary(queue)
        sites.append(
            {
                "game_id": game_id,
                "turn": turn,
                "x": x,
                "y": y,
                "summary": summary,
            }
        )

    ordinary = [site for site in sites if site["game_id"] != SPECIAL_GAME_ID]
    special = [site for site in sites if site["game_id"] == SPECIAL_GAME_ID]
    detail_sites = [
        site
        for site in sites
        if (
            site["summary"]["phase_order_violation"]
            or site["summary"]["pairs_over_two_fights"]
            or site["summary"]["repeated_ship_pairs"]
            or site["summary"]["vcr_count"] >= args.detail_min_queue
        )
    ][: args.detail_limit]

    return {
        "schema": "planets-lab.combat-host-queue-shape-audit.v1",
        "read_only": True,
        "evidence_boundary": (
            "Factual VCR queue shape only. This diagnostic does not infer why an engagement "
            "occurred or claim mission, Primary Enemy, friendly-code or diplomacy semantics."
        ),
        "summary": {
            "archives": len(archives),
            "raw_vcr_observations": raw_observations,
            "unique_vcrs": len(cases),
            "payload_conflicts": len(payload_conflicts),
            "malformed_members": malformed_members,
            "missing_position_vcrs": missing_position,
            "combat_sites": len(sites),
        },
        "scopes": {
            "ordinary": _scope(ordinary),
            "game_591478": _scope(special),
            "all": _scope(sites),
        },
        "details": detail_sites,
        "seconds": round(time.perf_counter() - started, 3),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only factual audit of NuHost VCR queue shapes.")
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--archive", action="append", default=[])
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--detail-limit", type=int, default=100)
    parser.add_argument("--detail-min-queue", type=int, default=6)
    return parser.parse_args()


def _print_scope(name: str, scope: Mapping[str, Any]) -> None:
    print(f"===== {name} =====")
    for key in (
        "sites",
        "multi_vcr_sites",
        "ship_only_sites",
        "planet_phase_sites",
        "phase_order_violations",
        "sites_with_repeated_ship_pair",
        "sites_with_pair_over_two_fights",
        "queue_lengths",
        "profiles",
        "battle_shapes",
        "ship_counts_per_site",
        "planet_counts_per_site",
        "max_ship_appearances_per_site",
        "max_pair_fights_per_site",
    ):
        print(f"{key}: {scope.get(key)}")


def main() -> int:
    args = parse_args()
    try:
        report = run(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("===== HOST COMBAT QUEUE SHAPE AUDIT =====")
    print(f"summary: {report['summary']}")
    for name, scope in report["scopes"].items():
        print()
        _print_scope(name, scope)
    print()
    print(f"detail_sites: {len(report['details'])}")
    print(f"seconds: {report['seconds']}")
    if args.output is not None:
        print(f"output: {args.output}")
    print("NOTE: factual queue shape only; no engagement-causality semantics are inferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
