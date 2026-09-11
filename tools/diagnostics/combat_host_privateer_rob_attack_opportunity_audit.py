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
from planets_lab.rules.combat.selection import decide_ship_combat_pair

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
from combat_host_initial_standard_target_cloak_residual_audit import _boolish
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
from combat_host_privateer_rob_cloak_population_audit import (
    _cloak_transition,
    _stable_identity,
)
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
    _owner_raw,
    _static_specs,
)


SCHEMA = "planets-lab.combat-host-privateer-rob-attack-opportunity-audit.v1"
PRIVATEER_RACE_ID = 5
RACE_SPECIFIC_MISSION_ID = 9
DEFAULT_EXAMPLE_LIMIT = 100
TARGET_RESIDUAL = (360690, 83, 2374, 2260, 98, 264)


def _cloak_label(value: Any) -> str:
    flag = _boolish(value)
    if flag is True:
        return "true"
    if flag is False:
        return "false"
    return "unknown"


def _rob_pe_zero_target(
    *,
    race_id: int | None,
    raw: Mapping[str, Any],
    hull_can_cloak: bool | None,
) -> bool:
    pe = _intish(raw.get("enemy"))
    return (
        race_id == PRIVATEER_RACE_ID
        and _intish(raw.get("mission")) == RACE_SPECIFIC_MISSION_ID
        and hull_can_cloak is True
        and (pe is None or pe <= 0)
    )


def _factual_outcome(
    *,
    factual_pairs: set[tuple[int, int]],
    target_ship_id: int,
    attacker_ship_id: int,
) -> str:
    pair = _pair(target_ship_id, attacker_ship_id)
    if pair in factual_pairs:
        return "pair_vcr"
    target_other = any(target_ship_id in candidate for candidate in factual_pairs)
    attacker_other = any(attacker_ship_id in candidate for candidate in factual_pairs)
    if target_other and attacker_other:
        return "both_fought_other"
    if target_other:
        return "target_fought_other"
    if attacker_other:
        return "attacker_fought_other"
    return "neither_vcr"


def run(args: argparse.Namespace) -> dict[str, Any]:
    totals: Counter[str] = Counter()
    by_cloak: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    strict_outcomes: Counter[str] = Counter()
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
        relations = _relation_inventory(archive_data)
        start_stacks = _build_start_stack_index(ship_groups)
        seen, conflicts = _dedup_vcrs(archive_data)
        totals["payload_conflicts"] += int(conflicts)
        sites = _factual_sites(game_id=game_id, seen=seen)
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
                    storms: Sequence[StormRecord] | None = None
                    storm_issue = "storm_context_conflict"
                elif battle_turn in storm_invalid:
                    storms = None
                    storm_issue = "storm_context_invalid"
                else:
                    storms = storms_by_turn.get(battle_turn, ())
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
                            storms=storms or (),
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
            predictions = position_by_battle_turn[battle_turn]
            site_rows = {
                ship_id: entry
                for ship_id, entry in predictions.items()
                if entry.get("position") == site
            }
            if not site_rows:
                continue
            factual_pairs = set(factual["pairs"])

            for target_id, target in sorted(site_rows.items()):
                if not _rob_pe_zero_target(
                    race_id=target.get("race_id"),
                    raw=target["raw"],
                    hull_can_cloak=target.get("hull_can_cloak"),
                ):
                    continue
                totals["rob_pe_zero_targets_at_factual_sites"] += 1
                prior_cloak = _cloak_label(target["raw"].get("iscloaked"))

                for attacker_id, attacker in sorted(site_rows.items()):
                    if attacker_id == target_id or attacker["owner_id"] == target["owner_id"]:
                        continue
                    if not _requests_combat(attacker["raw"], int(target["owner_id"])):
                        continue
                    if _requests_combat(target["raw"], int(attacker["owner_id"])):
                        totals["target_self_request_unexpected"] += 1
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

                    target_strict = _candidate_input(
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
                    target_conditional = _candidate_input(
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

                    strict = _decision_projection(
                        decide_ship_combat_pair(
                            left=target_strict,
                            right=attacker_strict_input,
                            same_location=True,
                        )
                    )
                    conditional = _decision_projection(
                        decide_ship_combat_pair(
                            left=target_conditional,
                            right=attacker_conditional,
                            same_location=True,
                        )
                    )
                    conditional_plain = (
                        conditional.get("engagement_eligible") is True
                        and conditional.get("phase") == "standard"
                    )
                    if not conditional_plain:
                        totals["conditional_not_plain_standard"] += 1
                        continue

                    totals["conditional_plain_standard_opportunities"] += 1
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
                    by_cloak[f"{prior_cloak}:{outcome}"] += 1
                    if strict_plain:
                        strict_outcomes[outcome] += 1
                        by_cloak[f"strict:{prior_cloak}:{outcome}"] += 1

                    after_owner, after_raw = _owner_raw(ship_groups, battle_turn, target_id)
                    identity = _stable_identity(
                        before_owner=int(target["owner_id"]),
                        before_raw=target["raw"],
                        after_owner=after_owner,
                        after_raw=after_raw,
                    )
                    transition = _cloak_transition(
                        target["raw"].get("iscloaked"),
                        after_raw.get("iscloaked") if after_raw is not None else None,
                    )
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
                        "target_prior_cloak": prior_cloak,
                        "target_position_source": target.get("position_source"),
                        "attacker_position_source": attacker.get("position_source"),
                        "target": {
                            "race_id": target.get("race_id"),
                            "hull_id": target.get("hull_id"),
                            "mission": _intish(target["raw"].get("mission")),
                            "enemy": _intish(target["raw"].get("enemy")),
                            "friendlycode": target["raw"].get("friendlycode"),
                            "fuel": _intish(target["raw"].get("neutronium")),
                            "iscloaked": _boolish(target["raw"].get("iscloaked")),
                        },
                        "attacker": {
                            "race_id": attacker.get("race_id"),
                            "hull_id": attacker.get("hull_id"),
                            "mission": _intish(attacker["raw"].get("mission")),
                            "enemy": _intish(attacker["raw"].get("enemy")),
                            "friendlycode": attacker["raw"].get("friendlycode"),
                            "fuel": _intish(attacker["raw"].get("neutronium")),
                        },
                        "relation_signature": _safe_signature(signature),
                        "attacker_strict_diplomacy_allows_attack": attacker_strict,
                        "strict_plain_standard": strict_plain,
                        "strict": strict,
                        "conditional": conditional,
                        "factual_outcome": outcome,
                        "factual_pairs": [list(candidate) for candidate in sorted(factual_pairs)],
                        "target_after_identity": identity,
                        "target_cloak_transition": transition,
                        "target_after_iscloaked": (
                            _boolish(after_raw.get("iscloaked")) if after_raw is not None else None
                        ),
                    }
                    if is_target:
                        target_rows.append(row)
                    if len(rows) < args.example_limit:
                        rows.append(row)

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            **_serialize(totals),
            "conditional_outcomes": _serialize(outcomes),
            "strict_outcomes": _serialize(strict_outcomes),
            "by_prior_cloak": _serialize(by_cloak),
            "target_residual_rows": len(target_rows),
        },
        "target_residual": target_rows,
        "examples": rows,
        "evidence_boundary": (
            "Site-conditioned attack-opportunity differential over ordinary factual ship-combat sites. A target must be "
            "archive-resolved Privateer race 5, race-specific mission 9, cloak-capable hull and PE=0. Both target and "
            "opponent must independently reach the factual site through the candidate-set-v2 position predictor; visible "
            "T-1 foreign mine-route risks fail closed. The opponent must independently request combat through Kill!/PE. "
            "Conditional scope grants that raw requested direction; strict scope additionally requires an independent "
            "same-signature diplomacy control. Only canonical plain-STANDARD decisions are retained. Factual VCR pairs are "
            "held-out outcome labels, not eligibility inputs. T state is attribution-only for stable identity/cloak transition. "
            "This diagnostic does not promote raw iscloaked, Rob, or any cloak blocker into selection.py."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit hostile plain-STANDARD attack opportunities against Privateer Rob/PE0 ships."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT PRIVATEER ROB ATTACK-OPPORTUNITY AUDIT =====")
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
    print("NOTE: site-conditioned Privateer Rob targetability gate; no cloak blocker is promoted by this tool.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
