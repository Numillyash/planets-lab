from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.feature_scope import (
    DEFAULT_FEATURE_INDEX_PATH,
    optional_feature_scope,
)
from planets_lab.corpus.movement_differential import (
    _entity_map,
    _intish,
    _planet_tuples_by_turn,
    _settings_warp_well_state_by_turn,
)
from planets_lab.corpus.movement_residual_context import StormRecord, _storm_consensus_by_turn
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.movement_mine_context import build_mine_evidence_context
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.combat.order import standard_battle_priority_key
from planets_lab.rules.combat.selection import decide_ship_combat_pair

from combat_host_candidate_set_audit import (
    _build_independent_controls,
    _candidate_input,
    _factual_sites,
    _independent_permission,
    _owner_rows_for_turn,
    _pair,
    _requests_combat,
    _serialize,
    _tow_target_ids,
    _potential_chunnel_source_sites,
)
from combat_host_candidate_set_v2_audit import (
    _foreign_mine_route_risk,
    _factual_position_status,
)
from combat_host_factual_queue_selection_audit import (
    _build_start_stack_index,
    _decision_projection,
    _interference_state,
)
from combat_host_matching_fc_suppression_audit import (
    _relation_inventory,
    _relation_signature,
)
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_mission7_matched_control_audit import _dedup_vcrs
from combat_host_normal_movement_position_audit import (
    _archive_nuionstorms_consensus,
    _inbound_transfer_targets,
    _normal_position_prediction,
)
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    _int,
    _ship_side,
    _static_specs,
)


SCHEMA = "planets-lab.combat-host-initial-standard-target-audit.v1"
DEFAULT_EXAMPLE_LIMIT = 80


@dataclass(frozen=True, slots=True)
class PlainStandardCandidate:
    pair: tuple[int, int]
    active_ship_id: int
    target_ship_id: int
    active_priority: tuple[int, int, int]
    target_priority: tuple[int, int, int]

    @property
    def key(self) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        return self.active_priority, self.target_priority


def _priority_key_from_side(side: Mapping[str, Any]) -> tuple[int, int, int] | None:
    ship_id = _intish(side.get("ship_id"))
    if ship_id is None or ship_id <= 0:
        return None
    return standard_battle_priority_key(
        ship_id=ship_id,
        mission=_intish(side.get("mission")),
        primary_enemy=_intish(side.get("enemy")),
        friendly_code=side.get("friendlycode"),
    )


def _plain_standard_candidate(
    row: Mapping[str, Any],
    *,
    profile: str,
) -> tuple[PlainStandardCandidate | None, str | None]:
    decision = row.get(profile)
    if not isinstance(decision, Mapping):
        return None, "decision_missing"
    if decision.get("engagement_eligible") is not True:
        return None, None
    if decision.get("phase") != "standard":
        return None, "eligible_nonstandard_phase"

    left = row.get("left")
    right = row.get("right")
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        return None, "side_input_missing"

    left_key = _priority_key_from_side(left)
    right_key = _priority_key_from_side(right)
    if left_key is None or right_key is None:
        return None, "static_priority_unresolved"

    left_id = _intish(left.get("ship_id"))
    right_id = _intish(right.get("ship_id"))
    predicted_left = _intish(decision.get("left_ship_id"))
    predicted_right = _intish(decision.get("right_ship_id"))
    if (
        left_id is None
        or right_id is None
        or predicted_left is None
        or predicted_right is None
    ):
        return None, "standard_side_unresolved"

    expected_active = left_id if left_key < right_key else right_id
    expected_target = right_id if expected_active == left_id else left_id
    if predicted_right != expected_active or predicted_left != expected_target:
        return None, "nonplain_standard_side_override"

    active_key = left_key if expected_active == left_id else right_key
    target_key = right_key if expected_target == right_id else left_key
    return (
        PlainStandardCandidate(
            pair=_pair(left_id, right_id),
            active_ship_id=expected_active,
            target_ship_id=expected_target,
            active_priority=active_key,
            target_priority=target_key,
        ),
        None,
    )


def _select_first_plain_standard(
    candidates: Sequence[PlainStandardCandidate],
) -> PlainStandardCandidate | None:
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: candidate.key)


def _select_first_low_target_control(
    candidates: Sequence[PlainStandardCandidate],
) -> PlainStandardCandidate | None:
    """Alternative control: same first active ship, but lowest-priority target first."""

    if not candidates:
        return None
    first_active_priority = min(candidate.active_priority for candidate in candidates)
    active_rows = [
        candidate
        for candidate in candidates
        if candidate.active_priority == first_active_priority
    ]
    return max(active_rows, key=lambda candidate: candidate.target_priority)


def _factual_queue_by_site(
    *,
    game_id: int,
    seen: Mapping[Any, Any],
) -> dict[tuple[int, int, int], list[dict[str, Any]]]:
    result: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for (seen_game, battle_turn, vcr_id), (_digest, vcr) in sorted(seen.items()):
        if int(seen_game) != int(game_id):
            continue
        left = _ship_side(vcr, "left")
        right = _ship_side(vcr, "right")
        x = _int(vcr, "x")
        y = _int(vcr, "y")
        if left is None or right is None or x is None or y is None:
            continue
        left_id = int(left["ship_id"])
        right_id = int(right["ship_id"])
        result[(int(battle_turn), int(x), int(y))].append(
            {
                "vcr_id": int(vcr_id),
                "pair": _pair(left_id, right_id),
                "left_ship_id": left_id,
                "right_ship_id": right_id,
            }
        )
    for rows in result.values():
        rows.sort(key=lambda row: int(row["vcr_id"]))
    return result


def _profile_site_analysis(
    *,
    rows: Sequence[Mapping[str, Any]],
    profile: str,
    factual_pairs: set[tuple[int, int]],
    factual_first: Mapping[str, Any],
    all_factual_positions_exact: bool,
) -> dict[str, Any]:
    engagement_resolved = all(
        isinstance(row.get(profile), Mapping)
        and row[profile].get("engagement_eligible") is not None
        for row in rows
    )
    eligible_rows = [
        row
        for row in rows
        if isinstance(row.get(profile), Mapping)
        and row[profile].get("engagement_eligible") is True
    ]
    eligible_pairs = {_pair(*row["pair"]) for row in eligible_rows}

    candidates: list[PlainStandardCandidate] = []
    order_issues: Counter[str] = Counter()
    for row in eligible_rows:
        candidate, issue = _plain_standard_candidate(row, profile=profile)
        if issue is not None:
            order_issues[issue] += 1
        elif candidate is not None:
            candidates.append(candidate)

    order_resolved = len(candidates) == len(eligible_rows) and not order_issues
    factual_subset = factual_pairs <= eligible_pairs
    exact_set = eligible_pairs == factual_pairs
    broad_comparable = (
        all_factual_positions_exact
        and engagement_resolved
        and order_resolved
        and factual_subset
        and bool(candidates)
    )
    exact_comparable = broad_comparable and exact_set

    predicted = _select_first_plain_standard(candidates) if broad_comparable else None
    low_target_control = (
        _select_first_low_target_control(candidates) if broad_comparable else None
    )

    factual_pair = _pair(*factual_first["pair"])
    factual_right = int(factual_first["right_ship_id"])
    first_pair_exact = predicted is not None and predicted.pair == factual_pair
    first_right_exact = (
        predicted is not None
        and first_pair_exact
        and predicted.active_ship_id == factual_right
    )

    ordered = sorted(candidates, key=lambda candidate: candidate.key)
    pair_rank = None
    if broad_comparable:
        for index, candidate in enumerate(ordered, start=1):
            if candidate.pair == factual_pair:
                pair_rank = index
                break

    top_active_id = predicted.active_ship_id if predicted is not None else None
    top_active_targets = (
        sorted(
            [candidate for candidate in candidates if candidate.active_ship_id == top_active_id],
            key=lambda candidate: candidate.target_priority,
        )
        if top_active_id is not None
        else []
    )
    target_rank = None
    if broad_comparable and top_active_id == factual_right:
        for index, candidate in enumerate(top_active_targets, start=1):
            if candidate.pair == factual_pair:
                target_rank = index
                break

    return {
        "engagement_resolved": engagement_resolved,
        "eligible_pairs": [list(pair) for pair in sorted(eligible_pairs)],
        "eligible_pair_count": len(eligible_pairs),
        "order_resolved": order_resolved,
        "order_issues": _serialize(order_issues),
        "factual_subset": factual_subset,
        "exact_set": exact_set,
        "broad_comparable": broad_comparable,
        "exact_comparable": exact_comparable,
        "predicted_first": (
            {
                "pair": list(predicted.pair),
                "active_ship_id": predicted.active_ship_id,
                "target_ship_id": predicted.target_ship_id,
                "active_priority": list(predicted.active_priority),
                "target_priority": list(predicted.target_priority),
            }
            if predicted is not None
            else None
        ),
        "low_target_control_first": (
            {
                "pair": list(low_target_control.pair),
                "active_ship_id": low_target_control.active_ship_id,
                "target_ship_id": low_target_control.target_ship_id,
            }
            if low_target_control is not None
            else None
        ),
        "first_pair_exact": first_pair_exact if broad_comparable else None,
        "first_right_exact": first_right_exact if broad_comparable else None,
        "first_pair_rank": pair_rank,
        "top_active_ship_id": top_active_id,
        "top_active_target_count": len(top_active_targets),
        "factual_target_rank_within_top_active": target_rank,
        "low_target_control_pair_exact": (
            low_target_control is not None and low_target_control.pair == factual_pair
            if broad_comparable
            else None
        ),
    }


def _accumulate_scope(
    counter: Counter[str],
    ranks: Counter[str],
    analysis: Mapping[str, Any],
    *,
    exact: bool,
) -> None:
    comparable_key = "exact_comparable" if exact else "broad_comparable"
    if analysis.get(comparable_key) is not True:
        return
    counter["sites"] += 1
    if int(analysis.get("eligible_pair_count") or 0) > 1:
        counter["multi_candidate_sites"] += 1
    if analysis.get("first_pair_exact") is True:
        counter["first_pair_exact"] += 1
    else:
        counter["first_pair_mismatch"] += 1
    if analysis.get("first_right_exact") is True:
        counter["first_right_exact"] += 1
    else:
        counter["first_right_mismatch"] += 1
    if analysis.get("low_target_control_pair_exact") is True:
        counter["low_target_control_pair_exact"] += 1

    rank = analysis.get("first_pair_rank")
    if rank is not None:
        ranks[f"pair_rank:{int(rank)}"] += 1
    target_count = int(analysis.get("top_active_target_count") or 0)
    target_rank = analysis.get("factual_target_rank_within_top_active")
    if target_count > 1:
        counter["target_order_informative_sites"] += 1
        if target_rank is not None:
            ranks[f"target_rank:{int(target_rank)}"] += 1
            if int(target_rank) == 1:
                counter["target_highest_priority_exact"] += 1



def _merge_prediction_overlay(
    predicted_rows: dict[int, dict[str, Any]],
    overlay_rows: Mapping[int, Mapping[str, Any]] | None,
) -> None:
    if not isinstance(overlay_rows, Mapping):
        return
    for raw_ship_id, overlay in overlay_rows.items():
        if not isinstance(overlay, Mapping):
            continue
        ship_id = int(raw_ship_id)
        merged = dict(predicted_rows.get(ship_id, {}))
        merged.update(overlay)
        predicted_rows[ship_id] = merged


def run(args: argparse.Namespace) -> dict[str, Any]:
    totals: Counter[str] = Counter()
    strict_broad: Counter[str] = Counter()
    strict_exact: Counter[str] = Counter()
    conditional_broad: Counter[str] = Counter()
    conditional_exact: Counter[str] = Counter()
    strict_ranks: Counter[str] = Counter()
    conditional_ranks: Counter[str] = Counter()
    exclusion_reasons: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []

    feature_scope = optional_feature_scope(
        getattr(args, "feature_index", None),
        profile=getattr(args, "scope_profile", "combat-planar-no-horwasp"),
    )
    selection = feature_scope.to_dict() if feature_scope is not None else None

    for archive_path in sorted(args.archive_dir.glob("game-*.zip")):
        try:
            game_id = int(archive_path.stem.split("-")[-1])
        except ValueError:
            continue
        if feature_scope is not None:
            scope_class = feature_scope.classify(game_id)
            if scope_class != "selected":
                totals[f"scope_{scope_class}"] += 1
                continue
        totals["archives_considered"] += 1

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
        nuionstorms, _raw_storm_mode = _archive_nuionstorms_consensus(archive_data)
        mine_context = build_mine_evidence_context(
            game_id=game_id,
            archive_data=archive_data,
            snapshots=prepared.snapshots,
        )

        rows_by_turn: dict[int, dict[int, tuple[int, Mapping[str, Any]]]] = {}
        predictions_by_battle_turn: dict[int, dict[int, dict[str, Any]]] = {}

        for site_key, factual in sorted(sites.items()):
            battle_turn, x, y = site_key
            totals["sites"] += 1
            before_turn = battle_turn - 1
            factual_queue = factual_queues.get(site_key, [])
            if not factual_queue:
                exclusion_reasons["factual_queue_missing"] += 1
                continue
            factual_first = factual_queue[0]
            factual_pairs = set(factual["pairs"])

            if before_turn not in rows_by_turn:
                rows_by_turn[before_turn] = _owner_rows_for_turn(ship_groups, before_turn)
            owner_rows = rows_by_turn[before_turn]

            if battle_turn not in predictions_by_battle_turn:
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
                        "source": source,
                    }
                prediction_overlay = getattr(args, "prediction_overlay", None)
                if callable(prediction_overlay):
                    overlay_rows = prediction_overlay(
                        {
                            "game_id": game_id,
                            "battle_turn": battle_turn,
                            "before_turn": before_turn,
                            "owner_rows": owner_rows,
                            "specs": specs,
                            "planets": planets,
                            "warp_wells_enabled": warp_wells_enabled,
                            "eligible_warp_well_planet_ids": eligible_ids,
                            "races": races,
                            "mine_context": mine_context,
                        }
                    )
                    _merge_prediction_overlay(predicted_rows, overlay_rows)
                predictions_by_battle_turn[battle_turn] = predicted_rows

            predictions = predictions_by_battle_turn[battle_turn]
            site = (int(x), int(y))
            factual_ship_ids = sorted({ship_id for pair in factual_pairs for ship_id in pair})
            all_factual_positions_exact = True
            for ship_id in factual_ship_ids:
                status, _reason = _factual_position_status(
                    prediction=predictions.get(ship_id),
                    site=site,
                )
                if status != "exact":
                    all_factual_positions_exact = False
                    break
            if all_factual_positions_exact:
                totals["all_factual_positions_exact_sites"] += 1

            site_ship_rows = {
                ship_id: entry
                for ship_id, entry in predictions.items()
                if entry.get("position") == site
            }

            site_observer = getattr(args, "site_observer", None)
            if callable(site_observer):
                site_observer(
                    {
                        "game_id": game_id,
                        "battle_turn": battle_turn,
                        "before_turn": before_turn,
                        "x": x,
                        "y": y,
                        "site": site,
                        "site_ship_rows": site_ship_rows,
                        "relations": relations,
                        "controls": controls,
                        "start_stacks": start_stacks,
                        "factual": factual,
                        "factual_queue": factual_queue,
                    }
                )

            candidate_rows: list[dict[str, Any]] = []
            for a_id, b_id in combinations(sorted(site_ship_rows), 2):
                a = site_ship_rows[a_id]
                b = site_ship_rows[b_id]
                if int(a["owner_id"]) == int(b["owner_id"]):
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

                def side_input(entry: Mapping[str, Any], diplomacy: bool | None):
                    return _candidate_input(
                        game_id=game_id,
                        ship_id=int(entry["ship_id"]),
                        owner_id=int(entry["owner_id"]),
                        raw=entry["raw"],
                        race_id=entry["race_id"],
                        hull_id=entry["hull_id"],
                        hull_can_cloak=entry["hull_can_cloak"],
                        diplomacy_allows_attack=diplomacy,
                        interference_protected=(
                            a_interference if int(entry["ship_id"]) == a_id else b_interference
                        ),
                    )

                strict = _decision_projection(
                    decide_ship_combat_pair(
                        left=side_input(a, a_strict),
                        right=side_input(b, b_strict),
                        same_location=True,
                    )
                )
                conditional = _decision_projection(
                    decide_ship_combat_pair(
                        left=side_input(a, True if a_request else False),
                        right=side_input(b, True if b_request else False),
                        same_location=True,
                    )
                )
                candidate_rows.append(
                    {
                        "pair": list(pair),
                        "left": {
                            "ship_id": a_id,
                            "owner_id": a["owner_id"],
                            "mission": _intish(a["raw"].get("mission")),
                            "enemy": _intish(a["raw"].get("enemy")),
                            "friendlycode": a["raw"].get("friendlycode"),
                        },
                        "right": {
                            "ship_id": b_id,
                            "owner_id": b["owner_id"],
                            "mission": _intish(b["raw"].get("mission")),
                            "enemy": _intish(b["raw"].get("enemy")),
                            "friendlycode": b["raw"].get("friendlycode"),
                        },
                        "strict": strict,
                        "conditional": conditional,
                    }
                )

            strict = _profile_site_analysis(
                rows=candidate_rows,
                profile="strict",
                factual_pairs=factual_pairs,
                factual_first=factual_first,
                all_factual_positions_exact=all_factual_positions_exact,
            )
            conditional = _profile_site_analysis(
                rows=candidate_rows,
                profile="conditional",
                factual_pairs=factual_pairs,
                factual_first=factual_first,
                all_factual_positions_exact=all_factual_positions_exact,
            )

            _accumulate_scope(strict_broad, strict_ranks, strict, exact=False)
            _accumulate_scope(strict_exact, strict_ranks, strict, exact=True)
            _accumulate_scope(conditional_broad, conditional_ranks, conditional, exact=False)
            _accumulate_scope(conditional_exact, conditional_ranks, conditional, exact=True)

            for profile_name, analysis in (("strict", strict), ("conditional", conditional)):
                if all_factual_positions_exact and not analysis["engagement_resolved"]:
                    exclusion_reasons[f"{profile_name}:candidate_engagement_unresolved"] += 1
                if all_factual_positions_exact and analysis["engagement_resolved"] and not analysis["order_resolved"]:
                    for issue, count in analysis["order_issues"].items():
                        exclusion_reasons[f"{profile_name}:{issue}"] += int(count)
                if (
                    analysis["broad_comparable"]
                    and analysis["first_pair_exact"] is not True
                    and len(examples) < args.example_limit
                ):
                    examples.append(
                        {
                            "game_id": game_id,
                            "battle_turn": battle_turn,
                            "x": x,
                            "y": y,
                            "profile": profile_name,
                            "factual_first": factual_first,
                            "factual_queue": factual_queue[:8],
                            "factual_pairs": [list(pair) for pair in sorted(factual_pairs)],
                            "analysis": analysis,
                        }
                    )

    summary = {
        "archives_considered": int(totals["archives_considered"]),
        "feature_scope": selection,
        "scope_excluded_archives": int(totals["scope_excluded"]),
        "scope_unknown_archives": int(totals["scope_unknown"]),
        "scope_unindexed_archives": int(totals["scope_unindexed"]),
        "payload_conflicts": int(totals["payload_conflicts"]),
        "sites": int(totals["sites"]),
        "all_factual_positions_exact_sites": int(totals["all_factual_positions_exact_sites"]),
        "strict": {
            "broad": _serialize(strict_broad),
            "exact_set": _serialize(strict_exact),
            "ranks": _serialize(strict_ranks),
        },
        "conditional": {
            "broad": _serialize(conditional_broad),
            "exact_set": _serialize(conditional_exact),
            "ranks": _serialize(conditional_ranks),
        },
        "exclusion_reasons": _serialize(exclusion_reasons),
    }
    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": summary,
        "mismatch_examples": examples[: args.example_limit],
        "evidence_boundary": (
            "Initial plain-STANDARD target-selection differential only. The candidate stack is independently reconstructed "
            "from owner-current T-1 through the storm-aware position layer with visible T-1 foreign mine/web routes failed "
            "closed. Factual VCRs provide the battle-site coordinate, held-out pair set, and the observed first ship VCR only "
            "after candidate construction. Strong comparison requires every factual ship position exact, all candidate "
            "engagement decisions resolved, every eligible candidate to be plain STANDARD with static side orientation, and "
            "the factual pair set to be a subset of predicted eligible pairs. The exact-set control further requires equality. "
            "The tested hypothesis is first active ship by standard_battle_priority_key, then highest-priority eligible target. "
            "No battle outcome, survivor, capture, second-pass or planet state is modeled here. "
            "The archive population is selected through shared FeatureScope; UNKNOWN and "
            "unindexed games fail closed rather than being treated as ordinary."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the first plain STANDARD Host target selection before combat mutation."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument(
        "--feature-index",
        type=Path,
        default=DEFAULT_FEATURE_INDEX_PATH,
        help="Compiled feature index used to select the attributable combat corpus.",
    )
    parser.add_argument(
        "--scope-profile",
        default="combat-planar-no-horwasp",
        help="FeatureScope profile defining the clean combat population.",
    )
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT INITIAL STANDARD TARGET AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("MISMATCH EXAMPLES:")
    for row in report["mismatch_examples"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: first plain-STANDARD target-list selection only; no mutable combat outcome state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
