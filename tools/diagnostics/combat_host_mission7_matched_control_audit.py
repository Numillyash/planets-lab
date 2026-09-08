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

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import PerspectiveRecord, group_perspective_records
from planets_lab.rules.combat.order import (
    FriendlyCodePriorityKind,
    INTERCEPT_MISSION_ID,
    KILL_MISSION_ID,
    classify_battle_friendly_code,
    standard_battle_priority_key,
)

from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
    _canonical_hash,
    _decode_turn,
    _int,
    _objects,
    _owner_raw,
    _ship_side,
    _static_specs,
)
from combat_host_residual_physical_stack_audit import _turn_owner_index, _xy


TARGET_CASE = (621896, 28, 67)
DEFAULT_EXAMPLE_LIMIT = 20


def _serialize(counter: Counter[Any]) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    }


def _supported_nonmatching_fc(left_raw: Mapping[str, Any], right_raw: Mapping[str, Any]) -> bool:
    left_fc = classify_battle_friendly_code(left_raw.get("friendlycode"))
    right_fc = classify_battle_friendly_code(right_raw.get("friendlycode"))
    return (
        left_fc.kind is not FriendlyCodePriorityKind.UNSUPPORTED
        and right_fc.kind is not FriendlyCodePriorityKind.UNSUPPORTED
        and left_raw.get("friendlycode") != right_raw.get("friendlycode")
    )


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


def _fc_projection(raw: Mapping[str, Any]) -> dict[str, Any]:
    fc_text = raw.get("friendlycode") if isinstance(raw.get("friendlycode"), str) else None
    classified = classify_battle_friendly_code(fc_text)
    return {
        "text": fc_text,
        "kind": classified.kind.value,
        "numeric_value": classified.numeric_value,
        "evidence": classified.evidence,
    }


def _qualifies_noncloaking_targeted_intercept(
    *,
    interceptor_raw: Mapping[str, Any],
    interceptor_owner_id: int,
    interceptor_hull_can_cloak: bool | None,
    opponent_ship_id: int,
    opponent_owner_id: int,
    target_owner_id: int | None,
) -> bool:
    return (
        _intish(interceptor_raw.get("mission")) == INTERCEPT_MISSION_ID
        and _intish(interceptor_raw.get("mission1target")) == opponent_ship_id
        and interceptor_hull_can_cloak is False
        and target_owner_id == opponent_owner_id
        and _intish(interceptor_raw.get("enemy")) == opponent_owner_id
        and interceptor_owner_id > 0
    )


def _case2_shape(
    *,
    interceptor_fc: Mapping[str, Any],
    opponent_fc: Mapping[str, Any],
    opponent_mission: int | None,
    reciprocal_pe: bool,
) -> str:
    if not reciprocal_pe:
        return "not_reciprocal_pe"
    if (
        interceptor_fc.get("kind") == FriendlyCodePriorityKind.NUMERIC.value
        and interceptor_fc.get("numeric_value") == 1
        and opponent_fc.get("kind") == FriendlyCodePriorityKind.SYMBOLIC.value
        and opponent_mission != KILL_MISSION_ID
    ):
        return "case2_exact_order_shape"
    if (
        interceptor_fc.get("kind") == FriendlyCodePriorityKind.NUMERIC.value
        and opponent_fc.get("kind") == FriendlyCodePriorityKind.SYMBOLIC.value
        and opponent_mission != KILL_MISSION_ID
    ):
        return "numeric_vs_symbolic_nonkill"
    return "other_reciprocal_pe"


def _physical_context(
    *,
    ship_groups: Mapping[tuple[int, int], Sequence[PerspectiveRecord]],
    battle_turn: int,
    battle_xy: tuple[int, int],
    pair_ship_ids: set[int],
) -> dict[str, Any]:
    t_index, t_unresolved = _turn_owner_index(ship_groups, battle_turn)
    survivors = [
        ship_id
        for ship_id, record in t_index.items()
        if _xy(record.raw) == battle_xy
    ]
    extras = [ship_id for ship_id in survivors if ship_id not in pair_ship_ids]
    return {
        "t_owner_current_survivor_count": len(survivors),
        "t_pair_survivors": sorted(ship_id for ship_id in survivors if ship_id in pair_ship_ids),
        "t_untracked_survivor_count": len(extras),
        "t_untracked_survivor_ship_ids": sorted(extras),
        "t_unresolved_owner_record_count": len(t_unresolved),
    }


def _safe_side(
    *,
    ship_id: int,
    owner_id: int,
    race_id: int | None,
    hull_id: int,
    hull_can_cloak: bool | None,
    raw: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "race_id": race_id,
        "hull_id": hull_id,
        "hull_can_cloak": hull_can_cloak,
        "mission": _intish(raw.get("mission")),
        "mission1target": _intish(raw.get("mission1target")),
        "enemy": _intish(raw.get("enemy")),
        "friendly_code": _fc_projection(raw),
        "damage": _intish(raw.get("damage")),
        "neutronium": _intish(raw.get("neutronium")),
    }


def _candidate_row(
    *,
    game_id: int,
    battle_turn: int,
    vcr_id: int,
    x: int,
    y: int,
    interceptor_side: str,
    interceptor_ship_id: int,
    interceptor_owner_id: int,
    interceptor_race_id: int | None,
    interceptor_hull_id: int,
    interceptor_hull_can_cloak: bool | None,
    interceptor_raw: Mapping[str, Any],
    opponent_side: str,
    opponent_ship_id: int,
    opponent_owner_id: int,
    opponent_race_id: int | None,
    opponent_hull_id: int,
    opponent_hull_can_cloak: bool | None,
    opponent_raw: Mapping[str, Any],
    standard_relation: str,
    physical_context: Mapping[str, Any],
) -> dict[str, Any]:
    interceptor_fc = _fc_projection(interceptor_raw)
    opponent_fc = _fc_projection(opponent_raw)
    reciprocal_pe = _intish(opponent_raw.get("enemy")) == interceptor_owner_id
    opponent_mission = _intish(opponent_raw.get("mission"))
    shape = _case2_shape(
        interceptor_fc=interceptor_fc,
        opponent_fc=opponent_fc,
        opponent_mission=opponent_mission,
        reciprocal_pe=reciprocal_pe,
    )
    return {
        "game_id": game_id,
        "battle_turn": battle_turn,
        "vcr_id": vcr_id,
        "x": x,
        "y": y,
        "target_case": (game_id, battle_turn, vcr_id) == TARGET_CASE,
        "interceptor_side": interceptor_side,
        "opponent_side": opponent_side,
        "standard_relation": standard_relation,
        "standard_model_factual_right": standard_relation == "right_higher_priority",
        "order_shape": shape,
        "interceptor": _safe_side(
            ship_id=interceptor_ship_id,
            owner_id=interceptor_owner_id,
            race_id=interceptor_race_id,
            hull_id=interceptor_hull_id,
            hull_can_cloak=interceptor_hull_can_cloak,
            raw=interceptor_raw,
        ),
        "opponent": _safe_side(
            ship_id=opponent_ship_id,
            owner_id=opponent_owner_id,
            race_id=opponent_race_id,
            hull_id=opponent_hull_id,
            hull_can_cloak=opponent_hull_can_cloak,
            raw=opponent_raw,
        ),
        "reciprocal_pe": reciprocal_pe,
        "physical_context": dict(physical_context),
    }


def _dedup_vcrs(
    archive_data: bytes,
) -> tuple[dict[tuple[int, int, int], tuple[str, dict[str, Any]]], int]:
    members = turn_members(archive_data)
    raw_members = read_archive_members(archive_data, [member.name for member in members])
    seen: dict[tuple[int, int, int], tuple[str, dict[str, Any]]] = {}
    payload_conflicts = 0
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
    return seen, payload_conflicts


def run(args: argparse.Namespace) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    archives = sorted(args.archive_dir.glob("game-*.zip"))
    payload_conflicts = 0

    for archive_path in archives:
        try:
            archive_game_id = int(archive_path.stem.split("-")[-1])
        except ValueError:
            continue
        if archive_game_id == SPECIAL_GAME_ID:
            continue

        archive_data = archive_path.read_bytes()
        specs = _static_specs(archive_data)
        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=archive_game_id,
            cache_path=args.prepared_dir / f"game-{archive_game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        races, _race_conflicts = _player_races(prepared.snapshots)
        seen, conflicts = _dedup_vcrs(archive_data)
        payload_conflicts += conflicts

        sites: dict[tuple[int, int, int, int], list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
        for (game_id, turn, vcr_id), (_digest, vcr) in seen.items():
            left = _ship_side(vcr, "left")
            right = _ship_side(vcr, "right")
            x = _int(vcr, "x")
            y = _int(vcr, "y")
            if left is None or right is None or x is None or y is None:
                continue
            sites[(game_id, turn, x, y)].append((vcr_id, vcr))

        for (game_id, battle_turn, x, y), queue in sorted(sites.items()):
            if len(queue) != 1:
                continue
            vcr_id, vcr = queue[0]
            left = _ship_side(vcr, "left")
            right = _ship_side(vcr, "right")
            assert left is not None and right is not None

            left_id = int(left["ship_id"])
            right_id = int(right["ship_id"])
            before_turn = battle_turn - 1
            left_owner, left_raw = _owner_raw(ship_groups, before_turn, left_id)
            right_owner, right_raw = _owner_raw(ship_groups, before_turn, right_id)
            if left_raw is None or right_raw is None or left_owner is None or right_owner is None:
                continue

            left_hull = _intish(left_raw.get("hullid", left_raw.get("hull_id")))
            right_hull = _intish(right_raw.get("hullid", right_raw.get("hull_id")))
            if left_hull is None or right_hull is None:
                continue
            if (
                left_owner != left["owner_id"]
                or right_owner != right["owner_id"]
                or left_hull != left["hull_id"]
                or right_hull != right["hull_id"]
            ):
                continue
            if not _supported_nonmatching_fc(left_raw, right_raw):
                continue

            left_spec = specs.hulls.get(left_hull)
            right_spec = specs.hulls.get(right_hull)
            left_can_cloak = left_spec.can_cloak if left_spec is not None else None
            right_can_cloak = right_spec.can_cloak if right_spec is not None else None

            relation = _standard_relation(
                left_raw=left_raw,
                right_raw=right_raw,
                left_ship_id=left_id,
                right_ship_id=right_id,
            )
            if relation == "unsupported":
                continue

            physical = _physical_context(
                ship_groups=ship_groups,
                battle_turn=battle_turn,
                battle_xy=(x, y),
                pair_ship_ids={left_id, right_id},
            )

            side_specs = (
                (
                    "left", left_id, left_owner, left_hull, left_can_cloak, left_raw,
                    "right", right_id, right_owner, right_hull, right_can_cloak, right_raw,
                ),
                (
                    "right", right_id, right_owner, right_hull, right_can_cloak, right_raw,
                    "left", left_id, left_owner, left_hull, left_can_cloak, left_raw,
                ),
            )
            for (
                interceptor_side,
                interceptor_id,
                interceptor_owner,
                interceptor_hull,
                interceptor_can_cloak,
                interceptor_raw,
                opponent_side,
                opponent_id,
                opponent_owner,
                opponent_hull,
                opponent_can_cloak,
                opponent_raw,
            ) in side_specs:
                target_id = _intish(interceptor_raw.get("mission1target"))
                target_owner = None
                if target_id is not None and target_id > 0:
                    target_owner, _ = _owner_raw(ship_groups, before_turn, target_id)
                if not _qualifies_noncloaking_targeted_intercept(
                    interceptor_raw=interceptor_raw,
                    interceptor_owner_id=interceptor_owner,
                    interceptor_hull_can_cloak=interceptor_can_cloak,
                    opponent_ship_id=opponent_id,
                    opponent_owner_id=opponent_owner,
                    target_owner_id=target_owner,
                ):
                    continue
                if _intish(opponent_raw.get("enemy")) != interceptor_owner:
                    continue

                candidates.append(
                    _candidate_row(
                        game_id=game_id,
                        battle_turn=battle_turn,
                        vcr_id=vcr_id,
                        x=x,
                        y=y,
                        interceptor_side=interceptor_side,
                        interceptor_ship_id=interceptor_id,
                        interceptor_owner_id=interceptor_owner,
                        interceptor_race_id=races.get(interceptor_owner),
                        interceptor_hull_id=interceptor_hull,
                        interceptor_hull_can_cloak=interceptor_can_cloak,
                        interceptor_raw=interceptor_raw,
                        opponent_side=opponent_side,
                        opponent_ship_id=opponent_id,
                        opponent_owner_id=opponent_owner,
                        opponent_race_id=races.get(opponent_owner),
                        opponent_hull_id=opponent_hull,
                        opponent_hull_can_cloak=opponent_can_cloak,
                        opponent_raw=opponent_raw,
                        standard_relation=relation,
                        physical_context=physical,
                    )
                )

    target_rows = [row for row in candidates if row["target_case"]]
    controls = [row for row in candidates if not row["target_case"]]
    exact_shape = [row for row in candidates if row["order_shape"] == "case2_exact_order_shape"]
    numeric_symbolic = [
        row for row in candidates
        if row["order_shape"] in {"case2_exact_order_shape", "numeric_vs_symbolic_nonkill"}
    ]
    no_t_extras = [
        row for row in candidates
        if int(row["physical_context"]["t_untracked_survivor_count"]) == 0
    ]

    def relation_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
        return _serialize(Counter(str(row["standard_relation"]) for row in rows))

    return {
        "schema": "planets-lab.combat-host-mission7-matched-control-audit.v1",
        "read_only": True,
        "summary": {
            "archives_considered": sum(
                1 for path in archives if path.name != f"game-{SPECIAL_GAME_ID}.zip"
            ),
            "payload_conflicts": payload_conflicts,
            "candidate_rows": len(candidates),
            "target_case_rows": len(target_rows),
            "control_rows": len(controls),
            "standard_relation": relation_counts(candidates),
            "interceptor_side": _serialize(Counter(str(row["interceptor_side"]) for row in candidates)),
            "order_shape": _serialize(Counter(str(row["order_shape"]) for row in candidates)),
            "exact_case2_shape_relation": relation_counts(exact_shape),
            "numeric_vs_symbolic_nonkill_relation": relation_counts(numeric_symbolic),
            "no_t_extra_survivor_relation": relation_counts(no_t_extras),
            "interceptor_race_id": _serialize(
                Counter(str(row["interceptor"]["race_id"]) for row in candidates)
            ),
            "interceptor_hull_id": _serialize(
                Counter(str(row["interceptor"]["hull_id"]) for row in candidates)
            ),
        },
        "target_case": target_rows,
        "exact_case2_shape_examples": exact_shape[: args.example_limit],
        "numeric_vs_symbolic_nonkill_examples": numeric_symbolic[: args.example_limit],
        "control_examples": controls[: args.example_limit],
        "evidence_boundary": (
            "Matched-control diagnostic only. Population is restricted to ordinary one-VCR ship-vs-ship sites "
            "with supported nonmatching FCs where a non-cloakable mission-7 ship targets the factual opponent, "
            "its Primary Enemy matches that opponent owner, and the opponent has reciprocal Primary Enemy. "
            "A zero T extra-survivor count is a useful cleanliness signal but is not proof that no third ship "
            "was present earlier in Host. No Intercept-specific side rule is inferred from counts alone."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build ordinary matched controls for the remaining non-cloakable mission-7 side residual."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT MISSION7 MATCHED CONTROL AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("TARGET CASE:")
    for row in report["target_case"]:
        print(row)
    print()
    print("EXACT CASE2 ORDER-SHAPE EXAMPLES:")
    for row in report["exact_case2_shape_examples"]:
        print(row)
    print()
    print("NUMERIC-vs-SYMBOLIC NONKILL EXAMPLES:")
    for row in report["numeric_vs_symbolic_nonkill_examples"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: matched controls only; no combat rule or evidence status is promoted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
