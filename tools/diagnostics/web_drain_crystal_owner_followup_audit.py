from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping

import duckdb

from planets_lab.corpus.movement_damage_context import _race_map, _same_owner_identity_after
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_fuel_context import extract_static_specs, strict_fuel_proration_endpoint
from planets_lab.corpus.movement_mine_context import _point_in_field, build_mine_evidence_context
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology, sphere_adjusted_sample
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.fuel import movement_fuel_use
from planets_lab.validation.movement_geometry import MovementSample


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
RESIDUAL_VIEW = "movement_post_fuel_proration_residual"
HORWASP_HULL_IDS = frozenset(range(201, 214))
CRYSTAL_RACE_ID = 7
WEB_DRAIN_PER_FIELD = 25


def _ratio_bucket(distance: float, nominal: float) -> str:
    if nominal <= 0:
        return "nominal<=0"
    ratio = distance / nominal
    for label, target in (("~0.5x", 0.5), ("~1.0x", 1.0), ("~1.5x", 1.5), ("~2.0x", 2.0), ("~3.0x", 3.0)):
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
    return (
        7 <= int(row["warp"]) <= 9
        and _ratio_bucket(float(row["observed_distance"] or 0.0), float(row["nominal_max_distance"] or 0.0)) == "<0.5x"
        and _target_relation(row) == "observed=other"
        and _direction_bucket(row) == "same_line_forward"
    )


def _load_rows(database: Path) -> list[dict[str, Any]]:
    names = [
        "game_id", "before_archive_turn", "after_archive_turn", "ship_id", "hull_id", "warp",
        "is_gravitonic_hull", "x_before", "y_before", "x_after", "y_after", "target_x", "target_y",
        "observed_distance", "nominal_max_distance",
    ]
    con = duckdb.connect(str(database), read_only=True)
    try:
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Refine the post-v6 web-drain lead by requiring the visible post-decay web field owner "
            "to be the Crystal race, as required by current Planets.nu documentation."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--examples", type=int, default=40)
    args = parser.parse_args()

    rows = _load_rows(args.database)
    target_rows = [row for row in rows if _is_target_short_forward(row)]
    print("===== CRYSTAL-OWNER WEB-DRAIN FOLLOW-UP =====")
    print("residual_view=", RESIDUAL_VIEW)
    print("generic_non_horwasp_warp1_9_rows=", len(rows))
    print("target_short_forward_rows=", len(target_rows))

    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game[int(row["game_id"])].append(row)

    totals: Counter[str] = Counter()
    target: Counter[str] = Counter()
    candidates: list[dict[str, Any]] = []
    exact_by_game: Counter[int] = Counter()
    exact_by_hull: Counter[int] = Counter()

    def bump(key: str, *, is_target: bool) -> None:
        totals[key] += 1
        if is_target:
            target[key] += 1

    for game_id in sorted(by_game):
        archive_data = (RAW_DIR / f"game-{game_id}.zip").read_bytes()
        prepared, hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        records = prepared.snapshots
        ship_groups = group_perspective_records(records, "ship")
        races = _race_map(records)
        raw_topology = extract_map_topology(archive_data)
        topology = effective_sphere_topology(game_id=game_id, topology=raw_topology)
        specs = extract_static_specs(archive_data)
        mine_context = build_mine_evidence_context(game_id=game_id, archive_data=archive_data, snapshots=records)
        print(f"prepared game={game_id} cache_hit={hit} rows={len(by_game[game_id])}")

        for row in by_game[game_id]:
            is_target = _is_target_short_forward(row)
            bump("rows", is_target=is_target)
            if row["is_gravitonic_hull"] is True:
                bump("gravitonic_excluded", is_target=is_target)
                continue
            hull_id = row["hull_id"]
            if hull_id is None or int(hull_id) in HORWASP_HULL_IDS:
                bump("hull_unusable", is_target=is_target)
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

            race_id = races.get(owner_id)
            if race_id == CRYSTAL_RACE_ID:
                bump("target_is_crystal_race", is_target=is_target)
                continue

            sample = _sample_from_row(row)
            if topology.sphere is True and topology.mapwidth is not None and topology.mapheight is not None:
                sample = sphere_adjusted_sample(sample, width=int(topology.mapwidth), height=int(topology.mapheight))

            engine_id = _intish(before_raw.get("engineid"))
            fuel_before = _intish(before_raw.get("neutronium"))
            raw_mass = _intish(before_raw.get("mass"))
            damage = _intish(before_raw.get("damage"))
            if engine_id is None or engine_id not in specs.engines or fuel_before is None or raw_mass is None:
                bump("formula_not_ready", is_target=is_target)
                continue
            if fuel_before < 0 or raw_mass < 0:
                bump("formula_not_ready", is_target=is_target)
                continue
            bump("formula_ready", is_target=is_target)

            target_distance = hypot(sample.target_x - sample.x, sample.target_y - sample.y)
            if target_distance <= 0.0 or target_distance > sample.warp * sample.warp + 1e-9:
                bump("not_reachable_waypoint", is_target=is_target)
                continue
            bump("reachable_waypoint", is_target=is_target)

            origin = (sample.x, sample.y)
            post_webs = [
                field for field in mine_context.fields(after_turn)
                if field.is_web
                and field.owner_id is not None
                and field.owner_id > 0
                and field.owner_id != owner_id
                and _point_in_field(origin, field, mine_context.topology)
            ]
            crystal_webs = [field for field in post_webs if races.get(field.owner_id) == CRYSTAL_RACE_ID]
            non_crystal_webs = [field for field in post_webs if races.get(field.owner_id) != CRYSTAL_RACE_ID]
            pre_crystal_webs = [
                field for field in mine_context.fields(before_turn)
                if field.is_web
                and field.owner_id is not None
                and field.owner_id > 0
                and field.owner_id != owner_id
                and races.get(field.owner_id) == CRYSTAL_RACE_ID
                and _point_in_field(origin, field, mine_context.topology)
            ]

            if post_webs:
                bump("all_enemy_web_at_origin", is_target=is_target)
            if crystal_webs:
                bump("crystal_owner_web_at_origin", is_target=is_target)
            if non_crystal_webs:
                bump("non_crystal_owner_web_at_origin", is_target=is_target)
            if not crystal_webs:
                continue

            fuel_factor = specs.engines[engine_id].fuel_factor(sample.warp)
            raw_required = _required_fuel(
                fuel_factor=fuel_factor,
                total_mass=raw_mass,
                target_distance=target_distance,
                warp=sample.warp,
            )
            if fuel_before < raw_required:
                bump("raw_fuel_insufficient", is_target=is_target)
                continue
            bump("raw_fuel_sufficient", is_target=is_target)

            drain = min(fuel_before, WEB_DRAIN_PER_FIELD * len(crystal_webs))
            fuel_after_drain = fuel_before - drain
            mass_after_drain = raw_mass - drain
            if fuel_after_drain <= 0 or mass_after_drain < 0:
                bump("crystal_web_drain_to_zero_or_invalid", is_target=is_target)
                continue
            drained_required = _required_fuel(
                fuel_factor=fuel_factor,
                total_mass=mass_after_drain,
                target_distance=target_distance,
                warp=sample.warp,
            )
            if fuel_after_drain >= drained_required:
                bump("crystal_web_drain_still_sufficient", is_target=is_target)
                continue

            bump("crystal_web_raw_sufficient_to_insufficient", is_target=is_target)
            crystal_exact = strict_fuel_proration_endpoint(
                sample,
                fuel_available=fuel_after_drain,
                total_mass=mass_after_drain,
                fuel_factor=fuel_factor,
                race_id=race_id,
                damage=damage,
            ) is not None
            if crystal_exact:
                bump("crystal_web_drain_causal_exact", is_target=is_target)
                exact_by_game[game_id] += 1
                exact_by_hull[int(hull_id)] += 1

            all_drain = min(fuel_before, WEB_DRAIN_PER_FIELD * len(post_webs))
            all_fuel = fuel_before - all_drain
            all_mass = raw_mass - all_drain
            all_exact = (
                all_fuel > 0
                and all_mass >= 0
                and strict_fuel_proration_endpoint(
                    sample,
                    fuel_available=all_fuel,
                    total_mass=all_mass,
                    fuel_factor=fuel_factor,
                    race_id=race_id,
                    damage=damage,
                ) is not None
            )
            if all_exact:
                bump("all_enemy_web_model_exact", is_target=is_target)

            if len(candidates) < args.examples:
                candidates.append({
                    "game": game_id,
                    "turn": before_turn,
                    "ship": ship_id,
                    "hull": int(hull_id),
                    "target_family": is_target,
                    "target_race": race_id,
                    "all_enemy_web_count": len(post_webs),
                    "crystal_owner_web_count": len(crystal_webs),
                    "non_crystal_owner_web_count": len(non_crystal_webs),
                    "pre_turn_crystal_web_count": len(pre_crystal_webs),
                    "fuel_before": fuel_before,
                    "fuel_after_crystal_drain": fuel_after_drain,
                    "mass_before": raw_mass,
                    "mass_after_crystal_drain": mass_after_drain,
                    "raw_required": raw_required,
                    "drained_required": drained_required,
                    "crystal_owner_exact": crystal_exact,
                    "all_enemy_web_exact": all_exact,
                    "observed": sample.observed_destination,
                })

    keys = (
        "rows",
        "gravitonic_excluded",
        "same_identity_after",
        "identity_break_after",
        "target_is_crystal_race",
        "formula_ready",
        "reachable_waypoint",
        "all_enemy_web_at_origin",
        "crystal_owner_web_at_origin",
        "non_crystal_owner_web_at_origin",
        "raw_fuel_sufficient",
        "raw_fuel_insufficient",
        "crystal_web_drain_to_zero_or_invalid",
        "crystal_web_drain_still_sufficient",
        "crystal_web_raw_sufficient_to_insufficient",
        "crystal_web_drain_causal_exact",
        "all_enemy_web_model_exact",
    )

    print("\n===== GLOBAL CRYSTAL-OWNER DIFFERENTIAL =====")
    for key in keys:
        print(f"{key}=", totals[key])

    print("\n===== TARGET 116 CRYSTAL-OWNER DIFFERENTIAL =====")
    for key in keys:
        print(f"target_short_{key}=", target[key])

    print("\n===== STRICT EXACT BY GAME =====")
    for game_id, count in exact_by_game.most_common():
        print(game_id, count)

    print("\n===== STRICT EXACT BY HULL =====")
    for hull_id, count in exact_by_hull.most_common():
        print(hull_id, count)

    print("\n===== RAW-SUFFICIENT -> CRYSTAL-WEB-INSUFFICIENT CANDIDATES =====")
    for candidate in candidates:
        print(candidate)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "Current Planets.nu documentation states that only web minefields owned by a Crystal player "
        "produce the 25 KT web-drain effect, and drain uses the post-decay circle. This audit therefore "
        "treats non-Crystal-owned web fields as a control. Full-Alliance/safe-passage immunity is not yet "
        "reconstructed here, so even a Crystal-owner exact match remains corpus evidence rather than a "
        "production predicate until diplomacy compatibility is checked."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
