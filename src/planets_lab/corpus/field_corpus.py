from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .field_reconstruction import FieldReconstructionSummary, STATIC_FIELDS, reconstruct_fields
from .normalizer import ArchiveTurnSnapshot

FIELD_GAME_SCHEMA = "planets-lab.field-corpus-game.v1"
FIELD_STATS_SCHEMA = "planets-lab.field-corpus-stats.v1"


def summarize_field_game(
    *,
    game_id: int,
    settings_hash: str,
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> dict[str, Any]:
    summary = reconstruct_fields(snapshots)
    conflict_fields: Counter[str] = Counter()
    unresolved_dynamic_fields: Counter[str] = Counter()
    entities_by_kind: Counter[str] = Counter()
    entities_with_conflicts_by_kind: Counter[str] = Counter()
    entities_with_unresolved_by_kind: Counter[str] = Counter()

    for entity in summary.entities:
        entities_by_kind[entity.kind] += 1
        if entity.conflict_fields:
            entities_with_conflicts_by_kind[entity.kind] += 1
        if entity.unresolved_dynamic_fields:
            entities_with_unresolved_by_kind[entity.kind] += 1
        for field in entity.conflict_fields:
            conflict_fields[f"{entity.kind}.{field}"] += 1
        for field in entity.unresolved_dynamic_fields:
            unresolved_dynamic_fields[f"{entity.kind}.{field}"] += 1

    resolved_fields = sum(
        count
        for status, count in summary.field_status_counts.items()
        if status in {"owner_perspective", "current_consensus", "stale_static_consensus"}
    )
    total_fields = sum(summary.field_status_counts.values())

    return {
        "schema": FIELD_GAME_SCHEMA,
        "game_id": game_id,
        "settings_hash": settings_hash,
        "snapshots": len(snapshots),
        "entities": len(summary.entities),
        "entities_by_kind": dict(sorted(entities_by_kind.items())),
        "field_status_counts": dict(summary.field_status_counts),
        "resolved_fields": resolved_fields,
        "total_fields": total_fields,
        "entities_with_conflicts": summary.entities_with_conflicts,
        "entities_with_unresolved_dynamic": summary.entities_with_unresolved_dynamic,
        "entities_with_conflicts_by_kind": dict(sorted(entities_with_conflicts_by_kind.items())),
        "entities_with_unresolved_dynamic_by_kind": dict(
            sorted(entities_with_unresolved_by_kind.items())
        ),
        "conflict_field_counts": dict(sorted(conflict_fields.items())),
        "unresolved_dynamic_field_counts": dict(sorted(unresolved_dynamic_fields.items())),
    }


def aggregate_field_games(
    records: Iterable[Mapping[str, Any]],
    *,
    failed_game_ids: Iterable[int] = (),
) -> dict[str, Any]:
    rows = tuple(records)
    totals: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    conflict_fields: Counter[str] = Counter()
    unresolved_fields: Counter[str] = Counter()
    conflicts_by_kind: Counter[str] = Counter()
    unresolved_by_kind: Counter[str] = Counter()
    settings_hashes: Counter[str] = Counter()

    for row in rows:
        settings_hash = row.get("settings_hash")
        if isinstance(settings_hash, str):
            settings_hashes[settings_hash] += 1

        for key in (
            "snapshots",
            "entities",
            "resolved_fields",
            "total_fields",
            "entities_with_conflicts",
            "entities_with_unresolved_dynamic",
        ):
            value = row.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                totals[key] += value

        for source, target in (
            (row.get("field_status_counts", {}), statuses),
            (row.get("conflict_field_counts", {}), conflict_fields),
            (row.get("unresolved_dynamic_field_counts", {}), unresolved_fields),
            (row.get("entities_with_conflicts_by_kind", {}), conflicts_by_kind),
            (row.get("entities_with_unresolved_dynamic_by_kind", {}), unresolved_by_kind),
        ):
            if not isinstance(source, Mapping):
                continue
            for key, value in source.items():
                if isinstance(value, int) and not isinstance(value, bool):
                    target[str(key)] += value

    failed = tuple(sorted(set(int(game_id) for game_id in failed_game_ids)))
    return {
        "schema": FIELD_STATS_SCHEMA,
        "games_indexed": len(rows),
        "games_failed": len(failed),
        "failed_game_ids": list(failed),
        "settings_hashes": len(settings_hashes),
        "totals": dict(sorted(totals.items())),
        "field_status_counts": dict(sorted(statuses.items())),
        "conflict_field_counts": dict(sorted(conflict_fields.items())),
        "unresolved_dynamic_field_counts": dict(sorted(unresolved_fields.items())),
        "entities_with_conflicts_by_kind": dict(sorted(conflicts_by_kind.items())),
        "entities_with_unresolved_dynamic_by_kind": dict(sorted(unresolved_by_kind.items())),
    }
