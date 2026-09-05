from __future__ import annotations

from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any

import duckdb

from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology, sphere_adjusted_sample
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.sim.normal_movement import project_toward_waypoint
from planets_lab.validation.movement_geometry import MovementSample

from mine_report_coordinate_semantics_audit import _critical_mine_excerpt
from normal_mine_single_candidate_immunity_repair_audit import (
    BEFORE_TURN as TARGET_BEFORE_TURN,
    DATABASE,
    GAME_ID as TARGET_GAME,
    PREPARED_DIR,
    RAW_DIR,
    SHIP_ID as TARGET_SHIP,
    _load_row as _load_target_row,
)
from normal_mine_single_candidate_post_hit_motion_audit import _messages, _raw_turn_payload
from normal_mine_single_candidate_step_state_warpwell_audit import _click_for_point, _major_axis_clicks


TARGET_AFTER_TURN = TARGET_BEFORE_TURN + 1


def _load_production_rows() -> list[dict[str, Any]]:
    con = duckdb.connect(str(DATABASE), read_only=True)
    try:
        names = [
            "game_id",
            "before_archive_turn",
            "after_archive_turn",
            "before_embedded_turn",
            "ship_id",
            "hull_id",
            "warp",
            "x_before",
            "y_before",
            "x_after",
            "y_after",
            "target_x",
            "target_y",
            "nominal_max_distance",
            "mine_damage_hits",
            "mine_slowdown_hits",
        ]
        rows = con.execute(
            f"""
            SELECT {', '.join(names)}
            FROM movement_labeled_residual
            WHERE mine_strong_explained = true
              AND mine_category = 'normal_mine_hit_nearest_damage'
            ORDER BY game_id, before_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()
    return [dict(zip(names, row)) for row in rows]


def _sample_from_row(row: dict[str, Any]) -> MovementSample:
    return MovementSample(
        turn=int(row.get("before_embedded_turn") or row["before_archive_turn"]),
        ship_id=int(row["ship_id"]),
        x=int(row["x_before"]),
        y=int(row["y_before"]),
        target_x=int(row["target_x"]),
        target_y=int(row["target_y"]),
        warp=int(row["warp"]),
        next_x=int(row["x_after"]),
        next_y=int(row["y_after"]),
        game_id=int(row["game_id"]),
        hull_id=int(row["hull_id"]) if row.get("hull_id") is not None else None,
    )


def _effective_sample(sample: MovementSample, *, topology: Any) -> MovementSample:
    if topology.sphere is True and topology.mapwidth is not None and topology.mapheight is not None:
        return sphere_adjusted_sample(
            sample,
            width=int(topology.mapwidth),
            height=int(topology.mapheight),
        )
    return sample


def _analyze_row(
    row: dict[str, Any],
    *,
    archive_data: bytes,
    prepared: Any,
    topology: Any,
    is_target: bool,
) -> dict[str, Any]:
    sample = _effective_sample(_sample_from_row(row), topology=topology)
    origin = (sample.x, sample.y)
    target = (sample.target_x, sample.target_y)
    observed = sample.observed_destination

    target_vector = _vector(origin, target, topology)
    target_distance = hypot(*target_vector)
    nominal = float(row["nominal_max_distance"] or 0.0)
    regular_distance = min(target_distance, nominal)
    slowdown_hits = int(row.get("mine_slowdown_hits") or 0)
    expected_distance = max(0.0, regular_distance - 10.0 * slowdown_hits)

    regular_endpoint = project_toward_waypoint(
        x=origin[0], y=origin[1], target_x=target[0], target_y=target[1], distance=regular_distance
    )
    expected_endpoint = project_toward_waypoint(
        x=origin[0], y=origin[1], target_x=target[0], target_y=target[1], distance=expected_distance
    )
    observed_vector = _vector(origin, observed, topology)
    observed_distance = hypot(*observed_vector)

    before_turn = int(row["before_archive_turn"])
    after_turn = int(row["after_archive_turn"])
    ship_id = int(row["ship_id"])
    ship_groups = group_perspective_records(prepared.snapshots, "ship")
    owner_id, owner = _owner_record(ship_groups.get((before_turn, ship_id), ()))

    reports: list[dict[str, Any]] = []
    if owner_id is not None and owner is not None:
        payload = _raw_turn_payload(archive_data, turn=after_turn, player_id=owner_id)
        for message in _messages(payload):
            excerpt = _critical_mine_excerpt(message, ship_id=ship_id)
            if excerpt is not None:
                reports.append(excerpt)

    clicks = _major_axis_clicks(origin=origin, target=target)
    regular_click = _click_for_point(clicks, regular_endpoint)
    expected_click = _click_for_point(clicks, expected_endpoint)
    observed_click = _click_for_point(clicks, observed)
    impact_clicks = []
    impact_points = []
    for report in reports:
        x = report.get("event_x")
        y = report.get("event_y")
        if isinstance(x, int) and isinstance(y, int):
            point = (x, y)
            impact_points.append(point)
            impact_clicks.append(_click_for_point(clicks, point))

    valid_impact_clicks = [value for value in impact_clicks if value is not None]
    last_impact_click = max(valid_impact_clicks) if valid_impact_clicks else None

    return {
        "label": "TARGET" if is_target else "PRODUCTION",
        "game_id": int(row["game_id"]),
        "before_turn": before_turn,
        "ship_id": ship_id,
        "hull_id": row.get("hull_id"),
        "warp": int(row["warp"]),
        "mine_damage_hits": int(row.get("mine_damage_hits") or 0),
        "mine_slowdown_hits": slowdown_hits,
        "origin": origin,
        "target": target,
        "observed": observed,
        "target_distance": round(target_distance, 6),
        "regular_distance": round(regular_distance, 6),
        "expected_minus_10_per_hit_distance": round(expected_distance, 6),
        "observed_distance": round(observed_distance, 6),
        "distance_error_vs_minus_10": round(observed_distance - expected_distance, 6),
        "regular_endpoint": regular_endpoint,
        "expected_minus_10_endpoint": expected_endpoint,
        "minus_10_endpoint_exact": expected_endpoint == observed,
        "regular_click": regular_click,
        "expected_minus_10_click": expected_click,
        "observed_click": observed_click,
        "click_loss_observed": (
            regular_click - observed_click
            if regular_click is not None and observed_click is not None
            else None
        ),
        "click_loss_expected_minus_10": (
            regular_click - expected_click
            if regular_click is not None and expected_click is not None
            else None
        ),
        "matching_report_count": len(reports),
        "impact_points": impact_points,
        "impact_clicks": impact_clicks,
        "last_impact_click": last_impact_click,
        "clicks_after_last_impact": (
            observed_click - last_impact_click
            if observed_click is not None and last_impact_click is not None
            else None
        ),
    }


def main() -> int:
    if not DATABASE.is_file():
        raise SystemExit(f"missing database: {DATABASE}")

    production = _load_production_rows()
    print("===== NORMAL-MINE CLICK ACCOUNTING CROSS-CASE AUDIT =====")
    print("production_normal_rows=", len(production))

    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in production:
        by_game[int(row["game_id"])].append(row)

    analyzed: list[dict[str, Any]] = []
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
        print(f"prepared game={game_id} cache_hit={cache_hit} rows={len(by_game[game_id])}")
        for row in by_game[game_id]:
            analyzed.append(
                _analyze_row(
                    row,
                    archive_data=archive_data,
                    prepared=prepared,
                    topology=topology,
                    is_target=False,
                )
            )

    target_row = dict(_load_target_row())
    target_row.setdefault("game_id", TARGET_GAME)
    target_row.setdefault("before_archive_turn", TARGET_BEFORE_TURN)
    target_row.setdefault("after_archive_turn", TARGET_AFTER_TURN)
    target_row.setdefault("before_embedded_turn", TARGET_BEFORE_TURN)
    target_row.setdefault("ship_id", TARGET_SHIP)
    target_row.setdefault("mine_damage_hits", 1)
    target_row.setdefault("mine_slowdown_hits", 1)
    target_archive = (RAW_DIR / f"game-{TARGET_GAME}.zip").read_bytes()
    target_prepared, target_cache_hit = load_or_build_prepared_game_cache(
        target_archive,
        game_id=TARGET_GAME,
        cache_path=PREPARED_DIR / f"game-{TARGET_GAME}.pickle",
    )
    target_topology = effective_sphere_topology(
        game_id=TARGET_GAME,
        topology=extract_map_topology(target_archive),
    )
    target = _analyze_row(
        target_row,
        archive_data=target_archive,
        prepared=target_prepared,
        topology=target_topology,
        is_target=True,
    )

    totals = Counter()
    one_hit_errors: list[float] = []
    click_excesses: list[int] = []
    for item in analyzed:
        if item["matching_report_count"] > 0:
            totals["rows_with_report"] += 1
        if item["minus_10_endpoint_exact"]:
            totals["minus_10_endpoint_exact"] += 1
        if abs(float(item["distance_error_vs_minus_10"])) <= 1.5:
            totals["minus_10_distance_within_1_5"] += 1
        if item["observed_click"] is not None and item["expected_minus_10_click"] is not None:
            totals["click_resolved"] += 1
            excess = int(item["click_loss_observed"]) - int(item["click_loss_expected_minus_10"])
            click_excesses.append(excess)
            if excess == 0:
                totals["click_loss_exact"] += 1
        if item["mine_slowdown_hits"] == 1:
            one_hit_errors.append(float(item["distance_error_vs_minus_10"]))

    print("\n===== PRODUCTION SUMMARY =====")
    print("rows_with_report=", totals["rows_with_report"])
    print("minus_10_endpoint_exact=", totals["minus_10_endpoint_exact"])
    print("minus_10_distance_within_1_5=", totals["minus_10_distance_within_1_5"])
    print("click_resolved=", totals["click_resolved"])
    print("click_loss_exact=", totals["click_loss_exact"])
    print("one_hit_distance_error_min=", round(min(one_hit_errors), 6) if one_hit_errors else None)
    print("one_hit_distance_error_max=", round(max(one_hit_errors), 6) if one_hit_errors else None)
    print("observed_minus_expected_click_loss_values=", sorted(click_excesses))

    print("\n===== PRODUCTION ROWS =====")
    for item in analyzed:
        print(item)

    print("\n===== TARGET OUT-OF-SAMPLE =====")
    print("prepared_cache_hit=", target_cache_hit)
    print(target)
    if target["click_loss_observed"] is not None and target["click_loss_expected_minus_10"] is not None:
        print(
            "target_extra_click_loss_beyond_minus_10=",
            int(target["click_loss_observed"]) - int(target["click_loss_expected_minus_10"]),
        )

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "Production rows are already strict normal-mine labels. This diagnostic compares their exact Host-style "
        "major-axis click accounting with the documented 10-LY-per-slowdown-hit scalar rule, using regular distance "
        "to the waypoint rather than nominal warp distance. The target case is appended only as an out-of-sample "
        "survivor. No new mine semantics, labels, schemas, or corpus accounting are changed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
