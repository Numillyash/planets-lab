from __future__ import annotations

import argparse
import ast
import re
from collections import Counter, defaultdict
from itertools import combinations, permutations
from math import hypot
from pathlib import Path
from typing import Any, Mapping, Sequence

from planets_lab.corpus.movement_differential import (
    _entity_map,
    _planet_tuples_by_turn,
    _warp_well_destination,
)
from planets_lab.corpus.movement_residual_context import (
    GRAVITONIC_HULL_IDS,
    _storm_clusters,
    _storm_consensus_by_turn,
)
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.rules.ion_storm import CLASS_4_MIN_VOLTAGE, integer_drag_delta
from planets_lab.validation.movement_geometry import MovementSample

from intercept_fuel_historical_differential_audit import PREPARED_DIR, RAW_DIR


EXAMPLE_LIMIT = 100
EXTREME_MIN_VOLTAGE = 400.0


def _remaining_cases(path: Path) -> tuple[int, tuple[dict[str, Any], ...]]:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^post_classic_storm_residual=\s*(\d+)\s*$", text, re.M)
    if match is None:
        raise ValueError("post_classic_storm_residual counter missing")
    expected = int(match.group(1))
    start = "===== REMAINING CASES ====="
    end = "===== INTERPRETATION ====="
    if start not in text or end not in text:
        raise ValueError("reclassification REMAINING CASES markers missing")
    section = text.split(start, 1)[1].split(end, 1)[0]
    rows: list[dict[str, Any]] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        value = ast.literal_eval(line)
        if not isinstance(value, dict):
            raise ValueError("remaining row is not a dict")
        rows.append(value)
    if len(rows) != expected:
        raise ValueError(f"remaining rows truncated: expected={expected} parsed={len(rows)}")
    return expected, tuple(rows)


def _xy(value: Any, field: str) -> tuple[int, int]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError(f"{field} is not an xy pair: {value!r}")
    return int(value[0]), int(value[1])


def _qualifies(root: Any, point: tuple[int, int]) -> bool:
    radius = float(root.radius)
    voltage = float(root.voltage)
    if radius <= 0.0 or voltage < CLASS_4_MIN_VOLTAGE or voltage >= EXTREME_MIN_VOLTAGE:
        return False
    return hypot(float(point[0]) - float(root.x), float(point[1]) - float(root.y)) < radius


def _vector(root: Any) -> tuple[int, int]:
    return integer_drag_delta(int(root.warp), float(root.heading))


def _sum_vectors(roots: Sequence[Any]) -> tuple[int, int]:
    dx = 0
    dy = 0
    for root in roots:
        vx, vy = _vector(root)
        dx += vx
        dy += vy
    return dx, dy


def _endpoint_status(
    *,
    sample: MovementSample,
    geometry: tuple[int, int],
    observed: tuple[int, int],
    vector: tuple[int, int],
    planets: Sequence[tuple[int, int, int]],
) -> tuple[str | None, tuple[int, int] | None]:
    shifted = (geometry[0] + vector[0], geometry[1] + vector[1])
    if shifted == observed:
        return "direct", shifted
    well, ambiguous = _warp_well_destination(sample=sample, endpoint=shifted, planets=planets)
    if ambiguous:
        return "warp_well_ambiguous", well
    if well is not None and well == observed:
        return "warp_well", well
    return None, well


def _static_subset_witnesses(
    roots: Sequence[Any],
    *,
    origin: tuple[int, int],
    sample: MovementSample,
    geometry: tuple[int, int],
    observed: tuple[int, int],
    planets: Sequence[tuple[int, int, int]],
) -> tuple[dict[str, Any], ...]:
    eligible = tuple(root for root in roots if _qualifies(root, origin))
    found: list[dict[str, Any]] = []
    for size in range(2, len(eligible) + 1):
        for subset in combinations(eligible, size):
            vector = _sum_vectors(subset)
            endpoint_status, _ = _endpoint_status(
                sample=sample,
                geometry=geometry,
                observed=observed,
                vector=vector,
                planets=planets,
            )
            if endpoint_status not in {"direct", "warp_well"}:
                continue
            found.append(
                {
                    "root_ids": tuple(int(root.id) for root in subset),
                    "vectors": tuple(_vector(root) for root in subset),
                    "sum": vector,
                    "endpoint": endpoint_status,
                }
            )
    return tuple(found)


def _sorted_sequential_witness(
    roots: Sequence[Any],
    *,
    origin: tuple[int, int],
    sample: MovementSample,
    geometry: tuple[int, int],
    observed: tuple[int, int],
    planets: Sequence[tuple[int, int, int]],
) -> dict[str, Any] | None:
    point = origin
    applied: list[Any] = []
    for root in sorted(roots, key=lambda item: int(item.id)):
        if not _qualifies(root, point):
            continue
        applied.append(root)
        dx, dy = _vector(root)
        point = (point[0] + dx, point[1] + dy)
    if len(applied) < 2:
        return None
    vector = _sum_vectors(applied)
    endpoint_status, _ = _endpoint_status(
        sample=sample,
        geometry=geometry,
        observed=observed,
        vector=vector,
        planets=planets,
    )
    if endpoint_status not in {"direct", "warp_well"}:
        return None
    return {
        "root_ids": tuple(int(root.id) for root in applied),
        "vectors": tuple(_vector(root) for root in applied),
        "sum": vector,
        "endpoint": endpoint_status,
    }


def _permutation_subset_witnesses(
    roots: Sequence[Any],
    *,
    origin: tuple[int, int],
    sample: MovementSample,
    geometry: tuple[int, int],
    observed: tuple[int, int],
    planets: Sequence[tuple[int, int, int]],
) -> tuple[dict[str, Any], ...]:
    found: list[dict[str, Any]] = []
    seen: set[tuple[tuple[int, ...], str]] = set()
    for size in range(2, len(roots) + 1):
        for sequence in permutations(roots, size):
            point = origin
            applied: list[Any] = []
            for root in sequence:
                if not _qualifies(root, point):
                    break
                applied.append(root)
                dx, dy = _vector(root)
                point = (point[0] + dx, point[1] + dy)
            else:
                vector = _sum_vectors(applied)
                endpoint_status, _ = _endpoint_status(
                    sample=sample,
                    geometry=geometry,
                    observed=observed,
                    vector=vector,
                    planets=planets,
                )
                if endpoint_status not in {"direct", "warp_well"}:
                    continue
                root_ids = tuple(int(root.id) for root in applied)
                dedupe = (root_ids, endpoint_status)
                if dedupe in seen:
                    continue
                seen.add(dedupe)
                found.append(
                    {
                        "root_ids": root_ids,
                        "vectors": tuple(_vector(root) for root in applied),
                        "sum": vector,
                        "endpoint": endpoint_status,
                    }
                )
    return tuple(found)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Test the exact nine-row post-classic-storm finite-fuel Tow residual against bounded "
            "classic multi-root ion-storm combinations. This is an evidence-mining lead only: "
            "static subsets and arbitrary permutations do not establish Host storm processing order."
        )
    )
    parser.add_argument("--reclassification-log", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=EXAMPLE_LIMIT)
    args = parser.parse_args()
    if args.examples < 0:
        raise SystemExit("--examples must be non-negative")

    expected, cases = _remaining_cases(args.reclassification_log)
    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        by_game[int(case["game"])].append(case)

    totals: Counter[str] = Counter()
    totals["post_classic_storm_input"] = expected
    examples: list[dict[str, Any]] = []

    print("===== FINITE-FUEL TOW CLASSIC MULTI-ROOT STORM AUDIT =====")
    print("reclassification_log=", args.reclassification_log)
    print("post_classic_storm_input=", expected)

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        if not archive_path.is_file():
            raise FileNotFoundError(archive_path)
        archive_data = archive_path.read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        storms_by_turn, storm_conflicts, storm_invalid = _storm_consensus_by_turn(prepared.snapshots)
        entities = _entity_map(prepared.snapshots)
        planets_by_turn = _planet_tuples_by_turn(entities)
        game_counts: Counter[str] = Counter()

        for case in by_game[game_id]:
            totals["cases"] += 1
            game_counts["cases"] += 1
            before_turn = int(case["turn"])
            after_turn = int(case["after_turn"])
            origin = _xy(case["origin"], "origin")
            waypoint = _xy(case["waypoint"], "waypoint")
            geometry = _xy(case["geometry_endpoint"], "geometry_endpoint")
            observed = _xy(case["observed"], "observed")
            hull_id = int(case["hull"])
            warp = int(case["warp"])
            sample = MovementSample(
                turn=before_turn,
                ship_id=int(case["tower_ship"]),
                x=origin[0],
                y=origin[1],
                target_x=waypoint[0],
                target_y=waypoint[1],
                warp=warp,
                next_x=observed[0],
                next_y=observed[1],
                hull_id=hull_id,
                gravitonic=hull_id in GRAVITONIC_HULL_IDS,
                game_id=game_id,
            )
            planets = planets_by_turn.get(before_turn, ())
            case_payload: dict[str, Any] = {}
            any_exact = False

            for label, turn in (("before", before_turn), ("after", after_turn)):
                if turn in storm_conflicts:
                    totals[f"{label}_storm_conflict"] += 1
                    game_counts[f"{label}_storm_conflict"] += 1
                    case_payload[label] = {"status": "conflict"}
                    continue
                if turn in storm_invalid:
                    totals[f"{label}_storm_invalid"] += 1
                    game_counts[f"{label}_storm_invalid"] += 1
                    case_payload[label] = {"status": "invalid"}
                    continue

                storms = storms_by_turn.get(turn, ())
                roots = tuple(root for root, _ in _storm_clusters(storms))
                static = _static_subset_witnesses(
                    roots,
                    origin=origin,
                    sample=sample,
                    geometry=geometry,
                    observed=observed,
                    planets=planets,
                )
                sorted_witness = _sorted_sequential_witness(
                    roots,
                    origin=origin,
                    sample=sample,
                    geometry=geometry,
                    observed=observed,
                    planets=planets,
                )
                permutations_exact = _permutation_subset_witnesses(
                    roots,
                    origin=origin,
                    sample=sample,
                    geometry=geometry,
                    observed=observed,
                    planets=planets,
                )

                if static:
                    totals[f"{label}_static_subset_exact_rows"] += 1
                    game_counts[f"{label}_static_subset_exact_rows"] += 1
                    any_exact = True
                if sorted_witness is not None:
                    totals[f"{label}_sorted_sequential_exact_rows"] += 1
                    game_counts[f"{label}_sorted_sequential_exact_rows"] += 1
                    any_exact = True
                if permutations_exact:
                    totals[f"{label}_any_permutation_subset_exact_rows"] += 1
                    game_counts[f"{label}_any_permutation_subset_exact_rows"] += 1
                    any_exact = True

                case_payload[label] = {
                    "status": "known",
                    "root_count": len(roots),
                    "classic_origin_eligible_roots": tuple(
                        int(root.id) for root in roots if _qualifies(root, origin)
                    ),
                    "static_subset_exact": static,
                    "sorted_sequential_exact": sorted_witness,
                    "permutation_subset_exact": permutations_exact,
                }

            if any_exact:
                totals["rows_with_any_multi_root_exact_lead"] += 1
                game_counts["rows_with_any_multi_root_exact_lead"] += 1
            else:
                totals["no_multi_root_exact_lead"] += 1
                game_counts["no_multi_root_exact_lead"] += 1

            if len(examples) < args.examples:
                examples.append(
                    {
                        "game": game_id,
                        "turn": before_turn,
                        "after_turn": after_turn,
                        "tower_ship": int(case["tower_ship"]),
                        "target_ship": int(case["target_ship"]),
                        "origin": origin,
                        "geometry": geometry,
                        "observed": observed,
                        "residual": (observed[0] - geometry[0], observed[1] - geometry[1]),
                        "direction": case.get("direction"),
                        "before": case_payload.get("before"),
                        "after": case_payload.get("after"),
                    }
                )

        print({"game": game_id, "cache_hit": cache_hit, **dict(sorted(game_counts.items()))}, flush=True)

    if totals["cases"] != expected:
        raise AssertionError(f"case accounting mismatch: {totals['cases']} != {expected}")
    if totals["rows_with_any_multi_root_exact_lead"] + totals["no_multi_root_exact_lead"] != expected:
        raise AssertionError("multi-root row accounting mismatch")

    print("\n===== SUMMARY =====")
    for key in (
        "post_classic_storm_input",
        "cases",
        "rows_with_any_multi_root_exact_lead",
        "no_multi_root_exact_lead",
        "before_static_subset_exact_rows",
        "after_static_subset_exact_rows",
        "before_sorted_sequential_exact_rows",
        "after_sorted_sequential_exact_rows",
        "before_any_permutation_subset_exact_rows",
        "after_any_permutation_subset_exact_rows",
        "before_storm_conflict",
        "before_storm_invalid",
        "after_storm_conflict",
        "after_storm_invalid",
    ):
        print(f"{key}= {totals[key]}")

    print("\n===== CASES =====")
    for item in examples:
        print(item)

    print("\n===== INTERPRETATION =====")
    print(
        "A sorted sequential exact match is the strongest bounded multi-root lead because it uses "
        "the repository's stable root-id ordering and rechecks classic membership after each drag."
    )
    print(
        "Static-subset and arbitrary-permutation matches are weaker search leads only; they must not "
        "be promoted to Host behavior without an independent storm-order discriminator."
    )
    print(
        "Rows with no bounded multi-root exact lead remain the next population for passenger Chunnel "
        "/ special relocation context before additional Tow fuel inference."
    )
    print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
