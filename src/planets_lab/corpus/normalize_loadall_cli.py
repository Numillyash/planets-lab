from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .normalizer import (
    CorpusNormalizationError,
    consecutive_archive_transitions,
    load_archive_snapshots,
    ownerless_ship_diagnostics,
    summarize_archive_snapshots,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize a cached Planets.nu /game/loadall archive into player-perspective streams and validate canonical imports without dumping raw turn payloads."
    )
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()

    try:
        data = args.archive.read_bytes()
        snapshots = load_archive_snapshots(data)
    except (OSError, ValueError, CorpusNormalizationError) as exc:
        print(str(exc))
        return 2

    if not snapshots:
        print("no turn snapshots found")
        return 2

    summary = summarize_archive_snapshots(snapshots)
    transitions = consecutive_archive_transitions(snapshots)

    canonical_ok = 0
    canonical_failures: list[tuple[object, Exception]] = []
    entity_totals = Counter()
    nonempty = Counter()
    turn_offsets = Counter()

    for snapshot in snapshots:
        turn_offsets[snapshot.embedded_turn - snapshot.archive_turn] += 1
        try:
            state = snapshot.import_state()
        except Exception as exc:  # reporting boundary for corpus diagnostics
            canonical_failures.append((snapshot, exc))
            continue

        canonical_ok += 1
        counts = {
            "planets": len(state.planets),
            "ships": len(state.ships),
            "starbases": len(state.starbases),
            "ionstorms": len(state.ion_storms),
        }
        for kind, count in counts.items():
            entity_totals[kind] += count
            if count:
                nonempty[kind] += 1

    game_ids = sorted({snapshot.game_id for snapshot in snapshots})
    embedded_turns = sorted({snapshot.embedded_turn for snapshot in snapshots})
    offset_anomalies = [
        snapshot
        for snapshot in snapshots
        if snapshot.embedded_turn != snapshot.archive_turn
    ]
    transition_anomalies = [
        transition
        for transition in transitions
        if transition.embedded_turn_delta != 1
    ]

    print("===== NORMALIZED LOADALL CORPUS =====")
    print(f"archive:                       {args.archive}")
    print(f"game_ids:                      {game_ids}")
    print(f"snapshots:                     {summary.snapshots}")
    print(f"players:                       {list(summary.players)}")
    if summary.archive_turns:
        print(
            f"archive_turns:                 {summary.archive_turns[0]}..{summary.archive_turns[-1]} ({len(summary.archive_turns)})"
        )
    if embedded_turns:
        print(
            f"embedded_turns:                {embedded_turns[0]}..{embedded_turns[-1]} ({len(embedded_turns)})"
        )
    print(f"missing_grid_cells:             {len(summary.missing_grid_cells)}")
    print(f"transitions:                    {summary.transitions}")
    print(
        f"embedded_consecutive:           {summary.embedded_consecutive_transitions}/{summary.transitions}"
    )
    print(f"turn_offset_counts:             {dict(sorted(turn_offsets.items()))}")
    print(f"canonical_import:               {canonical_ok} ok / {len(canonical_failures)} failed")
    print(f"nonempty_snapshots_by_entity:   {dict(sorted(nonempty.items()))}")
    print(f"entity_records_across_snapshots:{dict(sorted(entity_totals.items()))}")

    if offset_anomalies:
        print("turn_offset_examples:")
        for snapshot in offset_anomalies[:20]:
            print(
                "  "
                f"player={snapshot.player_id} "
                f"archive_turn={snapshot.archive_turn} "
                f"embedded_turn={snapshot.embedded_turn} "
                f"offset={snapshot.embedded_turn - snapshot.archive_turn}"
            )

    if transition_anomalies:
        print("embedded_transition_anomalies:")
        for transition in transition_anomalies[:20]:
            print(
                "  "
                f"player={transition.before.player_id} "
                f"archive={transition.before.archive_turn}->{transition.after.archive_turn} "
                f"embedded={transition.before.embedded_turn}->{transition.after.embedded_turn} "
                f"delta={transition.embedded_turn_delta}"
            )

    if canonical_failures:
        print("canonical_failures:")
        for snapshot, exc in canonical_failures[:20]:
            print(
                "  "
                f"player={snapshot.player_id} "
                f"archive_turn={snapshot.archive_turn} "
                f"embedded_turn={snapshot.embedded_turn}: "
                f"{type(exc).__name__}: {exc}"
            )
            diagnostics = ownerless_ship_diagnostics(snapshot)
            for diagnostic in diagnostics[:10]:
                print(
                    "    ownerless_ship="
                    + json.dumps(diagnostic, ensure_ascii=False, sort_keys=True)
                )

    return 1 if canonical_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
