from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from math import hypot
from typing import Any

from .movement_chunnel_context import _sample_from_transition
from .movement_differential import _entity_map, _intish, _resolved_value
from .movement_horwasp_diagnostics import _is_pod_like
from .movement_horwasp_trajectory import _angle_error, _bearing, _error_bucket, _vector
from .movement_residual_context import _owner_record
from .movement_residual_profile import extract_hull_catalog
from .movement_topology_diagnostics import MapTopologyEvidence, extract_map_topology
from .normalizer import ArchiveTurnSnapshot
from .readiness import MOVEMENT_GEOMETRY, READY, evaluate_readiness
from .reconstruction import group_perspective_records


_SAFE_HISTORY_KEYS = frozenset(
    {
        "id",
        "x",
        "y",
        "targetx",
        "targety",
        "turn",
        "warp",
        "heading",
        "shipid",
        "planetid",
    }
)


def _safe_numeric_mapping(value: Any) -> dict[str, int | float]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, int | float] = {}
    for key, child in value.items():
        normalized = str(key).lower().replace("_", "")
        if normalized not in _SAFE_HISTORY_KEYS or isinstance(child, bool):
            continue
        if isinstance(child, (int, float)):
            result[str(key)] = child
    return dict(sorted(result.items()))


def safe_history_entries(raw: Mapping[str, Any], *, limit: int = 12) -> tuple[dict[str, int | float], ...]:
    """Return only navigation-like numeric values from the opaque Nu ``history`` field."""

    value = raw.get("history")
    candidates: list[Any] = []
    if isinstance(value, list):
        candidates.extend(value[: max(0, limit)])
    elif isinstance(value, Mapping):
        # Preserve neither arbitrary string keys nor arbitrary scalar values. A mapping
        # may itself be one history item or may contain a list/dict of history items.
        direct = _safe_numeric_mapping(value)
        if direct:
            candidates.append(value)
        for child in value.values():
            if len(candidates) >= max(0, limit):
                break
            if isinstance(child, Mapping):
                candidates.append(child)
            elif isinstance(child, list):
                candidates.extend(child[: max(0, limit) - len(candidates)])

    result: list[dict[str, int | float]] = []
    for candidate in candidates:
        safe = _safe_numeric_mapping(candidate)
        if safe:
            result.append(safe)
        if len(result) >= max(0, limit):
            break
    return tuple(result)


def sign_step_toward(
    origin: tuple[int, int],
    target: tuple[int, int],
    topology: MapTopologyEvidence,
) -> tuple[int, int]:
    dx, dy = _vector(origin, target, topology)
    return (0 if dx == 0 else (1 if dx > 0 else -1), 0 if dy == 0 else (1 if dy > 0 else -1))


def _xy(entity: Any) -> tuple[int, int] | None:
    if entity is None:
        return None
    x = _intish(_resolved_value(entity, "x"))
    y = _intish(_resolved_value(entity, "y"))
    if x is None or y is None:
        return None
    return x, y


def _distance(left: tuple[int, int], right: tuple[int, int], topology: MapTopologyEvidence) -> float:
    dx, dy = _vector(left, right, topology)
    return hypot(dx, dy)


def _history_shape(raw: Mapping[str, Any]) -> tuple[str, int | None]:
    value = raw.get("history")
    if isinstance(value, list):
        return "list", len(value)
    if isinstance(value, Mapping):
        return "mapping", len(value)
    if value is None:
        return "none", None
    return type(value).__name__, None


def diagnose_horwasp_state_linkage(
    archive_data: bytes,
    snapshots: Sequence[ArchiveTurnSnapshot],
    *,
    sample_limit: int = 30,
) -> dict[str, Any]:
    """Inspect authoritative owner-side Horwasp trajectory state across consecutive turns.

    This diagnostic intentionally uses all geometry-ready Pod-like transitions rather than
    only the residual subset. It measures wire-state timing and target linkage without
    declaring any movement mechanic proven.
    """

    records = tuple(snapshots)
    topology = extract_map_topology(archive_data)
    hull_catalog = extract_hull_catalog(archive_data)
    pod_hulls = {
        hull_id: hull
        for hull_id, hull in hull_catalog.hulls.items()
        if _is_pod_like(hull)
    }

    readiness = evaluate_readiness(records, MOVEMENT_GEOMETRY)
    entities = _entity_map(records)
    ship_groups = group_perspective_records(records, "ship")

    transitions_by_hull: Counter[int] = Counter()
    heading_before_error: dict[int, Counter[str]] = defaultdict(Counter)
    heading_after_error: dict[int, Counter[str]] = defaultdict(Counter)
    heading_change: dict[int, Counter[str]] = defaultdict(Counter)
    launch_turn_change: dict[int, Counter[str]] = defaultdict(Counter)
    target_change: dict[int, Counter[str]] = defaultdict(Counter)
    history_types: dict[int, Counter[str]] = defaultdict(Counter)
    history_lengths: dict[int, Counter[str]] = defaultdict(Counter)
    history_keys: dict[int, Counter[str]] = defaultdict(Counter)
    mite_counts: Counter[str] = Counter()
    samples: list[dict[str, Any]] = []

    for transition in readiness.results:
        if transition.status != READY:
            continue
        sample = _sample_from_transition(transition, entities)
        if sample is None or sample.hull_id not in pod_hulls:
            continue

        before_group = ship_groups.get((transition.before_archive_turn, transition.entity_id), ())
        owner_id, before_owner = _owner_record(before_group)
        if owner_id is None or owner_id <= 0 or before_owner is None:
            continue
        after_group = ship_groups.get((transition.after_archive_turn, transition.entity_id), ())
        after_owner_id, after_owner = _owner_record(after_group)
        if after_owner_id != owner_id or after_owner is None:
            continue

        hull_id = int(sample.hull_id)
        transitions_by_hull[hull_id] += 1
        origin = (sample.x, sample.y)
        observed = sample.observed_destination
        odx, ody = _vector(origin, observed, topology)
        observed_bearing = _bearing(odx, ody)

        before_heading_i = _intish(before_owner.raw.get("heading"))
        after_heading_i = _intish(after_owner.raw.get("heading"))
        before_heading = None if before_heading_i is None or before_heading_i < 0 else float(before_heading_i % 360)
        after_heading = None if after_heading_i is None or after_heading_i < 0 else float(after_heading_i % 360)
        heading_before_error[hull_id][_error_bucket(_angle_error(before_heading, observed_bearing))] += 1
        heading_after_error[hull_id][_error_bucket(_angle_error(after_heading, observed_bearing))] += 1
        if before_heading is None or after_heading is None:
            heading_change[hull_id]["unknown"] += 1
        elif before_heading == after_heading:
            heading_change[hull_id]["same"] += 1
        else:
            heading_change[hull_id]["changed"] += 1

        before_launch = _intish(before_owner.raw.get("turn"))
        after_launch = _intish(after_owner.raw.get("turn"))
        if before_launch is None or after_launch is None:
            launch_turn_change[hull_id]["unknown"] += 1
        elif before_launch == after_launch:
            launch_turn_change[hull_id]["same"] += 1
        else:
            launch_turn_change[hull_id]["changed"] += 1

        before_target = (_intish(before_owner.raw.get("targetx")), _intish(before_owner.raw.get("targety")))
        after_target = (_intish(after_owner.raw.get("targetx")), _intish(after_owner.raw.get("targety")))
        if None in before_target or None in after_target:
            target_change[hull_id]["unknown"] += 1
        elif before_target == after_target:
            target_change[hull_id]["same"] += 1
        else:
            target_change[hull_id]["changed"] += 1

        history_type, history_length = _history_shape(before_owner.raw)
        history_types[hull_id][history_type] += 1
        if history_length is not None:
            history_lengths[hull_id][str(history_length)] += 1
        history = safe_history_entries(before_owner.raw)
        for entry in history:
            for key in entry:
                history_keys[hull_id][key] += 1

        hull_name = str(pod_hulls[hull_id].get("name") or "")
        mite_detail: dict[str, Any] = {}
        if "mite" in hull_name.lower():
            mite_counts["mite_transitions"] += 1
            candidate_id = _intish(before_owner.raw.get("podhullid"))
            target_xy = None
            if None not in before_target:
                target_xy = (int(before_target[0]), int(before_target[1]))
                mite_counts["targetxy_present"] += 1
                predicted = sign_step_toward(origin, target_xy, topology)
                if (odx, ody) == predicted:
                    mite_counts["observed_sign_step_matches_targetxy"] += 1
                if abs(odx) <= 1 and abs(ody) <= 1 and (odx != 0 or ody != 0):
                    mite_counts["observed_unit_grid_step"] += 1

            candidate_before = None
            candidate_after = None
            if candidate_id is not None and candidate_id > 0:
                mite_counts["podhullid_positive"] += 1
                candidate_before = _xy(entities.get(("ship", transition.before_archive_turn, candidate_id)))
                candidate_after = _xy(entities.get(("ship", transition.after_archive_turn, candidate_id)))
                if candidate_before is not None:
                    mite_counts["candidate_exists_before"] += 1
                    predicted = sign_step_toward(origin, candidate_before, topology)
                    if (odx, ody) == predicted:
                        mite_counts["observed_sign_step_matches_candidate_before"] += 1
                if candidate_after is not None:
                    mite_counts["candidate_exists_after"] += 1
                    predicted = sign_step_toward(origin, candidate_after, topology)
                    if (odx, ody) == predicted:
                        mite_counts["observed_sign_step_matches_candidate_after"] += 1
                if candidate_before is not None and candidate_after is not None:
                    mite_counts["candidate_exists_both"] += 1

            if target_xy is not None and candidate_before is not None:
                d = _distance(target_xy, candidate_before, topology)
                if d <= 1.5:
                    mite_counts["targetxy_near_candidate_before"] += 1
                if d <= 0.01:
                    mite_counts["targetxy_equals_candidate_before"] += 1
            if target_xy is not None and candidate_after is not None:
                d = _distance(target_xy, candidate_after, topology)
                if d <= 1.5:
                    mite_counts["targetxy_near_candidate_after"] += 1
                if d <= 0.01:
                    mite_counts["targetxy_equals_candidate_after"] += 1

            mite_detail = {
                "candidate_id": candidate_id,
                "candidate_before": None if candidate_before is None else list(candidate_before),
                "candidate_after": None if candidate_after is None else list(candidate_after),
                "target_xy": None if target_xy is None else list(target_xy),
            }

        if len(samples) < max(0, sample_limit):
            samples.append(
                {
                    "archive_turn": transition.before_archive_turn,
                    "embedded_turn": transition.before_embedded_turn,
                    "ship_id": transition.entity_id,
                    "owner_id": owner_id,
                    "hull_id": hull_id,
                    "hull_name": pod_hulls[hull_id].get("name"),
                    "origin": list(origin),
                    "observed_destination": list(observed),
                    "observed_vector": [odx, ody],
                    "observed_distance": round(hypot(odx, ody), 3),
                    "observed_bearing": None if observed_bearing is None else round(observed_bearing, 3),
                    "heading_before": before_heading,
                    "heading_after": after_heading,
                    "turn_before": before_launch,
                    "turn_after": after_launch,
                    "target_before": list(before_target),
                    "target_after": list(after_target),
                    "history": list(history),
                    **mite_detail,
                }
            )

    return {
        "topology": {
            "sphere": topology.sphere,
            "mapwidth": topology.mapwidth,
            "mapheight": topology.mapheight,
            "mapshape": topology.mapshape,
            "stable": topology.stable,
        },
        "hull_names": {str(k): v.get("name") for k, v in sorted(pod_hulls.items())},
        "transitions_by_hull": {str(k): v for k, v in sorted(transitions_by_hull.items())},
        "heading_before_observed_error_counts": {str(k): dict(sorted(v.items())) for k, v in sorted(heading_before_error.items())},
        "heading_after_observed_error_counts": {str(k): dict(sorted(v.items())) for k, v in sorted(heading_after_error.items())},
        "heading_change_counts": {str(k): dict(sorted(v.items())) for k, v in sorted(heading_change.items())},
        "launch_turn_change_counts": {str(k): dict(sorted(v.items())) for k, v in sorted(launch_turn_change.items())},
        "target_change_counts": {str(k): dict(sorted(v.items())) for k, v in sorted(target_change.items())},
        "history_type_counts": {str(k): dict(sorted(v.items())) for k, v in sorted(history_types.items())},
        "history_length_counts": {str(k): dict(sorted(v.items(), key=lambda item: (-item[1], item[0]))) for k, v in sorted(history_lengths.items())},
        "history_key_counts": {str(k): dict(sorted(v.items(), key=lambda item: (-item[1], item[0]))) for k, v in sorted(history_keys.items())},
        "mite_linkage_counts": dict(sorted(mite_counts.items())),
        "samples": samples,
    }
