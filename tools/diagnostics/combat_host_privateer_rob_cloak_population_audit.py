from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records

from combat_host_candidate_set_audit import _owner_rows_for_turn, _pair, _serialize
from combat_host_initial_standard_target_cloak_residual_audit import (
    _basic_cloak_fuel_cost,
    _boolish,
)
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_mission7_matched_control_audit import _dedup_vcrs
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
    _owner_raw,
    _ship_side,
    _static_specs,
)


SCHEMA = "planets-lab.combat-host-privateer-rob-cloak-population-audit.v1"
PRIVATEER_RACE_ID = 5
RACE_SPECIFIC_MISSION_ID = 9
TARGET_RESIDUAL = (360690, 82, 83, 98)
DEFAULT_EXAMPLE_LIMIT = 80

# Static/equipment identity fields only. Cargo, fuel, ammo quantity, damage,
# crew and mission are deliberately excluded because Host may legitimately
# mutate them while the physical ship remains the same object.
EQUIPMENT_FIELDS = (
    "hullid",
    "engineid",
    "beamid",
    "beams",
    "torpedoid",
    "bays",
)


def _equipment_signature(raw: Mapping[str, Any]) -> tuple[int | None, ...]:
    return tuple(_intish(raw.get(field)) for field in EQUIPMENT_FIELDS)


def _stable_identity(
    *,
    before_owner: int | None,
    before_raw: Mapping[str, Any],
    after_owner: int | None,
    after_raw: Mapping[str, Any] | None,
) -> bool | None:
    """Conservatively decide whether consecutive records are the same physical ship.

    Same Ship ID is insufficient because post-combat build can reuse a freed ID.
    Require owner, static hull/equipment and, when present, the ship build-turn
    marker to remain aligned. Missing identity fields fail closed to ``None``.
    """

    if after_raw is None or before_owner is None or after_owner is None:
        return None
    if before_owner <= 0 or after_owner <= 0:
        return None
    if before_owner != after_owner:
        return False

    before_sig = _equipment_signature(before_raw)
    after_sig = _equipment_signature(after_raw)
    if any(value is None for value in before_sig + after_sig):
        return None
    if before_sig != after_sig:
        return False

    before_build_turn = _intish(before_raw.get("turn"))
    after_build_turn = _intish(after_raw.get("turn"))
    if before_build_turn is not None and after_build_turn is not None:
        if before_build_turn != after_build_turn:
            return False
    elif before_build_turn is not None or after_build_turn is not None:
        return None

    return True


def _cloak_transition(before: Any, after: Any) -> str:
    def label(value: Any) -> str:
        flag = _boolish(value)
        if flag is True:
            return "true"
        if flag is False:
            return "false"
        return "unknown"

    return f"{label(before)}_to_{label(after)}"


def _vcr_participation(
    *,
    game_id: int,
    seen: Mapping[Any, Any],
) -> Mapping[tuple[int, int], tuple[dict[str, Any], ...]]:
    rows: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for (seen_game, battle_turn, vcr_id), (_digest, vcr) in sorted(seen.items()):
        if int(seen_game) != int(game_id):
            continue
        left = _ship_side(vcr, "left")
        right = _ship_side(vcr, "right")
        if left is None or right is None:
            continue
        left_id = int(left["ship_id"])
        right_id = int(right["ship_id"])
        pair = _pair(left_id, right_id)
        rows[(int(battle_turn), left_id)].append(
            {
                "vcr_id": int(vcr_id),
                "pair": list(pair),
                "side": "left",
                "opponent_ship_id": right_id,
                "opponent_owner_id": right.get("owner_id"),
            }
        )
        rows[(int(battle_turn), right_id)].append(
            {
                "vcr_id": int(vcr_id),
                "pair": list(pair),
                "side": "right",
                "opponent_ship_id": left_id,
                "opponent_owner_id": left.get("owner_id"),
            }
        )
    return {key: tuple(value) for key, value in rows.items()}


def _safe_ship_excerpt(
    *,
    raw: Mapping[str, Any],
    hull_name: str | None,
    hull_can_cloak: bool | None,
    hull_mass: int | None,
) -> dict[str, Any]:
    fuel = _intish(raw.get("neutronium"))
    cloak_cost = _basic_cloak_fuel_cost(hull_mass)
    return {
        "ownerid": _intish(raw.get("ownerid", raw.get("owner_id"))),
        "hullid": _intish(raw.get("hullid", raw.get("hull_id"))),
        "hull_name": hull_name,
        "hull_can_cloak": hull_can_cloak,
        "mission": _intish(raw.get("mission")),
        "enemy": _intish(raw.get("enemy")),
        "friendlycode": raw.get("friendlycode"),
        "iscloaked": _boolish(raw.get("iscloaked")),
        "fuel": fuel,
        "damage": _intish(raw.get("damage")),
        "x": _intish(raw.get("x")),
        "y": _intish(raw.get("y")),
        "build_turn": _intish(raw.get("turn")),
        "cloak_reference_cost": cloak_cost,
        "cloak_reference_fuel_sufficient": (
            None if fuel is None or cloak_cost is None else fuel >= cloak_cost
        ),
        "equipment_signature": list(_equipment_signature(raw)),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    totals: Counter[str] = Counter()
    transitions: Counter[str] = Counter()
    games: Counter[int] = Counter()
    hulls: Counter[int] = Counter()
    rows: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []

    for archive_path in sorted(args.archive_dir.glob("game-*.zip")):
        try:
            game_id = int(archive_path.stem.split("-")[-1])
        except ValueError:
            continue
        if game_id == SPECIAL_GAME_ID:
            continue
        totals["archives_considered"] += 1

        archive_data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=args.prepared_dir / f"game-{game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        races, race_conflicts = _player_races(prepared.snapshots)
        if race_conflicts:
            totals["race_conflict_games"] += 1
        specs = _static_specs(archive_data)
        seen, conflicts = _dedup_vcrs(archive_data)
        totals["payload_conflicts"] += int(conflicts)
        vcrs = _vcr_participation(game_id=game_id, seen=seen)

        before_turns = sorted({turn for turn, _ship_id in ship_groups})
        for before_turn in before_turns:
            owner_rows = _owner_rows_for_turn(ship_groups, before_turn)
            for ship_id, (owner_id, before_raw) in sorted(owner_rows.items()):
                if races.get(owner_id) != PRIVATEER_RACE_ID:
                    continue
                if _intish(before_raw.get("mission")) != RACE_SPECIFIC_MISSION_ID:
                    continue

                hull_id = _intish(before_raw.get("hullid", before_raw.get("hull_id")))
                hull = specs.hulls.get(hull_id) if hull_id is not None else None
                if hull is None or not hull.can_cloak:
                    continue

                battle_turn = before_turn + 1
                after_owner, after_raw = _owner_raw(ship_groups, battle_turn, ship_id)
                identity = _stable_identity(
                    before_owner=owner_id,
                    before_raw=before_raw,
                    after_owner=after_owner,
                    after_raw=after_raw,
                )
                transition = _cloak_transition(
                    before_raw.get("iscloaked"),
                    after_raw.get("iscloaked") if after_raw is not None else None,
                )
                participation = vcrs.get((battle_turn, ship_id), ())
                pe = _intish(before_raw.get("enemy"))
                pe_zero = pe is None or pe <= 0
                is_target = (game_id, before_turn, battle_turn, ship_id) == TARGET_RESIDUAL

                totals["candidate_rows"] += 1
                games[game_id] += 1
                if hull_id is not None:
                    hulls[hull_id] += 1
                before_cloak = _boolish(before_raw.get("iscloaked"))
                totals[
                    "before_cloak_true"
                    if before_cloak is True
                    else ("before_cloak_false" if before_cloak is False else "before_cloak_unknown")
                ] += 1
                if after_raw is None:
                    totals["next_turn_owner_current_missing"] += 1
                if identity is True:
                    totals["stable_identity"] += 1
                    transitions[transition] += 1
                    totals["stable_vcr_participant" if participation else "stable_no_vcr"] += 1
                    if before_cloak is True and pe_zero:
                        totals[
                            "stable_before_cloaked_pe_zero_vcr"
                            if participation
                            else "stable_before_cloaked_pe_zero_no_vcr"
                        ] += 1
                    if transition == "true_to_true" and pe_zero:
                        totals[
                            "stable_true_to_true_pe_zero_vcr"
                            if participation
                            else "stable_true_to_true_pe_zero_no_vcr"
                        ] += 1
                elif identity is False:
                    totals["identity_mismatch"] += 1
                else:
                    totals["identity_unresolved"] += 1

                row = {
                    "game_id": game_id,
                    "before_turn": before_turn,
                    "battle_turn": battle_turn,
                    "ship_id": ship_id,
                    "owner_id": owner_id,
                    "race_id": PRIVATEER_RACE_ID,
                    "primary_enemy": pe,
                    "primary_enemy_zero": pe_zero,
                    "stable_identity": identity,
                    "cloak_transition": transition,
                    "vcr_participant": bool(participation),
                    "vcrs": list(participation),
                    "is_target_residual": is_target,
                    "before": _safe_ship_excerpt(
                        raw=before_raw,
                        hull_name=hull.name,
                        hull_can_cloak=hull.can_cloak,
                        hull_mass=hull.mass,
                    ),
                    "after_owner_id": after_owner,
                    "after": (
                        _safe_ship_excerpt(
                            raw=after_raw,
                            hull_name=(
                                specs.hulls.get(_intish(after_raw.get("hullid", after_raw.get("hull_id")))).name
                                if _intish(after_raw.get("hullid", after_raw.get("hull_id"))) in specs.hulls
                                else None
                            ),
                            hull_can_cloak=(
                                specs.hulls.get(_intish(after_raw.get("hullid", after_raw.get("hull_id")))).can_cloak
                                if _intish(after_raw.get("hullid", after_raw.get("hull_id"))) in specs.hulls
                                else None
                            ),
                            hull_mass=(
                                specs.hulls.get(_intish(after_raw.get("hullid", after_raw.get("hull_id")))).mass
                                if _intish(after_raw.get("hullid", after_raw.get("hull_id"))) in specs.hulls
                                else None
                            ),
                        )
                        if after_raw is not None
                        else None
                    ),
                }
                if is_target:
                    target_rows.append(row)
                if len(rows) < args.example_limit:
                    if is_target or identity is not True or before_cloak is True or participation:
                        rows.append(row)

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            **_serialize(totals),
            "cloak_transitions_stable": _serialize(transitions),
            "games": _serialize(games),
            "hulls": _serialize(hulls),
            "target_residual_rows": len(target_rows),
        },
        "target_residual": target_rows,
        "examples": rows,
        "evidence_boundary": (
            "Population-level transition audit for archive-resolved Privateer race 5, race-specific mission 9, "
            "cloak-capable hull records. It does not assert that mission 9 causes or preserves cloak. T-1/T "
            "iscloaked transitions are attribution evidence only. Same Ship ID is accepted as stable only when "
            "owner, hull/equipment and available build-turn identity remain aligned; post-combat ID reuse is otherwise "
            "kept out. VCR participation is observational and does not by itself establish attack direction. No combat "
            "eligibility or target-order rule is changed by this diagnostic."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit Privateer race-specific mission-9 cloak-state transitions around Host combat."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT PRIVATEER ROB CLOAK POPULATION AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("TARGET RESIDUAL:")
    for row in report["target_residual"]:
        print(row)
    print()
    print("EXAMPLES:")
    for row in report["examples"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: Privateer mission-9 cloak transition population only; no cloak blocker is promoted by this tool.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
