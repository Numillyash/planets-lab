from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
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
)
from .movement_residual_context import (
    GRAVITONIC_HULL_IDS,
    _observed_tow_targets,
    _owner_record,
    _storm_consensus_by_turn,
    _storm_expected_category,
)
from .normalizer import ArchiveTurnSnapshot, _decode_member_json
from .readiness import MOVEMENT_GEOMETRY, READY, evaluate_readiness
from .reconstruction import group_perspective_records


@dataclass(frozen=True, slots=True)
class HullCatalogSummary:
    first_member: str
    last_member: str
    consistent: bool
    first_hash: str
    last_hash: str
    hulls: Mapping[int, Mapping[str, Any]]


def _catalog_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _safe_hull_record(raw: Mapping[str, Any], advantage_names: Mapping[int, str]) -> dict[str, Any]:
    hull_id = _intish(raw.get("id"))
    if hull_id is None:
        raise ValueError("hull catalog record has no integer id")

    result: dict[str, Any] = {"id": hull_id, "keys": sorted(str(key) for key in raw)}
    for key in (
        "name",
        "raceid",
        "mass",
        "cargo",
        "fueltank",
        "crew",
        "engines",
        "beams",
        "torps",
        "launchers",
        "bays",
        "cancloak",
        "gravitonic",
        "isbase",
        "special",
    ):
        value = raw.get(key)
        if isinstance(value, (str, int, float, bool)) or value is None:
            if isinstance(value, str) and len(value) > 160:
                value = value[:157] + "..."
            result[key] = value

    advantage_ids: list[int] = []
    value = raw.get("advantages")
    if isinstance(value, list):
        for item in value:
            item_id = _intish(item.get("id") if isinstance(item, Mapping) else item)
            if item_id is not None:
                advantage_ids.append(item_id)
    elif value is not None:
        item_id = _intish(value)
        if item_id is not None:
            advantage_ids.append(item_id)
    if advantage_ids:
        result["advantage_ids"] = sorted(set(advantage_ids))
        result["advantage_names"] = [
            advantage_names[item_id]
            for item_id in result["advantage_ids"]
            if item_id in advantage_names
        ]
    return result


def extract_hull_catalog(archive_data: bytes) -> HullCatalogSummary:
    members = turn_members(archive_data)
    if not members:
        raise ValueError("archive contains no .trn members")
    first = members[0]
    last = members[-1]
    raw_by_name = read_archive_members(archive_data, [first.name, last.name])

    parsed_by_name: dict[str, Mapping[str, Any]] = {}
    for member in (first, last):
        parsed, _ = _decode_member_json(raw_by_name[member.name], member)
        parsed_by_name[member.name] = parsed

    first_hulls = parsed_by_name[first.name].get("hulls", [])
    last_hulls = parsed_by_name[last.name].get("hulls", [])
    if not isinstance(first_hulls, list) or not isinstance(last_hulls, list):
        raise ValueError("turn payload hulls catalog must be a list")

    advantages = parsed_by_name[first.name].get("advantages", [])
    advantage_names: dict[int, str] = {}
    if isinstance(advantages, list):
        for raw in advantages:
            if not isinstance(raw, Mapping):
                continue
            advantage_id = _intish(raw.get("id"))
            name = raw.get("name")
            if advantage_id is not None and isinstance(name, str):
                advantage_names[advantage_id] = name

    indexed: dict[int, dict[str, Any]] = {}
    for raw in first_hulls:
        if not isinstance(raw, Mapping):
            continue
        safe = _safe_hull_record(raw, advantage_names)
        indexed[int(safe["id"])] = safe

    return HullCatalogSummary(
        first_member=first.name,
        last_member=last.name,
        consistent=first_hulls == last_hulls,
        first_hash=_catalog_hash(first_hulls),
        last_hash=_catalog_hash(last_hulls),
        hulls=dict(sorted(indexed.items())),
    )


def profile_residual_hulls(
    snapshots: Sequence[ArchiveTurnSnapshot],
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

    cross: Counter[tuple[str, int]] = Counter()
    storm_cross: Counter[tuple[str, str, int]] = Counter()
    residual_total = 0

    for transition in readiness.results:
        if transition.status != READY:
            continue
        group = ship_groups.get((transition.before_archive_turn, transition.entity_id), ())
        owner_id, owner = _owner_record(group)
        if owner_id is None or owner_id == 0 or owner is None:
            continue
        if _classify_owner_record(owner, convention=convention) != MOVE_MOST_CANDIDATE:
            continue

        before = entities[("ship", transition.before_archive_turn, transition.entity_id)]
        after = entities[("ship", transition.after_archive_turn, transition.entity_id)]
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
            continue
        if (transition.before_archive_turn, transition.entity_id) in tow_targets:
            continue

        gravitonic = hull_id in GRAVITONIC_HULL_IDS
        effective = sample
        if gravitonic:
            effective = MovementSample(
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
            grav_category = _movement_category(effective, planets=planets)
            if grav_category in GEOMETRY_EXPLAINED_CATEGORIES:
                continue

        storm_turn = transition.after_archive_turn
        storm_status = "none"
        storm_category = None
        if storm_turn in storm_conflict_turns:
            storm_status = "storm_context_conflict"
        elif storm_turn in storm_invalid_turns:
            storm_status = "storm_context_invalid"
        else:
            storm_category, storm_status = _storm_expected_category(
                effective,
                storms=storms_by_turn.get(storm_turn, ()),
                planets=planets,
            )
        if storm_category is not None:
            continue

        residual_total += 1
        cross[(baseline, hull_id)] += 1
        storm_cross[(storm_status, baseline, hull_id)] += 1

    return {
        "residual_unresolved": residual_total,
        "category_hull_counts": {
            f"{category}|{hull_id}": count
            for (category, hull_id), count in sorted(cross.items())
        },
        "storm_status_category_hull_counts": {
            f"{status}|{category}|{hull_id}": count
            for (status, category, hull_id), count in sorted(storm_cross.items())
        },
    }


def aggregate_profile_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    combos: Counter[tuple[str, int, str]] = Counter()
    combo_games: dict[tuple[str, int, str], set[int]] = defaultdict(set)
    catalog_consistency: Counter[str] = Counter()
    residual_total = 0

    for row in rows:
        game_id = int(row["game_id"])
        residual_total += int(row.get("residual_unresolved", 0))
        catalog_consistency["consistent" if row.get("catalog_consistent") else "changed"] += 1
        catalog = row.get("hull_catalog", {})
        counts = row.get("category_hull_counts", {})
        if not isinstance(catalog, Mapping) or not isinstance(counts, Mapping):
            continue
        for key, count in counts.items():
            if not isinstance(key, str) or not isinstance(count, int):
                continue
            category, hull_text = key.rsplit("|", 1)
            hull_id = int(hull_text)
            descriptor = catalog.get(str(hull_id), {})
            name = descriptor.get("name") if isinstance(descriptor, Mapping) else None
            name_text = str(name) if name not in (None, "") else "<unnamed>"
            combo = (category, hull_id, name_text)
            combos[combo] += count
            combo_games[combo].add(game_id)

    return {
        "games": len(rows),
        "residual_unresolved": residual_total,
        "catalog_consistency": dict(sorted(catalog_consistency.items())),
        "category_hull_name_counts": [
            {
                "category": category,
                "hull_id": hull_id,
                "hull_name": name,
                "count": count,
                "games": len(combo_games[(category, hull_id, name)]),
            }
            for (category, hull_id, name), count in sorted(
                combos.items(), key=lambda item: (-item[1], item[0][0], item[0][1], item[0][2])
            )
        ],
    }
