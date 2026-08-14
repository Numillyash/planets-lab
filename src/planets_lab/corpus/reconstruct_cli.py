from __future__ import annotations

import argparse
from pathlib import Path

from .normalizer import CorpusNormalizationError, load_archive_snapshots
from .reconstruction import reconstruct_cross_perspective


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze fail-closed cross-perspective reconstruction of a cached "
            "Planets.nu /game/loadall archive without dumping raw private data."
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

    summary = reconstruct_cross_perspective(snapshots)

    print("===== CROSS-PERSPECTIVE RECONSTRUCTION =====")
    print(f"archive:             {args.archive}")
    print(f"snapshots:           {len(snapshots)}")
    print(f"entity_resolutions:  {len(summary.resolutions)}")
    print(f"status_counts:       {dict(summary.status_counts)}")
    print(f"kind_status_counts:  {dict(summary.kind_status_counts)}")

    conflicts = [r for r in summary.resolutions if r.status == "conflict"]
    no_current = [r for r in summary.resolutions if r.status == "no_current"]

    if conflicts:
        print("conflict_samples:")
        for resolution in conflicts[: max(0, args.samples)]:
            print(
                "  "
                f"kind={resolution.kind} id={resolution.entity_id} "
                f"archive_turn={resolution.archive_turn} "
                f"embedded_turn={resolution.embedded_turn} "
                f"current_players={list(resolution.current_players)} "
                f"conflicts={dict(resolution.conflicts)}"
            )

    if no_current:
        print("no_current_samples:")
        for resolution in no_current[: max(0, args.samples)]:
            print(
                "  "
                f"kind={resolution.kind} id={resolution.entity_id} "
                f"archive_turn={resolution.archive_turn} "
                f"embedded_turn={resolution.embedded_turn} "
                f"stale_players={list(resolution.stale_players)}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
