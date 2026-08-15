from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from planets_lab.rules.movement import WarpWellAmbiguityError, warp_well_planet_id
from planets_lab.validation.movement_geometry import MovementSample, host_major_minor_destination

from .archive import read_archive_members, turn_members
from .movement_context import MOVE_MOST_CANDIDATE, MovementMissionConvention, _classify_owner_record
from .movement_differential import (
    _entity_map,
    _intish,
    _movement_category,
    _planet_tuples_by_turn,
    _resolved_value,
)
from .movement_residual_context import _owner_record
from .normalizer import ArchiveTurnSnapshot, _decode_member_json
from .readiness import MOVEMENT_GEOMETRY, READY, evaluate_readiness
from .reconstruction import group_perspective_records

WARP_WELL_MATCH_CATEGORIES = frozenset(
    {
        "reachable_warp_well_match",
        "partial_host_major_minor_warp_well_match",
    }
)


@dataclass(frozen=True, slots=True)
class WarpWellAuditSummary:
    move_most_candidates: int
    warp_well_matches: int
    valid_ordinary_planet_matches: int
    invalid_debris_planet_matches: int
    disabled_warp_well_matches: int
    unknown_context_matches: int
    category_counts: Mapping[str, int]
    debris_value_counts: Mapping[int, int]


def extract_nowarpwells(archive_data: bytes) -> tuple[bool | None, str]:
    """Return the historical ``settings.nowarpwells`` consensus.

    Only the boolean mechanical setting is retained. Missing, malformed or
    conflicting settings fail closed to ``None`` for the audit.
    """

    members = turn_members(archive_data)
    raw_members = read_archive_members(archive_data, [member.name for member in members])
    values: set[bool] = set()
    saw_missing = False

    for member in members:
        parsed, _ = _decode_member_json(raw_members[member.name], member)
        settings = parsed.get("settings")
        if not isinstance(settings, Mapping) or "nowarpwells" not in settings:
            saw_missing = True
            continue
        raw = settings.get("nowarpwells")
        if isinstance(raw, bool):
            values.add(raw)
        elif isinstance(raw, int) and raw in (0, 1):
            values.add(bool(raw))
        else:
            saw_missing = True

    if len(values) != 1 or saw_missing:
        return None, "unknown_or_conflict"
    value = next(iter(values))
    return value, "disabled" if value else "enabled"


def _planet_debris_by_turn(
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> Mapping[tuple[int, int], int | None]:
    groups = group_perspective_records(tuple(snapshots), "planet")
    result: dict[tuple[int, int], int | None] = {}
    for key, records in groups.items():
        values: set[int] = set()
        malformed = False
        for record in records:
            if "debrisdisk" not in record.raw:
                malformed = True
                continue
            value = _intish(record.raw.get("debrisdisk"))
            if value is None or value < 0:
                malformed = True
                continue
            values.add(value)
        result[key] = next(iter(values)) if len(values) == 1 and not malformed else None
    return result


def _expected_pre_well_endpoint(sample: MovementSample, category: str) -> tuple[int, int]:
    if category == "reachable_warp_well_match":
        return sample.target_x, sample.target_y
    if category == "partial_host_major_minor_warp_well_match":
        return host_major_minor_destination(sample)
    raise ValueError(f"not a warp-well match category: {category}")


def audit_movement_warp_wells(
    snapshots: Sequence[ArchiveTurnSnapshot],
    *,
    nowarpwells: bool | None,
    convention: MovementMissionConvention = MovementMissionConvention(),
) -> WarpWellAuditSummary:
    records = tuple(snapshots)
    readiness = evaluate_readiness(records, MOVEMENT_GEOMETRY)
    entities = _entity_map(records)
    ship_groups = group_perspective_records(records, "ship")
    # The audit intentionally reproduces the pre-fix candidate universe so it
    # can continue reporting historical false-positive well matches after the
    # production differential starts filtering debris objects.
    planets_by_turn = _planet_tuples_by_turn(entities, include_ineligible=True)
    debris_by_turn = _planet_debris_by_turn(records)

    categories: Counter[str] = Counter()
    debris_values: Counter[int] = Counter()
    move_most_candidates = 0
    valid = 0
    invalid_debris = 0
    disabled = 0
    unknown = 0

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
        values = (
            _intish(_resolved_value(before, "x")),
            _intish(_resolved_value(before, "y")),
            _intish(_resolved_value(before, "targetx")),
            _intish(_resolved_value(before, "targety")),
            _intish(_resolved_value(before, "warp")),
            _intish(_resolved_value(after, "x")),
            _intish(_resolved_value(after, "y")),
        )
        if any(value is None for value in values):
            continue
        x, y, target_x, target_y, warp, next_x, next_y = values
        hull_id = _intish(_resolved_value(before, "hullid"))
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
        category = _movement_category(sample, planets=planets)
        if category not in WARP_WELL_MATCH_CATEGORIES:
            continue
        categories[category] += 1

        endpoint = _expected_pre_well_endpoint(sample, category)
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
            unknown += 1
            continue
        if planet_id is None:
            unknown += 1
            continue

        debris = debris_by_turn.get((transition.before_archive_turn, planet_id))
        if debris is None or nowarpwells is None:
            unknown += 1
            continue
        debris_values[debris] += 1
        if nowarpwells:
            disabled += 1
        elif debris != 0:
            invalid_debris += 1
        else:
            valid += 1

    matches = sum(categories.values())
    if valid + invalid_debris + disabled + unknown != matches:
        raise AssertionError("warp-well audit accounting is not closed")

    return WarpWellAuditSummary(
        move_most_candidates=move_most_candidates,
        warp_well_matches=matches,
        valid_ordinary_planet_matches=valid,
        invalid_debris_planet_matches=invalid_debris,
        disabled_warp_well_matches=disabled,
        unknown_context_matches=unknown,
        category_counts=dict(sorted(categories.items())),
        debris_value_counts=dict(sorted(debris_values.items())),
    )
