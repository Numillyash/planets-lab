from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any

import duckdb

from planets_lab.corpus.movement_chunnel_context import _sample_from_transition
from planets_lab.corpus.movement_differential import _entity_map, _intish
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology, sphere_adjusted_sample
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.fuel import movement_fuel_use
from planets_lab.rules.proration import prorate_waypoint_distance
from planets_lab.sim.normal_movement import project_toward_waypoint

from damage_limited_warp_residual_audit import (
    _direction_bucket,
    _ratio_bucket,
    _target_relation,
)
from generic_fuel_limited_residual_audit import (
    _identity,
    _max_affordable_whole_distance,
    _static_specs,
)
from mine_hit_hostorder_differential_audit import _owner_states


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
HORWASP_HULL_IDS = frozenset(range(201, 214))


def _project(sample: Any, distance: float) -> tuple[int, int]:
    return project_toward_waypoint(
        x=int(sample.x),
        y=int(sample.y),
        target_x=int(sample.target_x),
        target_y=int(sample.target_y),
        distance=distance,
    )


def _post_reset(after_raw: Any, *, observed_raw: tuple[int, int]) -> bool:
    if not hasattr(after_raw, "get"):
        return False
    fuel = _intish(after_raw.get("neutronium"))
    warp = _intish(after_raw.get("warp"))
    target_x = _intish(after_raw.get("targetx", after_raw.get("waypointx")))
    target_y = _intish(after_raw.get("targety", after_raw.get("waypointy")))
    return fuel == 0 and warp == 0 and (target_x, target_y) == observed_raw


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare documented Planets.nu insufficient-fuel waypoint proration against "
            "the historical affordable-frontier heuristic and a VGAP3-style max-distance "
            "ratio on the current final movement residual. The strongest subset is "
            "restricted to reachable non-Gravitonic waypoints with same-identity "
            "continuity and the documented out-of-fuel post-state reset."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--examples", type=int, default=40)
    args = parser.parse_args()

    con = duckdb.connect(str(args.database), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT
                game_id,
                before_archive_turn,
                after_archive_turn,
                ship_id,
                hull_id,
                baseline_category,
                warp,
                coalesce(is_gravitonic_hull, false),
                x_before,
                y_before,
                x_after,
                y_after,
                target_x,
                target_y,
                coalesce(observed_distance, 0.0),
                coalesce(nominal_max_distance, 0.0)
            FROM movement_post_mine_strong_residual
            WHERE hull_id NOT BETWEEN 201 AND 213
              AND warp BETWEEN 1 AND 9
            ORDER BY game_id, before_archive_turn, after_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()

    print("===== FUEL PRORATION HOST DIFFERENTIAL =====")
    print("residual_view= movement_post_mine_strong_residual")
    print("generic_non_horwasp_warp1_9_rows=", len(rows))

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    totals = Counter()
    nu_exact_hulls = Counter()
    nu_exact_games = Counter()
    strong_hulls = Counter()
    strong_games = Counter()
    target_strong_hulls = Counter()
    target_strong_games = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for game_id in sorted(by_game):
        archive_data = (RAW_DIR / f"game-{game_id}.zip").read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        raw_topology = extract_map_topology(archive_data)
        topology = effective_sphere_topology(game_id=game_id, topology=raw_topology)
        specs = _static_specs(archive_data)
        entities = _entity_map(prepared.snapshots)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        transition_by_key = {
            (item.before_archive_turn, item.after_archive_turn, item.entity_id): item
            for item in prepared.movement_geometry_readiness.results
        }
        print(
            f"prepared game={game_id} cache_hit={cache_hit} rows={len(by_game[game_id])} "
            f"raw_map=({raw_topology.mapwidth},{raw_topology.mapheight}) "
            f"effective_map=({topology.mapwidth},{topology.mapheight})"
        )

        for row in by_game[game_id]:
            (
                _game_id,
                before_turn,
                after_turn,
                ship_id,
                hull_id,
                baseline_category,
                warp,
                is_gravitonic,
                x,
                y,
                next_x,
                next_y,
                target_x,
                target_y,
                compiled_observed_distance,
                compiled_nominal_distance,
            ) = row
            before_turn = int(before_turn)
            after_turn = int(after_turn)
            ship_id = int(ship_id)
            hull_id = int(hull_id)
            warp = int(warp)
            x, y = int(x), int(y)
            next_x, next_y = int(next_x), int(next_y)
            target_x, target_y = int(target_x), int(target_y)
            compiled_observed_distance = float(compiled_observed_distance)
            compiled_nominal_distance = float(compiled_nominal_distance)
            totals["rows"] += 1

            target_short = (
                warp >= 7
                and _ratio_bucket(compiled_observed_distance, compiled_nominal_distance) == "<0.5x"
                and _target_relation(
                    x=x,
                    y=y,
                    next_x=next_x,
                    next_y=next_y,
                    target_x=target_x,
                    target_y=target_y,
                ) == "observed=other"
                and _direction_bucket(
                    x=x,
                    y=y,
                    next_x=next_x,
                    next_y=next_y,
                    target_x=target_x,
                    target_y=target_y,
                ) == "same_line_forward"
            )
            if target_short:
                totals["target_short_forward_rows"] += 1

            if bool(is_gravitonic):
                totals["gravitonic_excluded"] += 1
                if target_short:
                    totals["target_short_gravitonic_excluded"] += 1
                continue

            transition = transition_by_key.get((before_turn, after_turn, ship_id))
            if transition is None:
                totals["missing_transition"] += 1
                continue
            sample = _sample_from_transition(transition, entities)
            if sample is None:
                totals["missing_sample"] += 1
                continue
            if (
                topology.sphere is True
                and topology.mapwidth is not None
                and topology.mapheight is not None
            ):
                sample = sphere_adjusted_sample(
                    sample,
                    width=int(topology.mapwidth),
                    height=int(topology.mapheight),
                )

            target_distance = hypot(sample.target_x - sample.x, sample.target_y - sample.y)
            max_distance = warp * warp
            if target_distance > max_distance + 1e-9:
                totals["partial_waypoint_excluded"] += 1
                if target_short:
                    totals["target_short_partial_waypoint_excluded"] += 1
                continue
            totals["reachable_waypoint"] += 1
            if target_short:
                totals["target_short_reachable_waypoint"] += 1

            owner_id, before_raw, after_raw, same_identity = _owner_states(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=ship_id,
            )
            if owner_id is None or before_raw is None:
                totals["owner_state_missing"] += 1
                continue
            if not same_identity or after_raw is None:
                totals["identity_break_after"] += 1
                if target_short:
                    totals["target_short_identity_break_after"] += 1
                continue
            totals["same_identity_after"] += 1
            if target_short:
                totals["target_short_same_identity_after"] += 1

            before_fuel = _intish(before_raw.get("neutronium"))
            raw_mass = _intish(before_raw.get("mass"))
            engine_id = _intish(before_raw.get("engineid"))
            if (
                before_fuel is None
                or before_fuel < 0
                or raw_mass is None
                or raw_mass < 0
                or engine_id is None
                or engine_id not in specs.engines
            ):
                totals["formula_not_ready"] += 1
                continue
            totals["formula_ready"] += 1
            if target_short:
                totals["target_short_formula_ready"] += 1

            fuel_factor = specs.engines[engine_id].fuel_factor(warp)
            fuel_required = movement_fuel_use(
                fuel_factor=fuel_factor,
                total_mass=raw_mass,
                distance_traveled=target_distance,
                max_distance_per_turn=max_distance,
            )
            if fuel_required <= 0:
                totals["zero_required_fuel"] += 1
                continue
            if before_fuel <= 0:
                totals["zero_fuel_separate_mechanic"] += 1
                continue
            if before_fuel >= fuel_required:
                totals["raw_mass_sufficient_for_waypoint"] += 1
                continue

            totals["raw_mass_insufficient_for_waypoint"] += 1
            if target_short:
                totals["target_short_raw_mass_insufficient_for_waypoint"] += 1

            nu_proration = prorate_waypoint_distance(
                requested_distance=target_distance,
                fuel_available=before_fuel,
                fuel_required=fuel_required,
            )
            nu_endpoint = _project(sample, nu_proration.distance)

            frontier_distance = _max_affordable_whole_distance(
                fuel=before_fuel,
                fuel_factor=fuel_factor,
                total_mass=raw_mass,
                regular_distance=target_distance,
                max_distance_per_turn=max_distance,
            )
            frontier_endpoint = _project(sample, float(frontier_distance))

            vgap_distance = min(
                target_distance,
                max_distance * before_fuel / fuel_required,
            )
            vgap_endpoint = _project(sample, vgap_distance)

            observed = sample.observed_destination
            nu_exact = nu_endpoint == observed
            frontier_exact = frontier_endpoint == observed
            vgap_exact = vgap_endpoint == observed
            post_reset = _post_reset(
                after_raw,
                observed_raw=(next_x, next_y),
            )

            if post_reset:
                totals["post_out_of_fuel_reset"] += 1
                if target_short:
                    totals["target_short_post_out_of_fuel_reset"] += 1

            if nu_exact:
                totals["nu_proration_endpoint_exact"] += 1
                nu_exact_hulls[hull_id] += 1
                nu_exact_games[game_id] += 1
                if target_short:
                    totals["target_short_nu_proration_endpoint_exact"] += 1
            if frontier_exact:
                totals["frontier_endpoint_exact"] += 1
                if target_short:
                    totals["target_short_frontier_endpoint_exact"] += 1
            if vgap_exact:
                totals["vgap3_endpoint_exact"] += 1
                if target_short:
                    totals["target_short_vgap3_endpoint_exact"] += 1

            signature = (
                "nu" if nu_exact else "-",
                "frontier" if frontier_exact else "-",
                "vgap3" if vgap_exact else "-",
            )
            totals[f"rule_signature:{signature}"] += 1

            strong = nu_exact and post_reset
            if strong:
                totals["nu_proration_strong"] += 1
                strong_hulls[hull_id] += 1
                strong_games[game_id] += 1
                if target_short:
                    totals["target_short_nu_proration_strong"] += 1
                    target_strong_hulls[hull_id] += 1
                    target_strong_games[game_id] += 1

            detail = {
                "game": game_id,
                "turn": before_turn,
                "ship": ship_id,
                "hull": hull_id,
                "baseline": str(baseline_category),
                "warp": warp,
                "target_119_family": target_short,
                "fuel_before": before_fuel,
                "fuel_after": _intish(after_raw.get("neutronium")),
                "mass_before_raw": raw_mass,
                "engine_id": engine_id,
                "fuel_factor": fuel_factor,
                "target_distance": round(target_distance, 3),
                "fuel_required": fuel_required,
                "nu_distance": round(nu_proration.distance, 3),
                "frontier_distance": frontier_distance,
                "vgap3_distance": round(vgap_distance, 3),
                "observed": observed,
                "nu_endpoint": nu_endpoint,
                "frontier_endpoint": frontier_endpoint,
                "vgap3_endpoint": vgap_endpoint,
                "nu_exact": nu_exact,
                "frontier_exact": frontier_exact,
                "vgap3_exact": vgap_exact,
                "post_out_of_fuel_reset": post_reset,
            }
            bucket = "strong" if strong else "insufficient"
            if len(examples[bucket]) < args.examples:
                examples[bucket].append(detail)

    print("\n===== POPULATION =====")
    for key in (
        "rows",
        "target_short_forward_rows",
        "gravitonic_excluded",
        "target_short_gravitonic_excluded",
        "partial_waypoint_excluded",
        "target_short_partial_waypoint_excluded",
        "reachable_waypoint",
        "target_short_reachable_waypoint",
        "same_identity_after",
        "identity_break_after",
        "formula_ready",
        "zero_required_fuel",
        "zero_fuel_separate_mechanic",
        "raw_mass_sufficient_for_waypoint",
        "raw_mass_insufficient_for_waypoint",
        "target_short_raw_mass_insufficient_for_waypoint",
        "post_out_of_fuel_reset",
        "target_short_post_out_of_fuel_reset",
    ):
        print(f"{key}=", totals[key])

    print("\n===== RULE DIFFERENTIAL =====")
    for key in (
        "nu_proration_endpoint_exact",
        "frontier_endpoint_exact",
        "vgap3_endpoint_exact",
        "nu_proration_strong",
    ):
        print(f"{key}=", totals[key])

    print("\n===== TARGET 119 FAMILY DIFFERENTIAL =====")
    for key in (
        "target_short_forward_rows",
        "target_short_reachable_waypoint",
        "target_short_formula_ready",
        "target_short_raw_mass_insufficient_for_waypoint",
        "target_short_nu_proration_endpoint_exact",
        "target_short_frontier_endpoint_exact",
        "target_short_vgap3_endpoint_exact",
        "target_short_nu_proration_strong",
    ):
        print(f"{key}=", totals[key])

    print("\n===== RULE SIGNATURES =====")
    for key, count in sorted(
        ((key, count) for key, count in totals.items() if str(key).startswith("rule_signature:")),
        key=lambda item: (-item[1], str(item[0])),
    ):
        print(str(key).split(":", 1)[1], count)

    print("\n===== NU EXACT BY HULL =====")
    for hull_id, count in nu_exact_hulls.most_common():
        print(hull_id, count)

    print("\n===== NU EXACT BY GAME =====")
    for gid, count in nu_exact_games.most_common():
        print(gid, count)

    print("\n===== STRONG NU PRORATION BY HULL =====")
    for hull_id, count in strong_hulls.most_common():
        print(hull_id, count)

    print("\n===== STRONG NU PRORATION BY GAME =====")
    for gid, count in strong_games.most_common():
        print(gid, count)

    print("\n===== TARGET-119 STRONG BY HULL =====")
    for hull_id, count in target_strong_hulls.most_common():
        print(hull_id, count)

    print("\n===== TARGET-119 STRONG BY GAME =====")
    for gid, count in target_strong_games.most_common():
        print(gid, count)

    print("\n===== STRONG NU PRORATION EXAMPLES =====")
    for detail in examples["strong"]:
        print(detail)

    print("\n===== OTHER RAW-MASS INSUFFICIENT EXAMPLES =====")
    for detail in examples["insufficient"]:
        print(detail)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "The documented Nu rule is waypoint-distance proration: requested distance * "
        "fuel available / fuel required. Affordable-frontier and VGAP3-style projections "
        "are explicit competing controls, not production rules."
    )
    print(
        "This audit intentionally excludes Gravitonic ships, zero-fuel movement and "
        "waypoints beyond the normal per-turn reach. Raw snapshot mass is still only a "
        "candidate pre-movement mass, so production promotion requires exact endpoint "
        "discrimination plus the documented out-of-fuel reset and cross-game support."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
