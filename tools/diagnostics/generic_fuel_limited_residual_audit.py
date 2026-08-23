from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from math import ceil, hypot
from pathlib import Path
from typing import Any, Mapping

import duckdb

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.movement_chunnel_context import _sample_from_transition
from planets_lab.corpus.movement_differential import _entity_map, _intish
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.normalizer import _decode_member_json
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.data.nu_static import import_static_all
from planets_lab.rules.fuel import movement_fuel_use


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
HORWASP_HULL_IDS = frozenset(range(201, 214))


def _identity(owner_id: int | None, raw: Mapping[str, Any] | Any) -> tuple[Any, ...] | None:
    if owner_id is None or not hasattr(raw, "get"):
        return None
    return (
        owner_id,
        _intish(raw.get("hullid")),
        raw.get("name"),
        _intish(raw.get("turn")),
    )


def _static_specs(archive_data: bytes) -> NuStaticSpecs:
    members = turn_members(archive_data)
    if not members:
        raise ValueError("archive contains no .trn members")
    member = members[0]
    raw = read_archive_members(archive_data, [member.name])[member.name]
    payload, _ = _decode_member_json(raw, member)
    return NuStaticSpecs.from_catalog(import_static_all(payload))


def _cross_track_and_progress(
    target_vector: tuple[int, int],
    observed_vector: tuple[int, int],
) -> tuple[float | None, float | None]:
    tx, ty = target_vector
    ox, oy = observed_vector
    target_distance = hypot(tx, ty)
    if target_distance <= 1e-9:
        return None, None
    cross_track = abs(tx * oy - ty * ox) / target_distance
    progress = (tx * ox + ty * oy) / target_distance
    return cross_track, progress


def _fuel_bucket(value: int | None) -> str:
    if value is None:
        return "missing"
    if value == 0:
        return "zero"
    if value <= 5:
        return "1_5"
    if value <= 20:
        return "6_20"
    if value <= 50:
        return "21_50"
    if value <= 100:
        return "51_100"
    return "gt100"


def _max_affordable_whole_distance(
    *,
    fuel: int,
    fuel_factor: int,
    total_mass: int,
    regular_distance: float,
    max_distance_per_turn: int,
) -> int:
    upper = max(0, int(ceil(regular_distance)))
    best = 0
    for distance in range(upper + 1):
        required = movement_fuel_use(
            fuel_factor=fuel_factor,
            total_mass=total_mass,
            distance_traveled=distance,
            max_distance_per_turn=max_distance_per_turn,
        )
        if required <= fuel:
            best = distance
        else:
            break
    return best


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the generic post-sphere same-line short-movement residual for "
            "insufficient-fuel signatures across hulls and games. The audit reads "
            "private raw/prepared state locally but prints only derived mechanical data."
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
                is_gravitonic_hull
            FROM movement_post_horwasp_strong_residual
            WHERE hull_id NOT BETWEEN 201 AND 213
              AND warp BETWEEN 1 AND 9
            ORDER BY game_id, before_archive_turn, after_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()

    print("===== GENERIC FUEL-LIMITED RESIDUAL AUDIT =====")
    print("generic_non_horwasp_warp1_9_rows=", len(rows))

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    totals = Counter()
    hull_counts = Counter()
    game_counts = Counter()
    candidate_hulls = Counter()
    candidate_games = Counter()
    strong_hulls = Counter()
    strong_games = Counter()
    fuel_before_buckets = Counter()
    fuel_after_buckets = Counter()
    engine_counts = Counter()
    formula_status = Counter()
    baseline_counts = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        archive_data = archive_path.read_bytes()
        prepared, prepared_hit = load_or_build_prepared_game_cache(
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
            f"prepared game={game_id} cache_hit={prepared_hit} rows={len(by_game[game_id])} "
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
            ) = row
            hull_id = int(hull_id)
            before_turn = int(before_turn)
            after_turn = int(after_turn)
            ship_id = int(ship_id)
            warp = int(warp)

            totals["rows"] += 1
            hull_counts[hull_id] += 1
            game_counts[game_id] += 1
            baseline_counts[str(baseline_category)] += 1

            if is_gravitonic is True:
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

            origin = (sample.x, sample.y)
            observed = sample.observed_destination
            target = (sample.target_x, sample.target_y)
            observed_vector = _vector(origin, observed, topology)
            target_vector = _vector(origin, target, topology)
            observed_distance = hypot(*observed_vector)
            target_distance = hypot(*target_vector)
            nominal = float(warp * warp)
            regular_distance = min(target_distance, nominal)
            cross_track, progress = _cross_track_and_progress(target_vector, observed_vector)

            toward = (
                cross_track is not None
                and progress is not None
                and cross_track <= 1.5
                and progress > 0.0
            )
            short = (
                toward
                and observed_distance > 0.0
                and observed_distance + 1.5 < regular_distance
            )
            if toward:
                totals["same_line_forward"] += 1
            if short:
                totals["short_same_line_forward"] += 1
                candidate_hulls[hull_id] += 1
                candidate_games[game_id] += 1
            else:
                continue

            before_group = ship_groups.get((before_turn, ship_id), ())
            owner_id, before_owner = _owner_record(before_group)
            if owner_id is None or before_owner is None:
                totals["candidate_missing_before_owner"] += 1
                continue
            before_raw = before_owner.raw

            after_group = ship_groups.get((after_turn, ship_id), ())
            after_owner_id, after_owner = _owner_record(after_group)
            same_identity = (
                after_owner is not None
                and _identity(owner_id, before_raw) == _identity(after_owner_id, after_owner.raw)
            )
            if same_identity:
                totals["candidate_same_identity_after"] += 1
            else:
                totals["candidate_identity_break_after"] += 1

            before_fuel = _intish(before_raw.get("neutronium"))
            after_fuel = _intish(after_owner.raw.get("neutronium")) if same_identity else None
            raw_mass = _intish(before_raw.get("mass"))
            engine_id = _intish(before_raw.get("engineid"))
            fuel_before_buckets[_fuel_bucket(before_fuel)] += 1
            fuel_after_buckets[_fuel_bucket(after_fuel)] += 1
            engine_counts[engine_id] += 1

            formula_ready = (
                engine_id is not None
                and engine_id in specs.engines
                and raw_mass is not None
                and raw_mass >= 0
                and before_fuel is not None
                and before_fuel >= 0
            )
            if not formula_ready:
                formula_status["not_ready"] += 1
                continue
            totals["candidate_formula_ready"] += 1

            fuel_factor = specs.engines[engine_id].fuel_factor(warp)
            required_observed = movement_fuel_use(
                fuel_factor=fuel_factor,
                total_mass=raw_mass,
                distance_traveled=observed_distance,
                max_distance_per_turn=warp * warp,
            )
            required_regular = movement_fuel_use(
                fuel_factor=fuel_factor,
                total_mass=raw_mass,
                distance_traveled=regular_distance,
                max_distance_per_turn=warp * warp,
            )
            affordable_distance = _max_affordable_whole_distance(
                fuel=before_fuel,
                fuel_factor=fuel_factor,
                total_mass=raw_mass,
                regular_distance=regular_distance,
                max_distance_per_turn=warp * warp,
            )

            insufficient = before_fuel < required_regular
            observed_affordable = before_fuel >= required_observed
            frontier_match = abs(observed_distance - float(affordable_distance)) <= 1.5
            depleted_after = same_identity and after_fuel == 0

            if insufficient:
                formula_status["insufficient_for_regular"] += 1
            else:
                formula_status["sufficient_for_regular"] += 1
            if observed_affordable:
                formula_status["observed_affordable"] += 1
            else:
                formula_status["observed_not_affordable"] += 1
            if insufficient and observed_affordable:
                formula_status["formula_brackets_observed"] += 1
            if frontier_match:
                formula_status["affordable_frontier_match"] += 1
            if depleted_after:
                formula_status["depleted_after"] += 1

            strong = (
                same_identity
                and insufficient
                and observed_affordable
                and frontier_match
                and depleted_after
            )
            if strong:
                formula_status["strong_fuel_limit_signature"] += 1
                strong_hulls[hull_id] += 1
                strong_games[game_id] += 1

            detail = {
                "game": game_id,
                "turn": before_turn,
                "ship": ship_id,
                "hull": hull_id,
                "baseline": str(baseline_category),
                "warp": warp,
                "fuel_before": before_fuel,
                "fuel_after": after_fuel,
                "mass_before_raw": raw_mass,
                "engine_id": engine_id,
                "fuel_factor": fuel_factor,
                "target_distance": round(target_distance, 3),
                "regular_distance": round(regular_distance, 3),
                "observed_distance": round(observed_distance, 3),
                "cross_track": None if cross_track is None else round(cross_track, 3),
                "progress": None if progress is None else round(progress, 3),
                "required_observed": required_observed,
                "required_regular": required_regular,
                "affordable_whole_ly": affordable_distance,
                "same_identity_after": same_identity,
                "insufficient_for_regular": insufficient,
                "observed_affordable": observed_affordable,
                "affordable_frontier_match": frontier_match,
                "depleted_after": depleted_after,
            }
            bucket = "strong" if strong else (
                "bracketed" if insufficient and observed_affordable else "other"
            )
            if len(examples[bucket]) < args.examples:
                examples[bucket].append(detail)

    print("\n===== POPULATION =====")
    for key in (
        "rows",
        "gravitonic_excluded",
        "same_line_forward",
        "short_same_line_forward",
        "candidate_same_identity_after",
        "candidate_identity_break_after",
        "candidate_formula_ready",
    ):
        print(f"{key}=", totals[key])

    print("\n===== SHORT SAME-LINE CANDIDATE HULLS =====")
    for hull_id, count in candidate_hulls.most_common(40):
        print(hull_id, count)

    print("\n===== SHORT SAME-LINE CANDIDATE GAMES =====")
    for game_id, count in candidate_games.most_common():
        print(game_id, count)

    print("\n===== FORMULA STATUS =====")
    for key, count in formula_status.most_common():
        print(key, count)

    print("\n===== STRONG FUEL-LIMIT SIGNATURE BY HULL =====")
    for hull_id, count in strong_hulls.most_common():
        print(hull_id, count)

    print("\n===== STRONG FUEL-LIMIT SIGNATURE BY GAME =====")
    for game_id, count in strong_games.most_common():
        print(game_id, count)

    print("\n===== FUEL BEFORE BUCKETS (SHORT SAME-LINE) =====")
    for key, count in fuel_before_buckets.most_common():
        print(key, count)

    print("\n===== FUEL AFTER BUCKETS (SHORT SAME-LINE) =====")
    for key, count in fuel_after_buckets.most_common():
        print(key, count)

    print("\n===== ENGINE IDS (SHORT SAME-LINE) =====")
    for key, count in engine_counts.most_common():
        print(key, count)

    print("\n===== BASELINE CATEGORIES (GENERIC WARP1-9 POPULATION) =====")
    for key, count in baseline_counts.most_common():
        print(key, count)

    for bucket, title in (
        ("strong", "STRONG FUEL-LIMIT EXAMPLES"),
        ("bracketed", "BRACKETED BUT NOT STRONG EXAMPLES"),
        ("other", "OTHER SHORT SAME-LINE EXAMPLES"),
    ):
        print(f"\n===== {title} =====")
        for detail in examples[bucket]:
            print(detail)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "Raw snapshot mass is used only as a correlation input. A strong signature "
        "requires same-identity continuity, insufficient fuel for the regular move, "
        "affordability of the observed move, an observed distance near the maximum "
        "whole-light-year affordable frontier, and fuel depletion to zero."
    )
    print(
        "Do not promote fuel proration solely from bracketed rows; compare strong "
        "coverage across multiple hulls/games and inspect false negatives/controls."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
