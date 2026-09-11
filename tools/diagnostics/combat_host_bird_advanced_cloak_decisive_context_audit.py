from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from math import hypot
from pathlib import Path
from types import SimpleNamespace
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_differential import (
    _entity_map,
    _intish,
    _planet_tuples_by_turn,
    _settings_warp_well_state_by_turn,
)
from planets_lab.corpus.movement_mine_context import build_mine_evidence_context
from planets_lab.corpus.movement_residual_context import StormRecord, _storm_consensus_by_turn
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records

from combat_host_bird_super_spy_attack_opportunity_audit import run as run_population
from combat_host_candidate_set_audit import (
    _owner_rows_for_turn,
    _potential_chunnel_source_sites,
    _tow_target_ids,
)
from combat_host_candidate_set_v2_audit import _foreign_mine_route_risk
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_normal_movement_position_audit import (
    _archive_nuionstorms_consensus,
    _inbound_transfer_targets,
    _normal_position_prediction,
)
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR, SPECIAL_GAME_ID, _owner_raw, _static_specs
from combat_host_privateer_rob_initial_cloak_context_audit import (
    LOKI_HULL_ID,
    LOKI_MAX_ACTIVE_DAMAGE,
    LOKI_RANGE_LY,
    _xy,
)


SCHEMA = "planets-lab.combat-host-bird-advanced-cloak-decisive-context-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 40
ACTIVE_GLORY_CODES = frozenset({"pop", "trg"})


def _boolish(value: Any) -> bool | None:
    if value is True or value is False:
        return bool(value)
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "y"}:
            return True
        if text in {"0", "false", "no", "n"}:
            return False
    return None


def _stable_same_ship(
    *,
    before_owner: int,
    before_hull: int | None,
    after_owner: int | None,
    after_raw: Mapping[str, Any] | None,
) -> bool:
    if after_raw is None or after_owner != before_owner or before_hull is None:
        return False
    after_hull = _intish(after_raw.get("hullid", after_raw.get("hull_id")))
    return after_hull == before_hull


def _active_glory(raw: Mapping[str, Any], special: str) -> tuple[bool, str | None]:
    if "glory" not in special.lower():
        return False, None
    fc_raw = raw.get("friendlycode")
    fc = fc_raw.strip().lower() if isinstance(fc_raw, str) else None
    return fc in ACTIVE_GLORY_CODES, fc


def _distance_to_site(position: tuple[int, int] | None, site: tuple[int, int]) -> float | None:
    if position is None:
        return None
    return hypot(position[0] - site[0], position[1] - site[1])


def run(args: argparse.Namespace) -> dict[str, Any]:
    population = run_population(
        SimpleNamespace(
            archive_dir=args.archive_dir,
            prepared_dir=args.prepared_dir,
            example_limit=100000,
            output=None,
        )
    )
    focus_rows = [
        dict(row)
        for row in population.get("rows", ())
        if isinstance(row, Mapping)
        and row.get("expected_blocked") is not None
        and isinstance(row.get("candidate_state"), Mapping)
        and row["candidate_state"].get("reason") == "advanced_cloak_unresolved"
    ]

    by_game: dict[int, list[dict[str, Any]]] = {}
    for row in focus_rows:
        game_id = int(row["game_id"])
        if game_id == SPECIAL_GAME_ID:
            continue
        by_game.setdefault(game_id, []).append(row)

    output_rows: list[dict[str, Any]] = []
    summary: dict[str, int | bool] = {
        "focus_rows": len(focus_rows),
        "expected_blocked_rows": 0,
        "expected_eligible_rows": 0,
        "stable_t_identity_rows": 0,
        "postmove_active_glory_possible_rows": 0,
        "postmove_loki_possible_rows": 0,
        "t_cloak_false_rows": 0,
        "t_cloak_true_rows": 0,
    }

    for game_id, game_rows in sorted(by_game.items()):
        archive_path = args.archive_dir / f"game-{game_id}.zip"
        if not archive_path.exists():
            continue
        archive_data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=args.prepared_dir / f"game-{game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        races, race_conflicts = _player_races(prepared.snapshots)
        specs = _static_specs(archive_data)
        entities = _entity_map(prepared.snapshots)
        planets_by_turn = _planet_tuples_by_turn(entities, include_ineligible=True)
        warp_wells_by_turn, _warp_well_conflicts = _settings_warp_well_state_by_turn(prepared.snapshots)
        eligible_by_turn = getattr(entities, "warp_well_planet_ids_by_turn", {})
        topology = effective_sphere_topology(
            game_id=game_id,
            topology=extract_map_topology(archive_data),
        )
        storms_by_turn, storm_conflicts, storm_invalid = _storm_consensus_by_turn(prepared.snapshots)
        nuionstorms, _nuionstorms_raw = _archive_nuionstorms_consensus(archive_data)
        mine_context = build_mine_evidence_context(
            game_id=game_id,
            archive_data=archive_data,
            snapshots=prepared.snapshots,
        )

        before_cache: dict[int, dict[int, tuple[int, Mapping[str, Any]]]] = {}
        prediction_cache: dict[int, dict[int, dict[str, Any]]] = {}

        for row in game_rows:
            before_turn = int(row["before_turn"])
            battle_turn = int(row["battle_turn"])
            target_id = int(row["target_ship_id"])
            target_owner = int(row["target_owner_id"])
            site = (int(row["site"][0]), int(row["site"][1]))
            expected_blocked = bool(row["expected_blocked"])
            summary["expected_blocked_rows" if expected_blocked else "expected_eligible_rows"] += 1

            if before_turn not in before_cache:
                before_cache[before_turn] = _owner_rows_for_turn(ship_groups, before_turn)
            owner_rows = before_cache[before_turn]
            target_entry = owner_rows.get(target_id)
            if target_entry is None:
                continue
            owner_id, target_raw = target_entry
            target_hull = _intish(target_raw.get("hullid", target_raw.get("hull_id")))

            if battle_turn not in prediction_cache:
                tow_targets = _tow_target_ids(owner_rows)
                chunnel_sites = _potential_chunnel_source_sites(owner_rows)
                inbound_targets = _inbound_transfer_targets(owner_rows)
                planets = tuple(planets_by_turn.get(before_turn, ()))
                eligible_ids_raw = eligible_by_turn.get(before_turn)
                eligible_ids = (
                    frozenset(int(value) for value in eligible_ids_raw)
                    if eligible_ids_raw is not None
                    else None
                )
                warp_wells_enabled = warp_wells_by_turn.get(before_turn)
                if battle_turn in storm_conflicts:
                    move_storms: Sequence[StormRecord] | None = None
                    storm_issue = "storm_context_conflict"
                elif battle_turn in storm_invalid:
                    move_storms = None
                    storm_issue = "storm_context_invalid"
                else:
                    move_storms = storms_by_turn.get(battle_turn, ())
                    storm_issue = None

                predicted: dict[int, dict[str, Any]] = {}
                for ship_id, (ship_owner, raw) in owner_rows.items():
                    hull_id = _intish(raw.get("hullid", raw.get("hull_id")))
                    hull = specs.hulls.get(hull_id) if hull_id is not None else None
                    race_id = races.get(ship_owner)
                    if storm_issue is not None:
                        position = None
                        source = storm_issue
                    else:
                        position, source = _normal_position_prediction(
                            game_id=game_id,
                            ship_id=ship_id,
                            owner_id=ship_owner,
                            raw=raw,
                            race_id=race_id,
                            specs=specs,
                            planets=planets,
                            warp_wells_enabled=warp_wells_enabled,
                            eligible_warp_well_planet_ids=eligible_ids,
                            inbound_transfer_targets=inbound_targets,
                            tow_targets=tow_targets,
                            chunnel_source_sites=chunnel_sites,
                            sphere=topology.sphere,
                            storms=move_storms or (),
                            nuionstorms=nuionstorms,
                        )
                    mine_risk = None
                    if position is not None:
                        mine_risk = _foreign_mine_route_risk(
                            context=mine_context,
                            before_turn=before_turn,
                            owner_id=ship_owner,
                            raw=raw,
                            race_id=race_id,
                            hull_id=hull_id,
                        )
                    predicted[ship_id] = {
                        "owner_id": ship_owner,
                        "raw": raw,
                        "hull_id": hull_id,
                        "hull": hull,
                        "race_id": race_id,
                        "position": None if mine_risk is not None else position,
                        "raw_position_prediction": position,
                        "source": source,
                        "mine_risk": mine_risk,
                    }
                prediction_cache[battle_turn] = predicted

            predictions = prediction_cache[battle_turn]
            target_prediction = predictions.get(target_id, {})

            glory_rows: list[dict[str, Any]] = []
            loki_rows: list[dict[str, Any]] = []
            for ship_id, candidate in sorted(predictions.items()):
                if ship_id == target_id or int(candidate["owner_id"]) == target_owner:
                    continue
                raw = candidate["raw"]
                hull = candidate.get("hull")
                special = str(getattr(hull, "special", "") or "") if hull is not None else ""
                active_glory, fc = _active_glory(raw, special)
                if "glory" in special.lower():
                    final_position = candidate.get("position")
                    colocated = final_position == site if final_position is not None else None
                    if active_glory and colocated is True:
                        summary["postmove_active_glory_possible_rows"] += 1
                    glory_rows.append(
                        {
                            "ship_id": ship_id,
                            "owner_id": candidate["owner_id"],
                            "hull_id": candidate["hull_id"],
                            "hull_name": getattr(hull, "name", None),
                            "friendly_code": raw.get("friendlycode"),
                            "normalized_code": fc,
                            "active_code": active_glory,
                            "mission": _intish(raw.get("mission")),
                            "enemy": _intish(raw.get("enemy")),
                            "predicted_position": list(final_position) if final_position is not None else None,
                            "colocated_with_site": colocated,
                            "mine_risk": candidate.get("mine_risk"),
                        }
                    )

                if candidate.get("hull_id") == LOKI_HULL_ID:
                    damage = _intish(raw.get("damage"))
                    active = damage is not None and 0 <= damage <= LOKI_MAX_ACTIVE_DAMAGE
                    final_position = candidate.get("position")
                    distance = _distance_to_site(final_position, site)
                    within = active and distance is not None and distance <= LOKI_RANGE_LY + 1e-9
                    if within:
                        summary["postmove_loki_possible_rows"] += 1
                    loki_rows.append(
                        {
                            "ship_id": ship_id,
                            "owner_id": candidate["owner_id"],
                            "damage": damage,
                            "active_by_damage": active,
                            "predicted_position": list(final_position) if final_position is not None else None,
                            "distance_to_site": distance,
                            "within_10": within,
                            "mine_risk": candidate.get("mine_risk"),
                        }
                    )

            after_owner, after_raw = _owner_raw(ship_groups, battle_turn, target_id)
            stable_t = _stable_same_ship(
                before_owner=owner_id,
                before_hull=target_hull,
                after_owner=after_owner,
                after_raw=after_raw,
            )
            if stable_t:
                summary["stable_t_identity_rows"] += 1
            t_cloak = _boolish(after_raw.get("iscloaked")) if stable_t and after_raw is not None else None
            if t_cloak is True:
                summary["t_cloak_true_rows"] += 1
            elif t_cloak is False:
                summary["t_cloak_false_rows"] += 1

            output_rows.append(
                {
                    "game_id": game_id,
                    "before_turn": before_turn,
                    "battle_turn": battle_turn,
                    "site": list(site),
                    "target_ship_id": target_id,
                    "attacker_ship_id": int(row["attacker_ship_id"]),
                    "expected_blocked": expected_blocked,
                    "factual_outcome": row.get("factual_outcome"),
                    "initial_classification": row.get("initial_context", {}).get("classification"),
                    "target_start_position": list(_xy(target_raw)) if _xy(target_raw) is not None else None,
                    "target_full_position_prediction": (
                        list(target_prediction.get("position"))
                        if target_prediction.get("position") is not None
                        else None
                    ),
                    "target_position_source": target_prediction.get("source"),
                    "target_visible_mine_route_risk": target_prediction.get("mine_risk"),
                    "target_prior_iscloaked": _boolish(target_raw.get("iscloaked")),
                    "target_tminus1_damage": _intish(target_raw.get("damage")),
                    "target_tminus1_fuel": _intish(target_raw.get("neutronium")),
                    "postmove_glory_candidates": glory_rows,
                    "postmove_loki_candidates": loki_rows,
                    "t_stable_identity": stable_t,
                    "t_owner_id": after_owner,
                    "t_damage_attribution_only": (
                        _intish(after_raw.get("damage")) if stable_t and after_raw is not None else None
                    ),
                    "t_fuel_attribution_only": (
                        _intish(after_raw.get("neutronium")) if stable_t and after_raw is not None else None
                    ),
                    "t_iscloaked_attribution_only": t_cloak,
                    "source_candidate_state": row.get("candidate_state"),
                    "game_race_conflict": bool(race_conflicts),
                }
            )

    output_rows.sort(
        key=lambda row: (
            0 if row["expected_blocked"] is False else 1,
            int(row["game_id"]),
            int(row["battle_turn"]),
            int(row["target_ship_id"]),
        )
    )

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": summary,
        "rows": output_rows[: args.example_limit],
        "evidence_boundary": (
            "Focused attribution audit for the decisive Advanced Cloak rows left unresolved by the Bird Super Spy "
            "population gate. It reuses the same full position-v3/candidate-set-v2 predictor for the target, Loki and "
            "Glory candidates. Visible mine-route risk fails position prediction exactly as in the candidate layer. "
            "Predicted post-movement POP/TRG Glory colocation and post-movement Loki proximity are attribution signals, "
            "not automatically promoted decloak rules. T state is attribution-only because it is post-Host/postcombat and "
            "physical identity can be unstable. No canonical selection rule is changed."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit post-movement decloak context for decisive Bird Super Spy Advanced Cloak rows."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT BIRD ADVANCED CLOAK DECISIVE CONTEXT AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("ROWS:")
    for row in report["rows"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: attribution-only Advanced Cloak gate; canonical selection remains unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
