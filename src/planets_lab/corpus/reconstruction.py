from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .normalizer import ArchiveTurnSnapshot


SHIP_COMPARE_FIELDS = (
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

NONNEGATIVE_UNKNOWN_FIELDS = frozenset(SHIP_COMPARE_FIELDS)


@dataclass(frozen=True, slots=True)
class PerspectiveRecord:
    player_id: int
    archive_turn: int
    embedded_turn: int
    infoturn: int | None
    raw: Mapping[str, Any]

    @property
    def is_current(self) -> bool:
        return self.infoturn == self.embedded_turn


@dataclass(frozen=True, slots=True)
class EntityResolution:
    kind: str
    entity_id: int
    archive_turn: int
    embedded_turn: int
    status: str
    authoritative_player_id: int | None
    current_players: tuple[int, ...]
    stale_players: tuple[int, ...]
    conflicts: Mapping[str, tuple[Any, ...]]
    record: Mapping[str, Any] | None


@dataclass(frozen=True, slots=True)
class ReconstructionSummary:
    resolutions: tuple[EntityResolution, ...]
    status_counts: Mapping[str, int]
    kind_status_counts: Mapping[str, Mapping[str, int]]


def _intish(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _record_infoturn(raw: Mapping[str, Any]) -> int | None:
    return _intish(raw.get("infoturn"))


def _owner_id(raw: Mapping[str, Any]) -> int | None:
    value = raw.get("ownerid", raw.get("owner_id"))
    owner = _intish(value)
    return owner if owner and owner > 0 else None


def _entity_id(kind: str, raw: Mapping[str, Any]) -> int | None:
    if kind == "starbase":
        return _intish(raw.get("planetid", raw.get("planet_id")))
    return _intish(raw.get("id"))


def _records_for_snapshot(
    snapshot: ArchiveTurnSnapshot,
    kind: str,
) -> tuple[PerspectiveRecord, ...]:
    payload_key = {"planet": "planets", "ship": "ships", "starbase": "starbases"}[kind]
    value = snapshot.mechanics_payload.get(payload_key, [])
    if not isinstance(value, list):
        return ()
    result: list[PerspectiveRecord] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        result.append(
            PerspectiveRecord(
                player_id=snapshot.player_id,
                archive_turn=snapshot.archive_turn,
                embedded_turn=snapshot.embedded_turn,
                infoturn=_record_infoturn(raw),
                raw=raw,
            )
        )
    return tuple(result)


def group_perspective_records(
    snapshots: Sequence[ArchiveTurnSnapshot],
    kind: str,
) -> Mapping[tuple[int, int], tuple[PerspectiveRecord, ...]]:
    if kind not in {"planet", "ship", "starbase"}:
        raise ValueError(f"unsupported entity kind {kind!r}")
    grouped: dict[tuple[int, int], list[PerspectiveRecord]] = defaultdict(list)
    for snapshot in snapshots:
        for record in _records_for_snapshot(snapshot, kind):
            entity_id = _entity_id(kind, record.raw)
            if entity_id is None:
                continue
            grouped[(snapshot.archive_turn, entity_id)].append(record)
    return {
        key: tuple(sorted(records, key=lambda item: item.player_id))
        for key, records in grouped.items()
    }


def _normalized_compare_value(field: str, value: Any) -> Any:
    if field in NONNEGATIVE_UNKNOWN_FIELDS:
        number = _intish(value)
        if number is not None and number < 0:
            return None
        if number is not None:
            return number
    return value


def _field_conflicts(
    records: Sequence[PerspectiveRecord],
    fields: Sequence[str],
) -> dict[str, tuple[Any, ...]]:
    conflicts: dict[str, tuple[Any, ...]] = {}
    for field in fields:
        known: set[Any] = set()
        for record in records:
            if field not in record.raw:
                continue
            value = _normalized_compare_value(field, record.raw[field])
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                known.add(value)
        if len(known) > 1:
            conflicts[field] = tuple(sorted(known, key=repr))
    return conflicts


def _split_freshness(
    records: Sequence[PerspectiveRecord],
) -> tuple[tuple[PerspectiveRecord, ...], tuple[PerspectiveRecord, ...]]:
    current = tuple(record for record in records if record.is_current)
    stale = tuple(record for record in records if not record.is_current)
    return current, stale


def _embedded_turn(records: Sequence[PerspectiveRecord]) -> int:
    turns = {record.embedded_turn for record in records}
    if len(turns) != 1:
        raise ValueError(f"cross-perspective records disagree on embedded turn: {sorted(turns)}")
    return next(iter(turns))


def _resolution(
    *,
    kind: str,
    entity_id: int,
    archive_turn: int,
    records: Sequence[PerspectiveRecord],
    owner_hint: int | None = None,
) -> EntityResolution:
    embedded_turn = _embedded_turn(records)
    current, stale = _split_freshness(records)
    current_players = tuple(sorted(record.player_id for record in current))
    stale_players = tuple(sorted(record.player_id for record in stale))

    if not current:
        return EntityResolution(
            kind=kind,
            entity_id=entity_id,
            archive_turn=archive_turn,
            embedded_turn=embedded_turn,
            status="no_current",
            authoritative_player_id=None,
            current_players=current_players,
            stale_players=stale_players,
            conflicts={},
            record=None,
        )

    positive_owners = {_owner_id(record.raw) for record in current}
    positive_owners.discard(None)
    inferred_owner = owner_hint
    if inferred_owner is None and len(positive_owners) == 1:
        inferred_owner = next(iter(positive_owners))

    if inferred_owner is not None:
        owner_records = [record for record in current if record.player_id == inferred_owner]
        if owner_records:
            chosen = owner_records[0]
            return EntityResolution(
                kind=kind,
                entity_id=entity_id,
                archive_turn=archive_turn,
                embedded_turn=embedded_turn,
                status="owner_perspective",
                authoritative_player_id=inferred_owner,
                current_players=current_players,
                stale_players=stale_players,
                conflicts={},
                record=chosen.raw,
            )

    if kind == "ship":
        conflicts = _field_conflicts(current, SHIP_COMPARE_FIELDS)
        if conflicts:
            return EntityResolution(
                kind=kind,
                entity_id=entity_id,
                archive_turn=archive_turn,
                embedded_turn=embedded_turn,
                status="conflict",
                authoritative_player_id=None,
                current_players=current_players,
                stale_players=stale_players,
                conflicts=conflicts,
                record=None,
            )

    first = current[0]
    return EntityResolution(
        kind=kind,
        entity_id=entity_id,
        archive_turn=archive_turn,
        embedded_turn=embedded_turn,
        status="consensus",
        authoritative_player_id=None,
        current_players=current_players,
        stale_players=stale_players,
        conflicts={},
        record=first.raw,
    )


def reconstruct_cross_perspective(
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> ReconstructionSummary:
    records = tuple(snapshots)
    planet_groups = group_perspective_records(records, "planet")
    ship_groups = group_perspective_records(records, "ship")
    base_groups = group_perspective_records(records, "starbase")

    resolutions: list[EntityResolution] = []
    planet_owner_by_turn: dict[tuple[int, int], int | None] = {}

    for (archive_turn, entity_id), grouped in sorted(planet_groups.items()):
        resolved = _resolution(
            kind="planet",
            entity_id=entity_id,
            archive_turn=archive_turn,
            records=grouped,
        )
        resolutions.append(resolved)
        owner = _owner_id(resolved.record) if resolved.record is not None else None
        planet_owner_by_turn[(archive_turn, entity_id)] = owner

    for (archive_turn, entity_id), grouped in sorted(ship_groups.items()):
        resolutions.append(
            _resolution(
                kind="ship",
                entity_id=entity_id,
                archive_turn=archive_turn,
                records=grouped,
            )
        )

    for (archive_turn, entity_id), grouped in sorted(base_groups.items()):
        resolutions.append(
            _resolution(
                kind="starbase",
                entity_id=entity_id,
                archive_turn=archive_turn,
                records=grouped,
                owner_hint=planet_owner_by_turn.get((archive_turn, entity_id)),
            )
        )

    status_counts = Counter(resolution.status for resolution in resolutions)
    kind_status: dict[str, Counter[str]] = defaultdict(Counter)
    for resolution in resolutions:
        kind_status[resolution.kind][resolution.status] += 1

    return ReconstructionSummary(
        resolutions=tuple(resolutions),
        status_counts=dict(sorted(status_counts.items())),
        kind_status_counts={
            kind: dict(sorted(counts.items())) for kind, counts in sorted(kind_status.items())
        },
    )
