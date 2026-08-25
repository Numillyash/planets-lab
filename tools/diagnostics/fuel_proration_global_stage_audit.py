from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any

import duckdb

from planets_lab.corpus.movement_chunnel_context import _sample_from_transition
from planets_lab.corpus.movement_damage_context import _race_map, max_warp_from_damage
from planets_lab.corpus.movement_differential import _entity_map, _intish
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology, sphere_adjusted_sample
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.fuel import movement_fuel_use
from planets_lab.rules.proration import prorate_waypoint_distance

from fuel_proration_host_differential_audit import _project
from generic_fuel_limited_residual_audit import _max_affordable_whole_distance, _static_specs
from mine_hit_hostorder_differential_audit import _owner_states


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
HORWASP_HULL_IDS = frozenset(range(201, 214))


def _stage_name(stage: tuple[bool, bool, bool, bool] | None) -> str:
    if stage is None:
        return "missing_label_row"
    chunnel, horwasp, mine, final_residual = stage
    if chunnel:
        return "chunnel_explained"
    if horwasp:
        return "horwasp_strong_explained"
    if mine:
        return "mine_strong_explained"
    if final_residual:
        return "post_mine_strong_residual"
    return "other"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit documented Nu insufficient-fuel waypoint proration across the full "
            "current L1 external residual, then partition exact matches by downstream "
            "Chunnel/Horwasp/mine/final L2 stage. This is a pre-production overlap "
            "guard: it must not silently let an early L1 fuel classifier steal rows "
            "from already verified downstream mechanics."
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
                target_y
            FROM movement_residual
            WHERE hull_id NOT BETWEEN 201 AND 213
              AND warp BETWEEN 1 AND 9
            ORDER BY game_id, before_archive_turn, after_archive_turn, ship_id
            """
        ).fetchall()
        stage_rows = con.execute(
            """
            SELECT
                game_id,
                before_archive_turn,
                after_archive_turn,
                ship_id,
                coalesce(chunnel_explained, false),
                coalesce(horwasp_strong_explained, false),
                coalesce(mine_strong_explained, false),
                coalesce(post_mine_strong_residual, false)
            FROM movement_labeled_residual
            """
        ).fetchall()
    finally:
        con.close()

    stage_by_key = {
        (int(game_id), int(before_turn), int(after_turn), int(ship_id)): (
            bool(chunnel),
            bool(horwasp),
            bool(mine),
            bool(final_residual),
        )
        for (
            game_id,
            before_turn,
            after_turn,
            ship_id,
            chunnel,
            horwasp,
            mine,
            final_residual,
        ) in stage_rows
    }

    print("===== GLOBAL FUEL PRORATION STAGE AUDIT =====")
    print("residual_view= movement_residual")
    print("l1_non_horwasp_warp1_9_rows=", len(rows))

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    totals = Counter()
    exact_stages = Counter()
    nu_only_stages = Counter()
    exact_hulls = Counter()
    exact_games = Counter()
    nu_only_hulls = Counter()
    nu_only_games = Counter()
    examples: list[dict[str, Any]] = []

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
        races = _race_map(prepared.snapshots)
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
            ) = row
            before_turn = int(before_turn)
            after_turn = int(after_turn)
            ship_id = int(ship_id)
            hull_id = int(hull_id)
            warp = int(warp)
            totals["rows"] += 1

            if bool(is_gravitonic):
                totals["gravitonic_excluded"] += 1
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
                continue
            totals["reachable_waypoint"] += 1

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
                continue
            totals["same_identity_after"] += 1

            race_id = races.get(owner_id)
            damage = _intish(before_raw.get("damage"))
            if race_id is None or damage is None or damage < 0:
                totals["damage_guard_not_ready"] += 1
                continue
            max_damage_warp = max_warp_from_damage(damage, race_id)
            if max_damage_warp is None:
                totals["damage_guard_destroyed_or_invalid"] += 1
                continue
            if max_damage_warp < warp:
                totals["raw_damage_limited_excluded"] += 1
                continue
            totals["damage_guard_clear"] += 1

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

            nu_distance = prorate_waypoint_distance(
                requested_distance=target_distance,
                fuel_available=before_fuel,
                fuel_required=fuel_required,
            ).distance
            nu_endpoint = _project(sample, nu_distance)

            frontier_distance = _max_affordable_whole_distance(
                fuel=before_fuel,
                fuel_factor=fuel_factor,
                total_mass=raw_mass,
                regular_distance=target_distance,
                max_distance_per_turn=max_distance,
            )
            frontier_endpoint = _project(sample, float(frontier_distance))

            vgap_distance = min(target_distance, max_distance * before_fuel / fuel_required)
            vgap_endpoint = _project(sample, vgap_distance)

            observed = sample.observed_destination
            nu_exact = nu_endpoint == observed
            frontier_exact = frontier_endpoint == observed
            vgap_exact = vgap_endpoint == observed
            if not nu_exact:
                continue

            totals["nu_proration_endpoint_exact"] += 1
            key = (game_id, before_turn, after_turn, ship_id)
            stage = _stage_name(stage_by_key.get(key))
            exact_stages[stage] += 1
            exact_hulls[hull_id] += 1
            exact_games[game_id] += 1

            nu_only = not frontier_exact and not vgap_exact
            if nu_only:
                totals["nu_only_endpoint_exact"] += 1
                nu_only_stages[stage] += 1
                nu_only_hulls[hull_id] += 1
                nu_only_games[game_id] += 1

            if len(examples) < args.examples:
                examples.append(
                    {
                        "game": game_id,
                        "turn": before_turn,
                        "ship": ship_id,
                        "hull": hull_id,
                        "baseline": str(baseline_category),
                        "warp": warp,
                        "stage": stage,
                        "fuel_before": before_fuel,
                        "mass_before_raw": raw_mass,
                        "target_distance": round(target_distance, 3),
                        "fuel_required": fuel_required,
                        "nu_distance": round(nu_distance, 3),
                        "frontier_distance": frontier_distance,
                        "vgap3_distance": round(vgap_distance, 3),
                        "observed": observed,
                        "nu_endpoint": nu_endpoint,
                        "frontier_endpoint": frontier_endpoint,
                        "vgap3_endpoint": vgap_endpoint,
                        "nu_only": nu_only,
                    }
                )

    print("\n===== POPULATION =====")
    for key in (
        "rows",
        "gravitonic_excluded",
        "partial_waypoint_excluded",
        "reachable_waypoint",
        "same_identity_after",
        "identity_break_after",
        "damage_guard_not_ready",
        "damage_guard_destroyed_or_invalid",
        "raw_damage_limited_excluded",
        "damage_guard_clear",
        "formula_ready",
        "zero_required_fuel",
        "zero_fuel_separate_mechanic",
        "raw_mass_sufficient_for_waypoint",
        "raw_mass_insufficient_for_waypoint",
        "nu_proration_endpoint_exact",
        "nu_only_endpoint_exact",
    ):
        print(f"{key}=", totals[key])

    print("\n===== NU EXACT BY DOWNSTREAM STAGE =====")
    for stage, count in exact_stages.most_common():
        print(stage, count)

    print("\n===== NU-ONLY EXACT BY DOWNSTREAM STAGE =====")
    for stage, count in nu_only_stages.most_common():
        print(stage, count)

    print("\n===== NU EXACT BY HULL =====")
    for hull_id, count in exact_hulls.most_common():
        print(hull_id, count)

    print("\n===== NU EXACT BY GAME =====")
    for game_id, count in exact_games.most_common():
        print(game_id, count)

    print("\n===== NU-ONLY EXACT BY HULL =====")
    for hull_id, count in nu_only_hulls.most_common():
        print(hull_id, count)

    print("\n===== NU-ONLY EXACT BY GAME =====")
    for game_id, count in nu_only_games.most_common():
        print(game_id, count)

    print("\n===== NU EXACT EXAMPLES =====")
    for detail in examples:
        print(detail)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "The historical next-turn snapshot is not treated as an immediate post-Host "
        "state for editable warp/waypoint/fuel fields. Promotion is based on submitted "
        "before-turn mechanics plus exact Host x/y outcome, documented Nu waypoint "
        "proration, competing-rule discrimination and downstream-stage overlap."
    )
    print(
        "Raw damage-limited rows are excluded conservatively before evaluating fuel. "
        "If exact Nu matches overlap verified Chunnel/Horwasp/mine stages, do not add "
        "an early L1 fuel classifier without resolving that overlap first."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
