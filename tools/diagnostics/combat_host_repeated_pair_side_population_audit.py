from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.combat.order import (
    CLOAK_INTERCEPT_MISSION_ID,
    EVIL_EMPIRE_RACE_ID,
    GORBIE_HULL_ID,
    INTERCEPT_MISSION_ID,
    standard_battle_priority_key,
)

from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_mission7_matched_control_audit import _dedup_vcrs
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
    _int,
    _owner_raw,
    _ship_side,
)


DEFAULT_EXAMPLE_LIMIT = 40
TARGET_RESIDUAL_GROUPS = {
    (620917, 7, 1990, 1810, (13, 14)),
    (621896, 25, 2140, 2187, (34, 67)),
}


def _pair(left_ship_id: int, right_ship_id: int) -> tuple[int, int]:
    return tuple(sorted((left_ship_id, right_ship_id)))


def _serialize(counter: Counter[Any]) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    }


def _priority_key(ship_id: int, raw: Mapping[str, Any] | None) -> tuple[int, int, int] | None:
    if raw is None:
        return None
    return standard_battle_priority_key(
        ship_id=ship_id,
        mission=_intish(raw.get("mission")),
        primary_enemy=_intish(raw.get("enemy")),
        friendly_code=raw.get("friendlycode"),
    )


def _exact_pair_special_order(raw: Mapping[str, Any] | None, opponent_ship_id: int) -> bool:
    if raw is None:
        return False
    mission = _intish(raw.get("mission"))
    target = _intish(raw.get("mission1target"))
    return mission in {INTERCEPT_MISSION_ID, CLOAK_INTERCEPT_MISSION_ID} and target == opponent_ship_id


def _orientation_analysis(
    rows: Sequence[Mapping[str, Any]],
    *,
    priority_by_ship: Mapping[int, tuple[int, int, int] | None],
) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: int(row["vcr_id"]))
    pair = tuple(int(value) for value in ordered[0]["pair"])
    if len(pair) != 2:
        raise ValueError("pair must contain exactly two ship ids")
    if any(tuple(int(value) for value in row["pair"]) != pair for row in ordered):
        raise ValueError("rows must describe one ship pair")

    right_sequence = [int(row["right_ship_id"]) for row in ordered]
    left_sequence = [int(row["left_ship_id"]) for row in ordered]
    alternating_right = all(
        right_sequence[index] != right_sequence[index - 1]
        for index in range(1, len(right_sequence))
    )

    first_ship, second_ship = pair
    first_key = priority_by_ship.get(first_ship)
    second_key = priority_by_ship.get(second_ship)
    comparable = (
        first_key is not None
        and second_key is not None
        and first_key != second_key
    )
    high_priority_ship_id: int | None = None
    low_priority_ship_id: int | None = None
    first_static_right_exact: bool | None = None
    second_reversed_right_exact: bool | None = None
    two_pass_static_pattern_exact: bool | None = None

    if comparable:
        assert first_key is not None and second_key is not None
        if first_key < second_key:
            high_priority_ship_id, low_priority_ship_id = first_ship, second_ship
        else:
            high_priority_ship_id, low_priority_ship_id = second_ship, first_ship
        first_static_right_exact = right_sequence[0] == high_priority_ship_id
        if len(right_sequence) >= 2:
            second_reversed_right_exact = right_sequence[1] == low_priority_ship_id
        if len(right_sequence) == 2:
            two_pass_static_pattern_exact = bool(
                first_static_right_exact and second_reversed_right_exact
            )

    return {
        "pair": list(pair),
        "vcr_ids": [int(row["vcr_id"]) for row in ordered],
        "occurrence_count": len(ordered),
        "left_ship_sequence": left_sequence,
        "right_ship_sequence": right_sequence,
        "alternating_right_ship": alternating_right,
        "exactly_two_side_flip": (
            len(right_sequence) == 2 and right_sequence[0] != right_sequence[1]
        ),
        "priority_comparable": comparable,
        "high_priority_ship_id": high_priority_ship_id,
        "low_priority_ship_id": low_priority_ship_id,
        "first_static_right_exact": first_static_right_exact,
        "second_reversed_right_exact": second_reversed_right_exact,
        "two_pass_static_pattern_exact": two_pass_static_pattern_exact,
    }


def _side_tminus1_projection(
    *,
    ship_id: int,
    factual_owner_id: int | None,
    owner_tminus1: int | None,
    raw: Mapping[str, Any] | None,
) -> dict[str, Any]:
    aligned = (
        factual_owner_id is not None
        and owner_tminus1 is not None
        and factual_owner_id == owner_tminus1
        and raw is not None
    )
    if not aligned:
        return {
            "ship_id": ship_id,
            "factual_owner_id": factual_owner_id,
            "owner_tminus1": owner_tminus1,
            "owner_aligned": False,
            "battle_priority_key": None,
        }
    assert raw is not None
    return {
        "ship_id": ship_id,
        "factual_owner_id": factual_owner_id,
        "owner_tminus1": owner_tminus1,
        "owner_aligned": True,
        "mission": _intish(raw.get("mission")),
        "mission1target": _intish(raw.get("mission1target")),
        "enemy": _intish(raw.get("enemy")),
        "friendlycode": raw.get("friendlycode") if isinstance(raw.get("friendlycode"), str) else None,
        "battle_priority_key": _priority_key(ship_id, raw),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    payload_conflicts = 0
    invalid_owner_vcr_rows = 0
    archives_considered = 0
    repeated_groups: list[dict[str, Any]] = []

    for archive_path in sorted(args.archive_dir.glob("game-*.zip")):
        try:
            game_id = int(archive_path.stem.split("-")[-1])
        except ValueError:
            continue
        if game_id == SPECIAL_GAME_ID:
            continue
        archives_considered += 1

        archive_data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=args.prepared_dir / f"game-{game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        races, _race_conflicts = _player_races(prepared.snapshots)
        seen, conflicts = _dedup_vcrs(archive_data)
        payload_conflicts += conflicts

        sites: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
        for (seen_game, battle_turn, vcr_id), (_digest, vcr) in sorted(seen.items()):
            if seen_game != game_id:
                continue
            left = _ship_side(vcr, "left")
            right = _ship_side(vcr, "right")
            x = _int(vcr, "x")
            y = _int(vcr, "y")
            if left is None or right is None or x is None or y is None:
                continue
            left_id = int(left["ship_id"])
            right_id = int(right["ship_id"])
            left_owner = _int(vcr, "leftownerid")
            right_owner = _int(vcr, "rightownerid")
            if (
                left_owner is None
                or right_owner is None
                or left_owner <= 0
                or right_owner <= 0
            ):
                invalid_owner_vcr_rows += 1
                continue
            sites[(int(battle_turn), int(x), int(y))].append(
                {
                    "vcr_id": int(vcr_id),
                    "left_ship_id": left_id,
                    "right_ship_id": right_id,
                    "left_owner_id": left_owner,
                    "right_owner_id": right_owner,
                    "left_hull_id": int(left["hull_id"]),
                    "right_hull_id": int(right["hull_id"]),
                    "pair": _pair(left_id, right_id),
                }
            )

        for (battle_turn, x, y), site_rows in sorted(sites.items()):
            by_pair: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
            for row in site_rows:
                by_pair[tuple(row["pair"])].append(row)

            for pair, pair_rows in sorted(by_pair.items()):
                if len(pair_rows) < 2:
                    continue
                ordered = sorted(pair_rows, key=lambda row: int(row["vcr_id"]))
                owners_by_ship: dict[int, set[int]] = {pair[0]: set(), pair[1]: set()}
                hull_by_ship: dict[int, int] = {}
                for row in ordered:
                    owners_by_ship[int(row["left_ship_id"])].add(int(row["left_owner_id"]))
                    owners_by_ship[int(row["right_ship_id"])].add(int(row["right_owner_id"]))
                    hull_by_ship.setdefault(int(row["left_ship_id"]), int(row["left_hull_id"]))
                    hull_by_ship.setdefault(int(row["right_ship_id"]), int(row["right_hull_id"]))

                stable_owners = all(len(values) == 1 for values in owners_by_ship.values())
                factual_owner_by_ship: dict[int, int | None] = {
                    ship_id: (next(iter(values)) if len(values) == 1 else None)
                    for ship_id, values in owners_by_ship.items()
                }

                before_turn = battle_turn - 1
                tminus1: dict[int, dict[str, Any]] = {}
                priority_by_ship: dict[int, tuple[int, int, int] | None] = {}
                exact_special_order = False
                potential_galactic_power = False

                for ship_id in pair:
                    owner_t1, raw = _owner_raw(ship_groups, before_turn, ship_id)
                    projection = _side_tminus1_projection(
                        ship_id=ship_id,
                        factual_owner_id=factual_owner_by_ship[ship_id],
                        owner_tminus1=owner_t1,
                        raw=raw,
                    )
                    tminus1[ship_id] = projection
                    priority_by_ship[ship_id] = (
                        tuple(projection["battle_priority_key"])
                        if projection.get("battle_priority_key") is not None
                        else None
                    )
                    other_ship_id = pair[1] if ship_id == pair[0] else pair[0]
                    if projection.get("owner_aligned") and _exact_pair_special_order(raw, other_ship_id):
                        exact_special_order = True
                    factual_owner = factual_owner_by_ship[ship_id]
                    race_id = races.get(factual_owner) if factual_owner is not None else None
                    if race_id == EVIL_EMPIRE_RACE_ID and hull_by_ship.get(ship_id) == GORBIE_HULL_ID:
                        potential_galactic_power = True

                orientation = _orientation_analysis(
                    ordered,
                    priority_by_ship=priority_by_ship,
                )
                owner_aligned = stable_owners and all(
                    bool(tminus1[ship_id].get("owner_aligned")) for ship_id in pair
                )
                plain_static_comparable = bool(
                    len(ordered) == 2
                    and owner_aligned
                    and orientation["priority_comparable"]
                    and not exact_special_order
                    and not potential_galactic_power
                )

                group_key = (game_id, battle_turn, x, y, pair)
                repeated_groups.append(
                    {
                        "game_id": game_id,
                        "battle_turn": battle_turn,
                        "x": x,
                        "y": y,
                        "pair": list(pair),
                        "site_ship_vcr_ids": [
                            int(row["vcr_id"]) for row in sorted(site_rows, key=lambda item: int(item["vcr_id"]))
                        ],
                        "site_ship_vcr_count": len(site_rows),
                        "owners_by_ship": {
                            str(ship_id): sorted(values)
                            for ship_id, values in owners_by_ship.items()
                        },
                        "stable_owners": stable_owners,
                        "owner_tminus1_aligned": owner_aligned,
                        "tminus1": {str(ship_id): tminus1[ship_id] for ship_id in pair},
                        "exact_pair_intercept_or_ci_order": exact_special_order,
                        "potential_galactic_power": potential_galactic_power,
                        "plain_static_comparable": plain_static_comparable,
                        "is_target_residual_group": group_key in TARGET_RESIDUAL_GROUPS,
                        **orientation,
                    }
                )

    counts = Counter()
    occurrence_count = Counter()
    games = Counter()
    for row in repeated_groups:
        counts["repeated_pair_groups"] += 1
        counts["repeated_pair_vcr_rows"] += int(row["occurrence_count"])
        occurrence_count[int(row["occurrence_count"])] += 1
        games[int(row["game_id"])] += 1
        if int(row["occurrence_count"]) > 2:
            counts["over_documented_max_two_groups"] += 1
        if row["stable_owners"]:
            counts["stable_owner_groups"] += 1
        else:
            counts["owner_change_groups"] += 1
        if row["stable_owners"] and int(row["occurrence_count"]) == 2:
            counts["stable_owner_exactly_two_groups"] += 1
            if row["exactly_two_side_flip"]:
                counts["stable_owner_exactly_two_side_flip"] += 1
            else:
                counts["stable_owner_exactly_two_same_orientation"] += 1
        if row["plain_static_comparable"]:
            counts["plain_static_comparable_groups"] += 1
            if row["first_static_right_exact"]:
                counts["plain_static_first_right_exact"] += 1
            else:
                counts["plain_static_first_right_mismatch"] += 1
            if row["second_reversed_right_exact"]:
                counts["plain_static_second_reversed_exact"] += 1
            else:
                counts["plain_static_second_reversed_mismatch"] += 1
            if row["two_pass_static_pattern_exact"]:
                counts["plain_static_two_pass_exact"] += 1
            else:
                counts["plain_static_two_pass_mismatch"] += 1
        if row["is_target_residual_group"]:
            counts["target_residual_groups"] += 1

    max_occurrences = max((int(row["occurrence_count"]) for row in repeated_groups), default=0)

    priority_examples = [
        row for row in repeated_groups
        if (
            int(row["occurrence_count"]) > 2
            or not row["stable_owners"]
            or (
                row["plain_static_comparable"]
                and row["two_pass_static_pattern_exact"] is False
            )
            or row["is_target_residual_group"]
        )
    ]
    exact_examples = [
        row for row in repeated_groups
        if row["plain_static_comparable"] and row["two_pass_static_pattern_exact"] is True
    ]
    examples = (priority_examples + exact_examples)[: args.example_limit]

    summary = {
        "archives_considered": archives_considered,
        "special_game_591478_excluded": True,
        "payload_conflicts": payload_conflicts,
        "invalid_owner_vcr_rows": invalid_owner_vcr_rows,
        **{key: int(value) for key, value in sorted(counts.items())},
        "occurrence_count": _serialize(occurrence_count),
        "max_occurrences": max_occurrences,
        "games": _serialize(games),
    }

    return {
        "schema": "planets-lab.combat-host-repeated-pair-side-population-audit.v1",
        "read_only": True,
        "summary": summary,
        "target_residual_groups": [
            row for row in repeated_groups if row["is_target_residual_group"]
        ],
        "examples": examples,
        "evidence_boundary": (
            "Ordinary factual ship-vs-ship VCR population audit for repeated ship pairs within one battle-turn/location. "
            "Primary Planets.nu documentation establishes that a pair can fight at most twice and that stacked order can "
            "shift dynamically. This diagnostic tests the corpus orientation pattern. Exact second-pass side reversal is "
            "not promoted as primary DOCUMENTED by this tool; owner changes, exact Intercept/C&I pair orders and potential "
            "Empire-Gorbie Galactic Power are separated from the plain static-priority subset. Game 591478 is excluded."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit repeated same-pair ship combat side orientation across the ordinary corpus."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT REPEATED-PAIR SIDE POPULATION AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("TARGET RESIDUAL GROUPS:")
    for row in report["target_residual_groups"]:
        print(row)
    print()
    print("EXAMPLES:")
    for row in report["examples"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: repeated-pair orientation population only; no mutable queue rule is promoted until runtime is reviewed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
