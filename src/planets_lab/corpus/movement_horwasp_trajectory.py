from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from math import atan2, degrees, hypot
from typing import Any

from .movement_chunnel_context import (
    _effective_sample,
    _pre_chunnel_position,
    _sample_from_transition,
    discover_observed_chunnel_events,
    extract_stable_chunnel_abilities,
)
from .movement_context import MOVE_MOST_CANDIDATE, MovementMissionConvention, _classify_owner_record
from .movement_differential import GEOMETRY_EXPLAINED_CATEGORIES, _entity_map, _intish, _movement_category, _planet_tuples_by_turn, _resolved_value
from .movement_horwasp_diagnostics import _is_pod_like
from .movement_residual_context import _observed_tow_targets, _owner_record, _storm_consensus_by_turn, _storm_expected_category
from .movement_residual_profile import extract_hull_catalog
from .movement_topology_diagnostics import MapTopologyEvidence, extract_map_topology, wrapped_delta
from .normalizer import ArchiveTurnSnapshot
from .readiness import MOVEMENT_GEOMETRY, READY, evaluate_readiness
from .reconstruction import group_perspective_records


ACCELERATED_MAX_DISTANCE = {3: 14, 6: 54, 7: 74, 9: 122}
_SAFE_WAYPOINT_KEYS = frozenset({
    "id", "x", "y", "targetx", "targety", "planetid", "shipid", "turn", "warp", "heading"
})


def _vector(
    start: tuple[int, int],
    end: tuple[int, int],
    topology: MapTopologyEvidence,
) -> tuple[int, int]:
    if topology.sphere is True and topology.mapwidth and topology.mapheight:
        return (
            wrapped_delta(start[0], end[0], topology.mapwidth),
            wrapped_delta(start[1], end[1], topology.mapheight),
        )
    return end[0] - start[0], end[1] - start[1]


def _bearing(dx: int, dy: int) -> float | None:
    if dx == 0 and dy == 0:
        return None
    # Planets/Nu compass convention: 0=north, 90=east.
    return (degrees(atan2(dx, dy)) + 360.0) % 360.0


def _angle_error(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return abs((left - right + 180.0) % 360.0 - 180.0)


def _error_bucket(error: float | None) -> str:
    if error is None:
        return "unknown"
    if error <= 1.5:
        return "le_1_5_deg"
    if error <= 5.0:
        return "le_5_deg"
    if error <= 15.0:
        return "le_15_deg"
    if error <= 45.0:
        return "le_45_deg"
    return "gt_45_deg"


def _distance_class(distance: float, warp: int) -> str:
    if distance <= 0.75:
        return "stationary"
    normal = warp * warp
    accelerated = ACCELERATED_MAX_DISTANCE.get(warp)
    if abs(distance - normal) <= 1.5:
        return "near_normal_max"
    if accelerated is not None and abs(distance - accelerated) <= 1.5:
        return "near_accelerated_max"
    if distance < normal - 1.5:
        return "below_normal_max"
    if accelerated is None:
        return "above_normal_max_unsupported_warp"
    if distance < accelerated - 1.5:
        return "between_normal_and_accelerated"
    return "above_accelerated_max"


def _safe_waypoints(raw: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    value = raw.get("waypoints")
    if not isinstance(value, list):
        return ()
    result: list[dict[str, Any]] = []
    for item in value[:8]:
        if not isinstance(item, Mapping):
            continue
        safe: dict[str, Any] = {}
        for key, child in item.items():
            key_text = str(key).lower().replace("_", "")
            if key_text not in _SAFE_WAYPOINT_KEYS:
                continue
            if isinstance(child, bool):
                continue
            if isinstance(child, (int, float)):
                safe[str(key)] = child
        if safe:
            result.append(dict(sorted(safe.items())))
    return tuple(result)


def _xy(entity: Any) -> tuple[int, int] | None:
    if entity is None:
        return None
    x = _intish(_resolved_value(entity, "x"))
    y = _intish(_resolved_value(entity, "y"))
    if x is None or y is None:
        return None
    return x, y


def diagnose_horwasp_trajectories(
    archive_data: bytes,
    snapshots: Sequence[ArchiveTurnSnapshot],
    *,
    convention: MovementMissionConvention = MovementMissionConvention(),
    sample_limit: int = 30,
) -> dict[str, Any]:
    records = tuple(snapshots)
    topology = extract_map_topology(archive_data)
    hull_catalog = extract_hull_catalog(archive_data)
    abilities = extract_stable_chunnel_abilities(archive_data)
    pod_hulls = {
        hull_id: hull for hull_id, hull in hull_catalog.hulls.items() if _is_pod_like(hull)
    }

    readiness = evaluate_readiness(records, MOVEMENT_GEOMETRY)
    entities = _entity_map(records)
    ship_groups = group_perspective_records(records, "ship")
    planets_by_turn = _planet_tuples_by_turn(entities)
    storms_by_turn, storm_conflict_turns, storm_invalid_turns = _storm_consensus_by_turn(records)
    valid_pairs = {(item.before_archive_turn, item.after_archive_turn) for item in readiness.results}
    tow_targets, _ = _observed_tow_targets(
        entities=entities,
        ship_groups=ship_groups,
        valid_pairs=valid_pairs,
        convention=convention,
    )
    events, _ = discover_observed_chunnel_events(records, abilities, convention=convention)
    events_by_turn: dict[int, list[Any]] = defaultdict(list)
    for event in events:
        events_by_turn[event.before_archive_turn].append(event)

    pod_like_residual = 0
    distance_classes: dict[int, Counter[str]] = defaultdict(Counter)
    warp_distance: dict[int, Counter[str]] = defaultdict(Counter)
    launch_age: dict[int, Counter[str]] = defaultdict(Counter)
    heading_target_error: dict[int, Counter[str]] = defaultdict(Counter)
    heading_observed_error: dict[int, Counter[str]] = defaultdict(Counter)
    waypoint_counts: dict[int, Counter[str]] = defaultdict(Counter)
    waypoint_key_counts: dict[int, Counter[str]] = defaultdict(Counter)
    mite_links: Counter[str] = Counter()
    samples: list[dict[str, Any]] = []

    for transition in readiness.results:
        if transition.status != READY:
            continue
        group = ship_groups.get((transition.before_archive_turn, transition.entity_id), ())
        owner_id, owner = _owner_record(group)
        if owner_id is None or owner_id == 0 or owner is None:
            continue
        if _classify_owner_record(owner, convention=convention) != MOVE_MOST_CANDIDATE:
            continue
        sample = _sample_from_transition(transition, entities)
        if sample is None:
            continue
        planets = planets_by_turn.get(transition.before_archive_turn, ())
        baseline = _movement_category(sample, planets=planets)
        if baseline in GEOMETRY_EXPLAINED_CATEGORIES:
            continue
        if (transition.before_archive_turn, transition.entity_id) in tow_targets:
            continue

        effective = _effective_sample(sample)
        if effective is not sample:
            grav_category = _movement_category(effective, planets=planets)
            if grav_category in GEOMETRY_EXPLAINED_CATEGORIES:
                continue

        storm_turn = transition.after_archive_turn
        storms: Sequence[Any] = ()
        if storm_turn not in storm_conflict_turns and storm_turn not in storm_invalid_turns:
            storms = storms_by_turn.get(storm_turn, ())
            storm_category, _ = _storm_expected_category(effective, storms=storms, planets=planets)
            if storm_category is not None:
                continue

        if storm_turn in storm_conflict_turns or storm_turn in storm_invalid_turns:
            pre_position = None
        else:
            pre_position, _ = _pre_chunnel_position(effective, planets=planets, storms=storms)
        matches = [
            event for event in events_by_turn.get(transition.before_archive_turn, ())
            if event.destination == sample.observed_destination
            and event.pre_chunnel_position is not None
            and pre_position == event.pre_chunnel_position
        ]
        if len(matches) == 1:
            continue

        hull_id = sample.hull_id
        if hull_id is None or hull_id not in pod_hulls:
            continue
        pod_like_residual += 1

        origin = (sample.x, sample.y)
        observed = sample.observed_destination
        target = (sample.target_x, sample.target_y)
        odx, ody = _vector(origin, observed, topology)
        tdx, tdy = _vector(origin, target, topology)
        observed_distance = hypot(odx, ody)
        target_distance = hypot(tdx, tdy)
        observed_bearing = _bearing(odx, ody)
        target_bearing = _bearing(tdx, tdy)
        heading_value = _intish(owner.raw.get("heading"))
        heading = None if heading_value is None or heading_value < 0 else float(heading_value % 360)

        distance_classes[hull_id][_distance_class(observed_distance, sample.warp)] += 1
        warp_distance[hull_id][f"warp={sample.warp}|d={round(observed_distance, 1)}"] += 1
        heading_target_error[hull_id][_error_bucket(_angle_error(heading, target_bearing))] += 1
        heading_observed_error[hull_id][_error_bucket(_angle_error(heading, observed_bearing))] += 1

        launch_turn = _intish(owner.raw.get("turn"))
        age = None if launch_turn is None else transition.before_embedded_turn - launch_turn
        launch_age[hull_id]["unknown" if age is None else str(age)] += 1

        waypoints = _safe_waypoints(owner.raw)
        waypoint_counts[hull_id][str(len(waypoints))] += 1
        for waypoint in waypoints:
            for key in waypoint:
                waypoint_key_counts[hull_id][key] += 1

        hull_name = str(pod_hulls[hull_id].get("name") or "")
        mite_target_id = None
        mite_target_before = None
        mite_target_after = None
        mite_before_distance = None
        mite_after_distance = None
        if "mite" in hull_name.lower():
            mite_links["mite_residual_records"] += 1
            candidate = _intish(owner.raw.get("podhullid"))
            if candidate is not None and candidate > 0:
                mite_target_id = candidate
                mite_links["podhullid_positive"] += 1
                target_before_entity = entities.get(("ship", transition.before_archive_turn, candidate))
                target_after_entity = entities.get(("ship", transition.after_archive_turn, candidate))
                mite_target_before = _xy(target_before_entity)
                mite_target_after = _xy(target_after_entity)
                if mite_target_before is not None:
                    mite_links["candidate_ship_exists_before"] += 1
                    bdx, bdy = _vector(origin, mite_target_before, topology)
                    mite_before_distance = hypot(bdx, bdy)
                if mite_target_after is not None:
                    mite_links["candidate_ship_exists_after"] += 1
                    adx, ady = _vector(observed, mite_target_after, topology)
                    mite_after_distance = hypot(adx, ady)
                if mite_target_before is not None and mite_target_after is not None:
                    mite_links["candidate_ship_exists_both"] += 1
                    if mite_before_distance is not None and mite_after_distance is not None:
                        if mite_after_distance < mite_before_distance - 0.75:
                            mite_links["distance_to_candidate_decreased"] += 1
                        elif mite_after_distance > mite_before_distance + 0.75:
                            mite_links["distance_to_candidate_increased"] += 1
                        else:
                            mite_links["distance_to_candidate_roughly_same"] += 1
                    adx, ady = _vector(observed, mite_target_after, topology)
                    if adx == 0 and ady == 0:
                        mite_links["observed_endpoint_equals_candidate_after"] += 1

        if len(samples) < max(0, sample_limit):
            samples.append({
                "archive_turn": transition.before_archive_turn,
                "embedded_turn": transition.before_embedded_turn,
                "ship_id": transition.entity_id,
                "owner_id": owner_id,
                "hull_id": hull_id,
                "hull_name": pod_hulls[hull_id].get("name"),
                "category": baseline,
                "warp": sample.warp,
                "launch_turn": launch_turn,
                "launch_age": age,
                "heading": heading,
                "origin": list(origin),
                "target": list(target),
                "observed_destination": list(observed),
                "wrapped_observed_vector": [odx, ody],
                "wrapped_observed_distance": round(observed_distance, 3),
                "wrapped_observed_bearing": None if observed_bearing is None else round(observed_bearing, 3),
                "wrapped_target_vector": [tdx, tdy],
                "wrapped_target_distance": round(target_distance, 3),
                "wrapped_target_bearing": None if target_bearing is None else round(target_bearing, 3),
                "distance_class": _distance_class(observed_distance, sample.warp),
                "waypoints": list(waypoints),
                "mite_target_id": mite_target_id,
                "mite_target_before": None if mite_target_before is None else list(mite_target_before),
                "mite_target_after": None if mite_target_after is None else list(mite_target_after),
                "mite_target_distance_before": None if mite_before_distance is None else round(mite_before_distance, 3),
                "mite_target_distance_after": None if mite_after_distance is None else round(mite_after_distance, 3),
            })

    return {
        "topology": {
            "sphere": topology.sphere,
            "mapwidth": topology.mapwidth,
            "mapheight": topology.mapheight,
            "mapshape": topology.mapshape,
            "stable": topology.stable,
        },
        "pod_like_residual": pod_like_residual,
        "hull_names": {str(k): v.get("name") for k, v in sorted(pod_hulls.items())},
        "distance_class_counts": {str(k): dict(sorted(v.items())) for k, v in sorted(distance_classes.items())},
        "warp_distance_counts": {str(k): dict(sorted(v.items(), key=lambda item: (-item[1], item[0]))) for k, v in sorted(warp_distance.items())},
        "launch_age_counts": {str(k): dict(sorted(v.items(), key=lambda item: (-item[1], item[0]))) for k, v in sorted(launch_age.items())},
        "heading_target_error_counts": {str(k): dict(sorted(v.items())) for k, v in sorted(heading_target_error.items())},
        "heading_observed_error_counts": {str(k): dict(sorted(v.items())) for k, v in sorted(heading_observed_error.items())},
        "waypoint_count_counts": {str(k): dict(sorted(v.items())) for k, v in sorted(waypoint_counts.items())},
        "waypoint_key_counts": {str(k): dict(sorted(v.items(), key=lambda item: (-item[1], item[0]))) for k, v in sorted(waypoint_key_counts.items())},
        "mite_link_counts": dict(sorted(mite_links.items())),
        "samples": samples,
    }
