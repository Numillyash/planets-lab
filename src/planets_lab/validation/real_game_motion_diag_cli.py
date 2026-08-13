from __future__ import annotations

import sys

from planets_lab.validation.real_game import consecutive_transitions, load_jsonl
from planets_lab.validation.real_game_motion_diag import diagnose


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: python -m planets_lab.validation.real_game_motion_diag_cli DATASET.jsonl",
            file=sys.stderr,
        )
        return 2

    result = diagnose(consecutive_transitions(load_jsonl(sys.argv[1])))
    total = int(result["total"])
    explained = int(result["explained"])
    unresolved = int(result["unresolved"])

    print("===== REAL GAME MOTION MISMATCH DIAGNOSTICS =====")
    print(f"classified cases             {total}")
    print(f"explained cases              {explained}")
    print(f"unresolved cases             {unresolved}")
    if total:
        print(f"explained rate               {explained / total:.2%}")

    print("categories")
    for key, value in result["categories"].items():
        print(f"  {key:34s} {value}")

    print()
    print("first unresolved rows")
    for row in result["rows"]:
        print(
            "turn={turn} player={player} ship={ship} hull={hull} mission={mission} "
            "fc={friendly_code!r} warp={warp} damage={damage} fuel={fuel} "
            "category={category} origin={origin} target={target} expected={expected} "
            "observed={observed} target_dist={target_distance} "
            "observed_dist={observed_distance}".format(**row)
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
