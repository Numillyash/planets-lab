from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .field_reconstruction import PartialEntityResolution, reconstruct_fields
from .normalizer import ArchiveTurnSnapshot


READY = "ready"
PARTIAL = "partial"
CONFLICT = "conflict"
STALE = "stale"

RESOLVED_FIELD_STATUSES = frozenset(
    {"owner_perspective", "current_consensus", "stale_static_consensus"}
)


@dataclass(frozen=True, slots=True)
class ReadinessProfile:
    name: str
    kind: str
    before_fields: tuple[str, ...]
    after_fields: tuple[str, ...]
    description: str


MOVEMENT_GEOMETRY = ReadinessProfile(
    name="movement_geometry",
    kind="ship",
    before_fields=("ownerid", "hullid", "x", "y", "warp", "targetx", "targety"),
    after_fields=("ownerid", "x", "y"),
    description=(
        "Fields required to classify and compare ship movement geometry. "
        "This is a prerequisite profile, not proof that a transition is an ordinary move."
    ),
)

MOVEMENT_FUEL_MASS = ReadinessProfile(
    name="movement_fuel_mass",
    kind="ship",
    before_fields=(
        "ownerid",
        "hullid",
        "x",
        "y",
        "warp",
        "targetx",
        "targety",
        "engineid",
        "beams",
        "torps",
        "bays",
        "ammo",
        "neutronium",
        "duranium",
        "tritanium",
        "molybdenum",
        "supplies",
        "clans",
    ),
    after_fields=("ownerid", "x", "y", "neutronium"),
    description=(
        "Fields required by current normal-movement geometry plus fuel/movement-mass "
        "validation. Beam and torpedo component ids are conditionally required when "
        "the corresponding fitted counts are positive."
    ),
)

READINESS_PROFILES: Mapping[str, ReadinessProfile] = {
    profile.name: profile for profile in (MOVEMENT_GEOMETRY, MOVEMENT_FUEL_MASS)
}


@dataclass(frozen=True, slots=True)
class TransitionReadiness:
    profile: str
    kind: str
    entity_id: int
    before_archive_turn: int
    after_archive_turn: int
    before_embedded_turn: int
    after_embedded_turn: int
    status: str
    issues: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReadinessSummary:
    profile: str
    valid_turn_pairs: int
    skipped_turn_pairs: int
    evaluated_entities: int
    status_counts: Mapping[str, int]
    issue_counts: Mapping[str, int]
    results: tuple[TransitionReadiness, ...]


def _intish(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _archive_embedded_turns(
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> Mapping[int, tuple[int, ...]]:
    grouped: dict[int, set[int]] = defaultdict(set)
    for snapshot in snapshots:
        grouped[snapshot.archive_turn].add(snapshot.embedded_turn)
    return {
        archive_turn: tuple(sorted(values))
        for archive_turn, values in sorted(grouped.items())
    }


def _turn_pairs(
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> tuple[tuple[tuple[int, int, int, int], ...], int]:
    turns = _archive_embedded_turns(snapshots)
    archive_turns = sorted(turns)
    valid: list[tuple[int, int, int, int]] = []
    skipped = 0
    for before_archive, after_archive in zip(archive_turns, archive_turns[1:]):
        if after_archive != before_archive + 1:
            skipped += 1
            continue
        before_embedded = turns[before_archive]
        after_embedded = turns[after_archive]
        if (
            len(before_embedded) != 1
            or len(after_embedded) != 1
            or after_embedded[0] != before_embedded[0] + 1
        ):
            skipped += 1
            continue
        valid.append(
            (before_archive, after_archive, before_embedded[0], after_embedded[0])
        )
    return tuple(valid), skipped


def _entity_map(
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> Mapping[tuple[str, int, int], PartialEntityResolution]:
    summary = reconstruct_fields(snapshots)
    return {
        (entity.kind, entity.archive_turn, entity.entity_id): entity
        for entity in summary.entities
    }


def _field_issue(
    *,
    entity: PartialEntityResolution,
    side: str,
    field: str,
) -> tuple[str | None, str | None]:
    resolution = entity.fields[field]
    if resolution.status in RESOLVED_FIELD_STATUSES:
        return None, None
    issue = f"{side}.{entity.kind}.{field}.{resolution.status}"
    if resolution.status == "current_conflict":
        return CONFLICT, issue
    if resolution.status == "no_current":
        if not entity.current_players and entity.stale_players:
            return STALE, issue
        return PARTIAL, issue
    return PARTIAL, issue


def _resolved_value(entity: PartialEntityResolution, field: str) -> Any:
    resolution = entity.fields[field]
    if resolution.status not in RESOLVED_FIELD_STATUSES:
        return None
    return resolution.value


def _fuel_mass_conditional_fields(
    before: PartialEntityResolution,
) -> tuple[str, ...]:
    required: list[str] = []
    beams = _intish(_resolved_value(before, "beams"))
    torps = _intish(_resolved_value(before, "torps"))
    if beams is not None and beams > 0:
        required.append("beamid")
    if torps is not None and torps > 0:
        required.append("torpedoid")
    return tuple(required)


def _fuel_mass_semantic_issues(
    before: PartialEntityResolution,
) -> tuple[str, ...]:
    torps = _intish(_resolved_value(before, "torps"))
    bays = _intish(_resolved_value(before, "bays"))
    ammo = _intish(_resolved_value(before, "ammo"))
    if (
        torps is not None
        and bays is not None
        and ammo is not None
        and torps > 0
        and bays > 0
        and ammo > 0
    ):
        return ("before.ship.ammo.ambiguous_torpedo_or_fighter_ammo",)
    return ()


def _status_from_issues(issue_statuses: Sequence[str]) -> str:
    if CONFLICT in issue_statuses:
        return CONFLICT
    if STALE in issue_statuses:
        return STALE
    if PARTIAL in issue_statuses:
        return PARTIAL
    return READY


def evaluate_readiness(
    snapshots: Sequence[ArchiveTurnSnapshot],
    profile: ReadinessProfile,
) -> ReadinessSummary:
    records = tuple(snapshots)
    entities = _entity_map(records)
    turn_pairs, skipped_turn_pairs = _turn_pairs(records)
    results: list[TransitionReadiness] = []
    statuses: Counter[str] = Counter()
    issues: Counter[str] = Counter()

    for before_archive, after_archive, before_embedded, after_embedded in turn_pairs:
        before_entities = sorted(
            (
                entity
                for (kind, archive_turn, _), entity in entities.items()
                if kind == profile.kind and archive_turn == before_archive
            ),
            key=lambda entity: entity.entity_id,
        )
        for before in before_entities:
            after = entities.get((profile.kind, after_archive, before.entity_id))
            issue_statuses: list[str] = []
            entity_issues: list[str] = []

            if after is None:
                issue_statuses.append(PARTIAL)
                entity_issues.append(f"after.{profile.kind}.missing_entity")
            else:
                for side, entity, required_fields in (
                    ("before", before, profile.before_fields),
                    ("after", after, profile.after_fields),
                ):
                    for field in required_fields:
                        issue_status, issue = _field_issue(
                            entity=entity,
                            side=side,
                            field=field,
                        )
                        if issue_status is not None:
                            issue_statuses.append(issue_status)
                        if issue is not None:
                            entity_issues.append(issue)

                if profile.name == MOVEMENT_FUEL_MASS.name:
                    for field in _fuel_mass_conditional_fields(before):
                        issue_status, issue = _field_issue(
                            entity=before,
                            side="before",
                            field=field,
                        )
                        if issue_status is not None:
                            issue_statuses.append(issue_status)
                        if issue is not None:
                            entity_issues.append(issue)
                    semantic_issues = _fuel_mass_semantic_issues(before)
                    if semantic_issues:
                        issue_statuses.append(PARTIAL)
                        entity_issues.extend(semantic_issues)

                before_owner = _intish(_resolved_value(before, "ownerid"))
                after_owner = _intish(_resolved_value(after, "ownerid"))
                if (
                    before_owner is not None
                    and after_owner is not None
                    and before_owner != after_owner
                ):
                    issue_statuses.append(PARTIAL)
                    entity_issues.append("transition.ship.owner_changed")

            status = _status_from_issues(issue_statuses)
            statuses[status] += 1
            for issue in sorted(set(entity_issues)):
                issues[issue] += 1
            results.append(
                TransitionReadiness(
                    profile=profile.name,
                    kind=profile.kind,
                    entity_id=before.entity_id,
                    before_archive_turn=before_archive,
                    after_archive_turn=after_archive,
                    before_embedded_turn=before_embedded,
                    after_embedded_turn=after_embedded,
                    status=status,
                    issues=tuple(sorted(set(entity_issues))),
                )
            )

    return ReadinessSummary(
        profile=profile.name,
        valid_turn_pairs=len(turn_pairs),
        skipped_turn_pairs=skipped_turn_pairs,
        evaluated_entities=len(results),
        status_counts=dict(sorted(statuses.items())),
        issue_counts=dict(sorted(issues.items())),
        results=tuple(results),
    )


def evaluate_default_profiles(
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> Mapping[str, ReadinessSummary]:
    records = tuple(snapshots)
    return {
        name: evaluate_readiness(records, profile)
        for name, profile in READINESS_PROFILES.items()
    }
