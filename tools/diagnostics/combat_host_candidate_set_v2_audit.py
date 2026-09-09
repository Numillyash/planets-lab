from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from itertools import combinations
from math import hypot
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
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_mine_context import (
    _segment_intersects_field,
    build_mine_evidence_context,
)
from planets_lab.corpus.movement_residual_context import (
    GRAVITONIC_HULL_IDS,
    StormRecord,
    _storm_consensus_by_turn,
)
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
    _scope_summary,
    _serialize,
    _tow_target_ids,
)
from combat_host_factual_queue_selection_audit import (
    _build_start_stack_index,
    _decision_projection,
    _interference_state,
)
from combat_host_matching_fc_suppression_audit import (
    _relation_inventory,
    _relation_signature,
    _safe_signature,
)
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_mission7_matched_control_audit import _dedup_vcrs
from combat_host_normal_movement_position_audit import (
    _archive_nuionstorms_consensus,
    _effective_requested_warp,
    _inbound_transfer_targets,
    _normal_position_prediction,
)
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
    _static_specs,
)
from combat_host_residual_physical_stack_audit import _xy


SCHEMA = "planets-lab.combat-host-candidate-set-audit.v2"
DEFAULT_EXAMPLE_LIMIT = 80


def _foreign_mine_route_risk(
    *,
    context: Any,
    before_turn: int,
    owner_id: int,
    raw: Mapping[str, Any],
    race_id: int | None,
    hull_id: int | None,
) -> str | None:
    """Fail closed when visible T-1 foreign mines/webs can alter ordinary movement.

    This is deliberately a *risk* gate, not a mine-hit predictor. A random hit is
    not inferred. The purpose is only to avoid treating an otherwise deterministic
    normal-movement endpoint as position-proven when the T-1 route already crosses
    a foreign field capable of changing movement/fuel state.
    """

    effective_warp, issue = _effective_requested_warp(raw, race_id=race_id)
    if issue is not None or effective_warp is None or effective_warp <= 0:
        return None

    ox, oy = _xy(raw)
    tx = _intish(raw.get("targetx"))
    ty = _intish(raw.get("targety"))
    if ox is None or oy is None or tx is None or ty is None:
        return None

    topology = context.topology
    if topology.sphere is not False:
        return "mine_route_topology_unresolved"

    origin = (int(ox), int(oy))
    target = (int(tx), int(ty))
    dx, dy = _vector(origin, target, topology)
    target_distance = hypot(dx, dy)
    if target_distance <= 1e-9:
        return None

    nominal_distance = float(effective_warp * effective_warp)
    if hull_id in GRAVITONIC_HULL_IDS:
        nominal_distance *= 2.0
    regular_distance = min(target_distance, nominal_distance)
    if regular_distance <= 1e-9:
        return None

    scale = regular_distance / target_distance
    route_vector = (dx * scale, dy * scale)
    for field in context.fields(before_turn):
        if field.owner_id == owner_id:
            continue
        if not _segment_intersects_field(
            origin=origin,
            vector=route_vector,
            field_record=field,
            topology=topology,
        ):
            continue
        if field.owner_id is None or field.owner_id <= 0:
            return "unknown_owner_mine_route_risk"
        return "web_mine_route_risk" if field.is_web else "normal_mine_route_risk"
    return None


def _factual_position_status(
    *,
    prediction: Mapping[str, Any] | None,
    site: tuple[int, int],
) -> tuple[str, str]:
    if prediction is None:
        return "unresolved", "owner_current_missing"
    position = prediction.get("position")
    source = str(prediction.get("source") or "unknown")
    if position is None:
        return "unresolved", source
    if tuple(position) == site:
        return "exact", source
    return "mismatch", source


def _pair_position_status(
    pair: tuple[int, int],
    ship_status: Mapping[int, str],
) -> str:
    left = ship_status.get(pair[0], "unresolved")
    right = ship_status.get(pair[1], "unresolved")
    if left == "exact" and right == "exact":
        return "exact"
    if "mismatch" in (left, right):
        return "mismatch"
    return "unresolved"


def run(args: argparse.Namespace) -> dict[str, Any]:
    archives_considered = 0
    payload_conflicts = 0
    all_candidate_rows: list[dict[str, Any]] = []
    site_reports: list[dict[str, Any]] = []
    factual_pair_counts: Counter[str] = Counter()
    factual_ship_position_counts: Counter[str] = Counter()
    factual_position_reasons: Counter[str] = Counter()
    candidate_position_sources: Counter[str] = Counter()
    mine_risk_counts: Counter[str] = Counter()
    position_examples: list[dict[str, Any]] = []

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
        specs = _static_specs(archive_data)
        relations = _relation_inventory(archive_data)
        start_stacks = _build_start_stack_index(ship_groups)
        seen, conflicts = _dedup_vcrs(archive_data)
        payload_conflicts += conflicts
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
                            mine_risk_counts[mine_risk] += 1
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
                        "source": source,
                    }
                position_by_battle_turn[battle_turn] = predicted_rows

            predictions = position_by_battle_turn[battle_turn]
            site = (x, y)
            factual_pairs = set(factual["pairs"])
            factual_ship_ids = sorted({ship_id for pair in factual_pairs for ship_id in pair})
            factual_ship_status: dict[int, str] = {}
            for ship_id in factual_ship_ids:
                status, reason = _factual_position_status(
                    prediction=predictions.get(ship_id),
                    site=site,
                )
                factual_ship_status[ship_id] = status
                factual_ship_position_counts[status] += 1
                factual_position_reasons[f"{status}:{reason}"] += 1
                if status != "exact" and len(position_examples) < args.example_limit:
                    entry = predictions.get(ship_id)
                    position_examples.append(
                        {
                            "game_id": game_id,
                            "battle_turn": battle_turn,
                            "x": x,
                            "y": y,
                            "ship_id": ship_id,
                            "status": status,
                            "reason": reason,
                            "predicted": list(entry["position"])
                            if entry is not None and entry.get("position") is not None
                            else None,
                        }
                    )

            site_ship_rows: dict[int, dict[str, Any]] = {}
            for ship_id, entry in predictions.items():
                if entry.get("position") != site:
                    continue
                site_ship_rows[ship_id] = entry
                candidate_position_sources[str(entry.get("source") or "unknown")] += 1

            candidate_rows: list[dict[str, Any]] = []
            for a_id, b_id in combinations(sorted(site_ship_rows), 2):
                a = site_ship_rows[a_id]
                b = site_ship_rows[b_id]
                if a["owner_id"] == b["owner_id"]:
                    continue
                pair = _pair(a_id, b_id)
                signature = _relation_signature(
                    relations.get(before_turn, {}),
                    int(a["owner_id"]),
                    int(b["owner_id"]),
                )
                a_request = _requests_combat(a["raw"], int(b["owner_id"]))
                b_request = _requests_combat(b["raw"], int(a["owner_id"]))
                excluded = frozenset(factual["pair_rows"].get(pair, set()))
                a_strict = _independent_permission(
                    request=a_request,
                    owner_id=int(a["owner_id"]),
                    opponent_owner_id=int(b["owner_id"]),
                    signature=signature,
                    controls=controls,
                    excluded_rows=excluded,
                )
                b_strict = _independent_permission(
                    request=b_request,
                    owner_id=int(b["owner_id"]),
                    opponent_owner_id=int(a["owner_id"]),
                    signature=signature,
                    controls=controls,
                    excluded_rows=excluded,
                )
                a_interference = _interference_state(
                    game_id=game_id,
                    before_turn=before_turn,
                    owner_id=int(a["owner_id"]),
                    raw=a["raw"],
                    start_stacks=start_stacks,
                )
                b_interference = _interference_state(
                    game_id=game_id,
                    before_turn=before_turn,
                    owner_id=int(b["owner_id"]),
                    raw=b["raw"],
                    start_stacks=start_stacks,
                )

                strict_a = _candidate_input(
                    game_id=game_id,
                    ship_id=a_id,
                    owner_id=int(a["owner_id"]),
                    raw=a["raw"],
                    race_id=a["race_id"],
                    hull_id=a["hull_id"],
                    hull_can_cloak=a["hull_can_cloak"],
                    diplomacy_allows_attack=a_strict,
                    interference_protected=a_interference,
                )
                strict_b = _candidate_input(
                    game_id=game_id,
                    ship_id=b_id,
                    owner_id=int(b["owner_id"]),
                    raw=b["raw"],
                    race_id=b["race_id"],
                    hull_id=b["hull_id"],
                    hull_can_cloak=b["hull_can_cloak"],
                    diplomacy_allows_attack=b_strict,
                    interference_protected=b_interference,
                )
                conditional_a = _candidate_input(
                    game_id=game_id,
                    ship_id=a_id,
                    owner_id=int(a["owner_id"]),
                    raw=a["raw"],
                    race_id=a["race_id"],
                    hull_id=a["hull_id"],
                    hull_can_cloak=a["hull_can_cloak"],
                    diplomacy_allows_attack=True if a_request else False,
                    interference_protected=a_interference,
                )
                conditional_b = _candidate_input(
                    game_id=game_id,
                    ship_id=b_id,
                    owner_id=int(b["owner_id"]),
                    raw=b["raw"],
                    race_id=b["race_id"],
                    hull_id=b["hull_id"],
                    hull_can_cloak=b["hull_can_cloak"],
                    diplomacy_allows_attack=True if b_request else False,
                    interference_protected=b_interference,
                )
                strict = _decision_projection(
                    decide_ship_combat_pair(
                        left=strict_a,
                        right=strict_b,
                        same_location=True,
                    )
                )
                conditional = _decision_projection(
                    decide_ship_combat_pair(
                        left=conditional_a,
                        right=conditional_b,
                        same_location=True,
                    )
                )
                row = {
                    "game_id": game_id,
                    "battle_turn": battle_turn,
                    "x": x,
                    "y": y,
                    "pair": list(pair),
                    "factual_pair": pair in factual_pairs,
                    "relation_signature": _safe_signature(signature),
                    "left": {
                        "ship_id": a_id,
                        "owner_id": a["owner_id"],
                        "position_source": a["source"],
                        "mission": _intish(a["raw"].get("mission")),
                        "mission1target": _intish(a["raw"].get("mission1target")),
                        "enemy": _intish(a["raw"].get("enemy")),
                        "friendlycode": a["raw"].get("friendlycode"),
                        "strict_diplomacy_allows_attack": a_strict,
                    },
                    "right": {
                        "ship_id": b_id,
                        "owner_id": b["owner_id"],
                        "position_source": b["source"],
                        "mission": _intish(b["raw"].get("mission")),
                        "mission1target": _intish(b["raw"].get("mission1target")),
                        "enemy": _intish(b["raw"].get("enemy")),
                        "friendlycode": b["raw"].get("friendlycode"),
                        "strict_diplomacy_allows_attack": b_strict,
                    },
                    "strict": strict,
                    "conditional": conditional,
                }
                candidate_rows.append(row)
                all_candidate_rows.append(row)

            candidate_pairs = {tuple(row["pair"]) for row in candidate_rows}
            covered_factual = factual_pairs & candidate_pairs
            factual_pair_counts["total"] += len(factual_pairs)
            factual_pair_counts["candidate_covered"] += len(covered_factual)
            for pair in sorted(factual_pairs):
                status = _pair_position_status(pair, factual_ship_status)
                factual_pair_counts[f"position_{status}"] += 1
                if pair not in candidate_pairs:
                    factual_pair_counts["candidate_uncovered"] += 1

            strict_eligible = {
                tuple(row["pair"])
                for row in candidate_rows
                if row["strict"].get("engagement_eligible") is True
            }
            strict_blocked = {
                tuple(row["pair"])
                for row in candidate_rows
                if row["strict"].get("engagement_eligible") is False
            }
            strict_unresolved = candidate_pairs - strict_eligible - strict_blocked
            conditional_eligible = {
                tuple(row["pair"])
                for row in candidate_rows
                if row["conditional"].get("engagement_eligible") is True
            }
            conditional_blocked = {
                tuple(row["pair"])
                for row in candidate_rows
                if row["conditional"].get("engagement_eligible") is False
            }
            conditional_unresolved = candidate_pairs - conditional_eligible - conditional_blocked
            all_factual_position_covered = factual_pairs <= candidate_pairs
            all_strict_resolved = not strict_unresolved
            all_conditional_resolved = not conditional_unresolved
            site_reports.append(
                {
                    "game_id": game_id,
                    "battle_turn": battle_turn,
                    "x": x,
                    "y": y,
                    "factual_pairs": [list(pair) for pair in sorted(factual_pairs)],
                    "predicted_site_ship_ids": sorted(site_ship_rows),
                    "candidate_pairs": [list(pair) for pair in sorted(candidate_pairs)],
                    "factual_candidate_covered": len(covered_factual),
                    "all_factual_position_covered": all_factual_position_covered,
                    "strict_all_candidate_resolved": all_strict_resolved,
                    "strict_factual_subset_of_eligible": (
                        factual_pairs <= strict_eligible
                        if all_factual_position_covered and all_strict_resolved
                        else None
                    ),
                    "strict_eligible_exact_factual": (
                        strict_eligible == factual_pairs
                        if all_factual_position_covered and all_strict_resolved
                        else None
                    ),
                    "conditional_all_candidate_resolved": all_conditional_resolved,
                    "conditional_factual_subset_of_eligible": (
                        factual_pairs <= conditional_eligible
                        if all_factual_position_covered and all_conditional_resolved
                        else None
                    ),
                    "conditional_eligible_exact_factual": (
                        conditional_eligible == factual_pairs
                        if all_factual_position_covered and all_conditional_resolved
                        else None
                    ),
                }
            )

    site_counts: Counter[str] = Counter()
    for site in site_reports:
        site_counts["sites"] += 1
        if site["all_factual_position_covered"]:
            site_counts["all_factual_position_covered"] += 1
        if site["strict_all_candidate_resolved"]:
            site_counts["strict_all_candidate_resolved"] += 1
        if site["strict_factual_subset_of_eligible"] is True:
            site_counts["strict_factual_subset_of_eligible"] += 1
        elif site["strict_factual_subset_of_eligible"] is False:
            site_counts["strict_factual_not_subset_of_eligible"] += 1
        if site["strict_eligible_exact_factual"] is True:
            site_counts["strict_eligible_exact_factual"] += 1
        if site["conditional_all_candidate_resolved"]:
            site_counts["conditional_all_candidate_resolved"] += 1
        if site["conditional_factual_subset_of_eligible"] is True:
            site_counts["conditional_factual_subset_of_eligible"] += 1
        elif site["conditional_factual_subset_of_eligible"] is False:
            site_counts["conditional_factual_not_subset_of_eligible"] += 1
        if site["conditional_eligible_exact_factual"] is True:
            site_counts["conditional_eligible_exact_factual"] += 1

    decision_examples = [
        row
        for row in all_candidate_rows
        if row["factual_pair"]
        and (
            row["conditional"].get("engagement_eligible") is not True
            or row["strict"].get("engagement_eligible") is False
        )
    ]
    extra_examples = [
        row
        for row in all_candidate_rows
        if not row["factual_pair"] and row["conditional"].get("engagement_eligible") is True
    ]

    summary = {
        "archives_considered": archives_considered,
        "special_game_591478_excluded": True,
        "payload_conflicts": payload_conflicts,
        "factual_ship_combat_sites": len(site_reports),
        "factual_unique_pairs": int(factual_pair_counts["total"]),
        "factual_pairs_candidate_covered": int(factual_pair_counts["candidate_covered"]),
        "factual_pairs_candidate_uncovered": int(factual_pair_counts["candidate_uncovered"]),
        "factual_pair_position_status": {
            "exact": int(factual_pair_counts["position_exact"]),
            "mismatch": int(factual_pair_counts["position_mismatch"]),
            "unresolved": int(factual_pair_counts["position_unresolved"]),
        },
        "factual_ship_position_status": _serialize(factual_ship_position_counts),
        "factual_position_reasons": _serialize(factual_position_reasons),
        "candidate_pairs": len(all_candidate_rows),
        "candidate_position_sources": _serialize(candidate_position_sources),
        "mine_route_risk": _serialize(mine_risk_counts),
        "strict": _scope_summary(all_candidate_rows, "strict"),
        "conditional": _scope_summary(all_candidate_rows, "conditional"),
        "sites": _serialize(site_counts),
    }
    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": summary,
        "position_examples": position_examples[: args.example_limit],
        "decision_examples": (decision_examples + extra_examples)[: args.example_limit],
        "evidence_boundary": (
            "Site-conditioned candidate-set v2 differential. Factual VCRs provide only ordinary battle-site coordinates "
            "and held-out pair sets. Every candidate ship must independently reach that site from owner-current T-1 state "
            "through the repaired storm-aware position-v3 predictor. Visible T-1 foreign normal/web mine route crossings "
            "fail closed because hit occurrence is stochastic; no mine hit is inferred. Battle-turn-created fields and other "
            "unobservable same-Host-turn effects can therefore remain position mismatches rather than predictor inputs. "
            "Tow/Intercept/C&I/HYP/Chunnel-source/transfer/MKT/sphere/fuel-proration and other unresolved position branches "
            "remain excluded. Strict diplomacy is leave-pair-out; conditional diplomacy remains an upper-bound composition "
            "profile. Extra eligible nonfactual pairs are not queue errors until mutable target selection is reconstructed."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit storm-aware T-1-derived combat candidate sets against ordinary factual VCR pairs."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT CANDIDATE-SET V2 AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("POSITION EXAMPLES:")
    for row in report["position_examples"]:
        print(row)
    print()
    print("DECISION EXAMPLES:")
    for row in report["decision_examples"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: site-conditioned position-derived candidate-set gate; not a mutable Host queue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
