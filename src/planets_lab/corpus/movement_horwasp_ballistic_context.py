from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace
from math import cos, floor, hypot, radians, sin
from typing import Any

from .movement_chunnel_context import (
    _effective_sample,
    _pre_chunnel_position,
    _sample_from_transition,
    discover_observed_chunnel_events,
    extract_stable_chunnel_abilities,
)
from .movement_context import MOVE_MOST_CANDIDATE, MovementMissionConvention, _classify_owner_record
from .movement_differential import GEOMETRY_EXPLAINED_CATEGORIES, _entity_map, _intish, _movement_category, _planet_tuples_by_turn
from .movement_horwasp_state_linkage import safe_history_entries
from .movement_horwasp_trajectory import _vector
from .movement_residual_context import _observed_tow_targets, _owner_record, _storm_consensus_by_turn, _storm_expected_category
from .movement_residual_profile import extract_hull_catalog
from .movement_topology_diagnostics import MapTopologyEvidence, extract_map_topology
from .normalizer import ArchiveTurnSnapshot
from .readiness import MOVEMENT_GEOMETRY, READY, evaluate_readiness
from .reconstruction import group_perspective_records


MOVEMENT_HORWASP_BALLISTIC_GAME_SCHEMA = "planets-lab.movement-horwasp-ballistic-game.v2"
MOVEMENT_HORWASP_BALLISTIC_STATS_SCHEMA = "planets-lab.movement-horwasp-ballistic-stats.v2"

# Empirical movement/target-linkage evidence for historical game 591478 shows
# a 2170-ly toroidal wrap period even though its raw settings advertise
# mapwidth=mapheight=2150. Keep the override exact and fail closed: it is not a
# general mapwidth+20 rule and must never alter the raw topology facts.
_SCOPED_EFFECTIVE_WRAP_PERIODS: Mapping[int, tuple[int, int]] = {
    591478: (2170, 2170),
}
_SCOPED_RAW_WRAP_PERIODS: Mapping[int, tuple[int, int]] = {
    591478: (2150, 2150),
}

# Accelerator and Sentry are ballistic Horwasp hulls but their historical
# catalog entries may advertise another primary ability instead of the literal
# word "Pod". Keep these exact names as an explicit documented exception.
_BALLISTIC_NAME_EXCEPTIONS = frozenset({"Accelerator", "Sentry"})


def _effective_ballistic_topology(
    *,
    game_id: int | None,
    topology: MapTopologyEvidence,
) -> MapTopologyEvidence:
    """Return the evidence-scoped topology used only for ballistic vectors.

    Raw map settings remain authoritative facts elsewhere. The sole historical
    override is guarded by exact game ID, sphere/stability state and the raw
    dimensions that were independently audited before promotion.
    """

    if game_id is None:
        return topology
    effective = _SCOPED_EFFECTIVE_WRAP_PERIODS.get(int(game_id))
    expected_raw = _SCOPED_RAW_WRAP_PERIODS.get(int(game_id))
    if effective is None or expected_raw is None:
        return topology
    if topology.sphere is not True or topology.stable is not True:
        return topology
    if (topology.mapwidth, topology.mapheight) != expected_raw:
        return topology
    return replace(
        topology,
        mapwidth=effective[0],
        mapheight=effective[1],
    )


def _historical_ballistic_hulls(catalog: Mapping[int, Mapping[str, Any]]) -> dict[int, Mapping[str, Any]]:
    result: dict[int, Mapping[str, Any]] = {}
    for hull_id, hull in catalog.items():
        name = str(hull.get("name") or "")
        special = str(hull.get("special") or "")
        advantages = " ".join(str(item) for item in hull.get("advantage_names", ()))
        text = f"{special} {advantages}".lower()
        if "mite" in name.lower():
            continue
        if "pod" in text or name in _BALLISTIC_NAME_EXCEPTIONS:
            result[int(hull_id)] = hull
    return result


def _historical_mite_hulls(catalog: Mapping[int, Mapping[str, Any]]) -> frozenset[int]:
    return frozenset(
        int(hull_id)
        for hull_id, hull in catalog.items()
        if "mite" in str(hull.get("name") or "").lower()
    )


def _round_signed_half_up(value: float) -> int:
    if value < 0:
        return -floor(abs(value) + 0.5)
    return floor(value + 0.5)


def ballistic_vector(*, warp: int, heading: int | float, accelerated: bool) -> tuple[int, int]:
    if warp < 0:
        raise ValueError("warp must be non-negative")
    distance = float(warp * warp) * (1.5 if accelerated else 1.0)
    angle = radians(float(heading) % 360.0)
    return (
        _round_signed_half_up(distance * sin(angle)),
        _round_signed_half_up(distance * cos(angle)),
    )


def _previous_mode(
    raw: Mapping[str, Any],
    *,
    origin: tuple[int, int],
    warp: int,
    topology: MapTopologyEvidence,
) -> str:
    history = safe_history_entries(raw, limit=1)
    if not history:
        return "launch"
    x = _intish(history[0].get("x"))
    y = _intish(history[0].get("y"))
    if x is None or y is None:
        return "unknown"
    dx, dy = _vector((x, y), origin, topology)
    distance = hypot(dx, dy)
    normal = float(warp * warp)
    accelerated = normal * 1.5
    if abs(distance - normal) <= 1.5:
        return "normal"
    if abs(distance - accelerated) <= 1.5:
        return "accelerated"
    return "unknown"


def _ballistic_match(
    *,
    origin: tuple[int, int],
    observed: tuple[int, int],
    warp: int,
    heading: int,
    topology: MapTopologyEvidence,
    accelerated: bool,
) -> bool:
    observed_vector = _vector(origin, observed, topology)
    return observed_vector == ballistic_vector(
        warp=warp,
        heading=heading,
        accelerated=accelerated,
    )


def _classify_ballistic_formula(
    *,
    raw: Mapping[str, Any],
    origin: tuple[int, int],
    observed: tuple[int, int],
    target: tuple[int, int],
    warp: int,
    topology: MapTopologyEvidence,
) -> tuple[str | None, bool]:
    heading = _intish(raw.get("heading"))
    if heading is None or heading < 0 or warp <= 0:
        return None, False

    mode = _previous_mode(raw, origin=origin, warp=warp, topology=topology)
    normal_match = _ballistic_match(
        origin=origin,
        observed=observed,
        warp=warp,
        heading=heading,
        topology=topology,
        accelerated=False,
    )
    accelerated_match = _ballistic_match(
        origin=origin,
        observed=observed,
        warp=warp,
        heading=heading,
        topology=topology,
        accelerated=True,
    )

    # A surviving deep-space Pod can terminate exactly at a target. Treat this
    # as strong only when the speed mode is already inferable from state N.
    target_vector = _vector(origin, target, topology)
    observed_vector = _vector(origin, observed, topology)
    target_distance = hypot(*target_vector)
    if observed_vector == target_vector:
        if mode == "normal" and target_distance <= warp * warp + 1.5:
            return "ballistic_terminal_normal", True
        if mode == "accelerated" and target_distance <= 1.5 * warp * warp + 1.5:
            return "ballistic_terminal_accelerated", True
        if mode == "launch" and target_distance <= warp * warp + 1.5:
            return "ballistic_terminal_launch_normal", True

    if mode == "normal" and normal_match:
        return "ballistic_normal_history_confirmed", True
    if mode == "accelerated" and accelerated_match:
        return "ballistic_accelerated_history_confirmed", True
    if mode == "launch" and normal_match:
        return "ballistic_launch_normal", True

    # These matches support the documented formula, but current state does not
    # independently prove the speed mode before seeing N+1.
    if mode == "normal" and accelerated_match:
        return "ballistic_accelerator_transition_observed", False
    if mode == "launch" and accelerated_match:
        return "ballistic_launch_accelerated_observed", False
    if mode == "unknown" and normal_match:
        return "ballistic_normal_mode_unknown", False
    if mode == "unknown" and accelerated_match:
        return "ballistic_accelerated_mode_unknown", False

    return None, False


def evaluate_horwasp_ballistic_context(
    archive_data: bytes,
    snapshots: Sequence[ArchiveTurnSnapshot],
    *,
    game_id: int | None = None,
    convention: MovementMissionConvention = MovementMissionConvention(),
) -> dict[str, Any]:
    records = tuple(snapshots)
    raw_topology = extract_map_topology(archive_data)
    topology = _effective_ballistic_topology(game_id=game_id, topology=raw_topology)
    hull_catalog = extract_hull_catalog(archive_data)
    ballistic_hulls = _historical_ballistic_hulls(hull_catalog.hulls)
    mite_hulls = _historical_mite_hulls(hull_catalog.hulls)
    abilities = extract_stable_chunnel_abilities(archive_data)

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

    residual_before = 0
    ballistic_candidates = 0
    mite_residual = 0
    strong_explained = 0
    observed_context_explained = 0
    category_counts: Counter[str] = Counter()
    explained_hulls: Counter[int] = Counter()
    unresolved_hulls: Counter[int] = Counter()

    for transition in readiness.results:
        if transition.status != READY:
            continue
        group = ship_groups.get((transition.before_archive_turn, transition.entity_id), ())
        owner_id, owner = _owner_record(group)
        if owner_id is None or owner_id <= 0 or owner is None:
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
        chunnel_matches = [
            event
            for event in events_by_turn.get(transition.before_archive_turn, ())
            if event.destination == sample.observed_destination
            and event.pre_chunnel_position is not None
            and pre_position == event.pre_chunnel_position
        ]
        if len(chunnel_matches) == 1:
            continue

        residual_before += 1
        hull_id = int(sample.hull_id) if sample.hull_id is not None else None
        if hull_id is None:
            continue
        if hull_id in mite_hulls:
            mite_residual += 1
            unresolved_hulls[hull_id] += 1
            continue
        if hull_id not in ballistic_hulls:
            unresolved_hulls[hull_id] += 1
            continue

        ballistic_candidates += 1
        category, strong = _classify_ballistic_formula(
            raw=owner.raw,
            origin=(sample.x, sample.y),
            observed=sample.observed_destination,
            target=(sample.target_x, sample.target_y),
            warp=sample.warp,
            topology=topology,
        )
        if category is None:
            category_counts["ballistic_unresolved"] += 1
            unresolved_hulls[hull_id] += 1
            continue
        category_counts[category] += 1
        explained_hulls[hull_id] += 1
        if strong:
            strong_explained += 1
        else:
            observed_context_explained += 1

    if strong_explained + observed_context_explained > ballistic_candidates:
        raise AssertionError("Horwasp ballistic accounting exceeds candidates")

    return {
        "schema": MOVEMENT_HORWASP_BALLISTIC_GAME_SCHEMA,
        "topology": {
            "sphere": raw_topology.sphere,
            "mapwidth": raw_topology.mapwidth,
            "mapheight": raw_topology.mapheight,
            "mapshape": raw_topology.mapshape,
            "stable": raw_topology.stable,
        },
        "effective_topology": {
            "sphere": topology.sphere,
            "mapwidth": topology.mapwidth,
            "mapheight": topology.mapheight,
            "mapshape": topology.mapshape,
            "stable": topology.stable,
        },
        "catalog_consistent": hull_catalog.consistent,
        "ballistic_hull_ids": sorted(ballistic_hulls),
        "mite_hull_ids": sorted(mite_hulls),
        "hull_names": {
            str(hull_id): hull_catalog.hulls[hull_id].get("name")
            for hull_id in sorted(set(ballistic_hulls).union(mite_hulls))
        },
        "residual_before": residual_before,
        "ballistic_candidates": ballistic_candidates,
        "mite_residual": mite_residual,
        "strong_explained": strong_explained,
        "observed_context_explained": observed_context_explained,
        "ballistic_unresolved": ballistic_candidates - strong_explained - observed_context_explained,
        "residual_after_strong": residual_before - strong_explained,
        "residual_after_observed": residual_before - strong_explained - observed_context_explained,
        "category_counts": dict(sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))),
        "explained_hull_counts": {str(k): v for k, v in sorted(explained_hulls.items(), key=lambda item: (-item[1], item[0]))},
        "unresolved_hull_counts": {str(k): v for k, v in sorted(unresolved_hulls.items(), key=lambda item: (-item[1], item[0]))},
    }
