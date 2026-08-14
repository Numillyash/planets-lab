from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from .field_reconstruction import reconstruct_fields
from .normalizer import CorpusNormalizationError, load_archive_snapshots


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze field-level, provenance-aware cross-perspective reconstruction "
            "of a cached Planets.nu /game/loadall archive."
        )
    )
    parser.add_argument("archive", type=Path)
    parser.add_argument("--samples", type=int, default=20)
    args = parser.parse_args()

    try:
        snapshots = load_archive_snapshots(args.archive.read_bytes())
    except (OSError, ValueError, CorpusNormalizationError) as exc:
        print(str(exc))
        return 2

    summary = reconstruct_fields(snapshots)

    print("===== FIELD-LEVEL CROSS-PERSPECTIVE RECONSTRUCTION =====")
    print(f"archive:                     {args.archive}")
    print(f"snapshots:                   {len(snapshots)}")
    print(f"entities:                    {len(summary.entities)}")
    print(f"field_status_counts:         {dict(summary.field_status_counts)}")
    print(f"kind_field_status_counts:    {dict(summary.kind_field_status_counts)}")
    print(f"entities_with_conflicts:     {summary.entities_with_conflicts}")
    print(f"entities_with_unresolved_dynamic: {summary.entities_with_unresolved_dynamic}")

    conflict_fields = Counter()
    unresolved_fields = Counter()
    conflict_entities = []
    unresolved_entities = []
    for entity in summary.entities:
        for field in entity.conflict_fields:
            conflict_fields[(entity.kind, field)] += 1
        for field in entity.unresolved_dynamic_fields:
            unresolved_fields[(entity.kind, field)] += 1
        if entity.conflict_fields:
            conflict_entities.append(entity)
        if entity.unresolved_dynamic_fields:
            unresolved_entities.append(entity)

    if conflict_fields:
        print("conflict_field_counts:")
        for (kind, field), count in sorted(
            conflict_fields.items(), key=lambda item: (-item[1], item[0])
        ):
            print(f"  {kind}.{field}: {count}")

    if unresolved_fields:
        print("unresolved_dynamic_field_counts_top:")
        for (kind, field), count in sorted(
            unresolved_fields.items(), key=lambda item: (-item[1], item[0])
        )[:40]:
            print(f"  {kind}.{field}: {count}")

    if conflict_entities:
        print("conflict_samples:")
        for entity in conflict_entities[: max(0, args.samples)]:
            details = {
                field: entity.fields[field].alternatives
                for field in entity.conflict_fields
            }
            resolved_examples = {
                field: resolution.value
                for field, resolution in entity.fields.items()
                if resolution.status in {
                    "owner_perspective",
                    "current_consensus",
                    "stale_static_consensus",
                }
            }
            print(
                "  "
                f"kind={entity.kind} id={entity.entity_id} "
                f"archive_turn={entity.archive_turn} embedded_turn={entity.embedded_turn} "
                f"owner_hint={entity.owner_hint!r} "
                f"current_players={list(entity.current_players)} "
                f"conflicts={details} "
                f"resolved_sample={dict(list(resolved_examples.items())[:8])}"
            )

    if unresolved_entities:
        print("unresolved_dynamic_samples:")
        for entity in unresolved_entities[: max(0, args.samples)]:
            static_recovered = {
                field: resolution.value
                for field, resolution in entity.fields.items()
                if resolution.status == "stale_static_consensus"
            }
            print(
                "  "
                f"kind={entity.kind} id={entity.entity_id} "
                f"archive_turn={entity.archive_turn} embedded_turn={entity.embedded_turn} "
                f"unresolved={list(entity.unresolved_dynamic_fields)} "
                f"static_recovered={static_recovered} "
                f"stale_players={list(entity.stale_players)}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
