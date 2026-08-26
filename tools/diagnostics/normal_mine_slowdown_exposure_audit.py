from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from math import ceil, hypot
from pathlib import Path
from typing import Any, Mapping

import duckdb

from planets_lab.corpus.movement_damage_context import _same_owner_identity_after
from planets_lab.corpus.movement_mine_context import _point_in_field, build_mine_evidence_context
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology, sphere_adjusted_sample
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.validation.movement_geometry import MovementSample


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
RESIDUAL_VIEW = "movement_post_fuel_proration_residual"
HORWASP_HULL_IDS = frozenset(range(201, 214))


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
        )
        == "<0.5x"
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


def _planned_endpoint(sample: MovementSample, nominal_distance: float) -> tuple[float, float, float]:
    dx = float(sample.target_x - sample.x)
    dy = float(sample.target_y - sample.y)
    target_distance = hypot(dx, dy)
    if target_distance <= 1e-9:
        return float(sample.x), float(sample.y), 0.0
    planned_distance = min(target_distance, max(0.0, nominal_distance))
    scale = planned_distance / target_distance
    return sample.x + dx * scale, sample.y + dy * scale, planned_distance


def _route_exposed_fields(
    *,
    start: tuple[float, float],
    end: tuple[float, float],
    fields: list[Any],
    topology: Any,
) -> set[int]:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    distance = hypot(dx, dy)
    steps = max(1, int(ceil(distance)))
    exposed: set[int] = set()
    for step in range(steps + 1):
        t = step / steps
        point = (start[0] + dx * t, start[1] + dy * t)
        for index, field in enumerate(fields):
            if index in exposed:
                continue
            if _point_in_field(point, field, topology):
                exposed.add(index)
    return exposed


def _near_ten_multiple(deficit: float, *, tolerance: float = 1.5) -> tuple[bool, int | None]:
    if deficit <= 0:
        return False, None
    hits = max(1, int(round(deficit / 10.0)))
    return abs(deficit - hits * 10.0) <= tolerance, hits


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Measure whether current post-v6 residual routes are exposed to owner-different "
            "normal minefields and whether their movement deficits have the documented "
            "10-light-year-per-hit slowdown geometry. This is an exposure audit, not a "
            "mine-hit RNG or repair reconstruction."
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

    print("===== NORMAL-MINE SLOWDOWN EXPOSURE AUDIT =====")
    print("residual_view=", RESIDUAL_VIEW)
    print("generic_non_horwasp_warp1_9_rows=", len(rows))
    print("target_short_forward_rows=", len(target_rows))
    print("documented_slowdown_per_hit_ly= 10")
    print("documented_not_slowed_hull_tech_threshold= 7")

    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game[int(row["game_id"])].append(row)

    totals: Counter[str] = Counter()
    target: Counter[str] = Counter()
    target_exposure_by_game: Counter[int] = Counter()
    target_exposure_by_hull: Counter[int] = Counter()
    target_ten_by_game: Counter[int] = Counter()
    target_ten_by_hull: Counter[int] = Counter()
    examples: list[dict[str, Any]] = []

    def bump(key: str, *, is_target: bool) -> None:
        totals[key] += 1
        if is_target:
            target[key] += 1

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
        raw_topology = extract_map_topology(archive_data)
        topology = effective_sphere_topology(game_id=game_id, topology=raw_topology)
        mine_context = build_mine_evidence_context(
            game_id=game_id,
            archive_data=archive_data,
            snapshots=records,
        )

        print(
            f"prepared game={game_id} cache_hit={hit} rows={len(by_game[game_id])} "
            f"raw_map=({raw_topology.mapwidth},{raw_topology.mapheight}) "
            f"effective_map=({topology.mapwidth},{topology.mapheight})"
        )

        for row in by_game[game_id]:
            is_target = _is_target_short_forward(row)
            bump("rows", is_target=is_target)

            before_turn = int(row["before_archive_turn"])
            after_turn = int(row["after_archive_turn"])
            ship_id = int(row["ship_id"])
            hull_id = int(row["hull_id"]) if row["hull_id"] is not None else None

            owner_id, owner = _owner_record(ship_groups.get((before_turn, ship_id), ()))
            if owner_id is None or owner_id <= 0 or owner is None:
                bump("owner_missing", is_target=is_target)
                continue
            if not _same_owner_identity_after(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=ship_id,
                owner_id=owner_id,
                before_raw=owner.raw,
            ):
                bump("identity_break_after", is_target=is_target)
                continue
            bump("same_identity_after", is_target=is_target)

            sample = _sample_from_row(row)
            effective_sample = sample
            if (
                topology.sphere is True
                and topology.mapwidth is not None
                and topology.mapheight is not None
            ):
                effective_sample = sphere_adjusted_sample(
                    sample,
                    width=int(topology.mapwidth),
                    height=int(topology.mapheight),
                )

            fields = [
                field
                for field in mine_context.fields(after_turn)
                if not field.is_web
                and field.owner_id is not None
                and field.owner_id > 0
                and field.owner_id != owner_id
            ]
            if not fields:
                bump("no_owner_different_normal_fields", is_target=is_target)
                continue
            bump("owner_different_normal_fields_present", is_target=is_target)

            start = (float(effective_sample.x), float(effective_sample.y))
            end_x, end_y, planned_distance = _planned_endpoint(
                effective_sample,
                float(row["nominal_max_distance"] or 0.0),
            )
            if planned_distance <= 0:
                bump("planned_distance_zero", is_target=is_target)
                continue

            origin_exposure = any(_point_in_field(start, field, topology) for field in fields)
            if origin_exposure:
                bump("normal_mine_origin_exposure", is_target=is_target)

            exposed = _route_exposed_fields(
                start=start,
                end=(end_x, end_y),
                fields=fields,
                topology=topology,
            )
            if not exposed:
                bump("no_normal_mine_route_exposure", is_target=is_target)
                continue

            bump("normal_mine_route_exposure", is_target=is_target)
            if len(exposed) > 1:
                bump("normal_mine_multi_field_route_exposure", is_target=is_target)

            if is_target:
                target_exposure_by_game[game_id] += 1
                if hull_id is not None:
                    target_exposure_by_hull[hull_id] += 1

            observed_distance = hypot(
                effective_sample.next_x - effective_sample.x,
                effective_sample.next_y - effective_sample.y,
            )
            deficit = planned_distance - observed_distance
            if deficit > 0:
                bump("positive_planned_distance_deficit", is_target=is_target)
            near_ten, implied_hits = _near_ten_multiple(deficit)
            if near_ten:
                bump("deficit_near_10n", is_target=is_target)
                if is_target:
                    target_ten_by_game[game_id] += 1
                    if hull_id is not None:
                        target_ten_by_hull[hull_id] += 1

            if is_target and len(examples) < args.examples:
                examples.append(
                    {
                        "game": game_id,
                        "turn": before_turn,
                        "ship": ship_id,
                        "hull": hull_id,
                        "baseline": row.get("baseline_category"),
                        "gravitonic": row["is_gravitonic_hull"] is True,
                        "field_count": len(fields),
                        "exposed_field_count": len(exposed),
                        "origin_exposure": origin_exposure,
                        "planned_distance": round(planned_distance, 3),
                        "observed_distance": round(observed_distance, 3),
                        "deficit": round(deficit, 3),
                        "deficit_near_10n": near_ten,
                        "implied_slowdown_hits": implied_hits if near_ten else None,
                    }
                )

    print("\n===== GLOBAL POST-V6 NORMAL-MINE EXPOSURE =====")
    for key in (
        "rows",
        "same_identity_after",
        "identity_break_after",
        "owner_different_normal_fields_present",
        "no_owner_different_normal_fields",
        "normal_mine_origin_exposure",
        "normal_mine_route_exposure",
        "normal_mine_multi_field_route_exposure",
        "no_normal_mine_route_exposure",
        "positive_planned_distance_deficit",
        "deficit_near_10n",
    ):
        print(f"{key}=", totals.get(key, 0))

    print("\n===== TARGET 116 NORMAL-MINE EXPOSURE =====")
    print("target_short_rows=", len(target_rows))
    for key in (
        "same_identity_after",
        "identity_break_after",
        "owner_different_normal_fields_present",
        "no_owner_different_normal_fields",
        "normal_mine_origin_exposure",
        "normal_mine_route_exposure",
        "normal_mine_multi_field_route_exposure",
        "no_normal_mine_route_exposure",
        "positive_planned_distance_deficit",
        "deficit_near_10n",
    ):
        print(f"target_short_{key}=", target.get(key, 0))

    print("\n===== TARGET ROUTE EXPOSURE BY GAME =====")
    for game_id, count in target_exposure_by_game.most_common():
        print(game_id, count)

    print("\n===== TARGET ROUTE EXPOSURE BY HULL =====")
    for hull_id, count in target_exposure_by_hull.most_common():
        print(hull_id, count)

    print("\n===== TARGET 10N DEFICIT + ROUTE EXPOSURE BY GAME =====")
    for game_id, count in target_ten_by_game.most_common():
        print(game_id, count)

    print("\n===== TARGET 10N DEFICIT + ROUTE EXPOSURE BY HULL =====")
    for hull_id, count in target_ten_by_hull.most_common():
        print(hull_id, count)

    print("\n===== TARGET EXPOSURE EXAMPLES =====")
    for example in examples:
        print(example)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This pass is intentionally an upper-bound exposure/geometry audit. Owner-different "
        "normal minefields are not yet filtered by historical diplomacy, hull tech level is "
        "not yet reconstructed, and mine-hit RNG/repair is not inferred. A material target "
        "population with route exposure plus deficits near 10*N ly justifies a second pass; "
        "sparse/zero exposure or sparse 10*N geometry rejects repair-hidden normal-mine "
        "slowdown as a broad explanation for the dominant family."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
