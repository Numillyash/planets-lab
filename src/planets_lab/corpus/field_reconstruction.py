from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .normalizer import ArchiveTurnSnapshot
from .reconstruction import PerspectiveRecord, group_perspective_records


SHIP_FIELDS = (
    "ownerid",
    "hullid",
    "x",
    "y",
    "warp",
    "targetx",
    "targety",
    "engineid",
    "beamid",
    "torpedoid",
    "beams",
    "torps",
    "bays",
    "ammo",
    "damage",
    "crew",
    "neutronium",
    "duranium",
    "tritanium",
    "molybdenum",
    "supplies",
    "clans",
    "megacredits",
)

PLANET_FIELDS = (
    "ownerid",
    "x",
    "y",
    "temp",
    "neutronium",
    "duranium",
    "tritanium",
    "molybdenum",
    "supplies",
    "clans",
    "megacredits",
    "factories",
    "mines",
    "defense",
    "groundneutronium",
    "groundduranium",
    "groundtritanium",
    "groundmolybdenum",
    "densityneutronium",
    "densityduranium",
    "densitytritanium",
    "densitymolybdenum",
    "nativeclans",
    "nativetype",
    "nativegovernment",
    "nativehappypoints",
    "nativetaxrate",
    "colonisthappypoints",
    "colonisttaxrate",
)

STARBASE_FIELDS = (
    "fighters",
    "defense",
    "damage",
    "hulltechlevel",
    "enginetechlevel",
    "beamtechlevel",
    "torptechlevel",
    "isbuilding",
    "buildhullid",
    "buildengineid",
    "buildbeamid",
    "buildbeamcount",
    "buildtorpedoid",
    "buildtorpcount",
)

FIELDS_BY_KIND = {
    "planet": PLANET_FIELDS,
    "ship": SHIP_FIELDS,
    "starbase": STARBASE_FIELDS,
}

# These fields describe structural identity/geometry that is not expected to
# change during a game. Stale observations may therefore fill them when no
# current record exists. Dynamic state deliberately has no stale fallback.
STATIC_FIELDS = {
    "planet": frozenset({"x", "y"}),
    "ship": frozenset({"hullid"}),
    "starbase": frozenset(),
}

# Negative historical wire values represent unknown/hidden numeric state for
# these player-perspective records. Zero remains a real observed value.
NUMERIC_UNKNOWN_FIELDS = frozenset(
    set(SHIP_FIELDS) | set(PLANET_FIELDS) | set(STARBASE_FIELDS)
)


@dataclass(frozen=True, slots=True)
class FieldResolution:
    field: str
    status: str
    value: Any
    authoritative_player_id: int | None
    source_players: tuple[int, ...]
    source_infoturn: int | None
    alternatives: tuple[Any, ...] = ()


@dataclass(frozen=True, slots=True)
class PartialEntityResolution:
    kind: str
    entity_id: int
    archive_turn: int
    embedded_turn: int
    owner_hint: int | None
    current_players: tuple[int, ...]
    stale_players: tuple[int, ...]
    fields: Mapping[str, FieldResolution]

    @property
    def conflict_fields(self) -> tuple[str, ...]:
        return tuple(
            field
            for field, resolution in self.fields.items()
            if resolution.status == "current_conflict"
        )

    @property
    def unresolved_dynamic_fields(self) -> tuple[str, ...]:
        static = STATIC_FIELDS[self.kind]
        return tuple(
            field
            for field, resolution in self.fields.items()
            if field not in static and resolution.status == "no_current"
        )


@dataclass(frozen=True, slots=True)
class FieldReconstructionSummary:
    entities: tuple[PartialEntityResolution, ...]
    field_status_counts: Mapping[str, int]
    kind_field_status_counts: Mapping[str, Mapping[str, int]]
    entities_with_conflicts: int
    entities_with_unresolved_dynamic: int


# A corpus evaluator commonly asks for the same reconstruction several times:
# readiness, baseline movement and later context layers historically each built
# it independently. Keep exactly one in-process result by object identity. The
# strong reference to the snapshot tuple prevents Python id reuse and bounds
# memory to one game's reconstruction. This is deliberately not a persistent
# cache: code/schema changes cannot make a stale result survive a process.
_LAST_RECONSTRUCTION_RECORDS: tuple[ArchiveTurnSnapshot, ...] | None = None
_LAST_RECONSTRUCTION_SUMMARY: FieldReconstructionSummary | None = None


def clear_reconstruction_cache() -> None:
    global _LAST_RECONSTRUCTION_RECORDS, _LAST_RECONSTRUCTION_SUMMARY
    _LAST_RECONSTRUCTION_RECORDS = None
    _LAST_RECONSTRUCTION_SUMMARY = None


def _intish(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _known_value(field: str, raw: Mapping[str, Any]) -> Any:
    if field not in raw:
        return None
    value = raw[field]
    if field in NUMERIC_UNKNOWN_FIELDS:
        number = _intish(value)
        if number is not None:
            if number < 0:
                return None
            return number
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return None


def _positive_owner(records: Sequence[PerspectiveRecord]) -> int | None:
    owners: set[int] = set()
    for record in records:
        owner = _intish(record.raw.get("ownerid", record.raw.get("owner_id")))
        if owner is not None and owner > 0:
            owners.add(owner)
    return next(iter(owners)) if len(owners) == 1 else None


def _split(records: Sequence[PerspectiveRecord]) -> tuple[tuple[PerspectiveRecord, ...], tuple[PerspectiveRecord, ...]]:
    current = tuple(record for record in records if record.is_current)
    stale = tuple(record for record in records if not record.is_current)
    return current, stale


def _consensus_values(
    records: Sequence[PerspectiveRecord], field: str
) -> tuple[tuple[Any, ...], tuple[int, ...]]:
    by_value: dict[Any, set[int]] = defaultdict(set)
    for record in records:
        value = _known_value(field, record.raw)
        if value is None:
            continue
        by_value[value].add(record.player_id)
    values = tuple(sorted(by_value, key=repr))
    players = tuple(sorted({p for group in by_value.values() for p in group}))
    return values, players


def _resolve_field(
    *,
    kind: str,
    field: str,
    current: Sequence[PerspectiveRecord],
    stale: Sequence[PerspectiveRecord],
    owner_hint: int | None,
) -> FieldResolution:
    if owner_hint is not None:
        for record in current:
            if record.player_id != owner_hint:
                continue
            value = _known_value(field, record.raw)
            if value is not None:
                return FieldResolution(
                    field=field,
                    status="owner_perspective",
                    value=value,
                    authoritative_player_id=owner_hint,
                    source_players=(owner_hint,),
                    source_infoturn=record.infoturn,
                )

    values, players = _consensus_values(current, field)
    if len(values) == 1:
        infoturns = {
            record.infoturn
            for record in current
            if _known_value(field, record.raw) == values[0]
        }
        source_infoturn = next(iter(infoturns)) if len(infoturns) == 1 else None
        return FieldResolution(
            field=field,
            status="current_consensus",
            value=values[0],
            authoritative_player_id=None,
            source_players=players,
            source_infoturn=source_infoturn,
        )
    if len(values) > 1:
        return FieldResolution(
            field=field,
            status="current_conflict",
            value=None,
            authoritative_player_id=None,
            source_players=players,
            source_infoturn=None,
            alternatives=values,
        )

    if field in STATIC_FIELDS[kind] and stale:
        known_stale = [record for record in stale if _known_value(field, record.raw) is not None]
        if known_stale:
            newest = max(
                (record.infoturn for record in known_stale if record.infoturn is not None),
                default=None,
            )
            candidates = (
                tuple(record for record in known_stale if record.infoturn == newest)
                if newest is not None
                else tuple(known_stale)
            )
            stale_values, stale_players = _consensus_values(candidates, field)
            if len(stale_values) == 1:
                return FieldResolution(
                    field=field,
                    status="stale_static_consensus",
                    value=stale_values[0],
                    authoritative_player_id=None,
                    source_players=stale_players,
                    source_infoturn=newest,
                )
            if len(stale_values) > 1:
                return FieldResolution(
                    field=field,
                    status="current_conflict",
                    value=None,
                    authoritative_player_id=None,
                    source_players=stale_players,
                    source_infoturn=newest,
                    alternatives=stale_values,
                )

    return FieldResolution(
        field=field,
        status="no_current",
        value=None,
        authoritative_player_id=None,
        source_players=(),
        source_infoturn=None,
    )


def _embedded_turn(records: Sequence[PerspectiveRecord]) -> int:
    turns = {record.embedded_turn for record in records}
    if len(turns) != 1:
        raise ValueError(f"cross-perspective records disagree on embedded turn: {sorted(turns)}")
    return next(iter(turns))


def _resolve_entity(
    *,
    kind: str,
    archive_turn: int,
    entity_id: int,
    records: Sequence[PerspectiveRecord],
    owner_hint: int | None = None,
) -> PartialEntityResolution:
    current, stale = _split(records)
    inferred_owner = owner_hint if owner_hint is not None else _positive_owner(current)
    fields = {
        field: _resolve_field(
            kind=kind,
            field=field,
            current=current,
            stale=stale,
            owner_hint=inferred_owner,
        )
        for field in FIELDS_BY_KIND[kind]
    }
    return PartialEntityResolution(
        kind=kind,
        entity_id=entity_id,
        archive_turn=archive_turn,
        embedded_turn=_embedded_turn(records),
        owner_hint=inferred_owner,
        current_players=tuple(sorted(record.player_id for record in current)),
        stale_players=tuple(sorted(record.player_id for record in stale)),
        fields=fields,
    )


def reconstruct_fields(
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> FieldReconstructionSummary:
    global _LAST_RECONSTRUCTION_RECORDS, _LAST_RECONSTRUCTION_SUMMARY

    records = snapshots if isinstance(snapshots, tuple) else tuple(snapshots)
    if records is _LAST_RECONSTRUCTION_RECORDS and _LAST_RECONSTRUCTION_SUMMARY is not None:
        return _LAST_RECONSTRUCTION_SUMMARY

    groups = {
        kind: group_perspective_records(records, kind)
        for kind in ("planet", "ship", "starbase")
    }

    entities: list[PartialEntityResolution] = []
    planet_owner_by_turn: dict[tuple[int, int], int | None] = {}

    for (archive_turn, entity_id), grouped in sorted(groups["planet"].items()):
        entity = _resolve_entity(
            kind="planet",
            archive_turn=archive_turn,
            entity_id=entity_id,
            records=grouped,
        )
        entities.append(entity)
        owner_field = entity.fields["ownerid"]
        owner = _intish(owner_field.value)
        planet_owner_by_turn[(archive_turn, entity_id)] = owner if owner and owner > 0 else None

    for (archive_turn, entity_id), grouped in sorted(groups["ship"].items()):
        entities.append(
            _resolve_entity(
                kind="ship",
                archive_turn=archive_turn,
                entity_id=entity_id,
                records=grouped,
            )
        )

    for (archive_turn, entity_id), grouped in sorted(groups["starbase"].items()):
        entities.append(
            _resolve_entity(
                kind="starbase",
                archive_turn=archive_turn,
                entity_id=entity_id,
                records=grouped,
                owner_hint=planet_owner_by_turn.get((archive_turn, entity_id)),
            )
        )

    field_counts = Counter()
    kind_field_counts: dict[str, Counter[str]] = defaultdict(Counter)
    entities_with_conflicts = 0
    entities_with_unresolved_dynamic = 0
    for entity in entities:
        if entity.conflict_fields:
            entities_with_conflicts += 1
        if entity.unresolved_dynamic_fields:
            entities_with_unresolved_dynamic += 1
        for resolution in entity.fields.values():
            field_counts[resolution.status] += 1
            kind_field_counts[entity.kind][resolution.status] += 1

    summary = FieldReconstructionSummary(
        entities=tuple(entities),
        field_status_counts=dict(sorted(field_counts.items())),
        kind_field_status_counts={
            kind: dict(sorted(counts.items()))
            for kind, counts in sorted(kind_field_counts.items())
        },
        entities_with_conflicts=entities_with_conflicts,
        entities_with_unresolved_dynamic=entities_with_unresolved_dynamic,
    )
    _LAST_RECONSTRUCTION_RECORDS = records
    _LAST_RECONSTRUCTION_SUMMARY = summary
    return summary
