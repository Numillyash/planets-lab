from __future__ import annotations

import argparse
import ast
from collections import Counter
from math import hypot
from pathlib import Path
from typing import Any, Mapping

from tow_finite_fuel_residual_shape_audit import _parse_clean_cases, _xy


EXAMPLE_LIMIT = 100


def _case_key(item: Mapping[str, Any]) -> tuple[int, int, int, int]:
    return (
        int(item["game"]),
        int(item["turn"]),
        int(item["tower_ship"]),
        int(item["target_ship"]),
    )


def _dict_lines_between(path: Path, start: str, end: str) -> tuple[dict[str, Any], ...]:
    text = path.read_text(encoding="utf-8")
    if start not in text or end not in text:
        raise ValueError(f"missing section markers in {path}: {start!r} / {end!r}")
    section = text.split(start, 1)[1].split(end, 1)[0]
    values: list[dict[str, Any]] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        value = ast.literal_eval(line)
        if not isinstance(value, dict):
            raise ValueError(f"non-dict row in {path}")
        values.append(value)
    return tuple(values)


def _mode_rows(path: Path) -> tuple[dict[str, Any], ...]:
    text = path.read_text(encoding="utf-8")
    before_summary = text.split("===== SUMMARY =====", 1)[0]
    values: list[dict[str, Any]] = []
    for raw_line in before_summary.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        value = ast.literal_eval(line)
        if not isinstance(value, dict):
            continue
        if "game" in value and "mode_status" in value:
            values.append(value)
    return tuple(values)


def _origin_hit(item: Mapping[str, Any]) -> bool:
    hits = item.get("hits")
    if not isinstance(hits, Mapping):
        return False
    return any(bool(value) and str(key).endswith("_origin") for key, value in hits.items())


def _shape(case: Mapping[str, Any]) -> dict[str, Any]:
    origin = _xy(case["origin"], "origin")
    waypoint = _xy(case["waypoint"], "waypoint")
    geometry = _xy(case["geometry_endpoint"], "geometry_endpoint")
    observed = _xy(case["observed"], "observed")
    residual = (observed[0] - geometry[0], observed[1] - geometry[1])
    residual_norm = hypot(*residual)
    route = (waypoint[0] - origin[0], waypoint[1] - origin[1])
    route_len = hypot(*route)
    if route_len > 0.0:
        cross = (route[0] * residual[1] - route[1] * residual[0]) / route_len
        observed_along = (
            (observed[0] - origin[0]) * route[0]
            + (observed[1] - origin[1]) * route[1]
        ) / route_len
    else:
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
        "residual_vector": residual,
        "residual_norm": residual_norm,
        "residual_norm_round": int(round(residual_norm)),
        "direction": direction,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcile the 53 clean finite-fuel Tow residual rows after public loadinfo resolved "
            "nuionstorms=false for the residual games. Rows are attributed to classic ion-storm "
            "drag only when the earlier classic audit recorded an exact root drag-vector match "
            "and qualifying classic origin membership. Log reconciliation only; no corpus rebuild, "
            "simulator rule, or planets-intel change."
        )
    )
    parser.add_argument("--external-log", type=Path, required=True)
    parser.add_argument("--classic-log", type=Path, required=True)
    parser.add_argument("--mode-log", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=EXAMPLE_LIMIT)
    args = parser.parse_args()
    if args.examples < 0:
        raise SystemExit("--examples must be non-negative")

    expected, clean_cases = _parse_clean_cases(args.external_log)
    classic_rows = _dict_lines_between(
        args.classic_log,
        "===== CASES =====",
        "===== INTERPRETATION =====",
    )
    mode_rows = _mode_rows(args.mode_log)

    clean_by_key = {_case_key(item): item for item in clean_cases}
    if len(clean_by_key) != len(clean_cases):
        raise ValueError("duplicate clean Tow residual case keys")

    classic_by_key: dict[tuple[int, int, int, int], dict[str, Any]] = {}
    for item in classic_rows:
        key = _case_key(item)
        if key in classic_by_key:
            raise ValueError(f"duplicate classic-audit case key: {key}")
        classic_by_key[key] = item
        if key not in clean_by_key:
            raise ValueError(f"classic-audit row is not in clean residual population: {key}")

    mode_by_game: dict[int, dict[str, Any]] = {}
    for item in mode_rows:
        game = int(item["game"])
        if game in mode_by_game:
            raise ValueError(f"duplicate mode row for game {game}")
        mode_by_game[game] = item

    expected_games = sorted({int(item["game"]) for item in clean_cases})
    if sorted(mode_by_game) != expected_games:
        raise ValueError(
            f"mode game set mismatch: expected={expected_games} got={sorted(mode_by_game)}"
        )

    totals: Counter[str] = Counter()
    totals["clean_residual_input"] = expected
    remaining: list[dict[str, Any]] = []
    attributed: list[dict[str, Any]] = []

    print("===== FINITE-FUEL TOW CLASSIC-STORM RECLASSIFICATION =====")
    print("external_log=", args.external_log)
    print("classic_log=", args.classic_log)
    print("mode_log=", args.mode_log)
    print("clean_residual_input=", expected)

    for game in expected_games:
        mode = mode_by_game[game]
        resolved_false = (
            mode.get("loadinfo") == "ok"
            and mode.get("nuionstorms") is False
            and mode.get("mode_status") == "resolved_false"
        )
        if resolved_false:
            totals["mode_false_games"] += 1
        else:
            totals["mode_not_false_games"] += 1
        print(
            {
                "game": game,
                "loadinfo": mode.get("loadinfo"),
                "nuionstorms": mode.get("nuionstorms"),
                "mode_status": mode.get("mode_status"),
            }
        )

    for case in clean_cases:
        key = _case_key(case)
        game = key[0]
        classic = classic_by_key.get(key)
        mode = mode_by_game[game]
        mode_false = (
            mode.get("loadinfo") == "ok"
            and mode.get("nuionstorms") is False
            and mode.get("mode_status") == "resolved_false"
        )
        exact_root_vector = bool(classic and classic.get("root_ids"))
        classic_origin = bool(classic and _origin_hit(classic))

        totals["cases"] += 1
        if exact_root_vector:
            totals["exact_root_vector_rows"] += 1
        if classic_origin:
            totals["classic_origin_rows"] += 1

        if mode_false and exact_root_vector and classic_origin:
            totals["classic_storm_attributed"] += 1
            totals[f"classic_storm_attributed_game:{game}"] += 1
            attributed.append(dict(case))
            continue

        totals["post_classic_storm_residual"] += 1
        totals[f"post_classic_storm_residual_game:{game}"] += 1
        enriched = {**case, **_shape(case)}
        remaining.append(enriched)
        if not mode_false:
            totals["remaining_due_mode"] += 1
        if not exact_root_vector:
            totals["remaining_no_exact_root_vector"] += 1
        if exact_root_vector and not classic_origin:
            totals["remaining_no_classic_origin_membership"] += 1

    if totals["cases"] != expected:
        raise AssertionError(f"case accounting mismatch: {totals['cases']} != {expected}")
    if totals["classic_storm_attributed"] + totals["post_classic_storm_residual"] != expected:
        raise AssertionError("classic-storm reclassification accounting mismatch")

    print("\n===== SUMMARY =====")
    for key in (
        "clean_residual_input",
        "cases",
        "mode_false_games",
        "mode_not_false_games",
        "exact_root_vector_rows",
        "classic_origin_rows",
        "classic_storm_attributed",
        "post_classic_storm_residual",
        "remaining_due_mode",
        "remaining_no_exact_root_vector",
        "remaining_no_classic_origin_membership",
    ):
        print(f"{key}= {totals[key]}")
    for key, value in sorted(totals.items()):
        if key.startswith("classic_storm_attributed_game:") or key.startswith(
            "post_classic_storm_residual_game:"
        ):
            print(f"{key}= {value}")

    by_hull: Counter[int] = Counter()
    by_race: Counter[int | None] = Counter()
    by_warp: Counter[int] = Counter()
    by_baseline: Counter[str] = Counter()
    by_norm: Counter[int] = Counter()
    by_direction: Counter[str] = Counter()
    for item in remaining:
        hull_raw = item.get("hull", item.get("tower_hull"))
        if hull_raw is not None:
            by_hull[int(hull_raw)] += 1
        race_raw = item.get("race")
        by_race[int(race_raw) if race_raw is not None else None] += 1
        warp_raw = item.get("warp", item.get("tower_warp"))
        if warp_raw is not None:
            by_warp[int(warp_raw)] += 1
        by_baseline[str(item.get("baseline_category"))] += 1
        by_norm[int(item["residual_norm_round"])] += 1
        by_direction[str(item["direction"])] += 1

    print("\n===== REMAINING SHAPE =====")
    print("by_hull=", dict(by_hull.most_common()))
    print("by_race=", dict(by_race.most_common()))
    print("by_warp=", dict(by_warp.most_common()))
    print("by_baseline=", dict(by_baseline.most_common()))
    print("by_residual_norm_round=", dict(by_norm.most_common()))
    print("by_direction=", dict(by_direction.most_common()))

    print("\n===== REMAINING CASES =====")
    for item in sorted(
        remaining,
        key=lambda row: (
            int(row["game"]),
            int(row["turn"]),
            int(row["tower_ship"]),
            int(row["target_ship"]),
        ),
    )[: args.examples]:
        print(
            {
                "game": int(item["game"]),
                "turn": int(item["turn"]),
                "after_turn": int(item["after_turn"]),
                "tower_ship": int(item["tower_ship"]),
                "target_ship": int(item["target_ship"]),
                "hull": item.get("hull", item.get("tower_hull")),
                "race": item.get("race"),
                "warp": item.get("warp", item.get("tower_warp")),
                "origin": item["origin"],
                "waypoint": item["waypoint"],
                "geometry_endpoint": item["geometry_endpoint"],
                "observed": item["observed"],
                "residual_vector": item["residual_vector"],
                "residual_norm": round(float(item["residual_norm"]), 3),
                "direction": item["direction"],
                "baseline_category": item.get("baseline_category"),
            }
        )

    print("\n===== INTERPRETATION =====")
    print(
        "Rows classified as classic_storm_attributed combine three independent historical facts: "
        "exact after-turn root drag-vector equality, qualifying classic root-circle membership at "
        "Tow origin, and public loadinfo nuionstorms=false for that game."
    )
    print(
        "This removes attributable classic-storm confounders from the Tow evidence-mining residual "
        "population only. It does not establish a general storm-order rule or finite-fuel Tow cost basis."
    )
    print(
        "The post-classic-storm residual is the bounded population for the next non-fuel context probe; "
        "test multi-root classic storm combinations and special relocation/passenger Chunnel before "
        "performing further Tow fuel inference."
    )
    print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
