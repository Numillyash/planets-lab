from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

from planets_lab.corpus.movement_residual_context import (
    _resolved_storm_offset,
    _storm_clusters,
    _storm_consensus_by_turn,
)
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.rules.ion_storm import CLASS_4_MIN_VOLTAGE, integer_drag_delta, local_voltage

from intercept_fuel_historical_differential_audit import PREPARED_DIR, RAW_DIR
from tow_finite_fuel_residual_shape_audit import _parse_clean_cases, _xy


EXAMPLE_LIMIT = 100


def _storm_vector_matches(
    storms: Sequence[Any],
    *,
    residual: tuple[int, int],
    origin: tuple[int, int],
    geometry: tuple[int, int],
    observed: tuple[int, int],
) -> tuple[dict[str, Any], ...]:
    matches: list[dict[str, Any]] = []
    for root, circles in _storm_clusters(storms):
        vector = integer_drag_delta(root.warp, root.heading)
        if vector != residual:
            continue
        matches.append(
            {
                "storm_id": root.id,
                "storm_warp": root.warp,
                "heading": root.heading,
                "drag_vector": vector,
                "origin_voltage": round(local_voltage(circles, *origin), 3),
                "geometry_voltage": round(local_voltage(circles, *geometry), 3),
                "observed_voltage": round(local_voltage(circles, *observed), 3),
            }
        )
    return tuple(matches)


def _resolved_at(
    storms: Sequence[Any],
    *,
    point: tuple[int, int],
) -> tuple[tuple[int, int] | None, str]:
    return _resolved_storm_offset(storms, x=point[0], y=point[1])


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare the 53 clean finite-fuel Tow residual vectors against actual historical "
            "ion-storm drag vectors and against the existing resolved-storm-offset classifier "
            "evaluated at origin, direct Tow geometry endpoint, and factual endpoint. "
            "Evidence mining only; this does not promote a Host rule."
        )
    )
    parser.add_argument("--external-log", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=EXAMPLE_LIMIT)
    args = parser.parse_args()
    if args.examples < 0:
        raise SystemExit("--examples must be non-negative")

    expected, cases = _parse_clean_cases(args.external_log)
    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        by_game[int(case["game"])].append(case)

    totals: Counter[str] = Counter()
    totals["clean_residual_input"] = expected
    examples: list[dict[str, Any]] = []

    print("===== FINITE-FUEL TOW STORM-VECTOR FOLLOW-UP =====")
    print("external_log=", args.external_log)
    print("clean_residual_input=", expected)

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
        game_counts: Counter[str] = Counter()

        for case in by_game[game_id]:
            before_turn = int(case["turn"])
            after_turn = int(case["after_turn"])
            origin = _xy(case["origin"], "origin")
            geometry = _xy(case["geometry_endpoint"], "geometry_endpoint")
            observed = _xy(case["observed"], "observed")
            residual = (observed[0] - geometry[0], observed[1] - geometry[1])

            totals["cases"] += 1
            game_counts["cases"] += 1

            turn_payload: dict[str, Any] = {}
            any_single_root_exact = False
            any_resolved_exact = False

            for label, turn in (("before", before_turn), ("after", after_turn)):
                if turn in storm_conflicts:
                    totals[f"{label}_turn_storm_conflict"] += 1
                    game_counts[f"{label}_turn_storm_conflict"] += 1
                    turn_payload[label] = {"status": "conflict"}
                    continue
                if turn in storm_invalid:
                    totals[f"{label}_turn_storm_invalid"] += 1
                    game_counts[f"{label}_turn_storm_invalid"] += 1
                    turn_payload[label] = {"status": "invalid"}
                    continue

                storms = storms_by_turn.get(turn, ())
                single_matches = _storm_vector_matches(
                    storms,
                    residual=residual,
                    origin=origin,
                    geometry=geometry,
                    observed=observed,
                )
                if single_matches:
                    totals[f"{label}_single_root_vector_exact"] += 1
                    game_counts[f"{label}_single_root_vector_exact"] += 1
                    any_single_root_exact = True
                    if len(single_matches) > 1:
                        totals[f"{label}_single_root_vector_ambiguous"] += 1
                    for match in single_matches:
                        totals[f"{label}_matched_root_warp:{int(match['storm_warp'])}"] += 1
                        if float(match["origin_voltage"]) >= CLASS_4_MIN_VOLTAGE:
                            totals[f"{label}_matched_root_origin_class4"] += 1
                        if float(match["geometry_voltage"]) >= CLASS_4_MIN_VOLTAGE:
                            totals[f"{label}_matched_root_geometry_class4"] += 1
                        if float(match["observed_voltage"]) >= CLASS_4_MIN_VOLTAGE:
                            totals[f"{label}_matched_root_observed_class4"] += 1

                resolved: dict[str, Any] = {}
                for point_name, point in (
                    ("origin", origin),
                    ("geometry", geometry),
                    ("observed", observed),
                ):
                    offset, status = _resolved_at(storms, point=point)
                    exact = offset == residual
                    resolved[point_name] = {
                        "offset": offset,
                        "status": status,
                        "exact": exact,
                    }
                    if exact:
                        totals[f"{label}_resolved_{point_name}_exact"] += 1
                        game_counts[f"{label}_resolved_{point_name}_exact"] += 1
                        any_resolved_exact = True

                turn_payload[label] = {
                    "status": "known",
                    "storm_count": len(storms),
                    "single_root_matches": single_matches,
                    "resolved": resolved,
                }

            if any_single_root_exact:
                totals["either_turn_single_root_vector_exact"] += 1
                game_counts["either_turn_single_root_vector_exact"] += 1
            else:
                totals["no_single_root_vector_exact"] += 1
                game_counts["no_single_root_vector_exact"] += 1

            if any_resolved_exact:
                totals["any_resolved_point_exact"] += 1
                game_counts["any_resolved_point_exact"] += 1
            else:
                totals["no_resolved_point_exact"] += 1
                game_counts["no_resolved_point_exact"] += 1

            if len(examples) < args.examples:
                examples.append(
                    {
                        "game": game_id,
                        "turn": before_turn,
                        "after_turn": after_turn,
                        "tower_ship": int(case["tower_ship"]),
                        "target_ship": int(case["target_ship"]),
                        "origin": origin,
                        "geometry_endpoint": geometry,
                        "observed": observed,
                        "residual_vector": residual,
                        "residual_norm": round((residual[0] ** 2 + residual[1] ** 2) ** 0.5, 3),
                        "before": turn_payload.get("before"),
                        "after": turn_payload.get("after"),
                    }
                )

        print({"game": game_id, "cache_hit": cache_hit, **dict(sorted(game_counts.items()))}, flush=True)

    if totals["cases"] != totals["clean_residual_input"]:
        raise AssertionError(
            f"case accounting mismatch: input={totals['clean_residual_input']} cases={totals['cases']}"
        )

    print("\n===== SUMMARY =====")
    for key in (
        "clean_residual_input",
        "cases",
        "either_turn_single_root_vector_exact",
        "no_single_root_vector_exact",
        "before_single_root_vector_exact",
        "after_single_root_vector_exact",
        "before_single_root_vector_ambiguous",
        "after_single_root_vector_ambiguous",
        "any_resolved_point_exact",
        "no_resolved_point_exact",
        "before_resolved_origin_exact",
        "before_resolved_geometry_exact",
        "before_resolved_observed_exact",
        "after_resolved_origin_exact",
        "after_resolved_geometry_exact",
        "after_resolved_observed_exact",
        "before_turn_storm_conflict",
        "before_turn_storm_invalid",
        "after_turn_storm_conflict",
        "after_turn_storm_invalid",
    ):
        print(f"{key}= {totals[key]}")
    for key, value in sorted(totals.items()):
        if "matched_root_" in key:
            print(f"{key}= {value}")

    print("\n===== CASES =====")
    for item in examples:
        print(item)

    print("\n===== INTERPRETATION =====")
    print(
        "An exact historical root-storm drag vector is attribution evidence for the vector shape only. "
        "It does not by itself prove that the Tow pair qualified for drag at that Host phase."
    )
    print(
        "Resolved-offset exactness at origin reproduces the current classifier assumption; exactness only at geometry/observed "
        "is a Host-order lead that requires independent validation before changing storm or Tow mechanics."
    )
    print("finite-fuel Tow remains OPEN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
