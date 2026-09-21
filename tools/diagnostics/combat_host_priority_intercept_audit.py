from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.normalizer import _decode_member_json
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import PerspectiveRecord, group_perspective_records
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.data.nu_static import import_static_all
from planets_lab.rules.combat.order import (
    INTERCEPT_MISSION_ID,
    classify_battle_friendly_code,
    priority_intercept_order_signature,
    standard_battle_priority_key,
    FriendlyCodePriorityKind,
)

RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
SPECIAL_GAME_ID = 591478


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _decode_turn(raw: bytes, member_name: str) -> dict[str, Any]:
    payload = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    parsed = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{member_name}: turn payload must be an object")
    return parsed


def _objects(record: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = record.get(key)
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _int(record: Mapping[str, Any] | None, key: str) -> int | None:
    if not isinstance(record, Mapping):
        return None
    return _intish(record.get(key))


def _static_specs(archive_data: bytes) -> NuStaticSpecs:
    members = turn_members(archive_data)
    if not members:
        raise ValueError("archive contains no .trn members")
    member = members[0]
    raw = read_archive_members(archive_data, [member.name])[member.name]
    payload, _ = _decode_member_json(raw, member)
    return NuStaticSpecs.from_catalog(import_static_all(payload))


def _owner_raw(
    ship_groups: Mapping[tuple[int, int], Sequence[PerspectiveRecord]],
    turn: int,
    ship_id: int,
) -> tuple[int | None, Mapping[str, Any] | None]:
    owner_id, record = _owner_record(ship_groups.get((turn, ship_id), ()))
    return owner_id, record.raw if record is not None else None


def _ship_side(vcr: Mapping[str, Any], side: str) -> dict[str, Any] | None:
    raw = vcr.get(side)
    if not isinstance(raw, Mapping):
        return None
    ship_id = _int(raw, "objectid")
    hull_id = _int(raw, "hullid")
    if ship_id is None or hull_id is None or hull_id <= 0:
        return None
    owner_key = "leftownerid" if side == "left" else "rightownerid"
    return {
        "ship_id": ship_id,
        "hull_id": hull_id,
        "owner_id": _int(vcr, owner_key),
    }


def _serialize(counter: Counter[Any]) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    }


def _pia_side_classification(
    *,
    raw: Mapping[str, Any],
    opponent_ship_id: int,
    target_owner_id: int | None,
    hull_can_cloak: bool | None,
) -> str:
    mission = _intish(raw.get("mission"))
    if mission != INTERCEPT_MISSION_ID:
        return "not_intercept"

    target_id = _intish(raw.get("mission1target"))
    signature = priority_intercept_order_signature(
        mission=mission,
        mission_target_id=target_id,
        primary_enemy=_intish(raw.get("enemy")),
        target_owner_id=target_owner_id,
        hull_can_cloak=hull_can_cloak,
    )
    if signature is None:
        return "signature_unknown"
    if not signature:
        return "nonqualifying_intercept"
    if target_id == opponent_ship_id:
        return "targets_factual_opponent"
    return "targets_other_ship"


def _standard_relation(
    *,
    left_raw: Mapping[str, Any],
    right_raw: Mapping[str, Any],
    left_ship_id: int,
    right_ship_id: int,
) -> str:
    left_key = standard_battle_priority_key(
        ship_id=left_ship_id,
        mission=_intish(left_raw.get("mission")),
        primary_enemy=_intish(left_raw.get("enemy")),
        friendly_code=left_raw.get("friendlycode"),
    )
    right_key = standard_battle_priority_key(
        ship_id=right_ship_id,
        mission=_intish(right_raw.get("mission")),
        primary_enemy=_intish(right_raw.get("enemy")),
        friendly_code=right_raw.get("friendlycode"),
    )
    if left_key is None or right_key is None:
        return "unsupported"
    if right_key < left_key:
        return "right_higher_priority"
    if left_key < right_key:
        return "left_higher_priority"
    return "priority_tie"


def _pair_key(left_ship_id: int, right_ship_id: int) -> tuple[int, int]:
    return tuple(sorted((left_ship_id, right_ship_id)))


def _site_pia_summary(queue: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize an already-enriched ship-vs-ship queue.

    Each queue row must contain `vcr_id`, `pair`, `pia_attackers`, and side ship
    ids. `pia_attackers` is the set/list of ships whose T-1 orders qualify for
    Priority Intercept specifically against the other member of that pair.
    """

    ordered = sorted(queue, key=lambda row: int(row["vcr_id"]))
    pair_attackers: dict[tuple[int, int], set[int]] = defaultdict(set)
    first_pair_vcr: dict[tuple[int, int], int] = {}
    first_pair_row: dict[tuple[int, int], Mapping[str, Any]] = {}

    for row in ordered:
        pair_raw = row["pair"]
        pair = (int(pair_raw[0]), int(pair_raw[1]))
        pair_attackers[pair].update(int(value) for value in row.get("pia_attackers", ()))
        if pair not in first_pair_vcr:
            first_pair_vcr[pair] = int(row["vcr_id"])
            first_pair_row[pair] = row

    linked_pairs = {pair for pair, attackers in pair_attackers.items() if attackers}
    ambiguous_pairs = {pair for pair, attackers in pair_attackers.items() if len(attackers) > 1}

    linked_flags = [
        (tuple(int(value) for value in row["pair"]) in linked_pairs)
        for row in ordered
    ]
    seen_non_pia = False
    prefix_violation = False
    for linked in linked_flags:
        if not linked:
            seen_non_pia = True
        elif seen_non_pia:
            prefix_violation = True
            break

    unique_attacker_pairs = {
        pair: next(iter(attackers))
        for pair, attackers in pair_attackers.items()
        if len(attackers) == 1
    }
    attacker_first_vcr: dict[int, int] = {}
    for pair, attacker in unique_attacker_pairs.items():
        vcr_id = first_pair_vcr[pair]
        attacker_first_vcr[attacker] = min(vcr_id, attacker_first_vcr.get(attacker, vcr_id))

    factual_attacker_order = [
        attacker
        for attacker, _vcr in sorted(attacker_first_vcr.items(), key=lambda item: item[1])
    ]
    expected_reverse_id = sorted(attacker_first_vcr, reverse=True)
    reverse_id_comparable = len(factual_attacker_order) >= 2 and not ambiguous_pairs
    reverse_id_exact = (
        factual_attacker_order == expected_reverse_id
        if reverse_id_comparable
        else None
    )

    attacker_sides: Counter[str] = Counter()
    for pair, attacker in unique_attacker_pairs.items():
        row = first_pair_row[pair]
        left_id = int(row["left_ship_id"])
        right_id = int(row["right_ship_id"])
        if attacker == right_id:
            attacker_sides["attacker_right"] += 1
        elif attacker == left_id:
            attacker_sides["attacker_left"] += 1
        else:
            attacker_sides["attacker_not_in_first_pair_vcr"] += 1

    return {
        "pia_linked_pairs": len(linked_pairs),
        "pia_ambiguous_pairs": len(ambiguous_pairs),
        "prefix_violation": prefix_violation,
        "attacker_sides": _serialize(attacker_sides),
        "factual_first_attacker_order": factual_attacker_order,
        "expected_reverse_ship_id_order": expected_reverse_id,
        "reverse_id_comparable": reverse_id_comparable,
        "reverse_id_exact": reverse_id_exact,
    }


def _mission7_population_row(
    *,
    game_id: int,
    turn: int,
    ship_id: int,
    owner_id: int | None,
    raw: Mapping[str, Any],
    ship_groups: Mapping[tuple[int, int], Sequence[PerspectiveRecord]],
    specs: NuStaticSpecs,
) -> dict[str, Any]:
    target_id = _intish(raw.get("mission1target"))
    target_owner: int | None = None
    if target_id is not None and target_id > 0:
        target_owner, _target_raw = _owner_raw(ship_groups, turn, target_id)
    hull_id = _intish(raw.get("hullid", raw.get("hull_id")))
    hull = specs.hulls.get(hull_id) if hull_id is not None else None
    can_cloak = hull.can_cloak if hull is not None else None
    signature = priority_intercept_order_signature(
        mission=INTERCEPT_MISSION_ID,
        mission_target_id=target_id,
        primary_enemy=_intish(raw.get("enemy")),
        target_owner_id=target_owner,
        hull_can_cloak=can_cloak,
    )
    if target_id is None or target_id <= 0:
        target_relation = "zero_or_missing"
    elif target_owner is None:
        target_relation = "owner_unresolved"
    elif target_owner == owner_id:
        target_relation = "same_owner"
    else:
        target_relation = "other_owner"
    return {
        "game_id": game_id,
        "turn": turn,
        "ship_id": ship_id,
        "owner_id": owner_id,
        "hull_id": hull_id,
        "hull_can_cloak": can_cloak,
        "mission1target": target_id,
        "enemy": _intish(raw.get("enemy")),
        "target_owner_id": target_owner,
        "target_relation": target_relation,
        "signature": signature,
    }


def _population_scope(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(rows),
        "games": _serialize(Counter(row["game_id"] for row in rows)),
        "hull_can_cloak": _serialize(Counter(str(row.get("hull_can_cloak")) for row in rows)),
        "target_relation": _serialize(Counter(str(row.get("target_relation")) for row in rows)),
        "signature": _serialize(Counter(str(row.get("signature")) for row in rows)),
    }


def _scope_sites(sites: Sequence[Mapping[str, Any]], example_limit: int) -> dict[str, Any]:
    site_counts = Counter()
    attacker_sides = Counter()
    isolated_classes = Counter()
    isolated_non_pia_standard = Counter()
    reverse_counts = Counter()
    examples: list[dict[str, Any]] = []

    for site in sites:
        summary = site["pia_summary"]
        queue = site["ship_queue"]
        if summary["pia_linked_pairs"]:
            site_counts["sites_with_pia_linked_pair"] += 1
        if summary["prefix_violation"]:
            site_counts["pia_prefix_violation"] += 1
        elif summary["pia_linked_pairs"]:
            site_counts["pia_prefix_exact"] += 1

        attacker_sides.update(summary["attacker_sides"])
        if summary["reverse_id_comparable"]:
            if summary["reverse_id_exact"]:
                reverse_counts["reverse_id_exact"] += 1
            else:
                reverse_counts["reverse_id_mismatch"] += 1

        if len(queue) == 1:
            row = queue[0]
            left_class = str(row["left_pia"])
            right_class = str(row["right_pia"])
            left_target = left_class == "targets_factual_opponent"
            right_target = right_class == "targets_factual_opponent"
            if left_target and right_target:
                isolated_classes["mutual_pia"] += 1
            elif left_target:
                isolated_classes["pia_left"] += 1
            elif right_target:
                isolated_classes["pia_right"] += 1
            elif left_class == "signature_unknown" or right_class == "signature_unknown":
                isolated_classes["pia_signature_unknown"] += 1
            elif left_class != "not_intercept" or right_class != "not_intercept":
                isolated_classes["mission7_non_pia"] += 1
                left_raw = row.get("left_raw")
                right_raw = row.get("right_raw")
                if isinstance(left_raw, Mapping) and isinstance(right_raw, Mapping):
                    left_fc = classify_battle_friendly_code(left_raw.get("friendlycode"))
                    right_fc = classify_battle_friendly_code(right_raw.get("friendlycode"))
                    if (
                        left_fc.kind is not FriendlyCodePriorityKind.UNSUPPORTED
                        and right_fc.kind is not FriendlyCodePriorityKind.UNSUPPORTED
                        and left_raw.get("friendlycode") != right_raw.get("friendlycode")
                    ):
                        isolated_non_pia_standard[_standard_relation(
                            left_raw=left_raw,
                            right_raw=right_raw,
                            left_ship_id=int(row["left_ship_id"]),
                            right_ship_id=int(row["right_ship_id"]),
                        )] += 1

        if (
            (summary["prefix_violation"] or summary["reverse_id_exact"] is False)
            and len(examples) < example_limit
        ):
            examples.append(
                {
                    "game_id": site["game_id"],
                    "turn": site["turn"],
                    "x": site["x"],
                    "y": site["y"],
                    "pia_summary": summary,
                    "queue": [
                        {
                            "vcr_id": row["vcr_id"],
                            "left_ship_id": row["left_ship_id"],
                            "right_ship_id": row["right_ship_id"],
                            "left_pia": row["left_pia"],
                            "right_pia": row["right_pia"],
                            "pia_attackers": list(row["pia_attackers"]),
                        }
                        for row in queue
                    ],
                }
            )

    return {
        "sites": len(sites),
        "site_counts": _serialize(site_counts),
        "pia_attacker_sides": _serialize(attacker_sides),
        "isolated_mission7_classes": _serialize(isolated_classes),
        "isolated_non_pia_standard_priority": _serialize(isolated_non_pia_standard),
        "multi_attacker_reverse_id": _serialize(reverse_counts),
        "examples": examples,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    population_rows: list[dict[str, Any]] = []
    sites_out: list[dict[str, Any]] = []
    payload_conflicts = 0
    archives = sorted(args.archive_dir.glob("game-*.zip"))

    for archive_path in archives:
        try:
            archive_game_id = int(archive_path.stem.split("-")[-1])
        except ValueError:
            continue
        data = archive_path.read_bytes()
        specs = _static_specs(data)
        prepared, _ = load_or_build_prepared_game_cache(
            data,
            game_id=archive_game_id,
            cache_path=args.prepared_dir / f"game-{archive_game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")

        for (turn, ship_id), group in sorted(ship_groups.items()):
            owner_id, owner_record = _owner_record(group)
            if owner_record is None or _intish(owner_record.raw.get("mission")) != INTERCEPT_MISSION_ID:
                continue
            population_rows.append(
                _mission7_population_row(
                    game_id=archive_game_id,
                    turn=turn,
                    ship_id=ship_id,
                    owner_id=owner_id,
                    raw=owner_record.raw,
                    ship_groups=ship_groups,
                    specs=specs,
                )
            )

        members = turn_members(data)
        raw_members = read_archive_members(data, [member.name for member in members])
        seen: dict[tuple[int, int, int], tuple[str, dict[str, Any]]] = {}
        for member in members:
            try:
                rst = _decode_turn(raw_members[member.name], member.name)
            except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            game = rst.get("game")
            game_id = _int(game, "id")
            game_turn = _int(game, "turn")
            if game_id is None or game_turn is None:
                continue
            for vcr in _objects(rst, "vcrs"):
                vcr_id = _int(vcr, "id")
                battle_turn = _int(vcr, "turn") or game_turn
                x = _int(vcr, "x")
                y = _int(vcr, "y")
                if vcr_id is None or x is None or y is None:
                    continue
                key = (game_id, battle_turn, vcr_id)
                digest = _canonical_hash(vcr)
                existing = seen.get(key)
                if existing is None:
                    seen[key] = (digest, vcr)
                elif existing[0] != digest:
                    payload_conflicts += 1

        by_site: dict[tuple[int, int, int, int], list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
        for (game_id, turn, vcr_id), (_digest, vcr) in seen.items():
            x = _int(vcr, "x")
            y = _int(vcr, "y")
            if x is None or y is None:
                continue
            left = _ship_side(vcr, "left")
            right = _ship_side(vcr, "right")
            if left is None or right is None:
                continue
            by_site[(game_id, turn, x, y)].append((vcr_id, vcr))

        for (game_id, turn, x, y), raw_queue in by_site.items():
            ship_queue: list[dict[str, Any]] = []
            before_turn = turn - 1
            for vcr_id, vcr in sorted(raw_queue, key=lambda item: item[0]):
                left = _ship_side(vcr, "left")
                right = _ship_side(vcr, "right")
                assert left is not None and right is not None
                left_id = int(left["ship_id"])
                right_id = int(right["ship_id"])
                left_owner, left_raw = _owner_raw(ship_groups, before_turn, left_id)
                right_owner, right_raw = _owner_raw(ship_groups, before_turn, right_id)

                row: dict[str, Any] = {
                    "vcr_id": vcr_id,
                    "left_ship_id": left_id,
                    "right_ship_id": right_id,
                    "pair": _pair_key(left_id, right_id),
                    "pia_attackers": (),
                    "left_pia": "identity_unready",
                    "right_pia": "identity_unready",
                }
                if left_raw is None or right_raw is None:
                    ship_queue.append(row)
                    continue
                left_hull = _intish(left_raw.get("hullid", left_raw.get("hull_id")))
                right_hull = _intish(right_raw.get("hullid", right_raw.get("hull_id")))
                if (
                    left_owner != left["owner_id"]
                    or right_owner != right["owner_id"]
                    or left_hull != left["hull_id"]
                    or right_hull != right["hull_id"]
                ):
                    ship_queue.append(row)
                    continue

                left_spec = specs.hulls.get(left_hull) if left_hull is not None else None
                right_spec = specs.hulls.get(right_hull) if right_hull is not None else None
                left_target_id = _intish(left_raw.get("mission1target"))
                right_target_id = _intish(right_raw.get("mission1target"))
                left_target_owner: int | None = None
                right_target_owner: int | None = None
                if left_target_id is not None and left_target_id > 0:
                    left_target_owner, _ = _owner_raw(ship_groups, before_turn, left_target_id)
                if right_target_id is not None and right_target_id > 0:
                    right_target_owner, _ = _owner_raw(ship_groups, before_turn, right_target_id)

                left_pia = _pia_side_classification(
                    raw=left_raw,
                    opponent_ship_id=right_id,
                    target_owner_id=left_target_owner,
                    hull_can_cloak=left_spec.can_cloak if left_spec is not None else None,
                )
                right_pia = _pia_side_classification(
                    raw=right_raw,
                    opponent_ship_id=left_id,
                    target_owner_id=right_target_owner,
                    hull_can_cloak=right_spec.can_cloak if right_spec is not None else None,
                )
                attackers: list[int] = []
                if left_pia == "targets_factual_opponent":
                    attackers.append(left_id)
                if right_pia == "targets_factual_opponent":
                    attackers.append(right_id)
                row.update(
                    {
                        "left_pia": left_pia,
                        "right_pia": right_pia,
                        "pia_attackers": tuple(attackers),
                        "left_raw": dict(left_raw),
                        "right_raw": dict(right_raw),
                    }
                )
                ship_queue.append(row)

            if not ship_queue:
                continue
            summary = _site_pia_summary(ship_queue)
            sites_out.append(
                {
                    "game_id": game_id,
                    "turn": turn,
                    "x": x,
                    "y": y,
                    "ship_queue": ship_queue,
                    "pia_summary": summary,
                }
            )

    ordinary_population = [row for row in population_rows if row["game_id"] != SPECIAL_GAME_ID]
    special_population = [row for row in population_rows if row["game_id"] == SPECIAL_GAME_ID]
    ordinary_sites = [site for site in sites_out if site["game_id"] != SPECIAL_GAME_ID]
    special_sites = [site for site in sites_out if site["game_id"] == SPECIAL_GAME_ID]

    return {
        "schema": "planets-lab.combat-host-priority-intercept-audit.v1",
        "read_only": True,
        "summary": {
            "archives": len(archives),
            "mission7_records": len(population_rows),
            "ship_combat_sites": len(sites_out),
            "payload_conflicts": payload_conflicts,
        },
        "population": {
            "ordinary": _population_scope(ordinary_population),
            "game_591478": _population_scope(special_population),
            "all": _population_scope(population_rows),
        },
        "combat": {
            "ordinary": _scope_sites(ordinary_sites, args.example_limit),
            "game_591478": _scope_sites(special_sites, args.example_limit),
            "all": _scope_sites(sites_out, args.example_limit),
        },
        "evidence_boundary": (
            "This audit recognizes only the documented static Priority Intercept order signature: mission 7, "
            "installed cloak capability, positive intercept target, and Primary Enemy matching the target owner. "
            "It then compares that signature with factual VCR pair/queue placement. It does not assume that the "
            "priority actually applies when Intercept Interference, diplomacy, fuel, matching FC or other dynamic "
            "combat suppressors are present. Residuals are evidence for later classification, not auto-fit rules."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Priority Intercept order signatures against factual combat queues.")
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=50)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST PRIORITY INTERCEPT AUDIT =====")
    print(f"summary: {report['summary']}")
    for scope_name in ("ordinary", "game_591478", "all"):
        print()
        print(f"===== POPULATION {scope_name} =====")
        for key, value in report["population"][scope_name].items():
            print(f"{key}: {value}")
        print(f"===== COMBAT {scope_name} =====")
        combat = report["combat"][scope_name]
        for key in (
            "sites",
            "site_counts",
            "pia_attacker_sides",
            "isolated_mission7_classes",
            "isolated_non_pia_standard_priority",
            "multi_attacker_reverse_id",
        ):
            print(f"{key}: {combat[key]}")
        if combat["examples"]:
            print("examples:")
            for row in combat["examples"]:
                print(json.dumps(row, sort_keys=True))
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: PIA signature/queue differential only; dynamic Intercept Interference and full engagement eligibility remain separate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
