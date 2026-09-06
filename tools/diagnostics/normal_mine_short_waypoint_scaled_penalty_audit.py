from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from math import ceil, floor, hypot
from typing import Any

from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_mine_context import build_mine_evidence_context
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records

from mine_report_coordinate_semantics_audit import _critical_mine_excerpt
from normal_mine_click_accounting_cross_case_audit import (
    PREPARED_DIR,
    RAW_DIR,
    _effective_sample as _effective_production_sample,
    _load_production_rows,
    _sample_from_row,
)
from normal_mine_direct_major_click_penalty_audit import _point_for_click, _regular_major_click
from normal_mine_reported_excess_shortening_residual_audit import (
    DATABASE,
    TARGET_KEY,
    _effective_sample as _effective_residual_sample,
    _load_rows,
    _route_metrics,
    _same_line_metrics,
    _sample,
)
from normal_mine_single_candidate_post_hit_motion_audit import _messages, _raw_turn_payload
from normal_mine_single_candidate_step_state_warpwell_audit import _click_for_point, _major_axis_clicks


def _penalties(*, nominal_distance: float, regular_distance: float, slowdown_hits: int) -> dict[str, int | float]:
    fixed = 10 * slowdown_hits
    if regular_distance <= 1e-9:
        raw_scaled = float(fixed)
    else:
        raw_scaled = fixed * nominal_distance / regular_distance
    return {
        "fixed_10_clicks": fixed,
        "scaled_raw": raw_scaled,
        "scaled_floor": floor(raw_scaled + 1e-12),
        "scaled_nearest": floor(raw_scaled + 0.5),
        "scaled_ceil": ceil(raw_scaled - 1e-12),
    }


def _click_analysis(
    *,
    label: str,
    game_id: int,
    before_turn: int,
    ship_id: int,
    hull_id: int | None,
    warp: int,
    origin: tuple[int, int],
    target: tuple[int, int],
    observed: tuple[int, int],
    nominal_distance: float,
    regular_distance: float,
    slowdown_hits: int,
    sphere_topology: bool,
    impact: tuple[int, int] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "label": label,
        "game_id": game_id,
        "before_turn": before_turn,
        "ship_id": ship_id,
        "hull_id": hull_id,
        "warp": warp,
        "slowdown_hits": slowdown_hits,
        "origin": origin,
        "target": target,
        "impact": impact,
        "observed": observed,
        "nominal_distance": round(nominal_distance, 6),
        "regular_distance": round(regular_distance, 6),
        "short_waypoint": regular_distance < nominal_distance - 1e-9,
        "short_waypoint_slack": round(max(0.0, nominal_distance - regular_distance), 6),
        "scale_nominal_over_regular": (
            round(nominal_distance / regular_distance, 6) if regular_distance > 1e-9 else None
        ),
        "sphere_topology": sphere_topology,
    }

    penalties = _penalties(
        nominal_distance=nominal_distance,
        regular_distance=regular_distance,
        slowdown_hits=slowdown_hits,
    )
    item["penalties"] = {
        key: round(value, 6) if isinstance(value, float) else value
        for key, value in penalties.items()
    }

    if sphere_topology:
        item.update(
            {
                "click_status": "sphere_skipped",
                "regular_click": None,
                "impact_click": None,
                "observed_click": None,
                "observed_click_loss": None,
                "models": {},
            }
        )
        return item

    clicks = _major_axis_clicks(origin=origin, target=target)
    regular_click = _regular_major_click(
        origin=origin,
        target=target,
        regular_distance=regular_distance,
    )
    observed_click = _click_for_point(clicks, observed)
    impact_click = _click_for_point(clicks, impact) if impact is not None else None

    if regular_click is None or observed_click is None:
        item.update(
            {
                "click_status": "unresolved",
                "regular_click": regular_click,
                "impact_click": impact_click,
                "observed_click": observed_click,
                "observed_click_loss": None,
                "models": {},
            }
        )
        return item

    observed_loss = regular_click - observed_click
    models: dict[str, dict[str, Any]] = {}
    for name in ("fixed_10_clicks", "scaled_floor", "scaled_nearest", "scaled_ceil"):
        penalty = int(penalties[name])
        expected_click = max(0, regular_click - penalty)
        endpoint = _point_for_click(clicks, expected_click)
        delta = observed_loss - penalty
        models[name] = {
            "penalty_clicks": penalty,
            "expected_click": expected_click,
            "expected_endpoint": endpoint,
            "delta_observed_minus_expected_loss": delta,
            "loss_exact": delta == 0,
            "loss_within_1": abs(delta) <= 1,
            "endpoint_exact": endpoint == observed,
        }

    item.update(
        {
            "click_status": "resolved",
            "regular_click": regular_click,
            "impact_click": impact_click,
            "observed_click": observed_click,
            "observed_click_loss": observed_loss,
            "post_impact_clicks": (
                observed_click - impact_click if impact_click is not None else None
            ),
            "remaining_regular_clicks_after_impact": (
                regular_click - impact_click if impact_click is not None else None
            ),
            "models": models,
        }
    )
    return item


def _production_items() -> list[dict[str, Any]]:
    rows = _load_production_rows()
    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game[int(row["game_id"])].append(row)

    items: list[dict[str, Any]] = []
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
        print(f"production prepared game={game_id} cache_hit={cache_hit} rows={len(by_game[game_id])}")
        for row in by_game[game_id]:
            sample = _effective_production_sample(_sample_from_row(row), topology=topology)
            origin = (sample.x, sample.y)
            target = (sample.target_x, sample.target_y)
            observed = sample.observed_destination
            target_distance = hypot(*_vector(origin, target, topology))
            nominal_distance = float(row["nominal_max_distance"] or 0.0)
            regular_distance = min(target_distance, nominal_distance)
            items.append(
                _click_analysis(
                    label="PRODUCTION",
                    game_id=game_id,
                    before_turn=int(row["before_archive_turn"]),
                    ship_id=int(row["ship_id"]),
                    hull_id=int(row["hull_id"]) if row.get("hull_id") is not None else None,
                    warp=int(row["warp"]),
                    origin=origin,
                    target=target,
                    observed=observed,
                    nominal_distance=nominal_distance,
                    regular_distance=regular_distance,
                    slowdown_hits=int(row.get("mine_slowdown_hits") or 0),
                    sphere_topology=topology.sphere is True,
                )
            )
    return items


def _residual_items() -> list[dict[str, Any]]:
    rows = _load_rows()
    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game[int(row["game_id"])].append(row)

    items: list[dict[str, Any]] = []
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
        mine_context = build_mine_evidence_context(
            game_id=game_id,
            archive_data=archive_data,
            snapshots=prepared.snapshots,
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        payload_cache: dict[tuple[int, int], Mapping[str, Any]] = {}
        print(f"residual prepared game={game_id} cache_hit={cache_hit} rows={len(by_game[game_id])}")

        for row in by_game[game_id]:
            before_turn = int(row["before_archive_turn"])
            after_turn = int(row["after_archive_turn"])
            ship_id = int(row["ship_id"])
            owner_id, before_owner = _owner_record(ship_groups.get((before_turn, ship_id), ()))
            after_owner_id, after_owner = _owner_record(ship_groups.get((after_turn, ship_id), ()))
            if owner_id is None or owner_id <= 0 or before_owner is None:
                continue
            if after_owner_id != owner_id or after_owner is None:
                continue

            payload_key = (after_turn, owner_id)
            if payload_key not in payload_cache:
                payload_cache[payload_key] = _raw_turn_payload(
                    archive_data,
                    turn=after_turn,
                    player_id=owner_id,
                )
            reports = [
                excerpt
                for message in _messages(payload_cache[payload_key])
                if (excerpt := _critical_mine_excerpt(message, ship_id=ship_id)) is not None
            ]
            if len(reports) != 1 or reports[0].get("body_has_web_token") is True:
                continue

            sample = _effective_residual_sample(_sample(row), topology)
            hull_id = sample.hull_id
            hull = mine_context.specs.hulls.get(int(hull_id)) if hull_id is not None else None
            if hull is None or hull.tech_level >= 7:
                continue

            origin = (sample.x, sample.y)
            target = (sample.target_x, sample.target_y)
            observed = sample.observed_destination
            target_distance = hypot(*_vector(origin, target, topology))
            nominal_distance = float(row["nominal_max_distance"] or 0.0)
            regular_distance = min(target_distance, nominal_distance)
            observed_cross, observed_progress = _same_line_metrics(
                origin=origin,
                target=target,
                observed=observed,
                topology=topology,
            )

            event_x = reports[0].get("event_x")
            event_y = reports[0].get("event_y")
            if not isinstance(event_x, int) or not isinstance(event_y, int):
                continue
            impact = (event_x, event_y)
            impact_metrics = _route_metrics(
                origin=origin,
                target=target,
                point=impact,
                topology=topology,
            )
            if (
                impact_metrics is None
                or impact_metrics["cross_track"] > 1.5
                or regular_distance - impact_metrics["progress"] <= 10.0
                or observed_cross is None
                or observed_cross > 1.5
                or observed_progress is None
                or observed_progress <= 0.0
            ):
                continue

            items.append(
                _click_analysis(
                    label="RESIDUAL",
                    game_id=game_id,
                    before_turn=before_turn,
                    ship_id=ship_id,
                    hull_id=int(hull_id) if hull_id is not None else None,
                    warp=sample.warp,
                    origin=origin,
                    target=target,
                    impact=impact,
                    observed=observed,
                    nominal_distance=nominal_distance,
                    regular_distance=regular_distance,
                    slowdown_hits=1,
                    sphere_topology=topology.sphere is True,
                )
            )
    return items


def _summary(title: str, items: list[dict[str, Any]]) -> None:
    totals: Counter[str] = Counter()
    deltas: dict[str, Counter[int]] = {
        name: Counter()
        for name in ("fixed_10_clicks", "scaled_floor", "scaled_nearest", "scaled_ceil")
    }
    for item in items:
        totals["rows"] += 1
        if item["short_waypoint"]:
            totals["short_waypoint_rows"] += 1
        else:
            totals["full_range_rows"] += 1
        if item["click_status"] == "sphere_skipped":
            totals["sphere_skipped"] += 1
            continue
        if item["click_status"] != "resolved":
            totals["click_unresolved"] += 1
            continue
        totals["click_resolved"] += 1
        for name, model in item["models"].items():
            delta = int(model["delta_observed_minus_expected_loss"])
            deltas[name][delta] += 1
            if model["loss_exact"]:
                totals[f"{name}_loss_exact"] += 1
            if model["loss_within_1"]:
                totals[f"{name}_loss_within_1"] += 1
            if model["endpoint_exact"]:
                totals[f"{name}_endpoint_exact"] += 1

    print(f"\n===== {title} SUMMARY =====")
    for key in (
        "rows",
        "short_waypoint_rows",
        "full_range_rows",
        "sphere_skipped",
        "click_unresolved",
        "click_resolved",
    ):
        print(f"{key}=", totals[key])
    for name in ("fixed_10_clicks", "scaled_floor", "scaled_nearest", "scaled_ceil"):
        print(f"{name}_loss_exact=", totals[f"{name}_loss_exact"])
        print(f"{name}_loss_within_1=", totals[f"{name}_loss_within_1"])
        print(f"{name}_endpoint_exact=", totals[f"{name}_endpoint_exact"])
        print(f"{name}_delta_distribution=", dict(sorted(deltas[name].items())))


def main() -> int:
    if not DATABASE.is_file():
        raise SystemExit(f"missing database: {DATABASE}")

    print("===== NORMAL-MINE SHORT-WAYPOINT SCALED PENALTY AUDIT =====")
    production = _production_items()
    residual = _residual_items()
    combined = production + residual

    _summary("PRODUCTION", production)
    _summary("STRICT RESIDUAL", residual)
    _summary("COMBINED", combined)

    print("\n===== SCALED-FLOOR OUTLIERS (ABS DELTA > 1) =====")
    for item in combined:
        if item.get("click_status") != "resolved":
            continue
        delta = int(item["models"]["scaled_floor"]["delta_observed_minus_expected_loss"])
        if abs(delta) > 1:
            print(item)

    print("\n===== RESIDUAL SHORT-WAYPOINT ROWS =====")
    for item in residual:
        if item.get("short_waypoint") is True:
            print(item)

    print("\n===== TARGET =====")
    target = next(
        (
            item
            for item in residual
            if (item["game_id"], item["before_turn"], item["ship_id"]) == TARGET_KEY
        ),
        None,
    )
    print(target)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This diagnostic tests an empirical short-waypoint transformation suggested by the strict corpus: the "
        "normal-mine click penalty may scale with nominal_max_distance / regular_distance. It compares fixed 10-click, "
        "floor, nearest, and ceil variants on already production-closed controls and the separately selected strict "
        "single-normal-report residual population. A match is CORPUS_OBSERVED evidence for a classifier candidate; it "
        "does not by itself prove NuHost internal implementation or authorize relabeling. Sphere rows are skipped rather "
        "than forced through planar Host stepping. No schemas, labels, production rules, or corpus accounting change."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
