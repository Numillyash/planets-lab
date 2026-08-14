from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from planets_lab.validation.movement_geometry import MovementSample

from .movement_chunnel_context import (
    _effective_sample,
    _pre_chunnel_position,
    _sample_from_transition,
    discover_observed_chunnel_events,
    extract_stable_chunnel_abilities,
)
from .movement_context import MOVE_MOST_CANDIDATE, MovementMissionConvention, _classify_owner_record
from .movement_differential import GEOMETRY_EXPLAINED_CATEGORIES, _entity_map, _movement_category, _planet_tuples_by_turn
from .movement_residual_context import (
    _observed_tow_targets,
    _owner_record,
    _storm_consensus_by_turn,
    _storm_expected_category,
)
from .movement_residual_profile import HullCatalogSummary, extract_hull_catalog
from .normalizer import ArchiveTurnSnapshot
from .readiness import MOVEMENT_GEOMETRY, READY, evaluate_readiness
from .reconstruction import group_perspective_records


INTERESTING_FIELD_TOKENS = (
    "target",
    "speed",
    "warp",
    "accel",
    "destination",
    "heading",
    "angle",
    "turn",
    "mission",
    "pod",
    "mite",
    "momentum",
    "course",
)


def _is_safe_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (bool, int, float, str))


def _interesting_fields(raw: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in raw.items():
        key_text = str(key)
        lowered = key_text.lower()
        if not any(token in lowered for token in INTERESTING_FIELD_TOKENS):
            continue
        if not _is_safe_scalar(value):
            continue
        if isinstance(value, str):
            # Friendly codes, names and arbitrary text are intentionally not dumped.
            if lowered in {"friendlycode", "friendly_code", "name"}:
                continue
            if len(value) > 80:
                value = value[:77] + "..."
        result[key_text] = value
    return dict(sorted(result.items()))


def _is_pod_like(hull: Mapping[str, Any]) -> bool:
    name = hull.get("name")
    special = hull.get("special")
    text = " ".join(
        part.lower()
        for part in (name, special)
        if isinstance(part, str)
    )
    return any(token in text for token in ("pod", "mite", "rock", "stinger", "nest", "accelerator", "protofield"))


def diagnose_horwasp_residuals(
    archive_data: bytes,
    snapshots: Sequence[ArchiveTurnSnapshot],
    *,
    convention: MovementMissionConvention = MovementMissionConvention(),
    sample_limit: int = 20,
) -> dict[str, Any]:
    records = tuple(snapshots)
    abilities = extract_stable_chunnel_abilities(archive_data)
    hull_catalog: HullCatalogSummary = extract_hull_catalog(archive_data)
    pod_hulls = {
        hull_id: hull
        for hull_id, hull in hull_catalog.hulls.items()
        if _is_pod_like(hull)
    }

    readiness = evaluate_readiness(records, MOVEMENT_GEOMETRY)
    entities = _entity_map(records)
    ship_groups = group_perspective_records(records, "ship")
    planets_by_turn = _planet_tuples_by_turn(entities)
    storms_by_turn, storm_conflict_turns, storm_invalid_turns = _storm_consensus_by_turn(records)
    valid_pairs = {
        (item.before_archive_turn, item.after_archive_turn)
        for item in readiness.results
    }
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

    counts: Counter[tuple[str, int]] = Counter()
    key_counts: dict[int, Counter[str]] = defaultdict(Counter)
    field_values: dict[int, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    samples: list[dict[str, Any]] = []
    residual_after_chunnel = 0
    pod_like_residual = 0

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
            storm_category, _ = _storm_expected_category(
                effective,
                storms=storms,
                planets=planets,
            )
            if storm_category is not None:
                continue

        if storm_turn in storm_conflict_turns or storm_turn in storm_invalid_turns:
            pre_position = None
        else:
            pre_position, _ = _pre_chunnel_position(effective, planets=planets, storms=storms)
        matches = [
            event
            for event in events_by_turn.get(transition.before_archive_turn, ())
            if event.destination == sample.observed_destination
            and event.pre_chunnel_position is not None
            and pre_position == event.pre_chunnel_position
        ]
        if len(matches) == 1:
            continue

        residual_after_chunnel += 1
        hull_id = sample.hull_id
        if hull_id is None or hull_id not in pod_hulls:
            continue
        pod_like_residual += 1
        counts[(baseline, hull_id)] += 1
        raw = owner.raw
        for key in raw:
            key_counts[hull_id][str(key)] += 1
        interesting = _interesting_fields(raw)
        for key, value in interesting.items():
            field_values[hull_id][key][repr(value)] += 1

        if len(samples) < max(0, sample_limit):
            hull = pod_hulls[hull_id]
            samples.append(
                {
                    "archive_turn": transition.before_archive_turn,
                    "embedded_turn": transition.before_embedded_turn,
                    "ship_id": transition.entity_id,
                    "owner_id": owner_id,
                    "hull_id": hull_id,
                    "hull_name": hull.get("name"),
                    "category": baseline,
                    "origin": [sample.x, sample.y],
                    "observed_destination": [sample.next_x, sample.next_y],
                    "raw_keys": sorted(str(key) for key in raw),
                    "interesting_fields": interesting,
                }
            )

    return {
        "residual_after_chunnel": residual_after_chunnel,
        "pod_like_residual": pod_like_residual,
        "catalog_consistent": hull_catalog.consistent,
        "pod_hull_ids": sorted(pod_hulls),
        "category_hull_counts": {
            f"{category}|{hull_id}": count
            for (category, hull_id), count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        },
        "hull_names": {
            str(hull_id): pod_hulls[hull_id].get("name")
            for hull_id in sorted(pod_hulls)
        },
        "raw_key_counts": {
            str(hull_id): dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))
            for hull_id, counter in sorted(key_counts.items())
        },
        "interesting_field_values": {
            str(hull_id): {
                key: dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))
                for key, counter in sorted(fields.items())
            }
            for hull_id, fields in sorted(field_values.items())
        },
        "samples": samples,
    }
