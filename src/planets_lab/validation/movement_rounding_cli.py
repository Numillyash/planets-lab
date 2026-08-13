from __future__ import annotations

import csv
import sys

from planets_lab.validation import MovementSample, candidate_scores, projection_candidates


def _parse_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y"}


def main() -> int:
    reader = csv.DictReader(sys.stdin)
    samples = [
        MovementSample(
            turn=int(row["turn"]),
            ship_id=int(row["ship_id"]),
            x=int(row["x"]),
            y=int(row["y"]),
            target_x=int(row["target_x"]),
            target_y=int(row["target_y"]),
            warp=int(row["warp"]),
            next_x=int(row["next_x"]),
            next_y=int(row["next_y"]),
            gravitonic=_parse_bool(row.get("gravitonic")),
        )
        for row in reader
    ]

    print("===== MOVEMENT ROUNDING CANDIDATES =====")
    print("samples:", len(samples))

    for mode, (matches, total) in candidate_scores(samples).items():
        print("{:8s}: {}/{}".format(mode, matches, total))

    print()
    print("===== DISCRIMINATING SAMPLES =====")

    for sample in samples:
        candidates = projection_candidates(sample)
        if len(set(candidates.values())) <= 1:
            continue
        print(
            "turn={} ship={} observed=({}, {}) candidates={}".format(
                sample.turn,
                sample.ship_id,
                sample.next_x,
                sample.next_y,
                candidates,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
