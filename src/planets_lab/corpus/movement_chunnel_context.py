from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from planets_lab.validation.movement_geometry import MovementSample

from .archive import read_archive_members, turn_members
from .movement_context import MOVE_MOST_CANDIDATE, MovementMissionConvention, _classify_owner_record
from .movement_differential import (
    GEOMETRY_EXPLAINED_CATEGORIES,
    _entity_map,
    _intish,
    _movement_category,
    _planet_tuples_by_turn,
    _resolved_value,
    _warp_well_destination,
)
from .movement_residual_context import (
    GRAVITONIC_HULL_IDS,
    _navigation_endpoint,
    _observed_tow_targets,
    _owner_record,
    _resolved_storm_offset,
    _storm_consensus_by_turn,
    _storm_expected_category,
)
from .normalizer import ArchiveTurnSnapshot, _decode_member_json
from .readiness import MOVEMENT_GEOMETRY, READY, evaluate_readiness
from .reconstruction import PerspectiveRecord, group_perspective_records


MOVEMENT_CHUNNEL_CONTEXT_GAME_SCHEMA = "planets-lab.movement-chunnel-context-game.v1"
MOVEMENT_CHUNNEL_CONTEXT_STATS_SCHEMA = "planets-lab.movement-chunnel-context-stats.v1"


@dataclass(frozen=True, slots=True)
class ChunnelAbilityCatalog:
    initiator_hull_ids: frozenset[int]
    target_hull_ids: frozenset[int]
    self_hull_ids: frozenset[int]
    first_member: str
    last_member: str
    ability_sets_consistent: bool


@dataclass(frozen=True, slots=True)
class ObservedChunnelEvent:
    before_archive_turn: int
    after_archive_turn: int
    initiator_ship_id: int
    target_ship_id: int
    owner_id: int
    pre_chunnel_position: tuple[int, int] | None
    destination: tuple[int, int]


def _ability_sets(parsed: Mapping[str, Any]) -> tuple[frozenset[int], frozenset[int], frozenset[int]]:
    hulls = parsed.get("hulls", [])
    if not isinstance(hulls, list):
        raise ValueError("turn payload hulls catalog must be a list")
    initiators: set[int] = set()
    targets: set[int] = set()
    self_hulls: set[int] = set()
    for raw in hulls:
        if not isinstance(raw, Mapping):
            continue
        hull_id = _intish(raw.get("id"))
        if hull_id is None:
            continue
        special = raw.get("special", "")
        text = special.lower() if isinstance(special, str) else ""
        if "chunnel initiator" in text:
            initiators.add(hull_id)
        if "chunnel target" in text:
            targets.add(hull_id)
        if "chunnel self" in text:
            self_hulls.add(hull_id)
    return frozenset(initiators), frozenset(targets), frozenset(self_hulls)


def extract_stable_chunnel_abilities(archive_data: bytes) -> ChunnelAbilityCatalog:
    members = turn_members(archive_data)
    if not members:
        raise ValueError("archive contains no .trn members")
    first = members[0]
    last = members[-1]
    raw_by_name = read_archive_members(archive_data, [first.name, last.name])
    first_parsed, _ = _decode_member_json(raw_by_name[first.name], first)
    last_parsed, _ = _decode_member_json(raw_by_name[last.name], last)
    first_sets = _ability_sets(first_parsed)
    last_sets = _ability_sets(last_parsed)
    return ChunnelAbilityCatalog(
        initiator_hull_ids=first_sets[0].intersection(last_sets[0]),
        target_hull_ids=first_sets[1].intersection(last_sets[1]),
        self_hull_ids=first_sets[2].intersection(last_sets[2]),
        first_member=first.name,
        last_member=last.name,
        ability_sets_consistent=first_sets == last_sets,
    )


def _numeric_friendly_code(record: PerspectiveRecord) -> int | None:
    value = record.raw.get("friendlycode", record.raw.get("friendly_code", ""))
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > 3 or not text.isdigit():
        return None
    return int(text)


def _resolved_xy(entity: Any) -> tuple[int, int] | None:
    if entity is None:
        return None
    x = _intish(_resolved_value(entity, "x"))
    y = _intish(_resolved_value(entity, "y"))
    if x is None or y is None:
        return None
    return x, y


def _sample_from_transition(transition: Any, entities: Mapping[tuple[str, int, int], Any]) -> MovementSample | None:
    before = entities.get(("ship", transition.before_archive_turn, transition.entity_id))
    after = entities.get(("ship", transition.after_archive_turn, transition.entity_id))
    if before is None or after is None:
        return None
    values = tuple(
        _intish(_resolved_value(entity, field))
        for entity, field in (
            (before, "x"),
            (before, "y"),
            (before, "targetx"),
            (before, "targety"),
            (before, "warp"),
            (after, "x"),
            (after, "y"),
            (before, "hullid"),
        )
    )
    x, y, target_x, target_y, warp, next_x, next_y, hull_id = values
    if None in (x, y, target_x, target_y, warp, next_x, next_y) or hull_id is None:
        return None
    return MovementSample(
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


def _effective_sample(sample: MovementSample) -> MovementSample:
    if sample.hull_id not in GRAVITONIC_HULL_IDS:
        return sample
    return MovementSample(
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


def _pre_chunnel_position(
    sample: MovementSample,
    *,
    planets: Sequence[tuple[int, int, int]],
    storms: Sequence[Any],
) -> tuple[tuple[int, int] | None, str]:
    effective = _effective_sample(sample)
    offset, storm_status = _resolved_storm_offset(storms, x=effective.x, y=effective.y)
    if offset is None:
        return None, storm_status
    base = _navigation_endpoint(effective)
    shifted = (base[0] + offset[0], base[1] + offset[1])
    well, ambiguous = _warp_well_destination(sample=effective, endpoint=shifted, planets=planets)
    if ambiguous:
        return None, "warp_well_ambiguous"
    return (well if well is not None else shifted), storm_status


def _owner_index(
    *,
    ship_groups: Mapping[tuple[int, int], tuple[PerspectiveRecord, ...]],
    entities: Mapping[tuple[str, int, int], Any],
    target_hull_ids: frozenset[int],
) -> Mapping[tuple[int, int, int], tuple[int, ...]]:
    grouped: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    for (kind, turn, ship_id), entity in entities.items():
        if kind != "ship":
            continue
        hull_id = _intish(_resolved_value(entity, "hullid"))
        if hull_id not in target_hull_ids:
            continue
        owner_id, owner = _owner_record(ship_groups.get((turn, ship_id), ()))
        if owner_id is None or owner_id <= 0 or owner is None:
            continue
        grouped[(turn, owner_id, ship_id % 1000)].append(ship_id)
    return {key: tuple(sorted(values)) for key, values in grouped.items()}


def discover_observed_chunnel_events(
    snapshots: Sequence[ArchiveTurnSnapshot],
    abilities: ChunnelAbilityCatalog,
    *,
    convention: MovementMissionConvention = MovementMissionConvention(),
) -> tuple[tuple[ObservedChunnelEvent, ...], Mapping[str, int]]:
    records = tuple(snapshots)
    readiness = evaluate_readiness(records, MOVEMENT_GEOMETRY)
    entities = _entity_map(records)
    ship_groups = group_perspective_records(records, "ship")
    planets_by_turn = _planet_tuples_by_turn(entities)
    storms_by_turn, storm_conflict_turns, storm_invalid_turns = _storm_consensus_by_turn(records)
    targets = _owner_index(
        ship_groups=ship_groups,
        entities=entities,
        target_hull_ids=abilities.target_hull_ids,
    )

    counts: Counter[str] = Counter()
    events: list[ObservedChunnelEvent] = []
    for transition in readiness.results:
        if transition.status != READY:
            continue
        sample = _sample_from_transition(transition, entities)
        if sample is None or sample.hull_id not in abilities.initiator_hull_ids:
            continue
        group = ship_groups.get((transition.before_archive_turn, transition.entity_id), ())
        owner_id, owner = _owner_record(group)
        if owner_id is None or owner_id <= 0 or owner is None:
            continue
        if _classify_owner_record(owner, convention=convention) != MOVE_MOST_CANDIDATE:
            continue
        code = _numeric_friendly_code(owner)
        if code is None:
            continue
        counts["numeric_fc_initiator_candidates"] += 1
        candidate_ids = targets.get((transition.before_archive_turn, owner_id, code), ())
        if not candidate_ids:
            counts["no_matching_target_ability_ship"] += 1
            continue

        observed_matches: list[tuple[int, tuple[int, int]]] = []
        for target_id in candidate_ids:
            if target_id == transition.entity_id:
                continue
            target_after = entities.get(("ship", transition.after_archive_turn, target_id))
            destination = _resolved_xy(target_after)
            if destination is not None and destination == sample.observed_destination:
                observed_matches.append((target_id, destination))
        if not observed_matches:
            counts["target_code_without_observed_endpoint_match"] += 1
            continue

        target_id, destination = min(observed_matches, key=lambda item: item[0])
        if len({item[1] for item in observed_matches}) > 1:
            counts["multiple_observed_target_destinations"] += 1
            continue

        storm_turn = transition.after_archive_turn
        pre_position = None
        if storm_turn in storm_conflict_turns:
            counts["pre_chunnel_storm_context_conflict"] += 1
        elif storm_turn in storm_invalid_turns:
            counts["pre_chunnel_storm_context_invalid"] += 1
        else:
            pre_position, status = _pre_chunnel_position(
                sample,
                planets=planets_by_turn.get(transition.before_archive_turn, ()),
                storms=storms_by_turn.get(storm_turn, ()),
            )
            if pre_position is None:
                counts[f"pre_chunnel_{status}"] += 1

        if pre_position == destination:
            counts["endpoint_not_distinct_from_normal_move"] += 1
            continue
        events.append(
            ObservedChunnelEvent(
                before_archive_turn=transition.before_archive_turn,
                after_archive_turn=transition.after_archive_turn,
                initiator_ship_id=transition.entity_id,
                target_ship_id=target_id,
                owner_id=owner_id,
                pre_chunnel_position=pre_position,
                destination=destination,
            )
        )
        counts["observed_chunnel_event"] += 1

    return tuple(events), dict(sorted(counts.items()))


def evaluate_chunnel_residual_context(
    snapshots: Sequence[ArchiveTurnSnapshot],
    abilities: ChunnelAbilityCatalog,
    *,
    convention: MovementMissionConvention = MovementMissionConvention(),
) -> dict[str, Any]:
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
    tow_targets, _ = _observed_tow_targets(
        entities=entities,
        ship_groups=ship_groups,
        valid_pairs=valid_pairs,
        convention=convention,
    )
    events, event_counts = discover_observed_chunnel_events(records, abilities, convention=convention)
    events_by_turn: dict[int, list[ObservedChunnelEvent]] = defaultdict(list)
    for event in events:
        events_by_turn[event.before_archive_turn].append(event)

    residual_before = 0
    chunnel_explained = 0
    residual_after = 0
    chunnel_counts: Counter[str] = Counter()
    explained_categories: Counter[str] = Counter()
    explained_hulls: Counter[int] = Counter()
    residual_categories: Counter[str] = Counter()

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

        residual_before += 1
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
            event = matches[0]
            chunnel_explained += 1
            explained_categories[baseline] += 1
            if sample.hull_id is not None:
                explained_hulls[sample.hull_id] += 1
            if transition.entity_id == event.initiator_ship_id:
                chunnel_counts["initiator"] += 1
            elif owner_id == event.owner_id:
                chunnel_counts["passenger_same_owner"] += 1
            else:
                chunnel_counts["passenger_other_owner"] += 1
            continue
        if len(matches) > 1:
            chunnel_counts["ambiguous_matching_events"] += 1
        residual_after += 1
        residual_categories[baseline] += 1

    if chunnel_explained + residual_after != residual_before:
        raise AssertionError("chunnel residual accounting is not closed")

    return {
        "residual_before_chunnel": residual_before,
        "chunnel_explained": chunnel_explained,
        "residual_after_chunnel": residual_after,
        "observed_chunnel_events": len(events),
        "chunnel_counts": dict(sorted(chunnel_counts.items())),
        "explained_category_counts": dict(sorted(explained_categories.items())),
        "explained_hull_counts": {str(k): v for k, v in sorted(explained_hulls.items())},
        "residual_category_counts": dict(sorted(residual_categories.items())),
        "event_counts": dict(event_counts),
        "ability_catalog": {
            "initiator_hull_ids": sorted(abilities.initiator_hull_ids),
            "target_hull_ids": sorted(abilities.target_hull_ids),
            "self_hull_ids": sorted(abilities.self_hull_ids),
            "ability_sets_consistent": abilities.ability_sets_consistent,
            "first_member": abilities.first_member,
            "last_member": abilities.last_member,
        },
        "valid_turn_pairs": readiness.valid_turn_pairs,
        "skipped_turn_pairs": readiness.skipped_turn_pairs,
    }


def summarize_chunnel_residual_game(
    *,
    game_id: int,
    settings_hash: str,
    archive_data: bytes,
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> dict[str, Any]:
    abilities = extract_stable_chunnel_abilities(archive_data)
    summary = evaluate_chunnel_residual_context(snapshots, abilities)
    return {
        "schema": MOVEMENT_CHUNNEL_CONTEXT_GAME_SCHEMA,
        "game_id": game_id,
        "settings_hash": settings_hash,
        "snapshots": len(snapshots),
        **summary,
    }


def aggregate_chunnel_residual_games(
    records: Iterable[Mapping[str, Any]],
    *,
    failed_game_ids: Iterable[int] = (),
) -> dict[str, Any]:
    rows = tuple(records)
    totals: Counter[str] = Counter()
    chunnel_counts: Counter[str] = Counter()
    explained_categories: Counter[str] = Counter()
    explained_hulls: Counter[str] = Counter()
    residual_categories: Counter[str] = Counter()
    event_counts: Counter[str] = Counter()
    settings_hashes: Counter[str] = Counter()

    for row in rows:
        settings_hash = row.get("settings_hash")
        if isinstance(settings_hash, str):
            settings_hashes[settings_hash] += 1
        for key in (
            "snapshots",
            "residual_before_chunnel",
            "chunnel_explained",
            "residual_after_chunnel",
            "observed_chunnel_events",
            "valid_turn_pairs",
            "skipped_turn_pairs",
        ):
            value = row.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                totals[key] += value
        for source_key, target in (
            ("chunnel_counts", chunnel_counts),
            ("explained_category_counts", explained_categories),
            ("explained_hull_counts", explained_hulls),
            ("residual_category_counts", residual_categories),
            ("event_counts", event_counts),
        ):
            source = row.get(source_key, {})
            if not isinstance(source, Mapping):
                continue
            for key, count in source.items():
                if isinstance(count, int) and not isinstance(count, bool):
                    target[str(key)] += count

    failed = tuple(sorted(set(int(game_id) for game_id in failed_game_ids)))
    return {
        "schema": MOVEMENT_CHUNNEL_CONTEXT_STATS_SCHEMA,
        "games_indexed": len(rows),
        "games_failed": len(failed),
        "failed_game_ids": list(failed),
        "settings_hashes": len(settings_hashes),
        "totals": dict(sorted(totals.items())),
        "chunnel_counts": dict(sorted(chunnel_counts.items())),
        "explained_category_counts": dict(sorted(explained_categories.items())),
        "explained_hull_counts": dict(sorted(explained_hulls.items(), key=lambda item: int(item[0]))),
        "residual_category_counts": dict(sorted(residual_categories.items())),
        "event_counts": dict(sorted(event_counts.items())),
    }
