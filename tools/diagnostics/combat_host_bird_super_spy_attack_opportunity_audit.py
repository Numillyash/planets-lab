from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
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
from planets_lab.rules.combat.order import BIRD_RACE_ID
from planets_lab.rules.combat.selection import decide_ship_combat_pair

from combat_host_bird_super_spy_cloak_context_audit import (
    BIRD_SUPER_SPY_MISSION_ID,
    _boolish,
    _documented_super_spy_effective_cloak_candidate,
    _planet_ion_pulse_context,
)
from combat_host_candidate_set_audit import (
    _build_independent_controls,
    _candidate_input,
    _factual_sites,
    _independent_permission,
    _owner_rows_for_turn,
    _pair,
    _potential_chunnel_source_sites,
    _requests_combat,
    _serialize,
    _tow_target_ids,
)
from combat_host_candidate_set_v2_audit import _foreign_mine_route_risk
from combat_host_factual_queue_selection_audit import (
    _build_start_stack_index,
    _decision_projection,
    _interference_state,
)
from combat_host_initial_standard_target_audit import _factual_queue_by_site
from combat_host_matching_fc_suppression_audit import (
    _relation_inventory,
    _relation_signature,
    _safe_signature,
)
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_mission7_matched_control_audit import _dedup_vcrs
from combat_host_normal_movement_position_audit import (
    _archive_nuionstorms_consensus,
    _inbound_transfer_targets,
    _normal_position_prediction,
)
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR, SPECIAL_GAME_ID, _static_specs
from combat_host_privateer_rob_attack_opportunity_audit import _factual_outcome
from combat_host_privateer_rob_cloak_fuel_attribution_audit import (
    _glory_start_context,
    _inside_any_ion_disturbance,
    _loki_start_exposure,
)
from combat_host_privateer_rob_effective_cloak_threshold_audit import (
    _expected_blocked_from_initial_classification,
)
from combat_host_privateer_rob_initial_cloak_context_audit import (
    _reference_normal_move,
    _xy,
)
from combat_host_privateer_rob_initial_decision_audit import _initial_context


SCHEMA = "planets-lab.combat-host-bird-super-spy-attack-opportunity-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 120
TARGET_RESIDUAL = (511506, 94, 2716, 1999, 202, 496)


def _bird_super_spy_target(
    *,
    race_id: int | None,
    raw: Mapping[str, Any],
    hull_can_cloak: bool | None,
) -> bool:
    return (
        race_id == BIRD_RACE_ID
        and _intish(raw.get("mission")) == BIRD_SUPER_SPY_MISSION_ID
        and hull_can_cloak is True
    )


def _int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _candidate_state(
    *,
    target_id: int,
    target: Mapping[str, Any],
    owner_rows: Mapping[int, tuple[int, Mapping[str, Any]]],
    planet_groups: Mapping[Any, Any],
    before_turn: int,
    specs: Any,
    storms_by_turn: Mapping[int, Sequence[Any]],
    storm_conflicts: set[int] | frozenset[int],
    storm_invalid: set[int] | frozenset[int],
) -> dict[str, Any]:
    raw = target["raw"]
    owner_id = int(target["owner_id"])
    race_id = target.get("race_id")
    hull_id = target.get("hull_id")
    hull = specs.hulls.get(hull_id) if hull_id is not None else None
    hull_can_cloak = bool(hull.can_cloak) if hull is not None else None
    hull_mass = _int_value(getattr(hull, "mass", None)) if hull is not None else None
    special = str(getattr(hull, "special", "") or "") if hull is not None else ""
    advanced_cloak = "advanced cloak" in special.lower()
    mission = _intish(raw.get("mission"))
    damage = _intish(raw.get("damage"))
    fuel = _intish(raw.get("neutronium"))
    reference_cost = max(5, hull_mass // 20) if hull_mass is not None and hull_mass >= 0 else None
    position = _xy(raw)

    reference_move = _reference_normal_move(
        ship_id=target_id,
        owner_id=owner_id,
        race_id=race_id,
        hull_id=hull_id,
        raw=raw,
        specs=specs,
    )
    remaining = _int_value(reference_move.get("raw_reference_remaining_fuel"))

    loki_exposed, loki_ids = _loki_start_exposure(
        rows=owner_rows,
        target_owner_id=owner_id,
        target_position=position,
    )
    glory_rows = _glory_start_context(
        rows=owner_rows,
        target_owner_id=owner_id,
        target_position=position,
        specs=specs,
    )
    active_glory = any(row.get("active_code") is True for row in glory_rows)
    planet_ion_pulse = _planet_ion_pulse_context(
        planet_groups=planet_groups,
        turn=before_turn,
        ship_owner_id=owner_id,
        position=position,
    )

    if before_turn in storm_conflicts:
        ion_inside: bool | None = None
        storm_status = "conflict"
    elif before_turn in storm_invalid:
        ion_inside = None
        storm_status = "invalid"
    else:
        ion_inside = _inside_any_ion_disturbance(
            storms_by_turn.get(before_turn, ()),
            position=position,
        )
        storm_status = "resolved"

    candidate, reason = _documented_super_spy_effective_cloak_candidate(
        race_id=race_id,
        mission=mission,
        hull_can_cloak=hull_can_cloak,
        advanced_cloak=advanced_cloak,
        damage=damage,
        fuel_before=fuel,
        reference_cost=reference_cost,
        reference_move_resolved=reference_move.get("resolved") is True,
        reference_remaining_fuel=remaining,
        prior_iscloaked=_boolish(raw.get("iscloaked")),
        ion_start_inside=ion_inside,
        planet_ion_pulse_possible=planet_ion_pulse.get("possible"),
        loki_start_exposed=loki_exposed,
        active_glory_colocated=active_glory,
    )

    return {
        "effective_cloak": candidate,
        "reason": reason,
        "prior_iscloaked": _boolish(raw.get("iscloaked")),
        "damage": damage,
        "fuel": fuel,
        "reference_cost": reference_cost,
        "reference_move": reference_move,
        "advanced_cloak": advanced_cloak,
        "storm_status": storm_status,
        "ion_start_inside": ion_inside,
        "planet_ion_pulse": planet_ion_pulse,
        "loki_start_exposed": loki_exposed,
        "loki_ship_ids": loki_ids,
        "active_glory_colocated": active_glory,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    totals: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    classifications: Counter[str] = Counter()
    decisive_matrix: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
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
        planet_groups = group_perspective_records(prepared.snapshots, "planet")
        races, race_conflicts = _player_races(prepared.snapshots)
        if race_conflicts:
            totals["race_conflict_games"] += 1
        specs = _static_specs(archive_data)
        relations = _relation_inventory(archive_data)
        start_stacks = _build_start_stack_index(ship_groups)
        seen, conflicts = _dedup_vcrs(archive_data)
        totals["payload_conflicts"] += int(conflicts)
        sites = _factual_sites(game_id=game_id, seen=seen)
        factual_queues = _factual_queue_by_site(game_id=game_id, seen=seen)
        controls = _build_independent_controls(
            game_id=game_id,
            seen=seen,
            ship_groups=ship_groups,
            relations=relations,
        )

        entities = _entity_map(prepared.snapshots)
        planets_by_turn = _planet_tuples_by_turn(entities, include_ineligible=True)
        warp_wells_by_turn, _warp_well_conflicts = _settings_warp_well_state_by_turn(
            prepared.snapshots
        )
        eligible_by_turn = getattr(entities, "warp_well_planet_ids_by_turn", {})
        topology = effective_sphere_topology(
            game_id=game_id,
            topology=extract_map_topology(archive_data),
        )
        storms_by_turn, storm_conflicts, storm_invalid = _storm_consensus_by_turn(
            prepared.snapshots
        )
        nuionstorms, _nuionstorms_raw = _archive_nuionstorms_consensus(archive_data)
        mine_context = build_mine_evidence_context(
            game_id=game_id,
            archive_data=archive_data,
            snapshots=prepared.snapshots,
        )

        rows_by_turn: dict[int, dict[int, tuple[int, Mapping[str, Any]]]] = {}
        position_by_battle_turn: dict[int, dict[int, dict[str, Any]]] = {}

        for (battle_turn, x, y), factual in sorted(sites.items()):
            before_turn = battle_turn - 1
            if before_turn not in rows_by_turn:
                rows_by_turn[before_turn] = _owner_rows_for_turn(ship_groups, before_turn)
            owner_rows = rows_by_turn[before_turn]

            if battle_turn not in position_by_battle_turn:
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

                predicted_rows: dict[int, dict[str, Any]] = {}
                for ship_id, (owner_id, raw) in owner_rows.items():
                    hull_id = _intish(raw.get("hullid", raw.get("hull_id")))
                    hull = specs.hulls.get(hull_id) if hull_id is not None else None
                    race_id = races.get(owner_id)
                    if storm_issue is not None:
                        predicted = None
                        source = storm_issue
                    else:
                        predicted, source = _normal_position_prediction(
                            game_id=game_id,
                            ship_id=ship_id,
                            owner_id=owner_id,
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
                    if predicted is not None:
                        mine_risk = _foreign_mine_route_risk(
                            context=mine_context,
                            before_turn=before_turn,
                            owner_id=owner_id,
                            raw=raw,
                            race_id=race_id,
                            hull_id=hull_id,
                        )
                        if mine_risk is not None:
                            predicted = None
                            source = mine_risk
                    predicted_rows[ship_id] = {
                        "ship_id": ship_id,
                        "owner_id": owner_id,
                        "raw": raw,
                        "race_id": race_id,
                        "hull_id": hull_id,
                        "hull_can_cloak": hull.can_cloak if hull is not None else None,
                        "position": predicted,
                        "position_source": source,
                    }
                position_by_battle_turn[battle_turn] = predicted_rows

            site = (x, y)
            site_rows = {
                ship_id: entry
                for ship_id, entry in position_by_battle_turn[battle_turn].items()
                if entry.get("position") == site
            }
            if not site_rows:
                continue
            factual_pairs = set(factual["pairs"])
            factual_queue = factual_queues.get((battle_turn, x, y), ())

            for target_id, target in sorted(site_rows.items()):
                if not _bird_super_spy_target(
                    race_id=target.get("race_id"),
                    raw=target["raw"],
                    hull_can_cloak=target.get("hull_can_cloak"),
                ):
                    continue
                totals["bird_super_spy_targets_at_factual_sites"] += 1

                state = _candidate_state(
                    target_id=target_id,
                    target=target,
                    owner_rows=owner_rows,
                    planet_groups=planet_groups,
                    before_turn=before_turn,
                    specs=specs,
                    storms_by_turn=storms_by_turn,
                    storm_conflicts=storm_conflicts,
                    storm_invalid=storm_invalid,
                )
                reasons[str(state["reason"])] += 1

                for attacker_id, attacker in sorted(site_rows.items()):
                    if attacker_id == target_id or attacker["owner_id"] == target["owner_id"]:
                        continue
                    if not _requests_combat(attacker["raw"], int(target["owner_id"])):
                        continue
                    if _requests_combat(target["raw"], int(attacker["owner_id"])):
                        totals["bidirectional_request_opportunities"] += 1
                        continue

                    totals["raw_attack_opportunities"] += 1
                    pair = _pair(target_id, attacker_id)
                    signature = _relation_signature(
                        relations.get(before_turn, {}),
                        int(target["owner_id"]),
                        int(attacker["owner_id"]),
                    )
                    excluded = frozenset(factual["pair_rows"].get(pair, set()))
                    attacker_strict = _independent_permission(
                        request=True,
                        owner_id=int(attacker["owner_id"]),
                        opponent_owner_id=int(target["owner_id"]),
                        signature=signature,
                        controls=controls,
                        excluded_rows=excluded,
                    )
                    target_interference = _interference_state(
                        game_id=game_id,
                        before_turn=before_turn,
                        owner_id=int(target["owner_id"]),
                        raw=target["raw"],
                        start_stacks=start_stacks,
                    )
                    attacker_interference = _interference_state(
                        game_id=game_id,
                        before_turn=before_turn,
                        owner_id=int(attacker["owner_id"]),
                        raw=attacker["raw"],
                        start_stacks=start_stacks,
                    )

                    target_input = _candidate_input(
                        game_id=game_id,
                        ship_id=target_id,
                        owner_id=int(target["owner_id"]),
                        raw=target["raw"],
                        race_id=target.get("race_id"),
                        hull_id=target.get("hull_id"),
                        hull_can_cloak=target.get("hull_can_cloak"),
                        diplomacy_allows_attack=False,
                        interference_protected=target_interference,
                    )
                    attacker_conditional = _candidate_input(
                        game_id=game_id,
                        ship_id=attacker_id,
                        owner_id=int(attacker["owner_id"]),
                        raw=attacker["raw"],
                        race_id=attacker.get("race_id"),
                        hull_id=attacker.get("hull_id"),
                        hull_can_cloak=attacker.get("hull_can_cloak"),
                        diplomacy_allows_attack=True,
                        interference_protected=attacker_interference,
                    )
                    attacker_strict_input = _candidate_input(
                        game_id=game_id,
                        ship_id=attacker_id,
                        owner_id=int(attacker["owner_id"]),
                        raw=attacker["raw"],
                        race_id=attacker.get("race_id"),
                        hull_id=attacker.get("hull_id"),
                        hull_can_cloak=attacker.get("hull_can_cloak"),
                        diplomacy_allows_attack=attacker_strict,
                        interference_protected=attacker_interference,
                    )

                    conditional = _decision_projection(
                        decide_ship_combat_pair(
                            left=target_input,
                            right=attacker_conditional,
                            same_location=True,
                        )
                    )
                    if not (
                        conditional.get("engagement_eligible") is True
                        and conditional.get("phase") == "standard"
                    ):
                        totals["conditional_not_plain_standard"] += 1
                        continue
                    totals["conditional_plain_standard_opportunities"] += 1

                    strict = _decision_projection(
                        decide_ship_combat_pair(
                            left=target_input,
                            right=attacker_strict_input,
                            same_location=True,
                        )
                    )
                    strict_plain = (
                        strict.get("engagement_eligible") is True
                        and strict.get("phase") == "standard"
                    )
                    if strict_plain:
                        totals["strict_plain_standard_opportunities"] += 1

                    outcome = _factual_outcome(
                        factual_pairs=factual_pairs,
                        target_ship_id=target_id,
                        attacker_ship_id=attacker_id,
                    )
                    outcomes[outcome] += 1
                    context = _initial_context(
                        row={"target_ship_id": target_id, "attacker_ship_id": attacker_id},
                        owner_rows=owner_rows,
                        factual_queue=factual_queue,
                    )
                    classification = str(context.get("classification") or "unresolved")
                    classifications[classification] += 1
                    expected_blocked = _expected_blocked_from_initial_classification(classification)
                    candidate_blocked = (
                        True if state["effective_cloak"] is True
                        else False if state["effective_cloak"] is False
                        else None
                    )
                    decisive_match: bool | None = None
                    if expected_blocked is not None:
                        totals["decisive_rows"] += 1
                        if candidate_blocked is None:
                            totals["decisive_unresolved"] += 1
                            decisive_matrix[
                                f"expected_{'blocked' if expected_blocked else 'eligible'}:unresolved"
                            ] += 1
                        else:
                            decisive_match = candidate_blocked == expected_blocked
                            totals["decisive_match" if decisive_match else "decisive_mismatch"] += 1
                            decisive_matrix[
                                f"expected_{'blocked' if expected_blocked else 'eligible'}:candidate_"
                                f"{'blocked' if candidate_blocked else 'eligible'}"
                            ] += 1
                    else:
                        totals["nondecisive_rows"] += 1

                    if candidate_blocked is True and outcome == "pair_vcr":
                        totals["blocked_factual_pair_regressions"] += 1

                    is_target = (
                        game_id,
                        battle_turn,
                        x,
                        y,
                        target_id,
                        attacker_id,
                    ) == TARGET_RESIDUAL
                    row = {
                        "game_id": game_id,
                        "before_turn": before_turn,
                        "battle_turn": battle_turn,
                        "site": [x, y],
                        "target_ship_id": target_id,
                        "target_owner_id": target["owner_id"],
                        "attacker_ship_id": attacker_id,
                        "attacker_owner_id": attacker["owner_id"],
                        "pair": list(pair),
                        "is_target_residual": is_target,
                        "target": {
                            "race_id": target.get("race_id"),
                            "hull_id": target.get("hull_id"),
                            "mission": _intish(target["raw"].get("mission")),
                            "enemy": _intish(target["raw"].get("enemy")),
                            "friendlycode": target["raw"].get("friendlycode"),
                        },
                        "attacker": {
                            "race_id": attacker.get("race_id"),
                            "hull_id": attacker.get("hull_id"),
                            "mission": _intish(attacker["raw"].get("mission")),
                            "enemy": _intish(attacker["raw"].get("enemy")),
                            "friendlycode": attacker["raw"].get("friendlycode"),
                        },
                        "relation_signature": _safe_signature(signature),
                        "attacker_strict_diplomacy_allows_attack": attacker_strict,
                        "strict_plain_standard": strict_plain,
                        "factual_outcome": outcome,
                        "initial_context": context,
                        "candidate_state": state,
                        "expected_blocked": expected_blocked,
                        "candidate_blocked": candidate_blocked,
                        "decisive_match": decisive_match,
                    }
                    if is_target:
                        target_rows.append(row)
                    rows.append(row)

    rows.sort(
        key=lambda row: (
            0 if row.get("is_target_residual") else 1,
            0 if row.get("expected_blocked") is not None else 1,
            0 if row.get("decisive_match") is False else 1,
            int(row["game_id"]),
            int(row["battle_turn"]),
            int(row["attacker_ship_id"]),
            int(row["target_ship_id"]),
        )
    )

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            **_serialize(totals),
            "factual_outcomes": _serialize(outcomes),
            "initial_classifications": _serialize(classifications),
            "decisive_matrix": _serialize(decisive_matrix),
            "candidate_reasons": _serialize(reasons),
            "target_residual_rows": len(target_rows),
            "acceptance": {
                "no_race_conflicts": totals["race_conflict_games"] == 0,
                "no_payload_conflicts": totals["payload_conflicts"] == 0,
                "no_blocked_factual_pair_regressions": totals["blocked_factual_pair_regressions"] == 0,
                "no_decisive_mismatch": totals["decisive_mismatch"] == 0,
                "target_residual_present": len(target_rows) > 0,
                "target_residual_supported": any(
                    row.get("candidate_blocked") is True
                    and row.get("expected_blocked") is True
                    and row.get("decisive_match") is True
                    for row in target_rows
                ),
            },
        },
        "target_residual": target_rows,
        "rows": rows[: args.example_limit],
        "evidence_boundary": (
            "Population-wide site-conditioned differential for one directional Bird Super Spy targetability hypothesis. "
            "Bird race3 mission9 cloak-capable targets and hostile ships are independently positioned at factual combat sites "
            "through the same position-v3/candidate-set-v2 layers used by the initial STANDARD audit. Only one-way hostile "
            "plain-STANDARD opportunities are retained; bidirectional requests are separated. Factual VCRs are used only after "
            "opportunity construction as outcome/queue labels. The documented effective-cloak candidate is deliberately "
            "conservative: ordinary cloak only, damage/fuel/reference movement resolved, prior archived cloak positive, and "
            "T-1 ion-storm, possible planet Ion Pulse, Loki and active-Glory contexts clear. Advanced/out-of-scope/unresolved "
            "states remain unresolved. Queue-decisive scoring uses only initial_pair_vcr as eligible proof and an initial skipped "
            "target that outranks the factual opponent as blocker proof. No canonical selection rule is changed."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit population-wide hostile plain-STANDARD opportunities against Bird Super Spy cloak targets."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT BIRD SUPER SPY ATTACK OPPORTUNITY AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("TARGET RESIDUAL:")
    for row in report["target_residual"]:
        print(row)
    print()
    print("ROWS:")
    for row in report["rows"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: population differential only; canonical selection remains unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
