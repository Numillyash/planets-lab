from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping, Sequence

from planets_lab.corpus.movement_residual_context import _storm_consensus_by_turn
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.rules.ion_storm import CLASS_4_MIN_VOLTAGE

from classic_ion_storm_final_residual_audit import _nuionstorms_consensus
from intercept_fuel_historical_differential_audit import PREPARED_DIR, RAW_DIR
from tow_finite_fuel_residual_shape_audit import _parse_clean_cases, _xy
from tow_finite_fuel_transient_storm_state_audit import (
    _after_root_vector_matches,
    _cluster_map,
    _membership_variants,
)


EXAMPLE_LIMIT = 100
EXTREME_MIN_VOLTAGE = 400.0


def _classic_circle_membership(circle: Any, point: tuple[int, int]) -> tuple[bool, str, float]:
    radius = float(circle.radius)
    voltage = float(circle.voltage)
    distance = hypot(float(point[0]) - float(circle.x), float(point[1]) - float(circle.y))
    if radius <= 0.0:
        return False, "invalid_radius", distance
    if distance >= radius:
        return False, "outside_root_circle", distance
    if voltage < CLASS_4_MIN_VOLTAGE:
        return False, "below_class4", distance
    if voltage >= EXTREME_MIN_VOLTAGE:
        # Extreme-storm transport is a different mechanic. Keep this audit fail-closed.
        return False, "extreme_voltage", distance
    return True, "classic_drag_member", distance


def _root_circle_from_variant(
    circles: Sequence[Any],
    *,
    root_id: int,
) -> Any | None:
    candidates = [
        circle
        for circle in circles
        if int(circle.id) == int(root_id) and int(circle.parent_id) == 0
    ]
    if len(candidates) != 1:
        return None
    return candidates[0]


def _classic_variant_membership(
    *,
    root_ids: Sequence[int],
    before_storms: Sequence[Any],
    after_storms: Sequence[Any],
    origin: tuple[int, int],
    geometry: tuple[int, int],
) -> tuple[dict[str, bool], tuple[dict[str, Any], ...], dict[str, int]]:
    before_map = _cluster_map(before_storms)
    after_map = _cluster_map(after_storms)
    hits: dict[str, bool] = {}
    witnesses: list[dict[str, Any]] = []
    meta = Counter()

    for root_id in root_ids:
        after_cluster = after_map.get(int(root_id))
        if after_cluster is None:
            meta["missing_after_root"] += 1
            continue
        variants, variant_meta = _membership_variants(
            before_cluster=before_map.get(int(root_id)),
            after_cluster=after_cluster,
        )
        if variant_meta.get("stable_root_pair"):
            meta["stable_root_pair"] += 1
        if variant_meta.get("stable_cluster_id_set"):
            meta["stable_cluster_id_set"] += 1

        for variant_name, circles in variants.items():
            root_circle = _root_circle_from_variant(circles, root_id=int(root_id))
            if root_circle is None:
                meta[f"{variant_name}_root_unavailable"] += 1
                continue
            for point_name, point in (("origin", origin), ("geometry", geometry)):
                qualifies, status, distance = _classic_circle_membership(root_circle, point)
                key = f"{variant_name}_{point_name}"
                hits[key] = hits.get(key, False) or qualifies
                if qualifies:
                    witnesses.append(
                        {
                            "root_id": int(root_id),
                            "variant": variant_name,
                            "point": point_name,
                            "status": status,
                            "distance": round(distance, 3),
                            "radius": round(float(root_circle.radius), 3),
                            "voltage": round(float(root_circle.voltage), 3),
                        }
                    )
                else:
                    meta[f"{variant_name}_{point_name}_{status}"] += 1

    return hits, tuple(witnesses), dict(meta)


def _record_hits(
    *,
    hits: Mapping[str, bool],
    totals: Counter[str],
    mode_prefix: str,
) -> None:
    any_origin = False
    any_geometry = False
    for key, value in hits.items():
        if not value:
            continue
        totals[f"tow_classic_{key}_qualifies"] += 1
        totals[f"tow_{mode_prefix}_classic_{key}_qualifies"] += 1
        if key.endswith("_origin"):
            any_origin = True
        if key.endswith("_geometry"):
            any_geometry = True
    if any_origin:
        totals["tow_any_classic_origin_qualifies"] += 1
        totals[f"tow_{mode_prefix}_any_classic_origin_qualifies"] += 1
    if any_geometry:
        totals["tow_any_classic_geometry_qualifies"] += 1
        totals[f"tow_{mode_prefix}_any_classic_geometry_qualifies"] += 1
    if any_origin or any_geometry:
        totals["tow_any_classic_causal_point_qualifies"] += 1
        totals[f"tow_{mode_prefix}_any_classic_causal_point_qualifies"] += 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Test classic constant-voltage root-circle membership on the clean finite-fuel Tow "
            "residual rows whose displacement exactly equals an after-turn root-storm drag vector. "
            "Historical game mode is read only from archived mechanics payload. Evidence mining only."
        )
    )
    parser.add_argument("--external-log", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=EXAMPLE_LIMIT)
    args = parser.parse_args()
    if args.examples < 0:
        raise SystemExit("--examples must be non-negative")

    expected, clean_cases = _parse_clean_cases(args.external_log)
    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for case in clean_cases:
        by_game[int(case["game"])].append(case)

    totals: Counter[str] = Counter()
    totals["clean_residual_input"] = expected
    examples: list[dict[str, Any]] = []

    print("===== FINITE-FUEL TOW CLASSIC STORM MEMBERSHIP AUDIT =====")
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
        archive_mode, raw_mode_values = _nuionstorms_consensus(prepared.snapshots)
        if archive_mode is False:
            mode_prefix = "classic_mode"
        elif archive_mode is True:
            mode_prefix = "nu_mode"
        else:
            mode_prefix = "unknown_mode"

        storms_by_turn, storm_conflicts, storm_invalid = _storm_consensus_by_turn(prepared.snapshots)
        game_counts: Counter[str] = Counter()

        for case in by_game[game_id]:
            totals["tow_clean_cases"] += 1
            game_counts["tow_clean_cases"] += 1
            totals[f"tow_{mode_prefix}_rows"] += 1
            game_counts[f"tow_{mode_prefix}_rows"] += 1

            before_turn = int(case["turn"])
            after_turn = int(case["after_turn"])
            origin = _xy(case["origin"], "origin")
            geometry = _xy(case["geometry_endpoint"], "geometry_endpoint")
            observed = _xy(case["observed"], "observed")
            residual = (observed[0] - geometry[0], observed[1] - geometry[1])

            if before_turn in storm_conflicts or before_turn in storm_invalid:
                totals["tow_before_storm_context_unusable"] += 1
                continue
            if after_turn in storm_conflicts or after_turn in storm_invalid:
                totals["tow_after_storm_context_unusable"] += 1
                continue

            before_storms = storms_by_turn.get(before_turn, ())
            after_storms = storms_by_turn.get(after_turn, ())
            root_ids = _after_root_vector_matches(after_storms, residual)
            if not root_ids:
                totals["tow_no_after_root_vector_match"] += 1
                game_counts["tow_no_after_root_vector_match"] += 1
                continue

            totals["tow_after_root_vector_rows"] += 1
            game_counts["tow_after_root_vector_rows"] += 1
            totals[f"tow_{mode_prefix}_after_root_vector_rows"] += 1
            game_counts[f"tow_{mode_prefix}_after_root_vector_rows"] += 1
            totals["tow_after_root_vector_matches"] += len(root_ids)
            if len(root_ids) > 1:
                totals["tow_after_root_vector_ambiguous_rows"] += 1

            hits, witnesses, meta = _classic_variant_membership(
                root_ids=root_ids,
                before_storms=before_storms,
                after_storms=after_storms,
                origin=origin,
                geometry=geometry,
            )
            _record_hits(hits=hits, totals=totals, mode_prefix=mode_prefix)

            if len(examples) < args.examples:
                examples.append(
                    {
                        "game": game_id,
                        "turn": before_turn,
                        "after_turn": after_turn,
                        "tower_ship": int(case["tower_ship"]),
                        "target_ship": int(case["target_ship"]),
                        "nuionstorms_archive": archive_mode,
                        "root_ids": root_ids,
                        "origin": origin,
                        "geometry": geometry,
                        "observed": observed,
                        "residual": residual,
                        "hits": {key: value for key, value in sorted(hits.items()) if value},
                        "witnesses": witnesses,
                        "meta": meta,
                    }
                )

        print(
            {
                "game": game_id,
                "cache_hit": cache_hit,
                "nuionstorms_archive": archive_mode,
                "archive_raw_values": raw_mode_values,
                **dict(sorted(game_counts.items())),
            },
            flush=True,
        )

    if totals["tow_clean_cases"] != totals["clean_residual_input"]:
        raise AssertionError(
            f"Tow case accounting mismatch: input={totals['clean_residual_input']} cases={totals['tow_clean_cases']}"
        )
    if (
        totals["tow_after_root_vector_rows"]
        + totals["tow_no_after_root_vector_match"]
        + totals["tow_before_storm_context_unusable"]
        + totals["tow_after_storm_context_unusable"]
        != totals["tow_clean_cases"]
    ):
        raise AssertionError("Tow root-vector/context accounting mismatch")

    print("\n===== SUMMARY =====")
    primary = (
        "clean_residual_input",
        "tow_clean_cases",
        "tow_after_root_vector_rows",
        "tow_no_after_root_vector_match",
        "tow_after_root_vector_matches",
        "tow_after_root_vector_ambiguous_rows",
        "tow_classic_mode_rows",
        "tow_nu_mode_rows",
        "tow_unknown_mode_rows",
        "tow_classic_mode_after_root_vector_rows",
        "tow_nu_mode_after_root_vector_rows",
        "tow_unknown_mode_after_root_vector_rows",
        "tow_any_classic_origin_qualifies",
        "tow_any_classic_geometry_qualifies",
        "tow_any_classic_causal_point_qualifies",
        "tow_classic_mode_any_classic_origin_qualifies",
        "tow_classic_mode_any_classic_geometry_qualifies",
        "tow_classic_mode_any_classic_causal_point_qualifies",
        "tow_nu_mode_any_classic_causal_point_qualifies",
        "tow_unknown_mode_any_classic_causal_point_qualifies",
    )
    for key in primary:
        print(f"{key}= {totals[key]}")

    print("\n===== CLASSIC VARIANT COUNTERS =====")
    for key, value in sorted(totals.items()):
        if key.startswith("tow_classic_") and key.endswith("_qualifies") and key not in primary:
            print(f"{key}= {value}")

    print("\n===== MODE-SCOPED VARIANT COUNTERS =====")
    for key, value in sorted(totals.items()):
        if (
            key.startswith("tow_classic_mode_classic_")
            or key.startswith("tow_nu_mode_classic_")
            or key.startswith("tow_unknown_mode_classic_")
        ) and key.endswith("_qualifies"):
            print(f"{key}= {value}")

    print("\n===== CASES =====")
    for item in examples:
        print(item)

    print("\n===== INTERPRETATION =====")
    print(
        "Classic membership means constant root-storm voltage inside the root circle; it is only "
        "mode-consistent evidence when archived mechanics resolve nuionstorms=false."
    )
    print(
        "The after-turn root vector match remains a separate attribution fact. Membership under a "
        "classic variant does not by itself establish exact Host substep ordering."
    )
    print("Extreme (>=400 meV) storm transport remains fail-closed and is not treated as classic drag.")
    print("finite-fuel Tow remains OPEN; no simulator or planets-intel rule changes are made here.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
