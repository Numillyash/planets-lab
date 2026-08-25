from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping

import duckdb

from planets_lab.corpus.movement_damage_context import _race_map, _same_owner_identity_after
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_fuel_context import (
    extract_static_specs,
    strict_fuel_proration_endpoint,
)
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import (
    extract_map_topology,
    sphere_adjusted_sample,
)
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.fuel import movement_fuel_use
from planets_lab.validation.movement_geometry import MovementSample


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
RESIDUAL_VIEW = "movement_post_fuel_proration_residual"
HORWASP_HULL_IDS = frozenset(range(201, 214))
CLOAK_MISSION_ID = 10


def _ratio_bucket(distance: float, nominal: float) -> str:
    if nominal <= 0:
        return "nominal<=0"
    ratio = distance / nominal
    for label, target in (
        ("~0.5x", 0.5),
        ("~1.0x", 1.0),
        ("~1.5x", 1.5),
        ("~2.0x", 2.0),
        ("~3.0x", 3.0),
    ):
        if abs(ratio - target) <= 0.08:
            return label
    if ratio < 0.5:
        return "<0.5x"
    if ratio < 1.0:
        return "0.5-1.0x"
    if ratio < 1.5:
        return "1.0-1.5x"
    if ratio < 2.0:
        return "1.5-2.0x"
    if ratio < 3.0:
        return "2.0-3.0x"
    return ">3.0x"


def _target_relation(row: Mapping[str, Any]) -> str:
    origin = (int(row["x_before"]), int(row["y_before"]))
    observed = (int(row["x_after"]), int(row["y_after"]))
    target = (int(row["target_x"]), int(row["target_y"]))
    if observed == origin and target == origin:
        return "observed=origin,target=origin"
    if observed == origin:
        return "observed=origin"
    if target == origin:
        return "target=origin"
    if observed == target:
        return "observed=target"
    return "observed=other"


def _direction_bucket(row: Mapping[str, Any]) -> str:
    odx = int(row["x_after"]) - int(row["x_before"])
    ody = int(row["y_after"]) - int(row["y_before"])
    tdx = int(row["target_x"]) - int(row["x_before"])
    tdy = int(row["target_y"]) - int(row["y_before"])
    observed_norm = hypot(odx, ody)
    target_norm = hypot(tdx, tdy)
    if observed_norm <= 1e-9:
        return "observed_stationary"
    if target_norm <= 1e-9:
        return "target_is_origin"
    cosine = (odx * tdx + ody * tdy) / (observed_norm * target_norm)
    if cosine >= 0.98:
        return "same_line_forward"
    if cosine >= 0.75:
        return "mostly_forward"
    if cosine <= -0.98:
        return "same_line_reverse"
    if cosine <= -0.75:
        return "mostly_reverse"
    if -0.25 <= cosine <= 0.25:
        return "roughly_perpendicular"
    return "oblique"


def _is_target_short_forward(row: Mapping[str, Any]) -> bool:
    warp = int(row["warp"])
    return (
        7 <= warp <= 9
        and _ratio_bucket(
            float(row["observed_distance"] or 0.0),
            float(row["nominal_max_distance"] or 0.0),
        ) == "<0.5x"
        and _target_relation(row) == "observed=other"
        and _direction_bucket(row) == "same_line_forward"
    )


def _load_rows(database: Path) -> list[dict[str, Any]]:
    con = duckdb.connect(str(database), read_only=True)
    try:
        names = [
            "game_id",
            "before_archive_turn",
            "after_archive_turn",
            "ship_id",
            "hull_id",
            "warp",
            "is_gravitonic_hull",
            "x_before",
            "y_before",
            "x_after",
            "y_after",
            "target_x",
            "target_y",
            "observed_distance",
            "nominal_max_distance",
        ]
        raw_rows = con.execute(
            f"""
            SELECT {', '.join(names)}
            FROM {RESIDUAL_VIEW}
            WHERE warp BETWEEN 1 AND 9
              AND (hull_id IS NULL OR hull_id NOT BETWEEN 201 AND 213)
            ORDER BY game_id, before_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()
    return [dict(zip(names, row)) for row in raw_rows]


def _sample_from_row(row: Mapping[str, Any]) -> MovementSample:
    return MovementSample(
        turn=int(row["before_archive_turn"]),
        ship_id=int(row["ship_id"]),
        x=int(row["x_before"]),
        y=int(row["y_before"]),
        target_x=int(row["target_x"]),
        target_y=int(row["target_y"]),
        warp=int(row["warp"]),
        next_x=int(row["x_after"]),
        next_y=int(row["y_after"]),
        gravitonic=row["is_gravitonic_hull"] is True,
        game_id=int(row["game_id"]),
        hull_id=int(row["hull_id"]) if row["hull_id"] is not None else None,
    )


def _required_fuel(*, fuel_factor: int, total_mass: int, target_distance: float, warp: int) -> int:
    return movement_fuel_use(
        fuel_factor=fuel_factor,
        total_mass=total_mass,
        distance_traveled=target_distance,
        max_distance_per_turn=warp * warp,
    )


def _advanced_cloak(special: str) -> bool:
    return "advanced cloak" in special.lower()


def _cloak_cost(hull_mass: int) -> int:
    # Nu docs: 1 KT per 20 KT hull mass, rounded down, minimum 5 KT.
    return max(5, hull_mass // 20)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Test whether documented pre-movement Cloak fuel consumption converts otherwise "
            "fuel-sufficient post-v6 residual moves into exact Nu waypoint-proration endpoints."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--examples", type=int, default=40)
    args = parser.parse_args()

    if not args.database.is_file():
        raise SystemExit(f"missing compiled corpus database: {args.database}")
    if args.examples < 0:
        raise SystemExit("--examples must be non-negative")

    rows = _load_rows(args.database)
    target_rows = [row for row in rows if _is_target_short_forward(row)]

    print("===== CLOAK FUEL -> NU PRORATION DIFFERENTIAL =====")
    print("residual_view=", RESIDUAL_VIEW)
    print("generic_non_horwasp_warp1_9_rows=", len(rows))
    print("target_short_forward_rows=", len(target_rows))
    print("cloak_mission_id=", CLOAK_MISSION_ID)

    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game[int(row["game_id"])].append(row)

    totals: Counter[str] = Counter()
    target: Counter[str] = Counter()
    mission_counts: Counter[int | None] = Counter()
    target_mission_counts: Counter[int | None] = Counter()
    exact_by_game: Counter[int] = Counter()
    exact_by_hull: Counter[int] = Counter()
    exact_by_cost: Counter[int] = Counter()
    examples: list[dict[str, Any]] = []

    def bump(key: str, *, is_target: bool, amount: int = 1) -> None:
        totals[key] += amount
        if is_target:
            target[key] += amount

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        prepared_path = PREPARED_DIR / f"game-{game_id}.pickle"
        archive_data = archive_path.read_bytes()
        prepared, hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=prepared_path,
        )
        records = prepared.snapshots
        ship_groups = group_perspective_records(records, "ship")
        races = _race_map(records)
        raw_topology = extract_map_topology(archive_data)
        topology = effective_sphere_topology(game_id=game_id, topology=raw_topology)
        specs = extract_static_specs(archive_data)

        print(
            f"prepared game={game_id} cache_hit={hit} rows={len(by_game[game_id])} "
            f"raw_map=({raw_topology.mapwidth},{raw_topology.mapheight}) "
            f"effective_map=({topology.mapwidth},{topology.mapheight})"
        )

        for row in by_game[game_id]:
            is_target = _is_target_short_forward(row)
            bump("rows", is_target=is_target)

            hull_id_raw = row["hull_id"]
            if hull_id_raw is None:
                bump("hull_unusable", is_target=is_target)
                continue
            hull_id = int(hull_id_raw)
            if hull_id in HORWASP_HULL_IDS:
                bump("horwasp_excluded", is_target=is_target)
                continue
            if row["is_gravitonic_hull"] is True:
                bump("gravitonic_excluded", is_target=is_target)
                continue
            hull = specs.hulls.get(hull_id)
            if hull is None:
                bump("hull_spec_missing", is_target=is_target)
                continue

            before_turn = int(row["before_archive_turn"])
            after_turn = int(row["after_archive_turn"])
            ship_id = int(row["ship_id"])
            owner_id, owner = _owner_record(ship_groups.get((before_turn, ship_id), ()))
            if owner_id is None or owner_id <= 0 or owner is None:
                bump("owner_missing", is_target=is_target)
                continue
            before_raw = owner.raw
            if not _same_owner_identity_after(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=ship_id,
                owner_id=owner_id,
                before_raw=before_raw,
            ):
                bump("identity_break_after", is_target=is_target)
                continue
            bump("same_identity_after", is_target=is_target)

            mission = _intish(before_raw.get("mission"))
            mission_counts[mission] += 1
            if is_target:
                target_mission_counts[mission] += 1

            sample = _sample_from_row(row)
            effective_sample = sample
            if topology.sphere is True and topology.mapwidth is not None and topology.mapheight is not None:
                effective_sample = sphere_adjusted_sample(
                    sample,
                    width=int(topology.mapwidth),
                    height=int(topology.mapheight),
                )

            engine_id = _intish(before_raw.get("engineid"))
            fuel_before = _intish(before_raw.get("neutronium"))
            raw_mass = _intish(before_raw.get("mass"))
            damage = _intish(before_raw.get("damage"))
            race_id = races.get(owner_id)
            if (
                engine_id is None
                or engine_id not in specs.engines
                or fuel_before is None
                or fuel_before < 0
                or raw_mass is None
                or raw_mass < 0
                or damage is None
            ):
                bump("formula_not_ready", is_target=is_target)
                continue
            bump("formula_ready", is_target=is_target)

            target_distance = hypot(
                effective_sample.target_x - effective_sample.x,
                effective_sample.target_y - effective_sample.y,
            )
            if target_distance <= 0.0 or target_distance > effective_sample.warp ** 2 + 1e-9:
                bump("not_reachable_waypoint", is_target=is_target)
                continue
            bump("reachable_waypoint", is_target=is_target)

            fuel_factor = specs.engines[engine_id].fuel_factor(effective_sample.warp)
            raw_required = _required_fuel(
                fuel_factor=fuel_factor,
                total_mass=raw_mass,
                target_distance=target_distance,
                warp=effective_sample.warp,
            )
            if fuel_before >= raw_required:
                bump("raw_fuel_sufficient", is_target=is_target)
            else:
                bump("raw_fuel_insufficient", is_target=is_target)

            if strict_fuel_proration_endpoint(
                effective_sample,
                fuel_available=fuel_before,
                total_mass=raw_mass,
                fuel_factor=fuel_factor,
                race_id=race_id,
                damage=damage,
            ) is not None:
                bump("raw_proration_exact_control", is_target=is_target)

            if hull.can_cloak:
                bump("cloak_capable_hull", is_target=is_target)
            else:
                bump("non_cloak_hull", is_target=is_target)

            if _advanced_cloak(hull.special):
                bump("advanced_cloak_hull", is_target=is_target)
            elif hull.can_cloak:
                bump("standard_cloak_hull", is_target=is_target)

            if mission != CLOAK_MISSION_ID:
                if hull.can_cloak and not _advanced_cloak(hull.special) and damage <= 0:
                    cost = _cloak_cost(hull.mass)
                    if fuel_before > cost and raw_mass >= cost:
                        synthetic_exact = strict_fuel_proration_endpoint(
                            effective_sample,
                            fuel_available=fuel_before - cost,
                            total_mass=raw_mass - cost,
                            fuel_factor=fuel_factor,
                            race_id=race_id,
                            damage=damage,
                        ) is not None
                        if synthetic_exact:
                            bump("synthetic_cloak_cost_noncloak_mission_exact_control", is_target=is_target)
                continue

            bump("cloak_mission", is_target=is_target)
            if not hull.can_cloak:
                bump("cloak_mission_without_cloak_capability", is_target=is_target)
                continue
            if _advanced_cloak(hull.special):
                bump("cloak_mission_advanced_no_fuel_burn", is_target=is_target)
                continue
            if damage > 0:
                bump("cloak_mission_damaged_no_fuel_burn", is_target=is_target)
                continue

            cost = _cloak_cost(hull.mass)
            bump("standard_cloak_fuel_burn_candidate", is_target=is_target)
            if fuel_before <= cost:
                bump("cloak_cost_to_zero_or_invalid", is_target=is_target)
                continue
            if raw_mass < cost:
                bump("cloak_cost_invalid_mass", is_target=is_target)
                continue

            fuel_after_cloak = fuel_before - cost
            mass_after_cloak = raw_mass - cost
            bump("cloak_positive_fuel_after_burn", is_target=is_target)

            cloak_required = _required_fuel(
                fuel_factor=fuel_factor,
                total_mass=mass_after_cloak,
                target_distance=target_distance,
                warp=effective_sample.warp,
            )
            causal_conversion = fuel_before >= raw_required and fuel_after_cloak < cloak_required
            if causal_conversion:
                bump("raw_sufficient_to_cloak_insufficient", is_target=is_target)

            fuel_only_exact = strict_fuel_proration_endpoint(
                effective_sample,
                fuel_available=fuel_after_cloak,
                total_mass=raw_mass,
                fuel_factor=fuel_factor,
                race_id=race_id,
                damage=damage,
            ) is not None
            fuel_mass_exact = strict_fuel_proration_endpoint(
                effective_sample,
                fuel_available=fuel_after_cloak,
                total_mass=mass_after_cloak,
                fuel_factor=fuel_factor,
                race_id=race_id,
                damage=damage,
            ) is not None

            if fuel_only_exact:
                bump("cloak_fuel_only_endpoint_exact", is_target=is_target)
            if fuel_mass_exact:
                bump("cloak_fuel_mass_endpoint_exact", is_target=is_target)
            if fuel_mass_exact and not fuel_only_exact:
                bump("fuel_mass_exact_not_fuel_only", is_target=is_target)
            if fuel_only_exact and not fuel_mass_exact:
                bump("fuel_only_exact_not_fuel_mass", is_target=is_target)

            causal_exact = causal_conversion and fuel_mass_exact
            if causal_exact:
                bump("cloak_causal_exact", is_target=is_target)
                exact_by_game[game_id] += 1
                exact_by_hull[hull_id] += 1
                exact_by_cost[cost] += 1
                if len(examples) < args.examples:
                    examples.append(
                        {
                            "game": game_id,
                            "turn": before_turn,
                            "ship": ship_id,
                            "hull": hull_id,
                            "target_family": is_target,
                            "mission": mission,
                            "hull_mass": hull.mass,
                            "cloak_cost": cost,
                            "fuel_before": fuel_before,
                            "fuel_after_cloak": fuel_after_cloak,
                            "mass_before": raw_mass,
                            "mass_after_cloak": mass_after_cloak,
                            "raw_required": raw_required,
                            "post_cloak_required": cloak_required,
                            "fuel_only_exact": fuel_only_exact,
                            "fuel_mass_exact": fuel_mass_exact,
                            "observed": effective_sample.observed_destination,
                        }
                    )

    global_keys = (
        "rows",
        "gravitonic_excluded",
        "same_identity_after",
        "identity_break_after",
        "formula_ready",
        "reachable_waypoint",
        "raw_fuel_sufficient",
        "raw_fuel_insufficient",
        "raw_proration_exact_control",
        "cloak_capable_hull",
        "non_cloak_hull",
        "standard_cloak_hull",
        "advanced_cloak_hull",
        "cloak_mission",
        "cloak_mission_without_cloak_capability",
        "cloak_mission_advanced_no_fuel_burn",
        "cloak_mission_damaged_no_fuel_burn",
        "standard_cloak_fuel_burn_candidate",
        "cloak_cost_to_zero_or_invalid",
        "cloak_positive_fuel_after_burn",
        "raw_sufficient_to_cloak_insufficient",
        "cloak_fuel_only_endpoint_exact",
        "cloak_fuel_mass_endpoint_exact",
        "cloak_causal_exact",
        "fuel_mass_exact_not_fuel_only",
        "fuel_only_exact_not_fuel_mass",
        "synthetic_cloak_cost_noncloak_mission_exact_control",
    )

    print("\n===== GLOBAL POST-V6 CLOAK DIFFERENTIAL =====")
    for key in global_keys:
        print(f"{key}=", totals[key])

    print("\n===== TARGET 116 SHORT-FORWARD FAMILY =====")
    print("target_short_rows=", len(target_rows))
    for key in global_keys[1:]:
        print(f"target_short_{key}=", target[key])

    print("\n===== MISSION DISTRIBUTION AFTER IDENTITY GUARD =====")
    for mission, count in sorted(mission_counts.items(), key=lambda item: (item[0] is None, item[0] or -999)):
        print(mission, count)

    print("\n===== TARGET 116 MISSION DISTRIBUTION =====")
    for mission, count in sorted(target_mission_counts.items(), key=lambda item: (item[0] is None, item[0] or -999)):
        print(mission, count)

    print("\n===== EXACT CLOAK MODEL BY GAME =====")
    for key, value in exact_by_game.most_common():
        print(key, value)

    print("\n===== EXACT CLOAK MODEL BY HULL =====")
    for key, value in exact_by_hull.most_common():
        print(key, value)

    print("\n===== EXACT CLOAK MODEL BY CLOAK COST =====")
    for key, value in exact_by_cost.most_common():
        print(key, value)

    print("\n===== EXACT EXAMPLES =====")
    for example in examples:
        print(example)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "Nu documentation places Cloak before movement fuel calculation. Standard Cloak burns max(5, floor(hull_mass/20)) KT, Advanced Cloak burns zero, and a ship already damaged at the start of the turn does not consume cloak fuel. This audit promotes nothing: it asks whether submitted mission 10 plus static standard-cloak capability changes raw-sufficient rows into exact already-verified Nu waypoint-proration endpoints. Synthetic cloak-cost subtraction on cloak-capable non-Cloak rows is the specificity control."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
