from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from math import hypot
from typing import Any

from planets_lab.rules.ion_storm import IonStormCircle, integer_drag_delta, local_voltage
from planets_lab.validation.movement_geometry import MovementSample, host_major_minor_destination

from .movement_context import (
    MOVE_MOST_CANDIDATE,
    TOW_ATTEMPT,
    MovementMissionConvention,
    _classify_owner_record,
    _raw_owner,
    _resolved_owner_from_current,
)
from .movement_differential import (
    GEOMETRY_EXPLAINED_CATEGORIES,
    _entity_map,
    _intish,
    _movement_category,
    _planet_tuples_by_turn,
    _resolved_value,
    _warp_well_destination,
)
from .normalizer import ArchiveTurnSnapshot
from .readiness import MOVEMENT_GEOMETRY, READY, evaluate_readiness
from .reconstruction import PerspectiveRecord, group_perspective_records

# Official Planets.nu Gravitonic Accelerator hulls: BR4, BR5 Kaye, Meteor.
GRAVITONIC_HULL_IDS = frozenset({44, 45, 46})

MOVEMENT_RESIDUAL_CONTEXT_GAME_SCHEMA = "planets-lab.movement-residual-context-game.v2"
MOVEMENT_RESIDUAL_CONTEXT_STATS_SCHEMA = "planets-lab.movement-residual-context-stats.v2"


@dataclass(frozen=True, slots=True)
class StormRecord:
    id: int
    x: float
    y: float
    radius: float
    voltage: float
    warp: int
    heading: float
    parent_id: int


@dataclass(frozen=True, slots=True)
class MovementResidualContextSummary:
    move_most_candidates: int
    baseline_explained: int
    baseline_unresolved: int
    context_explained: int
    residual_unresolved: int
    context_counts: Mapping[str, int]
    residual_category_counts: Mapping[str, int]
    residual_hull_counts: Mapping[int, int]
    storm_context_counts: Mapping[str, int]
    tow_context_counts: Mapping[str, int]
    valid_turn_pairs: int
    skipped_turn_pairs: int


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _storm_record(raw: Mapping[str, Any]) -> StormRecord | None:
    storm_id = _intish(raw.get("id"))
    x = _number(raw.get("x"))
    y = _number(raw.get("y"))
    radius = _number(raw.get("radius"))
    voltage = _number(raw.get("voltage"))
    warp = _intish(raw.get("warp"))
    heading = _number(raw.get("heading"))
    parent_id = _intish(raw.get("parentid", raw.get("parent_id", 0)))
    if None in (storm_id, x, y, radius, voltage, warp, heading, parent_id):
        return None
    if not 0 <= warp <= 9:
        return None
    return StormRecord(
        id=storm_id,
        x=x,
        y=y,
        radius=radius,
        voltage=voltage,
        warp=warp,
        heading=heading,
        parent_id=parent_id,
    )


def _snapshot_storm_signature(snapshot: ArchiveTurnSnapshot) -> tuple[StormRecord, ...] | None:
    raw_value = snapshot.mechanics_payload.get("ionstorms", [])
    if not isinstance(raw_value, list):
        return None
    storms: list[StormRecord] = []
    for raw in raw_value:
        if not isinstance(raw, Mapping):
            return None
        record = _storm_record(raw)
        if record is None:
            return None
        storms.append(record)
    return tuple(sorted(storms, key=lambda item: item.id))


def _storm_consensus_by_turn(
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> tuple[Mapping[int, tuple[StormRecord, ...]], frozenset[int], frozenset[int]]:
    grouped: dict[int, list[tuple[StormRecord, ...] | None]] = defaultdict(list)
    for snapshot in snapshots:
        grouped[snapshot.archive_turn].append(_snapshot_storm_signature(snapshot))

    consensus: dict[int, tuple[StormRecord, ...]] = {}
    conflicts: set[int] = set()
    invalid: set[int] = set()
    for turn, signatures in grouped.items():
        if any(signature is None for signature in signatures):
            invalid.add(turn)
            continue
        known = {signature for signature in signatures if signature is not None}
        if len(known) != 1:
            conflicts.add(turn)
            continue
        consensus[turn] = next(iter(known))
    return consensus, frozenset(conflicts), frozenset(invalid)


def _storm_clusters(
    storms: Sequence[StormRecord],
) -> tuple[tuple[StormRecord, tuple[IonStormCircle, ...]], ...]:
    roots = tuple(sorted((storm for storm in storms if storm.parent_id == 0), key=lambda item: item.id))
    result: list[tuple[StormRecord, tuple[IonStormCircle, ...]]] = []
    for root in roots:
        members = [root]
        members.extend(
            sorted(
                (storm for storm in storms if storm.parent_id == root.id),
                key=lambda item: item.id,
            )
        )
        circles = tuple(
            IonStormCircle(
                id=storm.id,
                x=storm.x,
                y=storm.y,
                radius=storm.radius,
                voltage=storm.voltage,
                warp=storm.warp,
                heading=storm.heading,
                parent_id=storm.parent_id,
            )
            for storm in members
        )
        result.append((root, circles))
    return tuple(result)


def _resolved_storm_offset(
    storms: Sequence[StormRecord],
    *,
    x: int,
    y: int,
) -> tuple[tuple[int, int] | None, str]:
    effective_x = x
    effective_y = y
    total_dx = 0
    total_dy = 0
    affected = False

    for root, circles in _storm_clusters(storms):
        voltage = local_voltage(circles, effective_x, effective_y)
        if voltage < 150.0:
            continue
        affected = True
        if voltage >= 400.0:
            return None, "extreme_voltage"
        dx, dy = integer_drag_delta(root.warp, root.heading)
        effective_x += dx
        effective_y += dy
        total_dx += dx
        total_dy += dy

    if not affected:
        return (0, 0), "not_affected"
    return (total_dx, total_dy), "resolved_drag"


def _navigation_endpoint(sample: MovementSample) -> tuple[int, int]:
    origin = (sample.x, sample.y)
    if sample.warp <= 0:
        return origin
    target = (sample.target_x, sample.target_y)
    if hypot(target[0] - origin[0], target[1] - origin[1]) <= sample.nominal_max_distance:
        return target
    return host_major_minor_destination(sample)


def _storm_expected_category(
    sample: MovementSample,
    *,
    storms: Sequence[StormRecord],
    planets: Sequence[tuple[int, int, int]],
) -> tuple[str | None, str]:
    offset, status = _resolved_storm_offset(storms, x=sample.x, y=sample.y)
    if offset is None or offset == (0, 0):
        return None, status

    base = _navigation_endpoint(sample)
    shifted = (base[0] + offset[0], base[1] + offset[1])
    if sample.observed_destination == shifted:
        return "ion_storm_drag", status

    well, ambiguous = _warp_well_destination(sample=sample, endpoint=shifted, planets=planets)
    if ambiguous:
        return None, "warp_well_ambiguous"
    if well is not None and sample.observed_destination == well:
        return "ion_storm_drag_warp_well_match", status
    return None, status


def _owner_record(
    group: Sequence[PerspectiveRecord],
) -> tuple[int | None, PerspectiveRecord | None]:
    owner_id, issue = _resolved_owner_from_current(group)
    if issue is not None or owner_id is None or owner_id <= 0:
        return owner_id, None
    records = tuple(
        record
        for record in group
        if record.is_current and record.player_id == owner_id and _raw_owner(record) == owner_id
    )
    if len(records) != 1:
        return owner_id, None
    return owner_id, records[0]


def _xy(entity: Any) -> tuple[int, int] | None:
    if entity is None:
        return None
    x = _intish(_resolved_value(entity, "x"))
    y = _intish(_resolved_value(entity, "y"))
    if x is None or y is None:
        return None
    return x, y


def _observed_tow_targets(
    *,
    entities: Mapping[tuple[str, int, int], Any],
    ship_groups: Mapping[tuple[int, int], tuple[PerspectiveRecord, ...]],
    valid_pairs: Iterable[tuple[int, int]],
    convention: MovementMissionConvention,
) -> tuple[Mapping[tuple[int, int], tuple[int, ...]], Mapping[str, int]]:
    """Return observed tow-target routes, preserving tower-identity ambiguity.

    Every candidate tower counted for a target must be owner-visible as Tow,
    colocated with the target before movement, and share the target's non-zero
    observed destination. Multiple such towers are therefore route-equivalent:
    the identity of the actual winning tower may be ambiguous, but the target's
    movement route is not. The mapping stores all matching tower IDs so callers
    never mistake an arbitrary representative for resolved tower identity.
    """

    matches: dict[tuple[int, int], set[int]] = defaultdict(set)
    counts: Counter[str] = Counter()

    for before_turn, after_turn in sorted(set(valid_pairs)):
        tower_ids = sorted(
            entity_id
            for (kind, turn, entity_id) in entities
            if kind == "ship" and turn == before_turn
        )
        for tower_id in tower_ids:
            group = ship_groups.get((before_turn, tower_id), ())
            _, owner = _owner_record(group)
            if owner is None or _classify_owner_record(owner, convention=convention) != TOW_ATTEMPT:
                continue
            counts["tow_attempt_records"] += 1
            target_id = _intish(owner.raw.get("mission1target", owner.raw.get("mission1_target_id")))
            if target_id is None or target_id <= 0 or target_id == tower_id:
                counts["tow_invalid_target"] += 1
                continue

            tower_before = entities.get(("ship", before_turn, tower_id))
            target_before = entities.get(("ship", before_turn, target_id))
            tower_after = entities.get(("ship", after_turn, tower_id))
            target_after = entities.get(("ship", after_turn, target_id))
            tower_before_xy = _xy(tower_before)
            target_before_xy = _xy(target_before)
            tower_after_xy = _xy(tower_after)
            target_after_xy = _xy(target_after)
            if None in (tower_before_xy, target_before_xy, tower_after_xy, target_after_xy):
                counts["tow_missing_geometry"] += 1
                continue
            if tower_before_xy != target_before_xy:
                counts["tow_not_colocated"] += 1
                continue
            if tower_after_xy != target_after_xy:
                counts["tow_after_destination_differs"] += 1
                continue
            if tower_after_xy == tower_before_xy:
                counts["tow_stationary_pair"] += 1
                continue
            matches[(before_turn, target_id)].add(tower_id)

    resolved: dict[tuple[int, int], tuple[int, ...]] = {}
    for key, towers in matches.items():
        ordered = tuple(sorted(towers))
        if not ordered:
            continue
        resolved[key] = ordered
        counts["observed_tow_target_match"] += 1
        if len(ordered) == 1:
            counts["observed_tow_target_single"] += 1
        else:
            counts["observed_tow_target_route_equivalent_multiple"] += 1
    return resolved, dict(sorted(counts.items()))


def evaluate_movement_residual_context(
    snapshots: Sequence[ArchiveTurnSnapshot],
    *,
    convention: MovementMissionConvention = MovementMissionConvention(),
) -> MovementResidualContextSummary:
    records = tuple(snapshots)
    readiness = evaluate_readiness(records, MOVEMENT_GEOMETRY)
    entities = _entity_map(records)
    ship_groups = group_perspective_records(records, "ship")
    planets_by_turn = _planet_tuples_by_turn(entities)
    storms_by_turn, storm_conflict_turns, storm_invalid_turns = _storm_consensus_by_turn(records)

    valid_pairs = {
        (item.before_archive_turn, item.after_archive_turn)
        for item in readiness.results
    }
    tow_targets, tow_counts = _observed_tow_targets(
        entities=entities,
        ship_groups=ship_groups,
        valid_pairs=valid_pairs,
        convention=convention,
    )

    context_counts: Counter[str] = Counter()
    residual_categories: Counter[str] = Counter()
    residual_hulls: Counter[int] = Counter()
    storm_counts: Counter[str] = Counter()
    move_most_candidates = 0
    baseline_explained = 0
    baseline_unresolved = 0

    for transition in readiness.results:
        if transition.status != READY:
            continue
        group = ship_groups.get((transition.before_archive_turn, transition.entity_id), ())
        owner_id, owner = _owner_record(group)
        if owner_id is None or owner_id == 0 or owner is None:
            continue
        if _classify_owner_record(owner, convention=convention) != MOVE_MOST_CANDIDATE:
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
            hull_id=hull_id,
        )
        planets = planets_by_turn.get(transition.before_archive_turn, ())
        baseline = _movement_category(sample, planets=planets)
        if baseline in GEOMETRY_EXPLAINED_CATEGORIES:
            baseline_explained += 1
            continue
        baseline_unresolved += 1

        if (transition.before_archive_turn, transition.entity_id) in tow_targets:
            context_counts["observed_tow_target_match"] += 1
            continue

        gravitonic = hull_id in GRAVITONIC_HULL_IDS if hull_id is not None else False
        effective_sample = sample
        if gravitonic:
            effective_sample = MovementSample(
                turn=sample.turn,
                ship_id=sample.ship_id,
                x=sample.x,
                y=sample.y,
                target_x=sample.target_x,
                target_y=sample.target_y,
                warp=sample.warp,
                next_x=sample.next_x,
                next_y=sample.next_y,
                gravitonic=True,
                hull_id=sample.hull_id,
            )
            grav_category = _movement_category(effective_sample, planets=planets)
            if grav_category in GEOMETRY_EXPLAINED_CATEGORIES:
                context_counts[f"gravitonic_{grav_category}"] += 1
                continue

        storm_turn = transition.after_archive_turn
        if storm_turn in storm_conflict_turns:
            storm_counts["storm_context_conflict"] += 1
        elif storm_turn in storm_invalid_turns:
            storm_counts["storm_context_invalid"] += 1
        else:
            storms = storms_by_turn.get(storm_turn, ())
            storm_category, storm_status = _storm_expected_category(
                effective_sample,
                storms=storms,
                planets=planets,
            )
            storm_counts[storm_status] += 1
            if storm_category is not None:
                prefix = "gravitonic_" if gravitonic else ""
                context_counts[f"{prefix}{storm_category}"] += 1
                continue

        residual_categories[baseline] += 1
        if hull_id is not None:
            residual_hulls[hull_id] += 1

    context_explained = sum(context_counts.values())
    residual_unresolved = sum(residual_categories.values())
    if baseline_explained + baseline_unresolved != move_most_candidates:
        raise AssertionError("movement residual accounting does not cover Move Most candidates")
    if context_explained + residual_unresolved != baseline_unresolved:
        raise AssertionError("movement residual context accounting is not closed")

    return MovementResidualContextSummary(
        move_most_candidates=move_most_candidates,
        baseline_explained=baseline_explained,
        baseline_unresolved=baseline_unresolved,
        context_explained=context_explained,
        residual_unresolved=residual_unresolved,
        context_counts=dict(sorted(context_counts.items())),
        residual_category_counts=dict(sorted(residual_categories.items())),
        residual_hull_counts=dict(sorted(residual_hulls.items())),
        storm_context_counts=dict(sorted(storm_counts.items())),
        tow_context_counts=dict(sorted(tow_counts.items())),
        valid_turn_pairs=readiness.valid_turn_pairs,
        skipped_turn_pairs=readiness.skipped_turn_pairs,
    )


def summarize_movement_residual_context_game(
    *,
    game_id: int,
    settings_hash: str,
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> dict[str, Any]:
    summary = evaluate_movement_residual_context(snapshots)
    return {
        "schema": MOVEMENT_RESIDUAL_CONTEXT_GAME_SCHEMA,
        "game_id": game_id,
        "settings_hash": settings_hash,
        "snapshots": len(snapshots),
        "move_most_candidates": summary.move_most_candidates,
        "baseline_explained": summary.baseline_explained,
        "baseline_unresolved": summary.baseline_unresolved,
        "context_explained": summary.context_explained,
        "residual_unresolved": summary.residual_unresolved,
        "context_counts": dict(summary.context_counts),
        "residual_category_counts": dict(summary.residual_category_counts),
        "residual_hull_counts": {str(k): v for k, v in summary.residual_hull_counts.items()},
        "storm_context_counts": dict(summary.storm_context_counts),
        "tow_context_counts": dict(summary.tow_context_counts),
        "valid_turn_pairs": summary.valid_turn_pairs,
        "skipped_turn_pairs": summary.skipped_turn_pairs,
    }


def aggregate_movement_residual_context_games(
    records: Iterable[Mapping[str, Any]],
    *,
    failed_game_ids: Iterable[int] = (),
) -> dict[str, Any]:
    rows = tuple(records)
    totals: Counter[str] = Counter()
    contexts: Counter[str] = Counter()
    residual_categories: Counter[str] = Counter()
    residual_hulls: Counter[str] = Counter()
    storm_counts: Counter[str] = Counter()
    tow_counts: Counter[str] = Counter()
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
            "move_most_candidates",
            "baseline_explained",
            "baseline_unresolved",
            "context_explained",
            "residual_unresolved",
            "valid_turn_pairs",
            "skipped_turn_pairs",
        ):
            value = row.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                totals[key] += value
        for source_key, target in (
            ("context_counts", contexts),
            ("residual_category_counts", residual_categories),
            ("residual_hull_counts", residual_hulls),
            ("storm_context_counts", storm_counts),
            ("tow_context_counts", tow_counts),
        ):
            source = row.get(source_key, {})
            if not isinstance(source, Mapping):
                continue
            for key, count in source.items():
                if isinstance(count, int) and not isinstance(count, bool):
                    target[str(key)] += count
                    if source_key == "context_counts":
                        by_settings[str(settings_hash)][str(key)] += count

    failed = tuple(sorted(set(int(game_id) for game_id in failed_game_ids)))
    return {
        "schema": MOVEMENT_RESIDUAL_CONTEXT_STATS_SCHEMA,
        "games_indexed": len(rows),
        "games_failed": len(failed),
        "failed_game_ids": list(failed),
        "settings_hashes": len(settings_hashes),
        "totals": dict(sorted(totals.items())),
        "context_counts": dict(sorted(contexts.items())),
        "residual_category_counts": dict(sorted(residual_categories.items())),
        "residual_hull_counts": dict(sorted(residual_hulls.items(), key=lambda item: int(item[0]))),
        "storm_context_counts": dict(sorted(storm_counts.items())),
        "tow_context_counts": dict(sorted(tow_counts.items())),
        "context_counts_by_settings_hash": {
            settings_hash: dict(sorted(counts.items()))
            for settings_hash, counts in sorted(by_settings.items())
        },
    }
