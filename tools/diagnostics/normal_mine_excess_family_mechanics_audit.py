from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from math import hypot
from typing import Any

from planets_lab.corpus.movement_damage_context import max_warp_from_damage
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_mine_context import build_mine_evidence_context, nearest_damage_quantum
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.sim.normal_movement import project_toward_waypoint

from mine_report_coordinate_semantics_audit import _critical_mine_excerpt
from normal_mine_reported_excess_shortening_residual_audit import (
    DATABASE,
    PREPARED_DIR,
    RAW_DIR,
    TARGET_KEY,
    _effective_sample,
    _load_rows,
    _passage_values,
    _route_metrics,
    _same_line_metrics,
    _sample,
)
from normal_mine_single_candidate_immunity_repair_audit import _route_interval
from normal_mine_single_candidate_post_hit_motion_audit import _messages, _raw_turn_payload
from normal_mine_single_candidate_step_state_warpwell_audit import _click_for_point, _major_axis_clicks


SETTING_TOKENS = (
    "hulltech",
    "minehit",
    "mine_hit",
    "slowed",
    "slowdown",
    "slow_down",
)


def _intish(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _race_id(payload: Mapping[str, Any], owner_id: int) -> int | None:
    players = payload.get("players", [])
    if not isinstance(players, list):
        return None
    values: set[int] = set()
    for raw in players:
        if not isinstance(raw, Mapping):
            continue
        if _intish(raw.get("id")) != owner_id:
            continue
        race_id = _intish(raw.get("raceid"))
        if race_id is not None and race_id > 0:
            values.add(race_id)
    return next(iter(values)) if len(values) == 1 else None


def _safe_mine_setting_excerpt(payload: Mapping[str, Any]) -> dict[str, Any]:
    settings = payload.get("settings")
    if not isinstance(settings, Mapping):
        return {}
    result: dict[str, Any] = {}
    for key, value in settings.items():
        normalized = str(key).lower().replace("-", "_")
        compact = normalized.replace("_", "")
        if not any(token.replace("_", "") in compact for token in SETTING_TOKENS):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            result[str(key)] = value
    return dict(sorted(result.items()))


def _union_length(intervals: list[tuple[float, float]]) -> float:
    if not intervals:
        return 0.0
    ordered = sorted((min(a, b), max(a, b)) for a, b in intervals)
    total = 0.0
    start, end = ordered[0]
    for next_start, next_end in ordered[1:]:
        if next_start <= end:
            end = max(end, next_end)
            continue
        total += end - start
        start, end = next_start, next_end
    total += end - start
    return total


def _candidate(
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
    distance: float,
    observed: tuple[int, int],
    observed_distance: float,
) -> dict[str, Any]:
    clamped = max(0.0, distance)
    endpoint = project_toward_waypoint(
        x=origin[0],
        y=origin[1],
        target_x=target[0],
        target_y=target[1],
        distance=clamped,
    )
    return {
        "distance": round(clamped, 6),
        "distance_error": round(observed_distance - clamped, 6),
        "within_1_5": abs(observed_distance - clamped) <= 1.5,
        "endpoint": endpoint,
        "endpoint_exact": endpoint == observed,
    }


def main() -> int:
    if not DATABASE.is_file():
        raise SystemExit(f"missing database: {DATABASE}")

    rows = _load_rows()
    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_game[int(row["game_id"])].append(row)

    print("===== NORMAL-MINE EXCESS FAMILY MECHANICS AUDIT =====")
    print("source_rows=", len(rows))

    model_counts: Counter[str] = Counter()
    passage_counts: Counter[str] = Counter()
    setting_signatures: dict[int, set[tuple[tuple[str, Any], ...]]] = defaultdict(set)
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
            after_payload = payload_cache[payload_key]
            reports = [
                excerpt
                for message in _messages(after_payload)
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

            before_payload_key = (before_turn, owner_id)
            if before_payload_key not in payload_cache:
                payload_cache[before_payload_key] = _raw_turn_payload(
                    archive_data,
                    turn=before_turn,
                    player_id=owner_id,
                )
            before_payload = payload_cache[before_payload_key]
            settings = _safe_mine_setting_excerpt(before_payload)
            setting_signatures[game_id].add(tuple(settings.items()))
            race_id = _race_id(before_payload, owner_id)

            before_damage = _intish(before_owner.raw.get("damage"))
            hit_quantum = nearest_damage_quantum(hull.mass, web=False)
            report_damage = _intish(reports[0].get("reported_damage"))
            raw_after_hit_damage = (
                before_damage + hit_quantum
                if before_damage is not None and hit_quantum is not None
                else None
            )
            damage_max_warp = max_warp_from_damage(raw_after_hit_damage, race_id)
            damage_max_distance = (
                float(damage_max_warp * damage_max_warp)
                if damage_max_warp is not None
                else None
            )

            impact_progress = float(impact_metrics["progress"])
            candidates: dict[str, dict[str, Any]] = {}
            candidates["documented_minus10"] = _candidate(
                origin=origin,
                target=target,
                distance=max(0.0, regular_distance - 10.0),
                observed=observed,
                observed_distance=observed_distance,
            )

            if damage_max_distance is not None and nominal_distance > 0.0:
                remaining_time_nominal = max(0.0, 1.0 - impact_progress / nominal_distance)
                damage_time_nominal = min(
                    regular_distance,
                    impact_progress + damage_max_distance * remaining_time_nominal,
                )
                candidates["damage_time_nominal"] = _candidate(
                    origin=origin,
                    target=target,
                    distance=damage_time_nominal,
                    observed=observed,
                    observed_distance=observed_distance,
                )
                candidates["minus10_or_damage_time_min"] = _candidate(
                    origin=origin,
                    target=target,
                    distance=min(max(0.0, regular_distance - 10.0), damage_time_nominal),
                    observed=observed,
                    observed_distance=observed_distance,
                )

            if damage_max_distance is not None and regular_distance > 0.0:
                remaining_time_regular = max(0.0, 1.0 - impact_progress / regular_distance)
                damage_time_regular = min(
                    regular_distance,
                    impact_progress + damage_max_distance * remaining_time_regular,
                )
                candidates["damage_time_regular"] = _candidate(
                    origin=origin,
                    target=target,
                    distance=damage_time_regular,
                    observed=observed,
                    observed_distance=observed_distance,
                )
                candidates["damage_fresh_leg"] = _candidate(
                    origin=origin,
                    target=target,
                    distance=min(regular_distance, impact_progress + damage_max_distance),
                    observed=observed,
                    observed_distance=observed_distance,
                )

            click_candidate = None
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
                if regular_click is not None:
                    click_index = max(0, regular_click - 10)
                    click_endpoint = clicks[click_index][1]
                    click_distance = hypot(
                        click_endpoint[0] - origin[0],
                        click_endpoint[1] - origin[1],
                    )
                    click_candidate = {
                        "click": click_index,
                        "distance": round(click_distance, 6),
                        "distance_error": round(observed_distance - click_distance, 6),
                        "within_1_5": abs(observed_distance - click_distance) <= 1.5,
                        "endpoint": click_endpoint,
                        "endpoint_exact": click_endpoint == observed,
                    }
                    candidates["minus10_major_clicks"] = click_candidate

            for model_name, candidate in candidates.items():
                if candidate.get("within_1_5") is True:
                    model_counts[f"{model_name}_within_1_5"] += 1
                if candidate.get("endpoint_exact") is True:
                    model_counts[f"{model_name}_endpoint_exact"] += 1

            observed_seg_vector = _vector(origin, observed, topology)
            raw_enemy_intervals: list[tuple[float, float]] = []
            for field in mine_context.fields(after_turn):
                if field.is_web or field.owner_id is None or field.owner_id <= 0 or field.owner_id == owner_id:
                    continue
                interval = _route_interval(
                    origin=origin,
                    vector=observed_seg_vector,
                    field=field,
                    topology=topology,
                )
                if interval is None:
                    continue
                raw_enemy_intervals.append((float(interval[0]), float(interval[1])))

            raw_enemy_sum = sum(max(0.0, b - a) for a, b in raw_enemy_intervals)
            raw_enemy_union = _union_length(raw_enemy_intervals)
            passage_values = _passage_values(_messages(after_payload), ship_id=ship_id)
            passage_value = passage_values[0] if len(passage_values) == 1 else None
            if passage_value is not None:
                passage_counts["rows_with_single_passage"] += 1
                if abs(passage_value - raw_enemy_sum) <= 1.5:
                    passage_counts["passage_matches_raw_enemy_sum_1_5"] += 1
                if abs(passage_value - raw_enemy_union) <= 1.5:
                    passage_counts["passage_matches_raw_enemy_union_1_5"] += 1
                if abs(passage_value - observed_distance) <= 1.5:
                    passage_counts["passage_matches_observed_distance_1_5"] += 1

            excess = max(0.0, regular_distance - 10.0) - observed_distance
            item = {
                "game_id": game_id,
                "before_turn": before_turn,
                "ship_id": ship_id,
                "owner_id": owner_id,
                "race_id": race_id,
                "hull_id": int(hull_id) if hull_id is not None else None,
                "hull_tech": hull.tech_level,
                "warp": sample.warp,
                "before_damage": before_damage,
                "hit_quantum": hit_quantum,
                "report_damage": report_damage,
                "report_equals_hit_quantum": report_damage == hit_quantum,
                "raw_after_hit_damage": raw_after_hit_damage,
                "damage_max_warp": damage_max_warp,
                "regular_distance": round(regular_distance, 6),
                "impact_progress": round(impact_progress, 6),
                "observed_distance": round(observed_distance, 6),
                "excess_beyond_minus10": round(excess, 6),
                "passage_report": passage_value,
                "raw_enemy_field_interval_count": len(raw_enemy_intervals),
                "raw_enemy_field_sum": round(raw_enemy_sum, 6),
                "raw_enemy_field_union": round(raw_enemy_union, 6),
                "settings": settings,
                "candidates": candidates,
            }
            strict_items.append(item)

    print("\n===== STRICT POPULATION =====")
    print("strict_rows=", len(strict_items))
    print("excess_rows_gt_1_5=", sum(float(item["excess_beyond_minus10"]) > 1.5 for item in strict_items))
    print("target_present=", sum((item["game_id"], item["before_turn"], item["ship_id"]) == TARGET_KEY for item in strict_items))
    print("report_equals_hit_quantum=", sum(item["report_equals_hit_quantum"] is True for item in strict_items))
    print("race_id_ready=", sum(item["race_id"] is not None for item in strict_items))
    print("damage_max_warp_ready=", sum(item["damage_max_warp"] is not None for item in strict_items))

    print("\n===== GAME MINE-SLOWDOWN SETTING SIGNATURES =====")
    for game_id in sorted(setting_signatures):
        signatures = sorted(setting_signatures[game_id], key=repr)
        print({"game_id": game_id, "signature_count": len(signatures), "signatures": [dict(sig) for sig in signatures]})

    print("\n===== MODEL SUMMARY =====")
    for key in sorted(model_counts):
        print(f"{key}=", model_counts[key])

    print("\n===== PASSAGE GEOMETRY SUMMARY =====")
    for key in (
        "rows_with_single_passage",
        "passage_matches_raw_enemy_sum_1_5",
        "passage_matches_raw_enemy_union_1_5",
        "passage_matches_observed_distance_1_5",
    ):
        print(f"{key}=", passage_counts[key])

    print("\n===== STRICT ROW DETAILS =====")
    for item in strict_items:
        print(item)

    print("\n===== TARGET =====")
    for item in strict_items:
        if (item["game_id"], item["before_turn"], item["ship_id"]) == TARGET_KEY:
            print(item)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "This diagnostic compares multiple candidate mechanics without promoting any of them. Raw game settings are "
        "restricted to scalar keys whose names explicitly reference mine-hit slowdown/hull-tech behavior; unrelated "
        "settings, names, passwords, save keys, and identities are not printed. Damage-time candidates are analogical "
        "tests inspired by documented HOST/PHost behavior, not assumed NuHost semantics. Mine passage geometry uses "
        "deduplicated observed enemy normal fields only and deliberately does not claim hostility resolution. No "
        "production labels, schemas, or accounting are changed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
