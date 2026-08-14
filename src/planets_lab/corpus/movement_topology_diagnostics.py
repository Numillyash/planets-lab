from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import hypot
from typing import Any

from planets_lab.validation.movement_geometry import MovementSample, host_major_minor_destination

from .archive import read_archive_members, turn_members
from .movement_context import MOVE_MOST_CANDIDATE, MovementMissionConvention, _classify_owner_record
from .movement_differential import (
    GEOMETRY_EXPLAINED_CATEGORIES,
    _entity_map,
    _intish,
    _movement_category,
    _planet_tuples_by_turn,
    _raw_owner,
    _resolved_owner_from_current,
    _resolved_value,
)
from .normalizer import ArchiveTurnSnapshot, _decode_member_json
from .readiness import MOVEMENT_GEOMETRY, READY, evaluate_readiness
from .reconstruction import group_perspective_records


@dataclass(frozen=True, slots=True)
class MapTopologyEvidence:
    sphere: bool | None
    mapwidth: int | None
    mapheight: int | None
    mapshape: int | str | None
    first_member: str
    last_member: str
    stable: bool
    first_candidates: Mapping[str, Any]
    last_candidates: Mapping[str, Any]


_TOPOLOGY_NAMES = frozenset({"sphere", "mapwidth", "mapheight", "mapshape"})


def _safe_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (bool, int, float, str))


def _topology_candidates(value: Any, *, prefix: str = "") -> dict[str, Any]:
    """Return privacy-safe topology-like scalar settings from settings/game trees."""
    result: dict[str, Any] = {}
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            path = f"{prefix}.{key_text}" if prefix else key_text
            normalized = key_text.lower().replace("_", "").replace("-", "")
            if normalized in _TOPOLOGY_NAMES and _safe_scalar(child):
                result[path] = child
            if isinstance(child, (Mapping, list, tuple)):
                result.update(_topology_candidates(child, prefix=path))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            if isinstance(child, (Mapping, list, tuple)):
                path = f"{prefix}[{index}]" if prefix else f"[{index}]"
                result.update(_topology_candidates(child, prefix=path))
    return result


def _leaf_values(candidates: Mapping[str, Any], leaf: str) -> tuple[Any, ...]:
    result: list[Any] = []
    for path, value in candidates.items():
        normalized = path.rsplit(".", 1)[-1].lower().replace("_", "").replace("-", "")
        if normalized == leaf:
            result.append(value)
    return tuple(result)


def _unique_int(candidates: Mapping[str, Any], leaf: str) -> int | None:
    values = {_intish(value) for value in _leaf_values(candidates, leaf)}
    values.discard(None)
    return next(iter(values)) if len(values) == 1 else None


def _unique_bool(candidates: Mapping[str, Any], leaf: str) -> bool | None:
    values: set[bool] = set()
    for value in _leaf_values(candidates, leaf):
        if isinstance(value, bool):
            values.add(value)
        elif isinstance(value, int) and value in (0, 1):
            values.add(bool(value))
        elif isinstance(value, str) and value.strip().lower() in {"true", "false"}:
            values.add(value.strip().lower() == "true")
    return next(iter(values)) if len(values) == 1 else None


def _unique_shape(candidates: Mapping[str, Any]) -> int | str | None:
    values = set(_leaf_values(candidates, "mapshape"))
    return next(iter(values)) if len(values) == 1 else None


def extract_map_topology(archive_data: bytes) -> MapTopologyEvidence:
    members = turn_members(archive_data)
    if not members:
        raise ValueError("archive contains no .trn members")
    first = members[0]
    last = members[-1]
    raw_by_name = read_archive_members(archive_data, [first.name, last.name])

    parsed: dict[str, Mapping[str, Any]] = {}
    for member in (first, last):
        payload, _ = _decode_member_json(raw_by_name[member.name], member)
        parsed[member.name] = payload

    def candidates(payload: Mapping[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for root_name in ("settings", "game"):
            root = payload.get(root_name)
            if isinstance(root, (Mapping, list, tuple)):
                result.update(_topology_candidates(root, prefix=root_name))
        return dict(sorted(result.items()))

    first_candidates = candidates(parsed[first.name])
    last_candidates = candidates(parsed[last.name])
    sphere_first = _unique_bool(first_candidates, "sphere")
    sphere_last = _unique_bool(last_candidates, "sphere")
    width_first = _unique_int(first_candidates, "mapwidth")
    width_last = _unique_int(last_candidates, "mapwidth")
    height_first = _unique_int(first_candidates, "mapheight")
    height_last = _unique_int(last_candidates, "mapheight")
    shape_first = _unique_shape(first_candidates)
    shape_last = _unique_shape(last_candidates)

    return MapTopologyEvidence(
        sphere=sphere_first if sphere_first == sphere_last else None,
        mapwidth=width_first if width_first == width_last else None,
        mapheight=height_first if height_first == height_last else None,
        mapshape=shape_first if shape_first == shape_last else None,
        first_member=first.name,
        last_member=last.name,
        stable=first_candidates == last_candidates,
        first_candidates=first_candidates,
        last_candidates=last_candidates,
    )


def wrapped_delta(start: int, end: int, period: int) -> int:
    if period <= 0:
        raise ValueError("wrap period must be positive")
    raw = end - start
    candidates = (raw - period, raw, raw + period)
    return min(candidates, key=lambda value: (abs(value), abs(value - raw)))


def _wrapped_point_near(
    origin: tuple[int, int],
    point: tuple[int, int],
    *,
    width: int,
    height: int,
) -> tuple[int, int]:
    return (
        origin[0] + wrapped_delta(origin[0], point[0], width),
        origin[1] + wrapped_delta(origin[1], point[1], height),
    )


def _wrapped_planets_near(
    origin: tuple[int, int],
    planets: Sequence[tuple[int, int, int]],
    *,
    width: int,
    height: int,
) -> tuple[tuple[int, int, int], ...]:
    result: list[tuple[int, int, int]] = []
    for planet_id, x, y in planets:
        px, py = _wrapped_point_near(origin, (x, y), width=width, height=height)
        result.append((planet_id, px, py))
    return tuple(result)


def sphere_adjusted_sample(sample: MovementSample, *, width: int, height: int) -> MovementSample:
    origin = (sample.x, sample.y)
    target = _wrapped_point_near(origin, (sample.target_x, sample.target_y), width=width, height=height)
    observed = _wrapped_point_near(origin, sample.observed_destination, width=width, height=height)
    return MovementSample(
        turn=sample.turn,
        ship_id=sample.ship_id,
        x=sample.x,
        y=sample.y,
        target_x=target[0],
        target_y=target[1],
        warp=sample.warp,
        next_x=observed[0],
        next_y=observed[1],
        gravitonic=sample.gravitonic,
        game_id=sample.game_id,
        player_slot_id=sample.player_slot_id,
        hull_id=sample.hull_id,
        mission=sample.mission,
        damage=sample.damage,
        friendly_code=sample.friendly_code,
    )


def evaluate_sphere_geometry_effect(
    snapshots: Sequence[ArchiveTurnSnapshot],
    *,
    width: int,
    height: int,
    convention: MovementMissionConvention = MovementMissionConvention(),
) -> dict[str, Any]:
    records = tuple(snapshots)
    readiness = evaluate_readiness(records, MOVEMENT_GEOMETRY)
    entities = _entity_map(records)
    ship_groups = group_perspective_records(records, "ship")
    planets_by_turn = _planet_tuples_by_turn(entities)

    baseline_unresolved = 0
    sphere_explained = 0
    sphere_still_unresolved = 0
    baseline_to_sphere: Counter[str] = Counter()
    hulls: Counter[int] = Counter()

    for transition in readiness.results:
        if transition.status != READY:
            continue
        group = ship_groups.get((transition.before_archive_turn, transition.entity_id), ())
        owner_id, issue = _resolved_owner_from_current(group)
        if issue is not None or owner_id is None or owner_id <= 0:
            continue
        owner_records = tuple(
            record for record in group if record.is_current and record.player_id == owner_id
        )
        if len(owner_records) != 1 or _raw_owner(owner_records[0]) != owner_id:
            continue
        if _classify_owner_record(owner_records[0], convention=convention) != MOVE_MOST_CANDIDATE:
            continue

        before = entities[("ship", transition.before_archive_turn, transition.entity_id)]
        after = entities[("ship", transition.after_archive_turn, transition.entity_id)]
        values = tuple(
            _intish(_resolved_value(entity, field))
            for entity, field in (
                (before, "x"), (before, "y"), (before, "targetx"), (before, "targety"),
                (before, "warp"), (after, "x"), (after, "y"), (before, "hullid"),
            )
        )
        x, y, target_x, target_y, warp, next_x, next_y, hull_id = values
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
            continue
        baseline_unresolved += 1

        adjusted = sphere_adjusted_sample(sample, width=width, height=height)
        wrapped_planets = _wrapped_planets_near(
            (sample.x, sample.y), planets, width=width, height=height
        )
        sphere_category = _movement_category(adjusted, planets=wrapped_planets)
        baseline_to_sphere[f"{baseline}->{sphere_category}"] += 1
        if sphere_category in GEOMETRY_EXPLAINED_CATEGORIES:
            sphere_explained += 1
            if hull_id is not None:
                hulls[hull_id] += 1
        else:
            sphere_still_unresolved += 1

    if sphere_explained + sphere_still_unresolved != baseline_unresolved:
        raise AssertionError("sphere geometry accounting is not closed")
    return {
        "baseline_unresolved": baseline_unresolved,
        "sphere_explained": sphere_explained,
        "sphere_still_unresolved": sphere_still_unresolved,
        "baseline_to_sphere_counts": dict(sorted(baseline_to_sphere.items())),
        "sphere_explained_hull_counts": {str(k): v for k, v in sorted(hulls.items())},
    }
