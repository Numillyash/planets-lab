from __future__ import annotations

import sys

from planets_lab.validation.movement_geometry import projection_candidates
from planets_lab.validation.real_game import consecutive_transitions, load_jsonl
from planets_lab.validation.real_game_motion import partial_samples


KEY_TOKENS = (
    "fuel",
    "neutron",
    "mass",
    "cargo",
    "supply",
    "damage",
    "warp",
    "mission",
    "target",
    "engine",
    "hull",
)


def _raw_ship(batch, ship_id: int) -> dict:
    for raw in batch.ships:
        try:
            if int(raw.get("id", -1)) == ship_id:
                return dict(raw)
        except (TypeError, ValueError):
            continue
    return {}


def _interesting(raw: dict) -> dict:
    return {
        key: raw[key]
        for key in sorted(raw)
        if any(token in key.lower() for token in KEY_TOKENS)
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: python -m planets_lab.validation.real_game_motion_raw_cli DATASET.jsonl",
            file=sys.stderr,
        )
        return 2

    transitions = consecutive_transitions(load_jsonl(sys.argv[1]))
    by_key = {
        (t.before.game_id, t.before.stream.source_player_slot_id, t.before.turn): t
        for t in transitions
    }
    residuals = [
        sample
        for sample in partial_samples(transitions)
        if projection_candidates(sample)["host_major_minor"] != sample.observed_destination
    ]

    print("===== REAL GAME MOTION RAW RESIDUAL PAYLOADS =====")
    print(f"residual cases               {len(residuals)}")

    for sample in residuals:
        transition = by_key[(sample.game_id, sample.player_slot_id, sample.turn)]
        before = _raw_ship(transition.before, sample.ship_id)
        after = _raw_ship(transition.after, sample.ship_id)
        print()
        print(
            f"turn={sample.turn} player={sample.player_slot_id} ship={sample.ship_id} "
            f"observed={sample.observed_destination}"
        )
        print(f"  before_interesting={_interesting(before)!r}")
        print(f"  after_interesting={_interesting(after)!r}")
        print(f"  all_keys={tuple(sorted(before))!r}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
