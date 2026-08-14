from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from .archive import inspect_turn_member, turn_members


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a cached Planets.nu /game/loadall archive without dumping turn contents.")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--samples", type=int, default=3)
    args = parser.parse_args()

    data = args.archive.read_bytes()
    members = turn_members(data)
    if not members:
        print("no playerN-turnM.trn members found")
        return 2

    by_player: dict[int, set[int]] = defaultdict(set)
    by_turn: dict[int, set[int]] = defaultdict(set)
    for member in members:
        by_player[member.player].add(member.turn)
        by_turn[member.turn].add(member.player)

    players = sorted(by_player)
    turns = sorted(by_turn)
    expected = {(player, turn) for player in players for turn in turns}
    actual = {(member.player, member.turn) for member in members}
    missing = sorted(expected - actual)

    print("===== LOADALL ARCHIVE INVENTORY =====")
    print(f"turn_members: {len(members)}")
    print(f"players:      {players}")
    print(f"turns:        {turns[0]}..{turns[-1]} ({len(turns)})")
    print(f"grid:         {len(players)} x {len(turns)} = {len(expected)}")
    print(f"missing:      {len(missing)}")
    if missing:
        print("missing_examples:", missing[:20])

    sample_members = []
    seen: set[str] = set()
    candidates = [members[0], members[len(members) // 2], members[-1]] + list(members)
    for member in candidates:
        if member.name in seen:
            continue
        seen.add(member.name)
        sample_members.append(member)
        if len(sample_members) >= max(1, args.samples):
            break

    print()
    print("===== TURN PAYLOAD FORMAT =====")
    for member in sample_members:
        report = inspect_turn_member(data, member)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
