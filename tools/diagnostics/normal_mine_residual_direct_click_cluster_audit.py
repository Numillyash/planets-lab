from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from math import hypot
from typing import Any

from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_mine_context import build_mine_evidence_context
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records

from mine_report_coordinate_semantics_audit import _critical_mine_excerpt
from normal_mine_direct_major_click_penalty_audit import _regular_major_click
from normal_mine_reported_excess_shortening_residual_audit import (
    DATABASE,
    PREPARED_DIR,
    RAW_DIR,
    TARGET_KEY,
    _effective_sample,
    _load_rows,
    _route_metrics,
    _same_line_metrics,
    _sample,
)
from normal_mine_single_candidate_post_hit_motion_audit import _messages, _raw_turn_payload
from normal_mine_single_candidate_step_state_warpwell_audit import _click_for_point, _major_axis_clicks


def _intish(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _state(raw: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "warp": _intish(raw.get("warp")),
        "mission": _intish(raw.get("mission")),
        "mission1target": _intish(raw.get("mission1target", raw.get("mission1_target_id"))),
        "damage": _intish(raw.get("damage")),
        "supplies": _intish(raw.get("supplies")),
    }


def main() -> int:
    if not DATABASE.is_file():
        raise SystemExit(f"missing database: {DATABASE}")

    rows = _load_rows()
    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game[int(row["game_id"])].append(row)

    print("===== NORMAL-MINE RESIDUAL DIRECT-CLICK CLUSTER AUDIT =====")
    print("source_rows=", len(rows))

    totals: Counter[str] = Counter()
    delta_counts: Counter[int] = Counter()
    strict_items: list[dict[str, Any]] = []

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
        print(f"prepared game={game_id} cache_hit={cache_hit} rows={len(by_game[game_id])}")

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

            sample = _effective_sample(_sample(row), topology)
            hull_id = sample.hull_id
            hull = mine_context.specs.hulls.get(int(hull_id)) if hull_id is not None else None
            if hull is None or hull.tech_level >= 7:
                continue

            origin = (sample.x, sample.y)
            target = (sample.target_x, sample.target_y)
            observed = sample.observed_destination
            target_vector = _vector(origin, target, topology)
            observed_vector = _vector(origin, observed, topology)
            target_distance = hypot(*target_vector)
            observed_distance = hypot(*observed_vector)
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

            totals["strict_rows"] += 1
            scalar_excess = max(0.0, regular_distance - 10.0) - observed_distance

            item: dict[str, Any] = {
                "game_id": game_id,
                "before_turn": before_turn,
                "ship_id": ship_id,
                "owner_id": owner_id,
                "hull_id": int(hull_id) if hull_id is not None else None,
                "hull_tech": hull.tech_level,
                "warp": sample.warp,
                "origin": origin,
                "target": target,
                "impact": impact,
                "observed": observed,
                "reported_damage": reports[0].get("reported_damage"),
                "regular_distance": round(regular_distance, 6),
                "impact_progress": round(float(impact_metrics["progress"]), 6),
                "observed_distance": round(observed_distance, 6),
                "scalar_excess_beyond_minus10": round(scalar_excess, 6),
                "sphere_topology": topology.sphere is True,
                "before_state": _state(before_owner.raw),
                "after_state": _state(after_owner.raw),
            }

            if topology.sphere is True:
                totals["sphere_skipped"] += 1
                item.update(
                    {
                        "click_status": "sphere_skipped",
                        "regular_click": None,
                        "impact_click": None,
                        "observed_click": None,
                        "observed_click_loss": None,
                        "direct_click_delta": None,
                        "post_impact_clicks": None,
                        "remaining_regular_clicks_after_impact": None,
                        "control_band": False,
                    }
                )
                strict_items.append(item)
                continue

            clicks = _major_axis_clicks(origin=origin, target=target)
            regular_click = _regular_major_click(
                origin=origin,
                target=target,
                regular_distance=regular_distance,
            )
            impact_click = _click_for_point(clicks, impact)
            observed_click = _click_for_point(clicks, observed)

            if regular_click is None or observed_click is None:
                totals["click_unresolved"] += 1
                item.update(
                    {
                        "click_status": "unresolved",
                        "regular_click": regular_click,
                        "impact_click": impact_click,
                        "observed_click": observed_click,
                        "observed_click_loss": None,
                        "direct_click_delta": None,
                        "post_impact_clicks": None,
                        "remaining_regular_clicks_after_impact": None,
                        "control_band": False,
                    }
                )
                strict_items.append(item)
                continue

            totals["click_resolved"] += 1
            observed_click_loss = regular_click - observed_click
            direct_delta = observed_click_loss - 10
            delta_counts[direct_delta] += 1
            control_band = abs(direct_delta) <= 1
            if control_band:
                totals["control_band"] += 1
            if direct_delta == 0:
                totals["direct_exact"] += 1
            if direct_delta > 1:
                totals["extra_loss_gt_1"] += 1
            if direct_delta < -1:
                totals["less_loss_lt_minus_1"] += 1

            item.update(
                {
                    "click_status": "resolved",
                    "regular_click": regular_click,
                    "impact_click": impact_click,
                    "observed_click": observed_click,
                    "observed_click_loss": observed_click_loss,
                    "direct_click_delta": direct_delta,
                    "post_impact_clicks": (
                        observed_click - impact_click if impact_click is not None else None
                    ),
                    "remaining_regular_clicks_after_impact": (
                        regular_click - impact_click if impact_click is not None else None
                    ),
                    "control_band": control_band,
                }
            )
            strict_items.append(item)

    print("\n===== SUMMARY =====")
    for key in (
        "strict_rows",
        "sphere_skipped",
        "click_unresolved",
        "click_resolved",
        "control_band",
        "direct_exact",
        "extra_loss_gt_1",
        "less_loss_lt_minus_1",
    ):
        print(f"{key}=", totals[key])
    print("direct_click_delta_distribution=", dict(sorted(delta_counts.items())))

    print("\n===== CONTROL-BAND ROWS (DELTA -1..+1) =====")
    for item in strict_items:
        if item.get("control_band") is True:
            print(item)

    print("\n===== TRUE CLICK OUTLIERS (ABS DELTA > 1) =====")
    for item in strict_items:
        delta = item.get("direct_click_delta")
        if isinstance(delta, int) and abs(delta) > 1:
            print(item)

    print("\n===== UNRESOLVED / SPHERE =====")
    for item in strict_items:
        if item.get("click_status") != "resolved":
            print(item)

    print("\n===== TARGET =====")
    target_item = next(
        (
            item
            for item in strict_items
            if (item["game_id"], item["before_turn"], item["ship_id"]) == TARGET_KEY
        ),
        None,
    )
    print(target_item)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "The production-control audit established an empirical planar direct-click band of -1..+1 around a "
        "10-major-axis-click loss per slowdown hit. This residual audit applies only that observed differential "
        "signature to the 36 strict single-normal-report residual rows. Rows inside the band are candidates for a "
        "classifier refinement, not automatically relabeled. Rows outside the band remain genuine movement outliers. "
        "Sphere rows are skipped rather than forced through planar geometry. No labels, schemas, or accounting change."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
