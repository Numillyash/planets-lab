from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.combat.order import BIRD_RACE_ID

from combat_host_candidate_set_audit import _owner_rows_for_turn
from combat_host_initial_standard_target_residual_audit import TARGETS
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_mission7_matched_control_audit import _dedup_vcrs
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR, _owner_raw, _static_specs


SCHEMA = "planets-lab.combat-host-initial-standard-target-cloak-residual-audit.v1"
RACE_SPECIFIC_MISSION_ID = 9


def _boolish(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "y"}:
            return True
        if text in {"0", "false", "no", "n"}:
            return False
    return None


def _basic_cloak_fuel_cost(hull_mass: int | None) -> int | None:
    """Return the documented ordinary cloak fuel cost for a hull mass.

    Advanced Cloak can reduce the actual cost to zero, so this is a conservative
    ordinary-device reference value rather than a generic effective-cloak solver.
    """

    if hull_mass is None or hull_mass < 0:
        return None
    return max(5, hull_mass // 20)


def _super_spy_cloak_signature(
    *,
    race_id: int | None,
    mission: int | None,
    hull_can_cloak: bool | None,
) -> bool | None:
    """Recognize only the static Bird Super Spy + cloak-capable signature.

    This deliberately does not decide effective cloak: damage, fuel, Loki,
    nebula/ion effects, cloak type and other dynamic Host state remain external.
    """

    if race_id is None or mission is None or hull_can_cloak is None:
        return None
    return (
        race_id == BIRD_RACE_ID
        and mission == RACE_SPECIFIC_MISSION_ID
        and hull_can_cloak
    )


def _scalar_projection(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    result: dict[str, Any] = {}
    for key, child in sorted(value.items(), key=lambda item: str(item[0])):
        if child is None or isinstance(child, (str, int, float, bool)):
            result[str(key)] = child
    return result


def _ship_projection(
    *,
    ship_id: int,
    owner_id: int,
    raw: Mapping[str, Any],
    race_id: int | None,
    specs: Any,
    t_owner_id: int | None,
    t_raw: Mapping[str, Any] | None,
) -> dict[str, Any]:
    hull_id = _intish(raw.get("hullid", raw.get("hull_id")))
    hull = specs.hulls.get(hull_id) if hull_id is not None else None
    mission = _intish(raw.get("mission"))
    fuel = _intish(raw.get("neutronium"))
    damage = _intish(raw.get("damage"))
    hull_mass = int(hull.mass) if hull is not None else None
    cloak_cost = _basic_cloak_fuel_cost(hull_mass)
    signature = _super_spy_cloak_signature(
        race_id=race_id,
        mission=mission,
        hull_can_cloak=(hull.can_cloak if hull is not None else None),
    )

    basic_fuel_sufficient: bool | None
    if fuel is None or cloak_cost is None:
        basic_fuel_sufficient = None
    else:
        basic_fuel_sufficient = fuel >= cloak_cost

    t_same_owner = t_owner_id == owner_id if t_owner_id is not None else None
    t_same_hull: bool | None = None
    if t_raw is not None and hull_id is not None:
        t_hull_id = _intish(t_raw.get("hullid", t_raw.get("hull_id")))
        t_same_hull = t_hull_id == hull_id if t_hull_id is not None else None

    return {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "race_id": race_id,
        "hull_id": hull_id,
        "hull_name": hull.name if hull is not None else None,
        "hull_mass": hull_mass,
        "hull_can_cloak": hull.can_cloak if hull is not None else None,
        "mission": mission,
        "primary_enemy": _intish(raw.get("enemy")),
        "friendly_code": raw.get("friendlycode"),
        "tminus1_fuel": fuel,
        "tminus1_damage": damage,
        "tminus1_iscloaked": _boolish(raw.get("iscloaked")),
        "bird_super_spy_cloak_signature": signature,
        "basic_cloak_fuel_cost": cloak_cost,
        "basic_cloak_fuel_sufficient_tminus1": basic_fuel_sufficient,
        "t_owner_id": t_owner_id,
        "t_same_owner": t_same_owner,
        "t_same_hull": t_same_hull,
        "t_state": _scalar_projection(t_raw),
        "t_iscloaked": _boolish(t_raw.get("iscloaked")) if t_raw is not None else None,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    missing_archives: list[int] = []
    payload_conflicts = 0

    by_game: dict[int, list[dict[str, Any]]] = {}
    for target in TARGETS:
        by_game.setdefault(int(target["game_id"]), []).append(target)

    for game_id, game_targets in sorted(by_game.items()):
        archive_path = args.archive_dir / f"game-{game_id}.zip"
        if not archive_path.exists():
            missing_archives.append(game_id)
            continue

        archive_data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=args.prepared_dir / f"game-{game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        races, _race_conflicts = _player_races(prepared.snapshots)
        specs = _static_specs(archive_data)
        seen, conflicts = _dedup_vcrs(archive_data)
        payload_conflicts += conflicts

        for target in game_targets:
            battle_turn = int(target["battle_turn"])
            before_turn = battle_turn - 1
            owner_rows = _owner_rows_for_turn(ship_groups, before_turn)
            ship_ids = (
                int(target["active_ship_id"]),
                int(target["extra_target_ship_id"]),
                int(target["factual_target_ship_id"]),
            )

            ships: dict[str, Any] = {}
            for ship_id in ship_ids:
                before = owner_rows.get(ship_id)
                if before is None:
                    ships[str(ship_id)] = {"ship_id": ship_id, "tminus1_missing": True}
                    continue
                owner_id, raw = before
                t_owner, t_raw = _owner_raw(ship_groups, battle_turn, ship_id)
                ships[str(ship_id)] = _ship_projection(
                    ship_id=ship_id,
                    owner_id=int(owner_id),
                    raw=raw,
                    race_id=races.get(int(owner_id)),
                    specs=specs,
                    t_owner_id=t_owner,
                    t_raw=t_raw,
                )

            vcr_entry = seen.get((game_id, battle_turn, int(target["factual_vcr_id"])))
            vcr_projection: dict[str, Any] | None = None
            if vcr_entry is not None:
                _digest, vcr = vcr_entry
                left = vcr.get("left") if isinstance(vcr.get("left"), Mapping) else None
                right = vcr.get("right") if isinstance(vcr.get("right"), Mapping) else None
                vcr_projection = {
                    "top_level": _scalar_projection(vcr),
                    "left": _scalar_projection(left),
                    "right": _scalar_projection(right),
                }

            extra = ships.get(str(target["extra_target_ship_id"]), {})
            factual = ships.get(str(target["factual_target_ship_id"]), {})
            rows.append(
                {
                    **target,
                    "site": list(target["site"]),
                    "ships": ships,
                    "extra_target_static_super_spy_cloak_signature": extra.get(
                        "bird_super_spy_cloak_signature"
                    ),
                    "extra_target_basic_cloak_fuel_sufficient": extra.get(
                        "basic_cloak_fuel_sufficient_tminus1"
                    ),
                    "extra_target_t_iscloaked": extra.get("t_iscloaked"),
                    "factual_target_static_super_spy_cloak_signature": factual.get(
                        "bird_super_spy_cloak_signature"
                    ),
                    "factual_target_basic_cloak_fuel_sufficient": factual.get(
                        "basic_cloak_fuel_sufficient_tminus1"
                    ),
                    "factual_target_owner_changed_by_t": (
                        factual.get("t_same_owner") is False
                    ),
                    "vcr": vcr_projection,
                }
            )

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "target_sites": len(TARGETS),
            "rows_found": len(rows),
            "missing_archives": len(missing_archives),
            "payload_conflicts": payload_conflicts,
            "extra_static_super_spy_cloak_signature_true": sum(
                1
                for row in rows
                if row["extra_target_static_super_spy_cloak_signature"] is True
            ),
            "extra_basic_cloak_fuel_sufficient_true": sum(
                1
                for row in rows
                if row["extra_target_basic_cloak_fuel_sufficient"] is True
            ),
            "extra_t_iscloaked_true": sum(
                1 for row in rows if row["extra_target_t_iscloaked"] is True
            ),
            "factual_target_owner_changed_by_t": sum(
                1 for row in rows if row["factual_target_owner_changed_by_t"]
            ),
        },
        "missing_archive_game_ids": missing_archives,
        "rows": rows,
        "evidence_boundary": (
            "Focused attribution audit for the same two broad initial STANDARD target residuals. "
            "The static signature only identifies Bird race + race-specific mission 9 + a cloak-capable hull. "
            "It does not infer effective cloak through Loki, nebula/ion, damage, cloak type, or other dynamic Host state. "
            "T-state is control-only and is not fed back into precombat candidate selection. VCR scalar fields are printed "
            "only to attribute the factual combat/capture outcome. No combat selector is changed by this diagnostic."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect cloak/capture evidence for the two initial STANDARD target residuals."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT INITIAL STANDARD TARGET CLOAK RESIDUAL AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("RESIDUAL ROWS:")
    for row in report["rows"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: focused cloak/capture attribution; T state and VCR outcome are control-only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
