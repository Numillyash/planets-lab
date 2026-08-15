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


class _MovementEntityMap(dict):
    """Entity map carrying fail-closed warp-well eligibility by archive turn."""

    def __init__(
        self,
        *args: Any,
        warp_well_planet_ids_by_turn: Mapping[int, frozenset[int]],
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.warp_well_planet_ids_by_turn = dict(warp_well_planet_ids_by_turn)


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


def _settings_warp_well_state_by_turn(
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> tuple[Mapping[int, bool | None], frozenset[int]]:
    """Return whether ordinary warp wells are enabled for each archive turn.

    Normalized archive snapshots contain an explicit privacy-safe
    ``settings.nowarpwells`` value. Missing/malformed/conflicting normalized
    settings fail closed to ``None``. Manually constructed legacy test snapshots
    that contain no ``settings`` key at all keep the historical test default of
    enabled wells; those turns are returned in the legacy set.
    """

    grouped: dict[int, list[Mapping[str, Any] | None]] = defaultdict(list)
    missing_settings_key: dict[int, list[bool]] = defaultdict(list)

    for snapshot in snapshots:
        payload = snapshot.mechanics_payload
        has_settings = "settings" in payload
        missing_settings_key[snapshot.archive_turn].append(not has_settings)
        raw_settings = payload.get("settings")
        grouped[snapshot.archive_turn].append(
            raw_settings if isinstance(raw_settings, Mapping) else None
        )

    result: dict[int, bool | None] = {}
    legacy_turns: set[int] = set()
    for turn, settings_rows in grouped.items():
        if all(missing_settings_key.get(turn, ())):
            result[turn] = True
            legacy_turns.add(turn)
            continue

        values: set[bool] = set()
        invalid = False
        for settings in settings_rows:
            if not isinstance(settings, Mapping) or "nowarpwells" not in settings:
                invalid = True
                continue
            raw = settings.get("nowarpwells")
            if isinstance(raw, bool):
                values.add(raw)
            elif isinstance(raw, int) and not isinstance(raw, bool) and raw in (0, 1):
                values.add(bool(raw))
            else:
                invalid = True

        if invalid or len(values) != 1:
            result[turn] = None
        else:
            result[turn] = not next(iter(values))

    return result, frozenset(legacy_turns)


def _warp_well_planet_ids_by_turn(
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> Mapping[int, frozenset[int]]:
    """Resolve planet IDs that can legitimately supply an ordinary warp well.

    A warp well exists only when the historical game setting enables wells and
    the planet record has a stable ``debrisdisk == 0`` value. Nonzero debris
    membership denotes a planetoid/debris object and is excluded. Missing or
    conflicting mechanical context is fail-closed for normalized corpus data.
    """

    records = tuple(snapshots)
    enabled_by_turn, legacy_turns = _settings_warp_well_state_by_turn(records)
    planet_groups = group_perspective_records(records, "planet")
    eligible: dict[int, set[int]] = defaultdict(set)

    for (turn, planet_id), grouped in planet_groups.items():
        if enabled_by_turn.get(turn) is not True:
            continue

        values: set[int] = set()
        malformed = False
        saw_debris = False
        for record in grouped:
            if "debrisdisk" not in record.raw:
                if turn not in legacy_turns:
                    malformed = True
                continue
            saw_debris = True
            value = _intish(record.raw.get("debrisdisk"))
            if value is None or value < 0:
                malformed = True
                continue
            values.add(value)

        if turn in legacy_turns and not saw_debris:
            debris = 0
        elif not malformed and len(values) == 1:
            debris = next(iter(values))
        else:
            debris = None

        if debris == 0:
            eligible[turn].add(planet_id)

    return {turn: frozenset(ids) for turn, ids in eligible.items()}


def _entity_map(
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> Mapping[tuple[str, int, int], PartialEntityResolution]:
    reconstructed = reconstruct_fields(snapshots)
    return _MovementEntityMap(
        {
            (entity.kind, entity.archive_turn, entity.entity_id): entity
            for entity in reconstructed.entities
        },
        warp_well_planet_ids_by_turn=_warp_well_planet_ids_by_turn(snapshots),
    )


def _planet_tuples_by_turn(
    entities: Mapping[tuple[str, int, int], PartialEntityResolution],
    *,
    include_ineligible: bool = False,
) -> Mapping[int, tuple[tuple[int, int, int], ...]]:
    """Build one O(entities) planet geometry index for all archive turns.

    By default, when the entity map carries historical warp-well context, only
    ordinary planets eligible to supply a warp well are returned. The
    ``include_ineligible`` escape hatch exists for retrospective audits that must
    intentionally reproduce the pre-fix behavior.

    This must not be expressed as ``dict.setdefault(turn, _planet_tuples(...))``
    inside the per-ship loop: Python evaluates the default argument eagerly,
    which caused a full entity-map scan for every movement transition.
    """

    eligible_by_turn = getattr(entities, "warp_well_planet_ids_by_turn", None)
    grouped: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
    for (kind, turn, entity_id), entity in entities.items():
        if kind != "planet":
            continue
        if not include_ineligible and eligible_by_turn is not None:
            if entity_id not in eligible_by_turn.get(turn, frozenset()):
                continue
        x = _intish(_resolved_value(entity, "x"))
        y = _intish(_resolved_value(entity, "y"))
        if x is None or y is None:
            continue
        grouped[turn].append((entity_id, x, y))
    return {
        turn: tuple(sorted(planets))
        for turn, planets in grouped.items()
    }


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

    # Build warp-well-eligible planet geometry once per game. The old
    # per-transition setdefault expression evaluated its expensive default
    # eagerly even on cache hits.
    planets_by_turn = _planet_tuples_by_turn(entities)

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
        planets = planets_by_turn.get(transition.before_archive_turn, ())
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
