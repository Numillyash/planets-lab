from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from math import hypot
from typing import Any

from planets_lab.rules.movement import WarpWellAmbiguityError, warp_well_planet_id
from planets_lab.validation.movement_geometry import MovementSample, host_major_minor_destination

from .field_reconstruction import PartialEntityResolution, reconstruct_fields
from .movement_context import (
    GHOST,
    MOVE_MOST_CANDIDATE,
    MovementMissionConvention,
    _classify_owner_record,
    _raw_owner,
    _resolved_owner_from_current,
)
from .normalizer import ArchiveTurnSnapshot
from .readiness import MOVEMENT_GEOMETRY, READY, RESOLVED_FIELD_STATUSES, evaluate_readiness
from .reconstruction import group_perspective_records

MOVEMENT_DIFFERENTIAL_GAME_SCHEMA = "planets-lab.movement-differential-game.v1"
MOVEMENT_DIFFERENTIAL_STATS_SCHEMA = "planets-lab.movement-differential-stats.v1"

GEOMETRY_EXPLAINED_CATEGORIES = frozenset(
    {
        "warp_zero_stationary",
        "reachable_exact",
        "reachable_warp_well_match",
        "partial_host_major_minor",
        "partial_host_major_minor_warp_well_match",
    }
)


@dataclass(frozen=True, slots=True)
class MovementDifferentialSummary:
    geometry_ready: int
    classified_context: int
    move_most_candidates: int
    evaluated_move_most: int
    geometrically_explained: int
    unresolved: int
    category_counts: Mapping[str, int]
    excluded_intent_counts: Mapping[str, int]
    unresolved_hull_counts: Mapping[int, int]
    valid_turn_pairs: int
    skipped_turn_pairs: int


def _intish(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _resolved_value(entity: PartialEntityResolution, field: str) -> Any:
    resolution = entity.fields[field]
    if resolution.status not in RESOLVED_FIELD_STATUSES:
        return None
    return resolution.value


def _entity_map(
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> Mapping[tuple[str, int, int], PartialEntityResolution]:
    reconstructed = reconstruct_fields(snapshots)
    return {
        (entity.kind, entity.archive_turn, entity.entity_id): entity
        for entity in reconstructed.entities
    }


def _planet_tuples(
    entities: Mapping[tuple[str, int, int], PartialEntityResolution],
    archive_turn: int,
) -> tuple[tuple[int, int, int], ...]:
    result: list[tuple[int, int, int]] = []
    for (kind, turn, entity_id), entity in entities.items():
        if kind != "planet" or turn != archive_turn:
            continue
        x = _intish(_resolved_value(entity, "x"))
        y = _intish(_resolved_value(entity, "y"))
        if x is None or y is None:
            continue
        result.append((entity_id, x, y))
    return tuple(sorted(result))


def _warp_well_destination(
    *,
    sample: MovementSample,
    endpoint: tuple[int, int],
    planets: Sequence[tuple[int, int, int]],
) -> tuple[tuple[int, int] | None, bool]:
    try:
        planet_id = warp_well_planet_id(
            origin_x=sample.x,
            origin_y=sample.y,
            end_x=endpoint[0],
            end_y=endpoint[1],
            movement_warp=sample.warp,
            planets=planets,
        )
    except WarpWellAmbiguityError:
        return None, True
    if planet_id is None:
        return None, False
    for candidate_id, x, y in planets:
        if candidate_id == planet_id:
            return (x, y), False
    return None, False


def _movement_category(
    sample: MovementSample,
    *,
    planets: Sequence[tuple[int, int, int]],
) -> str:
    origin = (sample.x, sample.y)
    target = (sample.target_x, sample.target_y)
    observed = sample.observed_destination
    nominal = sample.nominal_max_distance
    observed_distance = sample.observed_distance

    if sample.warp <= 0:
        return "warp_zero_stationary" if observed == origin else "warp_zero_external_move"

    # Do not silently reinterpret super-nominal travel as ordinary movement.
    # Gravitonic movement, towing, ion storms and other external contexts are
    # intentionally left for later mechanic-specific classifiers.
    if observed_distance > nominal + 1.5:
        return "above_nominal"

    target_distance = hypot(target[0] - origin[0], target[1] - origin[1])
    if target_distance <= nominal:
        expected = target
        if observed == expected:
            return "reachable_exact"
        well, ambiguous = _warp_well_destination(
            sample=sample,
            endpoint=expected,
            planets=planets,
        )
        if ambiguous:
            return "reachable_warp_well_ambiguous"
        if well is not None and observed == well:
            return "reachable_warp_well_match"
        if observed == origin:
            return "reachable_stayed"
        return "reachable_other"

    expected = host_major_minor_destination(sample)
    if observed == expected:
        return "partial_host_major_minor"
    well, ambiguous = _warp_well_destination(
        sample=sample,
        endpoint=expected,
        planets=planets,
    )
    if ambiguous:
        return "partial_warp_well_ambiguous"
    if well is not None and observed == well:
        return "partial_host_major_minor_warp_well_match"
    if observed == origin:
        return "partial_stayed"
    return "partial_other"


def evaluate_movement_differential(
    snapshots: Sequence[ArchiveTurnSnapshot],
    *,
    convention: MovementMissionConvention = MovementMissionConvention(),
) -> MovementDifferentialSummary:
    records = tuple(snapshots)
    readiness = evaluate_readiness(records, MOVEMENT_GEOMETRY)
    entities = _entity_map(records)
    ship_groups = group_perspective_records(records, "ship")

    categories: Counter[str] = Counter()
    excluded_intents: Counter[str] = Counter()
    unresolved_hulls: Counter[int] = Counter()
    geometry_ready = 0
    classified_context = 0
    move_most_candidates = 0

    planet_cache: dict[int, tuple[tuple[int, int, int], ...]] = {}

    for transition in readiness.results:
        if transition.status != READY:
            continue
        geometry_ready += 1

        group = ship_groups.get((transition.before_archive_turn, transition.entity_id), ())
        owner_id, owner_issue = _resolved_owner_from_current(group)
        if owner_issue is not None or owner_id is None:
            # This should normally be zero after the owner-context stage. Keep
            # the category explicit so the differential remains fail-closed.
            excluded_intents["owner_context_unresolved"] += 1
            continue

        if owner_id == 0:
            intent = GHOST
        else:
            owner_records = tuple(
                record
                for record in group
                if record.is_current and record.player_id == owner_id
            )
            if len(owner_records) != 1 or _raw_owner(owner_records[0]) != owner_id:
                excluded_intents["owner_context_unresolved"] += 1
                continue
            intent = _classify_owner_record(owner_records[0], convention=convention)

        classified_context += 1
        if intent != MOVE_MOST_CANDIDATE:
            excluded_intents[intent] += 1
            continue
        move_most_candidates += 1

        before = entities[("ship", transition.before_archive_turn, transition.entity_id)]
        after = entities[("ship", transition.after_archive_turn, transition.entity_id)]
        x = _intish(_resolved_value(before, "x"))
        y = _intish(_resolved_value(before, "y"))
        target_x = _intish(_resolved_value(before, "targetx"))
        target_y = _intish(_resolved_value(before, "targety"))
        warp = _intish(_resolved_value(before, "warp"))
        next_x = _intish(_resolved_value(after, "x"))
        next_y = _intish(_resolved_value(after, "y"))
        hull_id = _intish(_resolved_value(before, "hullid"))
        if None in (x, y, target_x, target_y, warp, next_x, next_y):
            # Readiness should make this unreachable; preserve fail-closed
            # accounting if profile semantics change later.
            categories["internal_missing_ready_field"] += 1
            if hull_id is not None:
                unresolved_hulls[hull_id] += 1
            continue

        sample = MovementSample(
            turn=transition.before_embedded_turn,
            ship_id=transition.entity_id,
            x=x,
            y=y,
            target_x=target_x,
            target_y=target_y,
            warp=warp,
            next_x=next_x,
            next_y=next_y,
            game_id=before.embedded_turn,
            hull_id=hull_id,
        )
        planets = planet_cache.setdefault(
            transition.before_archive_turn,
            _planet_tuples(entities, transition.before_archive_turn),
        )
        category = _movement_category(sample, planets=planets)
        categories[category] += 1
        if category not in GEOMETRY_EXPLAINED_CATEGORIES and hull_id is not None:
            unresolved_hulls[hull_id] += 1

    evaluated = sum(categories.values())
    explained = sum(
        count
        for category, count in categories.items()
        if category in GEOMETRY_EXPLAINED_CATEGORIES
    )
    unresolved = evaluated - explained

    return MovementDifferentialSummary(
        geometry_ready=geometry_ready,
        classified_context=classified_context,
        move_most_candidates=move_most_candidates,
        evaluated_move_most=evaluated,
        geometrically_explained=explained,
        unresolved=unresolved,
        category_counts=dict(sorted(categories.items())),
        excluded_intent_counts=dict(sorted(excluded_intents.items())),
        unresolved_hull_counts=dict(sorted(unresolved_hulls.items())),
        valid_turn_pairs=readiness.valid_turn_pairs,
        skipped_turn_pairs=readiness.skipped_turn_pairs,
    )


def summarize_movement_differential_game(
    *,
    game_id: int,
    settings_hash: str,
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> dict[str, Any]:
    summary = evaluate_movement_differential(snapshots)
    return {
        "schema": MOVEMENT_DIFFERENTIAL_GAME_SCHEMA,
        "game_id": game_id,
        "settings_hash": settings_hash,
        "snapshots": len(snapshots),
        "geometry_ready": summary.geometry_ready,
        "classified_context": summary.classified_context,
        "move_most_candidates": summary.move_most_candidates,
        "evaluated_move_most": summary.evaluated_move_most,
        "geometrically_explained": summary.geometrically_explained,
        "unresolved": summary.unresolved,
        "category_counts": dict(summary.category_counts),
        "excluded_intent_counts": dict(summary.excluded_intent_counts),
        "unresolved_hull_counts": {
            str(key): value for key, value in summary.unresolved_hull_counts.items()
        },
        "valid_turn_pairs": summary.valid_turn_pairs,
        "skipped_turn_pairs": summary.skipped_turn_pairs,
    }


def aggregate_movement_differential_games(
    records: Iterable[Mapping[str, Any]],
    *,
    failed_game_ids: Iterable[int] = (),
) -> dict[str, Any]:
    rows = tuple(records)
    totals: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    excluded: Counter[str] = Counter()
    unresolved_hulls: Counter[str] = Counter()
    settings_hashes: Counter[str] = Counter()
    by_settings: dict[str, Counter[str]] = defaultdict(Counter)

    for row in rows:
        settings_hash = row.get("settings_hash")
        if isinstance(settings_hash, str):
            settings_hashes[settings_hash] += 1
        else:
            settings_hash = "unknown"

        for key in (
            "snapshots",
            "geometry_ready",
            "classified_context",
            "move_most_candidates",
            "evaluated_move_most",
            "geometrically_explained",
            "unresolved",
            "valid_turn_pairs",
            "skipped_turn_pairs",
        ):
            value = row.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                totals[key] += value

        source = row.get("category_counts", {})
        if isinstance(source, Mapping):
            for category, count in source.items():
                if isinstance(count, int) and not isinstance(count, bool):
                    categories[str(category)] += count
                    by_settings[str(settings_hash)][str(category)] += count

        source = row.get("excluded_intent_counts", {})
        if isinstance(source, Mapping):
            for intent, count in source.items():
                if isinstance(count, int) and not isinstance(count, bool):
                    excluded[str(intent)] += count

        source = row.get("unresolved_hull_counts", {})
        if isinstance(source, Mapping):
            for hull_id, count in source.items():
                if isinstance(count, int) and not isinstance(count, bool):
                    unresolved_hulls[str(hull_id)] += count

    failed = tuple(sorted(set(int(game_id) for game_id in failed_game_ids)))
    return {
        "schema": MOVEMENT_DIFFERENTIAL_STATS_SCHEMA,
        "games_indexed": len(rows),
        "games_failed": len(failed),
        "failed_game_ids": list(failed),
        "settings_hashes": len(settings_hashes),
        "totals": dict(sorted(totals.items())),
        "category_counts": dict(sorted(categories.items())),
        "excluded_intent_counts": dict(sorted(excluded.items())),
        "unresolved_hull_counts": dict(sorted(unresolved_hulls.items(), key=lambda item: int(item[0]))),
        "category_counts_by_settings_hash": {
            settings_hash: dict(sorted(counts.items()))
            for settings_hash, counts in sorted(by_settings.items())
        },
    }
