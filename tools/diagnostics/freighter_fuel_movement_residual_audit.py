from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any

import duckdb

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.movement_chunnel_context import _sample_from_transition
from planets_lab.corpus.movement_differential import (
    _entity_map,
    _intish,
    _movement_category,
    _planet_tuples_by_turn,
)
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.normalizer import _decode_member_json
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.data.nu_static import import_static_all
from planets_lab.rules.fuel import movement_fuel_use


DEFAULT_HULLS = (16, 17)
DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")


def _identity(owner_id: int | None, raw: dict[str, Any] | Any) -> tuple[Any, ...] | None:
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit cross-game freighter movement residuals for documented insufficient-fuel "
            "proration and zero-fuel movement signatures. This is a correlation audit; it "
            "does not promote a movement rule."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--hull-id", type=int, action="append", default=None)
    parser.add_argument("--examples", type=int, default=30)
    args = parser.parse_args()

    hull_ids = tuple(sorted(set(args.hull_id or DEFAULT_HULLS)))
    con = duckdb.connect(str(args.database), read_only=True)
    try:
        placeholders = ",".join("?" for _ in hull_ids)
        rows = con.execute(
            f"""
            SELECT game_id, before_archive_turn, after_archive_turn, ship_id, hull_id
            FROM movement_post_horwasp_strong_residual
            WHERE hull_id IN ({placeholders})
            ORDER BY game_id, before_archive_turn, ship_id
            """,
            list(hull_ids),
        ).fetchall()
    finally:
        con.close()

    print("hull_ids=", list(hull_ids))
    print("compiled_residual_rows=", len(rows))
    by_game: dict[int, list[tuple[int, int, int, int, int]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(tuple(int(value) for value in row))
    print("games=", sorted(by_game))

    totals: Counter[tuple[int, str]] = Counter()
    baseline_counts: Counter[tuple[int, str]] = Counter()
    fuel_before_counts: Counter[tuple[int, str]] = Counter()
    fuel_after_counts: Counter[tuple[int, str]] = Counter()
    engine_counts: Counter[tuple[int, int | None]] = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        prepared_path = PREPARED_DIR / f"game-{game_id}.pickle"
        archive_data = archive_path.read_bytes()
        prepared, hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=prepared_path,
        )
        topology = extract_map_topology(archive_data)
        specs = _static_specs(archive_data)
        records = prepared.snapshots
        entities = _entity_map(records)
        planets_by_turn = _planet_tuples_by_turn(entities)
        ship_groups = group_perspective_records(records, "ship")
        transition_by_key = {
            (item.before_archive_turn, item.after_archive_turn, item.entity_id): item
            for item in prepared.movement_geometry_readiness.results
        }
        print(
            f"game={game_id} prepared_cache_hit={hit} rows={len(by_game[game_id])} "
            f"sphere={topology.sphere} map=({topology.mapwidth},{topology.mapheight})"
        )

        for _gid, before_turn, after_turn, ship_id, hull_id in by_game[game_id]:
            totals[(hull_id, "rows")] += 1
            transition = transition_by_key.get((before_turn, after_turn, ship_id))
            if transition is None:
                totals[(hull_id, "missing_transition")] += 1
                continue
            sample = _sample_from_transition(transition, entities)
            if sample is None:
                totals[(hull_id, "missing_sample")] += 1
                continue

            before_group = ship_groups.get((before_turn, ship_id), ())
            owner_id, before_owner = _owner_record(before_group)
            if owner_id is None or before_owner is None:
                totals[(hull_id, "missing_before_owner")] += 1
                continue
            before_raw = before_owner.raw

            after_group = ship_groups.get((after_turn, ship_id), ())
            after_owner_id, after_owner = _owner_record(after_group)
            same_identity = (
                after_owner is not None
                and _identity(owner_id, before_raw) == _identity(after_owner_id, after_owner.raw)
            )
            if same_identity:
                totals[(hull_id, "same_identity_after")] += 1
            else:
                totals[(hull_id, "identity_break_after")] += 1

            before_fuel = _intish(before_raw.get("neutronium"))
            after_fuel = _intish(after_owner.raw.get("neutronium")) if same_identity else None
            raw_mass = _intish(before_raw.get("mass"))
            engine_id = _intish(before_raw.get("engineid"))
            fuel_before_counts[(hull_id, _fuel_bucket(before_fuel))] += 1
            fuel_after_counts[(hull_id, _fuel_bucket(after_fuel))] += 1
            engine_counts[(hull_id, engine_id)] += 1

            planets = planets_by_turn.get(before_turn, ())
            baseline = _movement_category(sample, planets=planets)
            baseline_counts[(hull_id, baseline)] += 1

            origin = (sample.x, sample.y)
            observed = sample.observed_destination
            target = (sample.target_x, sample.target_y)
            observed_vector = _vector(origin, observed, topology)
            target_vector = _vector(origin, target, topology)
            observed_distance = hypot(*observed_vector)
            target_distance = hypot(*target_vector)
            nominal = float(sample.warp * sample.warp)
            expected_regular_distance = min(target_distance, nominal)
            cross_track, progress = _cross_track_and_progress(target_vector, observed_vector)
            toward = (
                cross_track is not None
                and progress is not None
                and cross_track <= 1.5
                and progress >= -0.5
            )
            short = (
                observed_distance + 1.5 < expected_regular_distance
                and observed_distance > 0.0
            )
            if toward:
                totals[(hull_id, "toward_waypoint")] += 1
            if short:
                totals[(hull_id, "short_of_regular_geometry")] += 1
            if toward and short:
                totals[(hull_id, "short_toward_waypoint")] += 1

            fuel_formula_ready = False
            required_observed = None
            required_regular = None
            if (
                engine_id is not None
                and engine_id in specs.engines
                and raw_mass is not None
                and raw_mass >= 0
                and 1 <= sample.warp <= 9
            ):
                fuel_factor = specs.engines[engine_id].fuel_factor(sample.warp)
                max_distance = sample.warp * sample.warp
                required_observed = movement_fuel_use(
                    fuel_factor=fuel_factor,
                    total_mass=raw_mass,
                    distance_traveled=observed_distance,
                    max_distance_per_turn=max_distance,
                )
                required_regular = movement_fuel_use(
                    fuel_factor=fuel_factor,
                    total_mass=raw_mass,
                    distance_traveled=expected_regular_distance,
                    max_distance_per_turn=max_distance,
                )
                fuel_formula_ready = True
                totals[(hull_id, "fuel_formula_ready")] += 1

            insufficient_formula = (
                fuel_formula_ready
                and before_fuel is not None
                and required_regular is not None
                and before_fuel < required_regular
            )
            observed_formula_affordable = (
                fuel_formula_ready
                and before_fuel is not None
                and required_observed is not None
                and before_fuel >= required_observed
            )
            if insufficient_formula:
                totals[(hull_id, "before_fuel_below_regular_formula")] += 1
            if insufficient_formula and observed_formula_affordable:
                totals[(hull_id, "formula_brackets_observed")] += 1
            if insufficient_formula and observed_formula_affordable and toward and short:
                totals[(hull_id, "fuel_proration_signature")] += 1
            if before_fuel == 0 and observed_formula_affordable and toward and observed_distance > 0:
                totals[(hull_id, "zero_fuel_formula_move_signature")] += 1
            if before_fuel is not None and before_fuel > 0 and after_fuel == 0 and toward and short:
                totals[(hull_id, "depleted_to_zero_short_toward")] += 1

            detail = {
                "game": game_id,
                "turn": before_turn,
                "ship": ship_id,
                "hull": hull_id,
                "baseline": baseline,
                "warp": sample.warp,
                "fuel_before": before_fuel,
                "fuel_after": after_fuel,
                "mass_before_raw": raw_mass,
                "engine_id": engine_id,
                "target_distance": round(target_distance, 3),
                "observed_distance": round(observed_distance, 3),
                "regular_distance": round(expected_regular_distance, 3),
                "cross_track": None if cross_track is None else round(cross_track, 3),
                "progress": None if progress is None else round(progress, 3),
                "required_observed_raw_mass": required_observed,
                "required_regular_raw_mass": required_regular,
                "same_identity_after": same_identity,
            }
            if insufficient_formula and observed_formula_affordable and toward and short:
                if len(examples["fuel_proration_signature"]) < args.examples:
                    examples["fuel_proration_signature"].append(detail)
            elif before_fuel == 0 and observed_formula_affordable and toward and observed_distance > 0:
                if len(examples["zero_fuel_formula_move_signature"]) < args.examples:
                    examples["zero_fuel_formula_move_signature"].append(detail)
            elif len(examples["other"]) < args.examples:
                examples["other"].append(detail)

    print("\n===== SUMMARY BY HULL =====")
    summary_keys = (
        "rows",
        "same_identity_after",
        "identity_break_after",
        "toward_waypoint",
        "short_of_regular_geometry",
        "short_toward_waypoint",
        "fuel_formula_ready",
        "before_fuel_below_regular_formula",
        "formula_brackets_observed",
        "fuel_proration_signature",
        "zero_fuel_formula_move_signature",
        "depleted_to_zero_short_toward",
    )
    for hull_id in hull_ids:
        print(f"\nhull={hull_id}")
        for key in summary_keys:
            print(f"  {key}: {totals[(hull_id, key)]}")
        print("  baseline_categories=", Counter({
            category: count
            for (hid, category), count in baseline_counts.items()
            if hid == hull_id
        }))
        print("  fuel_before=", Counter({
            bucket: count
            for (hid, bucket), count in fuel_before_counts.items()
            if hid == hull_id
        }))
        print("  fuel_after=", Counter({
            bucket: count
            for (hid, bucket), count in fuel_after_counts.items()
            if hid == hull_id
        }))
        print("  engine_ids=", Counter({
            engine: count
            for (hid, engine), count in engine_counts.items()
            if hid == hull_id
        }))

    print("\n===== EXAMPLES: FUEL PRORATION SIGNATURE =====")
    for row in examples["fuel_proration_signature"]:
        print(row)
    print("\n===== EXAMPLES: ZERO-FUEL FORMULA MOVE SIGNATURE =====")
    for row in examples["zero_fuel_formula_move_signature"]:
        print(row)
    print("\n===== EXAMPLES: OTHER =====")
    for row in examples["other"]:
        print(row)

    print("\nNOTE: movement-fuel calculations above use the snapshot's raw mass field.")
    print("That mass is a correlation input, not proof of the exact post-host-order movement mass.")
    print("Promotion requires a clean subset and integer-coordinate projection evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
