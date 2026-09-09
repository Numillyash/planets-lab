from __future__ import annotations

import argparse
import ast
import re
from collections import Counter
from math import hypot
from pathlib import Path
from typing import Any


EXAMPLE_LIMIT = 80


def _parse_clean_cases(path: Path) -> tuple[int, tuple[dict[str, Any], ...]]:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"^without_known_context_or_transfer_confounder=\s*(\d+)\s*$",
        text,
        re.M,
    )
    if match is None:
        raise ValueError("without_known_context_or_transfer_confounder counter missing")
    expected = int(match.group(1))

    start = "===== CASES ====="
    end = "===== INTERPRETATION ====="
    if start not in text or end not in text:
        raise ValueError("external-context CASES markers missing")
    section = text.split(start, 1)[1].split(end, 1)[0]

    clean: list[dict[str, Any]] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        value = ast.literal_eval(line)
        if not isinstance(value, dict):
            raise ValueError("external-context case is not a dict")
        flags = value.get("known_context_or_transfer_flags", ())
        if not flags:
            clean.append(value)

    if len(clean) != expected:
        raise ValueError(
            f"clean residual cases are truncated or inconsistent: expected {expected}, parsed {len(clean)}. "
            "Re-run external-context with --examples >= classified_cases."
        )
    return expected, tuple(clean)


def _xy(value: Any, field: str) -> tuple[int, int]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError(f"{field} is not an xy pair: {value!r}")
    return int(value[0]), int(value[1])


def _route_shape(case: dict[str, Any]) -> dict[str, Any]:
    origin = _xy(case["origin"], "origin")
    waypoint = _xy(case["waypoint"], "waypoint")
    observed = _xy(case["observed"], "observed")
    geometry = _xy(case["geometry_endpoint"], "geometry_endpoint")

    rx = waypoint[0] - origin[0]
    ry = waypoint[1] - origin[1]
    route_len = hypot(rx, ry)
    dx = observed[0] - geometry[0]
    dy = observed[1] - geometry[1]
    residual_norm = hypot(dx, dy)
    geometry_distance = hypot(geometry[0] - origin[0], geometry[1] - origin[1])
    observed_distance = hypot(observed[0] - origin[0], observed[1] - origin[1])

    if route_len > 0:
        along = (dx * rx + dy * ry) / route_len
        cross = (rx * dy - ry * dx) / route_len
        observed_along = (
            (observed[0] - origin[0]) * rx + (observed[1] - origin[1]) * ry
        ) / route_len
    else:
        along = 0.0
        cross = residual_norm
        observed_along = 0.0

    if abs(cross) <= 0.75:
        if observed_along > route_len + 0.75:
            direction = "same_line_beyond_waypoint"
        elif observed_along < -0.75:
            direction = "same_line_backward"
        else:
            direction = "same_line_route"
    else:
        direction = "off_route"

    return {
        "residual_vector": (dx, dy),
        "residual_norm": residual_norm,
        "residual_norm_round": int(round(residual_norm)),
        "along": along,
        "cross": cross,
        "distance_delta": observed_distance - geometry_distance,
        "route_len": route_len,
        "geometry_distance": geometry_distance,
        "observed_distance_calc": observed_distance,
        "direction": direction,
    }


def _print_counter(title: str, counter: Counter[Any], *, limit: int = 30) -> None:
    print(f"\n===== {title} =====")
    for value, count in counter.most_common(limit):
        print(f"{count:4d}  {value}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Cluster the finite-fuel Tow rows that remain clean after the bounded external-context follow-up. "
            "This consumes the preserved external-context log only; it does not rerun discovery or warp wells."
        )
    )
    parser.add_argument("--external-log", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=EXAMPLE_LIMIT)
    args = parser.parse_args()
    if args.examples < 0:
        raise SystemExit("--examples must be non-negative")

    expected, cases = _parse_clean_cases(args.external_log)

    by_game: Counter[int] = Counter()
    by_hull: Counter[int] = Counter()
    by_race: Counter[int | None] = Counter()
    by_warp: Counter[int] = Counter()
    by_baseline: Counter[str] = Counter()
    by_vector: Counter[tuple[int, int]] = Counter()
    by_norm_round: Counter[int] = Counter()
    by_direction: Counter[str] = Counter()
    by_distance_delta_round: Counter[int] = Counter()
    by_game_norm: Counter[tuple[int, int]] = Counter()
    by_game_vector: Counter[tuple[int, tuple[int, int]]] = Counter()

    enriched: list[dict[str, Any]] = []
    for case in cases:
        shape = _route_shape(case)
        game = int(case["game"])
        hull = int(case["hull"])
        warp = int(case["warp"])
        race_raw = case.get("race")
        race = int(race_raw) if race_raw is not None else None
        baseline = str(case.get("baseline_category"))
        vector = shape["residual_vector"]
        norm_round = int(shape["residual_norm_round"])
        distance_delta_round = int(round(float(shape["distance_delta"])))

        by_game[game] += 1
        by_hull[hull] += 1
        by_race[race] += 1
        by_warp[warp] += 1
        by_baseline[baseline] += 1
        by_vector[vector] += 1
        by_norm_round[norm_round] += 1
        by_direction[str(shape["direction"])] += 1
        by_distance_delta_round[distance_delta_round] += 1
        by_game_norm[(game, norm_round)] += 1
        by_game_vector[(game, vector)] += 1
        enriched.append({**case, **shape})

    print("===== FINITE-FUEL TOW CLEAN RESIDUAL SHAPE AUDIT =====")
    print("external_log=", args.external_log)
    print("clean_residual_input=", expected)
    print("parsed_clean_cases=", len(cases))

    _print_counter("BY GAME", by_game)
    _print_counter("BY HULL", by_hull)
    _print_counter("BY RACE", by_race)
    _print_counter("BY WARP", by_warp)
    _print_counter("BY BASELINE CATEGORY", by_baseline)
    _print_counter("RESIDUAL VECTOR observed-geometry", by_vector)
    _print_counter("RESIDUAL NORM rounded ly", by_norm_round)
    _print_counter("OBSERVED-GEOMETRY DISTANCE DELTA rounded ly", by_distance_delta_round)
    _print_counter("ROUTE SHAPE", by_direction)
    _print_counter("GAME + RESIDUAL NORM", by_game_norm, limit=50)
    _print_counter("GAME + RESIDUAL VECTOR", by_game_vector, limit=50)

    print("\n===== CASES =====")
    for case in sorted(
        enriched,
        key=lambda item: (
            int(item["game"]),
            int(item["turn"]),
            int(item["tower_ship"]),
            int(item["target_ship"]),
        ),
    )[: args.examples]:
        print(
            {
                "game": int(case["game"]),
                "turn": int(case["turn"]),
                "tower_ship": int(case["tower_ship"]),
                "target_ship": int(case["target_ship"]),
                "hull": int(case["hull"]),
                "race": case.get("race"),
                "warp": int(case["warp"]),
                "origin": case["origin"],
                "waypoint": case["waypoint"],
                "geometry_endpoint": case["geometry_endpoint"],
                "observed": case["observed"],
                "residual_vector": case["residual_vector"],
                "residual_norm": round(float(case["residual_norm"]), 3),
                "along": round(float(case["along"]), 3),
                "cross": round(float(case["cross"]), 3),
                "distance_delta": round(float(case["distance_delta"]), 3),
                "direction": case["direction"],
                "baseline_category": case.get("baseline_category"),
            }
        )

    print("\n===== INTERPRETATION =====")
    print(
        "This is clustering only. Repeated vectors, distances, hulls or route shapes are leads for the next attributable diagnostic; "
        "they are not Host mechanics and do not promote finite-fuel Tow."
    )
    print(
        "The input excludes rows already carrying mine/storm/damage/direct-target-Chunnel/transfer flags from the bounded external-context pass."
    )
    print("finite-fuel Tow remains OPEN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
