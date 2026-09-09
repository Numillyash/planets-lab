from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import PerspectiveRecord, group_perspective_records
from planets_lab.rules.combat.eligibility import MATCHING_SHIP_FC_COMBAT_EXCEPTIONS
from planets_lab.rules.combat.order import BIRD_RACE_ID, orders_request_ship_combat

from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_mission7_matched_control_audit import _dedup_vcrs
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
    _decode_turn,
    _ship_side,
    _static_specs,
)
from combat_host_residual_physical_stack_audit import _turn_owner_index, _xy

DEFAULT_EXAMPLE_LIMIT = 40
RelationTriple = tuple[int | None, int | None, int | None]
RelationSignature = tuple[tuple[RelationTriple, ...], tuple[RelationTriple, ...]]


def _serialize(counter: Counter[Any]) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    }


def _positive_owner(raw: Mapping[str, Any]) -> int | None:
    value = _intish(raw.get("ownerid", raw.get("owner_id")))
    return value if value is not None and value > 0 else None


def _positive_fuel(raw: Mapping[str, Any]) -> bool:
    value = _intish(raw.get("neutronium"))
    return value is not None and value > 0


def _alive(raw: Mapping[str, Any]) -> bool:
    damage = _intish(raw.get("damage"))
    return damage is not None and 0 <= damage < 100


def _armed(raw: Mapping[str, Any]) -> bool:
    values = (_intish(raw.get("beams")), _intish(raw.get("torps")), _intish(raw.get("bays")))
    return any(value is not None and value > 0 for value in values)


def _ordinary_exact_matching_fc(left_raw: Mapping[str, Any], right_raw: Mapping[str, Any]) -> str | None:
    left = left_raw.get("friendlycode")
    right = right_raw.get("friendlycode")
    if not isinstance(left, str) or not isinstance(right, str) or left != right:
        return None
    if left.casefold() in MATCHING_SHIP_FC_COMBAT_EXCEPTIONS:
        return None
    return left


def _hostility_shape(
    *,
    left_raw: Mapping[str, Any],
    left_owner: int,
    right_raw: Mapping[str, Any],
    right_owner: int,
) -> str:
    left_requests = orders_request_ship_combat(
        mission=_intish(left_raw.get("mission")),
        primary_enemy=_intish(left_raw.get("enemy")),
        opponent_owner_id=right_owner,
    )
    right_requests = orders_request_ship_combat(
        mission=_intish(right_raw.get("mission")),
        primary_enemy=_intish(right_raw.get("enemy")),
        opponent_owner_id=left_owner,
    )
    if left_requests and right_requests:
        return "both"
    if left_requests:
        return "left_only"
    if right_requests:
        return "right_only"
    return "none"


def _relation_inventory(archive_data: bytes) -> dict[int, dict[tuple[int, int], set[RelationTriple]]]:
    members = turn_members(archive_data)
    raw_members = read_archive_members(archive_data, [member.name for member in members])
    result: dict[int, dict[tuple[int, int], set[RelationTriple]]] = defaultdict(lambda: defaultdict(set))
    for member in members:
        parsed = _decode_turn(raw_members[member.name], member.name)
        relations = parsed.get("relations")
        if not isinstance(relations, list):
            continue
        for raw in relations:
            if not isinstance(raw, Mapping):
                continue
            source = _intish(raw.get("playerid"))
            target = _intish(raw.get("playertoid"))
            if source is None or source <= 0 or target is None or target <= 0 or source == target:
                continue
            result[member.turn][(source, target)].add(
                (
                    _intish(raw.get("relationto")),
                    _intish(raw.get("relationfrom")),
                    _intish(raw.get("conflictlevel")),
                )
            )
    return result


def _relation_signature(
    relation_rows: Mapping[tuple[int, int], set[RelationTriple]],
    owner_a: int,
    owner_b: int,
) -> RelationSignature:
    low, high = sorted((owner_a, owner_b))
    forward = tuple(sorted(relation_rows.get((low, high), set()), key=repr))
    reverse = tuple(sorted(relation_rows.get((high, low), set()), key=repr))
    return forward, reverse


def _unique_relation_signature(signature: RelationSignature) -> bool:
    return len(signature[0]) == 1 and len(signature[1]) == 1


def _safe_signature(signature: RelationSignature) -> dict[str, list[list[int | None]]]:
    return {
        "low_to_high": [list(row) for row in signature[0]],
        "high_to_low": [list(row) for row in signature[1]],
    }


def _safe_ship(
    *,
    ship_id: int,
    race_id: int | None,
    hull_id: int,
    hull_can_cloak: bool | None,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "ship_id": ship_id,
        "owner_id": _positive_owner(before),
        "race_id": race_id,
        "hull_id": hull_id,
        "hull_can_cloak": hull_can_cloak,
        "friendly_code": before.get("friendlycode") if isinstance(before.get("friendlycode"), str) else None,
        "mission": _intish(before.get("mission")),
        "mission1target": _intish(before.get("mission1target")),
        "enemy": _intish(before.get("enemy")),
        "tminus1_fuel": _intish(before.get("neutronium")),
        "t_fuel": _intish(after.get("neutronium")),
        "tminus1_damage": _intish(before.get("damage")),
        "t_damage": _intish(after.get("damage")),
        "beams": _intish(before.get("beams")),
        "torps": _intish(before.get("torps")),
        "bays": _intish(before.get("bays")),
        "position": list(_xy(before)),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    pipeline: Counter[str] = Counter()
    payload_conflicts = 0
    archives_considered = 0

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
        races, _ = _player_races(prepared.snapshots)
        specs = _static_specs(archive_data)
        seen, conflicts = _dedup_vcrs(archive_data)
        payload_conflicts += conflicts
        relations = _relation_inventory(archive_data)

        pair_vcrs_by_turn: dict[int, set[frozenset[int]]] = defaultdict(set)
        site_participants: dict[tuple[int, int, int], set[int]] = defaultdict(set)
        factual_combat_owner_pairs: list[tuple[int, int, int]] = []
        for (seen_game, battle_turn, _vcr_id), (_digest, vcr) in seen.items():
            if seen_game != game_id:
                continue
            left = _ship_side(vcr, "left")
            right = _ship_side(vcr, "right")
            if left is None or right is None:
                continue
            left_id = int(left["ship_id"])
            right_id = int(right["ship_id"])
            pair_vcrs_by_turn[battle_turn].add(frozenset((left_id, right_id)))
            x = _intish(vcr.get("x"))
            y = _intish(vcr.get("y"))
            if x is not None and y is not None:
                site_participants[(battle_turn, x, y)].update((left_id, right_id))
            left_owner = int(left["owner_id"])
            right_owner = int(right["owner_id"])
            if left_owner > 0 and right_owner > 0 and left_owner != right_owner:
                factual_combat_owner_pairs.append((battle_turn, left_owner, right_owner))

        combat_signatures_by_turn: dict[int, set[RelationSignature]] = defaultdict(set)
        combat_signatures_game: set[RelationSignature] = set()
        for battle_turn, owner_a, owner_b in factual_combat_owner_pairs:
            signature = _relation_signature(relations.get(battle_turn - 1, {}), owner_a, owner_b)
            if not _unique_relation_signature(signature):
                continue
            combat_signatures_by_turn[battle_turn].add(signature)
            combat_signatures_game.add(signature)

        turns = sorted({turn for turn, _ship_id in ship_groups})
        for battle_turn in turns:
            if battle_turn - 1 not in turns:
                continue
            before_index, _before_unresolved = _turn_owner_index(ship_groups, battle_turn - 1)
            after_index, _after_unresolved = _turn_owner_index(ship_groups, battle_turn)

            stationary: list[tuple[int, PerspectiveRecord, PerspectiveRecord]] = []
            for ship_id, before_record in before_index.items():
                after_record = after_index.get(ship_id)
                if after_record is None:
                    continue
                before_owner = _positive_owner(before_record.raw)
                after_owner = _positive_owner(after_record.raw)
                before_xy = _xy(before_record.raw)
                after_xy = _xy(after_record.raw)
                if (
                    before_owner is None
                    or after_owner != before_owner
                    or None in before_xy
                    or before_xy != after_xy
                ):
                    continue
                stationary.append((ship_id, before_record, after_record))

            by_xy: dict[tuple[int, int], list[tuple[int, PerspectiveRecord, PerspectiveRecord]]] = defaultdict(list)
            for item in stationary:
                position = _xy(item[1].raw)
                assert position[0] is not None and position[1] is not None
                by_xy[(int(position[0]), int(position[1]))].append(item)

            for (x, y), ships in by_xy.items():
                for left_item, right_item in combinations(sorted(ships, key=lambda item: item[0]), 2):
                    pipeline["stationary_colocated_pairs"] += 1
                    left_id, left_before, left_after = left_item
                    right_id, right_before, right_after = right_item
                    left_owner = _positive_owner(left_before.raw)
                    right_owner = _positive_owner(right_before.raw)
                    assert left_owner is not None and right_owner is not None
                    if left_owner == right_owner:
                        continue
                    pipeline["different_owner_pairs"] += 1

                    matching_fc = _ordinary_exact_matching_fc(left_before.raw, right_before.raw)
                    if matching_fc is None:
                        continue
                    pipeline["ordinary_exact_matching_fc_pairs"] += 1

                    hostility = _hostility_shape(
                        left_raw=left_before.raw,
                        left_owner=left_owner,
                        right_raw=right_before.raw,
                        right_owner=right_owner,
                    )
                    if hostility == "none":
                        continue
                    pipeline["hostile_order_pairs"] += 1

                    left_race = races.get(left_owner)
                    right_race = races.get(right_owner)
                    if left_race is None or right_race is None or BIRD_RACE_ID in {left_race, right_race}:
                        continue
                    pipeline["resolved_nonbird_pairs"] += 1

                    left_hull = _intish(left_before.raw.get("hullid", left_before.raw.get("hull_id")))
                    right_hull = _intish(right_before.raw.get("hullid", right_before.raw.get("hull_id")))
                    if left_hull is None or right_hull is None:
                        continue
                    left_spec = specs.hulls.get(left_hull)
                    right_spec = specs.hulls.get(right_hull)
                    left_can_cloak = left_spec.can_cloak if left_spec is not None else None
                    right_can_cloak = right_spec.can_cloak if right_spec is not None else None
                    if left_can_cloak is not False or right_can_cloak is not False:
                        continue
                    pipeline["known_noncloaking_pairs"] += 1

                    if not (
                        _positive_fuel(left_before.raw)
                        and _positive_fuel(right_before.raw)
                        and _positive_fuel(left_after.raw)
                        and _positive_fuel(right_after.raw)
                        and _alive(left_before.raw)
                        and _alive(right_before.raw)
                        and _alive(left_after.raw)
                        and _alive(right_after.raw)
                        and _armed(left_before.raw)
                        and _armed(right_before.raw)
                    ):
                        continue
                    pipeline["fueled_alive_armed_pairs"] += 1

                    signature = _relation_signature(relations.get(battle_turn - 1, {}), left_owner, right_owner)
                    relation_unique = _unique_relation_signature(signature)
                    if relation_unique:
                        pipeline["unique_relation_pairs"] += 1
                    compatible_game = relation_unique and signature in combat_signatures_game
                    compatible_turn = relation_unique and signature in combat_signatures_by_turn.get(battle_turn, set())
                    if compatible_game:
                        pipeline["relation_combat_compatible_same_game_pairs"] += 1
                    if compatible_turn:
                        pipeline["relation_combat_compatible_same_turn_pairs"] += 1

                    pair_key = frozenset((left_id, right_id))
                    pair_vcr_present = pair_key in pair_vcrs_by_turn.get(battle_turn, set())
                    participants = site_participants.get((battle_turn, x, y), set())
                    either_in_other_ship_vcr = left_id in participants or right_id in participants
                    if not pair_vcr_present:
                        pipeline["pair_vcr_absent_pairs"] += 1
                    if not pair_vcr_present and not either_in_other_ship_vcr:
                        pipeline["isolated_no_ship_vcr_pairs"] += 1

                    if not compatible_game or pair_vcr_present:
                        continue

                    rows.append(
                        {
                            "game_id": game_id,
                            "battle_turn": battle_turn,
                            "x": x,
                            "y": y,
                            "matching_friendly_code": matching_fc,
                            "hostility_shape": hostility,
                            "relation_signature": _safe_signature(signature),
                            "relation_combat_compatible_same_game": compatible_game,
                            "relation_combat_compatible_same_turn": compatible_turn,
                            "pair_vcr_present": pair_vcr_present,
                            "either_ship_in_other_site_ship_vcr": either_in_other_ship_vcr,
                            "isolated_no_ship_vcr": not either_in_other_ship_vcr,
                            "left": _safe_ship(
                                ship_id=left_id,
                                race_id=left_race,
                                hull_id=left_hull,
                                hull_can_cloak=left_can_cloak,
                                before=left_before.raw,
                                after=left_after.raw,
                            ),
                            "right": _safe_ship(
                                ship_id=right_id,
                                race_id=right_race,
                                hull_id=right_hull,
                                hull_can_cloak=right_can_cloak,
                                before=right_before.raw,
                                after=right_after.raw,
                            ),
                        }
                    )

    isolated = [row for row in rows if row["isolated_no_ship_vcr"]]
    same_turn = [row for row in rows if row["relation_combat_compatible_same_turn"]]
    same_turn_isolated = [
        row for row in isolated if row["relation_combat_compatible_same_turn"]
    ]
    return {
        "schema": "planets-lab.combat-host-matching-fc-suppression-audit.v1",
        "read_only": True,
        "summary": {
            "archives_considered": archives_considered,
            "special_game_591478_excluded": True,
            "payload_conflicts": payload_conflicts,
            "pipeline": dict(sorted(pipeline.items())),
            "strict_relation_compatible_pair_vcr_absent_rows": len(rows),
            "strict_isolated_no_ship_vcr_rows": len(isolated),
            "same_turn_relation_compatible_rows": len(same_turn),
            "same_turn_relation_compatible_isolated_rows": len(same_turn_isolated),
            "matching_friendly_code": _serialize(Counter(row["matching_friendly_code"] for row in rows)),
            "hostility_shape": _serialize(Counter(row["hostility_shape"] for row in rows)),
            "games": _serialize(Counter(row["game_id"] for row in rows)),
        },
        "strict_rows": rows[: args.example_limit],
        "isolated_rows": isolated[: args.example_limit],
        "same_turn_rows": same_turn[: args.example_limit],
        "evidence_boundary": (
            "Negative-control audit for documented exact matching-FC ship-combat suppression. Candidates are stationary "
            "owner-current pairs present at the same coordinate in both T-1 and T, with unchanged owners, exact "
            "non-special matching FC, non-Bird resolved races, known non-cloakable hulls, positive fuel before/after, "
            "both ships alive and armed, and Kill!/Primary-Enemy hostility. The strict promoted rows additionally require "
            "a unique raw T-1 diplomacy relation signature that is independently seen in factual ship combat in the same "
            "game, and no factual VCR between the pair. The isolated subset also requires neither ship to appear in any "
            "other ship VCR at that site. This controls common absence-of-VCR confounders without assigning undocumented "
            "numeric diplomacy labels. Game 591478 is excluded."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit strict negative controls for exact matching-FC ship-combat suppression."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT MATCHING FC SUPPRESSION AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("STRICT ROWS:")
    for row in report["strict_rows"]:
        print(row)
    print()
    print("ISOLATED ROWS:")
    for row in report["isolated_rows"]:
        print(row)
    print()
    print("SAME-TURN RELATION CONTROL ROWS:")
    for row in report["same_turn_rows"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: strict negative controls only; numeric diplomacy levels are not assigned semantic labels.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
