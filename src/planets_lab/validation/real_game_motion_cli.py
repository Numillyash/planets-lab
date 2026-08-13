from __future__ import annotations

import sys

from planets_lab.validation.real_game import consecutive_transitions, load_jsonl
from planets_lab.validation.real_game_motion import summarize_motion


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m planets_lab.validation.real_game_motion_cli DATASET.jsonl", file=sys.stderr)
        return 2

    batches = load_jsonl(sys.argv[1])
    summary = summarize_motion(consecutive_transitions(batches))

    print("===== REAL GAME MOTION DIFFERENTIAL =====")
    for key in (
        "transitions",
        "source_ship_pairs",
        "source_ships_appeared",
        "source_ships_disappeared",
        "moved",
        "stationary",
        "special_cases",
        "ordinary_cases",
        "reachable_cases",
        "reachable_matches",
        "partial_cases",
        "excluded_above_nominal",
    ):
        print(f"{key:27s} {summary[key]}")

    reachable = int(summary["reachable_cases"])
    matches = int(summary["reachable_matches"])
    if reachable:
        print(f"reachable_match_rate        {matches / reachable:.2%}")

    print("rounding_scores")
    scores = summary["rounding_scores"]
    assert isinstance(scores, dict)
    for mode, value in scores.items():
        matched, total = value
        rate = matched / total if total else 0.0
        print(f"  {mode:8s} {matched}/{total} ({rate:.2%})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
