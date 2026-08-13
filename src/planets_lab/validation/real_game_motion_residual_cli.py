from __future__ import annotations

import sys

from planets_lab.validation.movement_geometry import projection_candidates
from planets_lab.validation.real_game import consecutive_transitions, load_jsonl
from planets_lab.validation.real_game_motion import partial_samples


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m planets_lab.validation.real_game_motion_residual_cli DATASET.jsonl", file=sys.stderr)
        return 2

    samples = partial_samples(consecutive_transitions(load_jsonl(sys.argv[1])))
    misses = []
    for sample in samples:
        expected = projection_candidates(sample)["host_major_minor"]
        if expected != sample.observed_destination:
            misses.append((sample, expected))

    print("===== REAL GAME MOTION RESIDUALS =====")
    print(f"partial samples              {len(samples)}")
    print(f"host projection matches      {len(samples) - len(misses)}")
    print(f"residual cases               {len(misses)}")
    for sample, expected in misses:
        print(
            f"turn={sample.turn} player={sample.player_slot_id} ship={sample.ship_id} "
            f"hull={sample.hull_id} warp={sample.warp} damage={sample.damage} "
            f"fc={sample.friendly_code!r} origin=({sample.x},{sample.y}) "
            f"target=({sample.target_x},{sample.target_y}) expected={expected} "
            f"observed={sample.observed_destination}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
