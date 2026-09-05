from __future__ import annotations

import re
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping

import duckdb

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_fuel_context import extract_static_specs
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology, sphere_adjusted_sample
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.sim.normal_movement import project_toward_waypoint
from planets_lab.validation.movement_geometry import MovementSample

from mine_report_coordinate_semantics_audit import _critical_mine_excerpt
from normal_mine_single_candidate_post_hit_motion_audit import _messages, _raw_turn_payload
from normal_mine_single_candidate_step_state_warpwell_audit import _click_for_point, _major_axis_clicks


DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
RESIDUAL_VIEW = "movement_post_fuel_proration_residual"
TARGET_KEY = (511506, 23, 160)

PASSAGE_RE = re.compile(
    r"passed\s+through\s+(?P<ly>\d+)\s+light\s+years?\s+of\s+mines",
    re.IGNORECASE,
)


def _load_rows() -> list[dict[str, Any]]:
    con = duckdb.connect(str(DATABASE), read_only=True)
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
        rows = con.execute(
            f"SELECT {', '.join(names)} FROM {RESIDUAL_VIEW} "
            "ORDER BY game_id, before_archive_turn, ship_id"
        ).fetchall()
    finally:
        con.close()
    return [dict(zip(names, row)) for row in rows]


def _sample(row: Mapping[str, Any]) -> MovementSample:
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
        gravitonic=row.get("is_gravitonic_hull") is True,
        game_id=int(row["game_id"]),
        hull_id=int(row["hull_id"]) if row.get("hull_id") is not None else None,
    )


def _effective_sample(sample: MovementSample, topology: Any) -> MovementSample:
    if topology.sphere is True and topology.mapwidth is not None and topology.mapheight is not None:
        return sphere_adjusted_sample(
            sample,
            width=int(topology.mapwidth),
            height=int(topology.mapheight),
        )
    return sample


def _route_metrics(
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
    point: tuple[int, int],
    topology: Any,
) -> dict[str, float] | None:
    tx, ty = _vector(origin, target, topology)
    px, py = _vector(origin, point, topology)
    route_length = hypot(tx, ty)
    if route_length <= 1e-9:
        return None
    ux, uy = tx / route_length, ty / route_length
    return {
        "progress": px * ux + py * uy,
        "cross_track": abs(px * uy - py * ux),
    }


def _same_line_metrics(
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
    observed: tuple[int, int],
    topology: Any,
) -> tuple[float | None, float | None]:
    tx, ty = _vector(origin, target, topology)
    ox, oy = _vector(origin, observed, topology)
    route_length = hypot(tx, ty)
    if route_length <= 1e-9:
        return None, None
    return (
        abs(tx * oy - ty * ox) / route_length,
        (tx * ox + ty * oy) / route_length,
    )


def _passage_values(messages: list[Mapping[str, Any]], *, ship_id: int) -> list[int]:
    values: list[int] = []
    for message in messages:
        if _intish(message.get("messagetype")) != 8 or _intish(message.get("target")) != ship_id:
            continue
        body = message.get("body") if isinstance(message.get("body"), str) else ""
        match = PASSAGE_RE.search(body)
        if match:
            values.append(int(match.group("ly")))
    return values


def _state(raw: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "damage": _intish(raw.get("damage")),
        "supplies": _intish(raw.get("supplies")),
        "neutronium": _intish(raw.get("neutronium")),
        "warp": _intish(raw.get("warp")),
        "mission": _intish(raw.get("mission")),
        "mission1target": _intish(raw.get("mission1target", raw.get("mission1_target_id"))),
    }


def main() -> int:
    if not DATABASE.is_file():
        raise SystemExit(f"missing database: {DATABASE}")

    rows = _load_rows()
    print("===== NORMAL-MINE REPORTED EXCESS-SHORTENING RESIDUAL AUDIT =====")
    print("residual_view=", RESIDUAL_VIEW)
    print("residual_rows=", len(rows))

    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game[int(row["game_id"])].append(row)

    totals = Counter()
    strict_rows: list[dict[str, Any]] = []
    excess_rows: list[dict[str, Any]] = []

    for game_id in sorted(by_game):
        archive_data = (RAW_DIR / f"game-{game_id}.zip").read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        topology = effective_sphere_topology(
            game_id=game_id,
            topology=extract_map_topology(archive_data),
        )
        specs = extract_static_specs(archive_data)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        payload_cache: dict[tuple[int, int], Mapping[str, Any]] = {}
        print(f"prepared game={game_id} cache_hit={cache_hit} rows={len(by_game[game_id])}")

        for row in by_game[game_id]:
            before_turn = int(row["before_archive_turn"])
            after_turn = int(row["after_archive_turn"])
            ship_id = int(row["ship_id"])
            hull_id = int(row["hull_id"]) if row.get("hull_id") is not None else None

            owner_id, before_owner = _owner_record(ship_groups.get((before_turn, ship_id), ()))
            after_owner_id, after_owner = _owner_record(ship_groups.get((after_turn, ship_id), ()))
            if owner_id is None or owner_id <= 0 or before_owner is None:
                totals["before_owner_unavailable"] += 1
                continue
            if after_owner_id != owner_id or after_owner is None:
                totals["after_owner_unavailable"] += 1
                continue
            totals["owner_pair_ready"] += 1

            payload_key = (after_turn, owner_id)
            if payload_key not in payload_cache:
                payload_cache[payload_key] = _raw_turn_payload(
                    archive_data,
                    turn=after_turn,
                    player_id=owner_id,
                )
            messages = _messages(payload_cache[payload_key])
            reports = [
                excerpt
                for message in messages
                if (excerpt := _critical_mine_excerpt(message, ship_id=ship_id)) is not None
            ]
            if not reports:
                continue

            totals["rows_with_mine_hit_report"] += 1
            totals["mine_hit_report_count"] += len(reports)
            if len(reports) == 1:
                totals["rows_with_single_mine_hit_report"] += 1
            else:
                totals["rows_with_multiple_mine_hit_reports"] += 1

            passage_values = _passage_values(messages, ship_id=ship_id)
            if passage_values:
                totals["rows_with_passage_report"] += 1

            sample = _effective_sample(_sample(row), topology)
            origin = (sample.x, sample.y)
            target = (sample.target_x, sample.target_y)
            observed = sample.observed_destination
            target_vector = _vector(origin, target, topology)
            observed_vector = _vector(origin, observed, topology)
            target_distance = hypot(*target_vector)
            observed_distance = hypot(*observed_vector)
            regular_distance = min(target_distance, float(row["nominal_max_distance"] or 0.0))
            observed_cross, observed_progress = _same_line_metrics(
                origin=origin,
                target=target,
                observed=observed,
                topology=topology,
            )

            hull = specs.hulls.get(hull_id) if hull_id is not None else None
            hull_tech = hull.tech_level if hull is not None else None
            normalish = len(reports) == 1 and reports[0].get("body_has_web_token") is not True
            impact = None
            impact_metrics = None
            event_x = reports[0].get("event_x") if len(reports) == 1 else None
            event_y = reports[0].get("event_y") if len(reports) == 1 else None
            if isinstance(event_x, int) and isinstance(event_y, int):
                impact = (event_x, event_y)
                impact_metrics = _route_metrics(
                    origin=origin,
                    target=target,
                    point=impact,
                    topology=topology,
                )

            strict = (
                normalish
                and hull_tech is not None
                and hull_tech < 7
                and impact_metrics is not None
                and impact_metrics["cross_track"] <= 1.5
                and regular_distance - impact_metrics["progress"] > 10.0
                and observed_cross is not None
                and observed_cross <= 1.5
                and observed_progress is not None
                and observed_progress > 0.0
            )
            if not strict:
                continue

            totals["strict_single_normal_report_rows"] += 1
            expected_distance = max(0.0, regular_distance - 10.0)
            excess_shortening = expected_distance - observed_distance
            expected_endpoint = project_toward_waypoint(
                x=origin[0],
                y=origin[1],
                target_x=target[0],
                target_y=target[1],
                distance=expected_distance,
            )

            regular_click = expected_click = observed_click = extra_click_loss = None
            if topology.sphere is not True:
                clicks = _major_axis_clicks(origin=origin, target=target)
                regular_endpoint = project_toward_waypoint(
                    x=origin[0],
                    y=origin[1],
                    target_x=target[0],
                    target_y=target[1],
                    distance=regular_distance,
                )
                regular_click = _click_for_point(clicks, regular_endpoint)
                expected_click = _click_for_point(clicks, expected_endpoint)
                observed_click = _click_for_point(clicks, observed)
                if regular_click is not None and expected_click is not None and observed_click is not None:
                    extra_click_loss = (regular_click - observed_click) - (regular_click - expected_click)

            item = {
                "game_id": game_id,
                "before_turn": before_turn,
                "ship_id": ship_id,
                "owner_id": owner_id,
                "hull_id": hull_id,
                "hull_tech": hull_tech,
                "warp": sample.warp,
                "origin": origin,
                "target": target,
                "observed": observed,
                "impact": impact,
                "impact_progress": round(float(impact_metrics["progress"]), 6),
                "remaining_at_impact": round(regular_distance - float(impact_metrics["progress"]), 6),
                "reported_damage": reports[0].get("reported_damage"),
                "passage_report_ly_values": passage_values,
                "regular_distance": round(regular_distance, 6),
                "observed_distance": round(observed_distance, 6),
                "expected_one_hit_distance": round(expected_distance, 6),
                "excess_shortening_beyond_one_hit": round(excess_shortening, 6),
                "expected_one_hit_endpoint": expected_endpoint,
                "expected_one_hit_endpoint_exact": expected_endpoint == observed,
                "regular_click": regular_click,
                "expected_one_hit_click": expected_click,
                "observed_click": observed_click,
                "extra_click_loss_beyond_one_hit": extra_click_loss,
                "before_state": _state(before_owner.raw),
                "after_state": _state(after_owner.raw),
            }
            strict_rows.append(item)

            if abs(excess_shortening) <= 1.5:
                totals["strict_within_one_hit_tolerance"] += 1
            elif excess_shortening > 1.5:
                totals["strict_excess_shortening_rows"] += 1
                excess_rows.append(item)

            if (game_id, before_turn, ship_id) == TARGET_KEY:
                totals["target_found_in_strict_population"] += 1
                if excess_shortening > 1.5:
                    totals["target_found_in_excess_population"] += 1

    print("\n===== SUMMARY =====")
    for key in (
        "owner_pair_ready",
        "before_owner_unavailable",
        "after_owner_unavailable",
        "rows_with_mine_hit_report",
        "mine_hit_report_count",
        "rows_with_single_mine_hit_report",
        "rows_with_multiple_mine_hit_reports",
        "rows_with_passage_report",
        "strict_single_normal_report_rows",
        "strict_within_one_hit_tolerance",
        "strict_excess_shortening_rows",
        "target_found_in_strict_population",
        "target_found_in_excess_population",
    ):
        print(f"{key}=", totals[key])

    print("\n===== STRICT SINGLE-NORMAL-REPORT ROWS =====")
    for item in strict_rows:
        print(item)

    print("\n===== EXCESS-SHORTENING FAMILY =====")
    for item in excess_rows:
        print(item)

    print("\n===== EXCESS FAMILY KEYS =====")
    print([(item["game_id"], item["before_turn"], item["ship_id"]) for item in excess_rows])

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This diagnostic searches only the post-fuel-proration residual population for owner-visible critical "
        "mine-hit reports. The strict subset requires exactly one non-web report, hull tech below 7, an on-route "
        "impact with more than 10 LY of regular movement remaining, and a same-line observed endpoint. It then asks "
        "whether more than 1.5 LY remains unexplained beyond the documented one-hit 10-LY slowdown. Message type 8 "
        "passage values are observational only. No labels, schemas, mission meanings, or corpus accounting change."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
