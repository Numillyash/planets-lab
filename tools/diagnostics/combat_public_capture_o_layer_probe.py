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
for _path in (REPO_ROOT / "src", DIAGNOSTICS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import combat_host_initial_standard_target_audit as baseline_module
import combat_host_post_capture_active_membership_audit as active_module
import combat_ship_chain_audit as chain_module
import combat_host_post_capture_special_movement_audit as special_movement_module
from combat_host_post_capture_pair_recomposition_audit import (
    _external_c2ng_original_order_prize_continuation,
)
from combat_host_post_mutation_next_pair_audit import _appearance_key
from combat_public_capture_side_frozen_candidate import (
    predict_frozen_capture_side,
)
from combat_public_capture_side_postheldout_validation import (
    evaluate_frozen_postheldout_candidate,
)
from combat_public_capture_side_postindependent_validation import (
    evaluate_frozen_postindependent_candidate,
)
from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.corpus_db_compact import reconstruct_compact_member
from planets_lab.corpus.corpus_db_runtime import (
    connect_compact_generation_read_only,
    connect_current_compact_read_only,
    first_last_member_refs,
    member_refs_for_turns,
    reconstruct_members,
)
from planets_lab.corpus.movement_differential import (
    _entity_map,
    _intish,
    _planet_tuples_by_turn,
    _settings_warp_well_state_by_turn,
)
from planets_lab.corpus.movement_mine_context import MineEvidenceContext
from planets_lab.corpus.movement_residual_context import (
    _storm_consensus_by_turn,
)
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import (
    MapTopologyEvidence,
    _topology_candidates,
    _unique_bool,
    _unique_int,
    _unique_shape,
)
from planets_lab.corpus.normalizer import (
    ArchiveTurnSnapshot,
    mechanics_projection,
)
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.data.nu_static import import_static_all

from combat_host_candidate_set_audit import (
    _build_independent_controls,
    _factual_sites,
    _owner_rows_for_turn,
    _potential_chunnel_source_sites,
    _tow_target_ids,
)
from combat_host_candidate_set_v2_audit import _foreign_mine_route_risk
from combat_host_factual_queue_selection_audit import _build_start_stack_index
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_normal_movement_position_audit import (
    _boolish,
    _find_named_setting,
    _inbound_transfer_targets,
    _normal_position_prediction,
)


SCHEMA = "planets-lab.combat-public-capture-o-layer-probe.v2.db1"
DEFAULT_DISCOVERY = Path(
    "artifacts/public-capture-side/discovery-capture-side.json"
)
DEFAULT_OUTPUT = Path(
    "artifacts/public-capture-side/discovery-o-layer-probe.json"
)


def _load_capture_side_report(
    path: Path,
    *,
    expected_partition: str,
) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("capture-side artifact must be a JSON object")
    if payload.get("partition") != expected_partition:
        raise ValueError(
            "O-layer probe partition mismatch: "
            f"expected {expected_partition!r}, got {payload.get('partition')!r}"
        )
    observations = payload.get("observations")
    if (
        not isinstance(observations, Sequence)
        or isinstance(observations, (str, bytes))
        or not all(isinstance(row, Mapping) for row in observations)
    ):
        raise ValueError("capture-side observations are missing or malformed")
    return payload


def _targets_by_site(
    observations: Sequence[Mapping[str, Any]],
) -> dict[tuple[int, int, int, int], list[Mapping[str, Any]]]:
    result: dict[
        tuple[int, int, int, int],
        list[Mapping[str, Any]],
    ] = defaultdict(list)
    for row in observations:
        game_id = row.get("game_id")
        turn = row.get("turn")
        position = row.get("position")
        if (
            isinstance(game_id, bool)
            or not isinstance(game_id, int)
            or isinstance(turn, bool)
            or not isinstance(turn, int)
            or not isinstance(position, Sequence)
            or isinstance(position, (str, bytes))
            or len(position) != 2
            or any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in position
            )
        ):
            raise ValueError("discovery observation has invalid site identity")
        result[(game_id, turn, int(position[0]), int(position[1]))].append(row)
    return result


def _appearance_mapping(
    appearances: Sequence[Mapping[str, Any]],
) -> dict[tuple[int, int, int, int], Mapping[str, Any]]:
    result: dict[tuple[int, int, int, int], Mapping[str, Any]] = {}
    for row in appearances:
        values = (
            row.get("game_id"),
            row.get("turn"),
            row.get("vcr_id"),
            row.get("ship_id"),
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in values
        ):
            continue
        game_id, turn, vcr_id, ship_id = (int(value) for value in values)
        result[_appearance_key(game_id, turn, vcr_id, ship_id)] = row
    return result



def _pseudo_seen_from_appearances(
    *,
    appearances: Sequence[Mapping[str, Any]],
    game_id: int,
    battle_turns: set[int],
) -> dict[tuple[int, int, int], tuple[str, dict[str, Any]]]:
    grouped: dict[tuple[int, int, int], dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in appearances:
        if row.get("game_id") != game_id or row.get("turn") not in battle_turns:
            continue
        vcr_id = row.get("vcr_id")
        side = row.get("side")
        if (
            isinstance(vcr_id, bool)
            or not isinstance(vcr_id, int)
            or side not in {"left", "right"}
        ):
            continue
        grouped[(game_id, int(row["turn"]), int(vcr_id))][str(side)] = row

    seen: dict[tuple[int, int, int], tuple[str, dict[str, Any]]] = {}
    for key, sides in sorted(grouped.items()):
        left = sides.get("left")
        right = sides.get("right")
        if not isinstance(left, Mapping) or not isinstance(right, Mapping):
            continue
        left_position = left.get("position")
        right_position = right.get("position")
        if (
            not isinstance(left_position, list)
            or not isinstance(right_position, list)
            or len(left_position) != 2
            or len(right_position) != 2
            or left_position != right_position
            or any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in left_position
            )
        ):
            continue
        left_ship = left.get("ship_id")
        right_ship = right.get("ship_id")
        left_hull = left.get("hull_id")
        right_hull = right.get("hull_id")
        left_owner = left.get("owner_id")
        right_owner = right.get("owner_id")
        numeric = (left_ship, right_ship, left_hull, right_hull, left_owner, right_owner)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in numeric):
            continue
        _game, turn, vcr_id = key
        vcr = {
            "id": vcr_id,
            "turn": turn,
            "x": int(left_position[0]),
            "y": int(left_position[1]),
            "leftownerid": int(left_owner),
            "rightownerid": int(right_owner),
            "left": {"objectid": int(left_ship), "hullid": int(left_hull)},
            "right": {"objectid": int(right_ship), "hullid": int(right_hull)},
        }
        seen[key] = ("appearance-cache", vcr)
    return seen


def _topology_from_payloads(
    *,
    first_member: TurnMember,
    first_payload: Mapping[str, Any],
    last_member: TurnMember,
    last_payload: Mapping[str, Any],
) -> MapTopologyEvidence:
    def candidates(payload: Mapping[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for root_name in ("settings", "game"):
            root = payload.get(root_name)
            if isinstance(root, (Mapping, list, tuple)):
                result.update(_topology_candidates(root, prefix=root_name))
        return dict(sorted(result.items()))

    first_candidates = candidates(first_payload)
    last_candidates = candidates(last_payload)
    sphere_first = _unique_bool(first_candidates, "sphere")
    sphere_last = _unique_bool(last_candidates, "sphere")
    width_first = _unique_int(first_candidates, "mapwidth")
    width_last = _unique_int(last_candidates, "mapwidth")
    height_first = _unique_int(first_candidates, "mapheight")
    height_last = _unique_int(last_candidates, "mapheight")
    shape_first = _unique_shape(first_candidates)
    shape_last = _unique_shape(last_candidates)
    return MapTopologyEvidence(
        sphere=sphere_first if sphere_first == sphere_last else None,
        mapwidth=width_first if width_first == width_last else None,
        mapheight=height_first if height_first == height_last else None,
        mapshape=shape_first if shape_first == shape_last else None,
        first_member=first_member.name,
        last_member=last_member.name,
        stable=first_candidates == last_candidates,
        first_candidates=first_candidates,
        last_candidates=last_candidates,
    )


def _nuionstorms_from_payloads(
    first_payload: Mapping[str, Any],
    last_payload: Mapping[str, Any],
) -> bool | None:
    parsed: set[bool] = set()
    for payload in (first_payload, last_payload):
        for value in _find_named_setting(payload, "nuionstorms"):
            flag = _boolish(value)
            if flag is not None:
                parsed.add(flag)
    return next(iter(parsed)) if len(parsed) == 1 else None


def _collect_targeted_appearances_from_db(
    *,
    connection: Any,
    game_id: int,
    battle_turns: set[int],
) -> tuple[list[dict[str, Any]], Mapping[str, Any]]:
    refs = member_refs_for_turns(
        connection,
        game_id=game_id,
        turns=battle_turns,
        include_embedded_turn=True,
    )
    unique_cases: dict[tuple[int, int, int], dict[str, Any]] = {}
    conflicts: set[tuple[int, int, int]] = set()
    summary: Counter[str] = Counter()
    summary["source_members"] = len(refs)

    for _ref, payload in reconstruct_members(connection, refs):
        game = payload.get("game")
        if not isinstance(game, Mapping):
            continue
        observed_game_id = chain_module._int(game, "id")
        game_turn = chain_module._int(game, "turn")
        if observed_game_id != game_id or game_turn is None:
            continue
        beams = chain_module._objects(payload, "beams")
        torpedoes = chain_module._objects(payload, "torpedos")
        settings = payload.get("settings")
        settings = dict(settings) if isinstance(settings, Mapping) else {}

        for raw_vcr in chain_module._objects(payload, "vcrs"):
            vcr_id = chain_module._int(raw_vcr, "id")
            battle_turn = chain_module._int(raw_vcr, "turn") or game_turn
            if vcr_id is None or battle_turn not in battle_turns:
                continue
            summary["raw_vcr_observations"] += 1
            key = (game_id, battle_turn, vcr_id)
            payload_hash = chain_module._canonical_hash(raw_vcr)
            existing = unique_cases.get(key)
            if existing is None:
                unique_cases[key] = {
                    "payload": dict(raw_vcr),
                    "payload_hash": payload_hash,
                    "beams": beams,
                    "torpedoes": torpedoes,
                    "settings": settings,
                }
            elif existing["payload_hash"] != payload_hash:
                conflicts.add(key)

    summary["unique_vcrs"] = len(unique_cases)
    summary["payload_conflicts"] = len(conflicts)

    appearances: list[dict[str, Any]] = []
    for key, case in sorted(unique_cases.items()):
        if key in conflicts:
            continue
        _game, turn, vcr_id = key
        try:
            replay = chain_module.replay_nuhost_from_nu_catalog(
                case["payload"],
                beams=case["beams"],
                torpedoes=case["torpedoes"],
                settings=case["settings"],
            )
        except chain_module.ReplayUnsupported:
            summary["replay_unsupported"] += 1
            continue

        summary["replay_supported"] += 1
        position = chain_module._position(case["payload"])
        for side_name in ("left", "right"):
            raw_side = case["payload"].get(side_name)
            replay_side = replay.get(side_name)
            if not isinstance(raw_side, Mapping) or not isinstance(replay_side, Mapping):
                continue
            appearance = chain_module._appearance(
                game_id=game_id,
                turn=turn,
                vcr_id=vcr_id,
                position=position,
                side_name=side_name,
                raw_side=raw_side,
                replay_side=replay_side,
            )
            if appearance is not None:
                appearances.append(appearance)
                summary["ship_appearances"] += 1

    return appearances, dict(summary)


def _targeted_db_context(
    *,
    connection: Any,
    game_id: int,
    battle_turns: set[int],
) -> dict[str, Any]:
    before_turns = {turn - 1 for turn in battle_turns}
    wanted_turns = before_turns | battle_turns
    snapshots: list[ArchiveTurnSnapshot] = []
    relations: dict[
        int,
        dict[tuple[int, int], set[tuple[int | None, int | None, int | None]]],
    ] = defaultdict(lambda: defaultdict(set))

    first_ref, last_ref = first_last_member_refs(connection, game_id=game_id)
    first_payload = reconstruct_compact_member(connection, first_ref.member_id)
    if last_ref.member_id == first_ref.member_id:
        last_payload = first_payload
    else:
        last_payload = reconstruct_compact_member(connection, last_ref.member_id)

    specs = NuStaticSpecs.from_catalog(import_static_all(first_payload))
    topology = effective_sphere_topology(
        game_id=game_id,
        topology=_topology_from_payloads(
            first_member=first_ref.turn_member,
            first_payload=first_payload,
            last_member=last_ref.turn_member,
            last_payload=last_payload,
        ),
    )
    nuionstorms = _nuionstorms_from_payloads(first_payload, last_payload)

    refs = member_refs_for_turns(
        connection,
        game_id=game_id,
        turns=wanted_turns,
        include_embedded_turn=False,
    )
    for ref, parsed in reconstruct_members(connection, refs):
        member = ref.turn_member
        projection = mechanics_projection(parsed, member=member.name)
        projection_game = projection["game"]
        projection_player = projection["player"]
        observed_game_id = projection_game.get("id")
        observed_player_id = projection_player.get("id")
        observed_turn = projection_game.get("turn")
        if (
            observed_game_id != game_id
            or isinstance(observed_player_id, bool)
            or not isinstance(observed_player_id, int)
            or isinstance(observed_turn, bool)
            or not isinstance(observed_turn, int)
        ):
            raise ValueError(f"{member.name}: targeted DB snapshot identity mismatch")

        snapshots.append(
            ArchiveTurnSnapshot(
                member=member,
                game_id=game_id,
                player_id=int(observed_player_id),
                embedded_turn=int(observed_turn),
                snapshot_hash=ref.decoded_payload_sha256,
                mechanics_payload=projection,
            )
        )

        if member.turn in before_turns:
            raw_relations = parsed.get("relations")
            if isinstance(raw_relations, list):
                for relation in raw_relations:
                    if not isinstance(relation, Mapping):
                        continue
                    source = _intish(relation.get("playerid"))
                    target = _intish(relation.get("playertoid"))
                    if (
                        source is None
                        or source <= 0
                        or target is None
                        or target <= 0
                        or source == target
                    ):
                        continue
                    relations[member.turn][(source, target)].add(
                        (
                            _intish(relation.get("relationto")),
                            _intish(relation.get("relationfrom")),
                            _intish(relation.get("conflictlevel")),
                        )
                    )

    ordered = tuple(
        sorted(snapshots, key=lambda item: (item.player_id, item.archive_turn))
    )
    return {
        "snapshots": ordered,
        "specs": specs,
        "topology": topology,
        "nuionstorms": nuionstorms,
        "relations": {
            turn: {pair: set(values) for pair, values in rows.items()}
            for turn, rows in relations.items()
        },
    }


def _visit_targeted_site_contexts(
    *,
    connection: Any,
    game_id: int,
    targets: Mapping[tuple[int, int, int, int], Sequence[Mapping[str, Any]]],
    appearances: Sequence[Mapping[str, Any]],
    observer: Any,
    collect_pre_mine_counterfactual: bool = False,
) -> dict[str, Any]:
    # Opt-in diagnostics only: never alter the primary position or queue.
    if type(collect_pre_mine_counterfactual) is not bool:
        raise ValueError("invalid pre-mine diagnostic flag")
    battle_turns = {
        int(turn)
        for target_game, turn, _x, _y in targets
        if int(target_game) == game_id
    }
    targeted = _targeted_db_context(
        connection=connection,
        game_id=game_id,
        battle_turns=battle_turns,
    )
    snapshots = targeted["snapshots"]
    specs = targeted["specs"]
    topology = targeted["topology"]
    relations = targeted["relations"]
    nuionstorms = targeted["nuionstorms"]

    ship_groups = group_perspective_records(snapshots, "ship")
    races, _race_conflicts = _player_races(snapshots)
    start_stacks = _build_start_stack_index(ship_groups)
    entities = _entity_map(snapshots)
    planets_by_turn = _planet_tuples_by_turn(entities, include_ineligible=True)
    warp_wells_by_turn, _legacy_warp_turns = _settings_warp_well_state_by_turn(
        snapshots
    )
    eligible_by_turn = getattr(entities, "warp_well_planet_ids_by_turn", {})
    storms_by_turn, storm_conflicts, storm_invalid = _storm_consensus_by_turn(
        snapshots
    )
    mine_context = MineEvidenceContext(
        snapshots=tuple(snapshots),
        specs=specs,
        topology=topology,
        ship_groups=ship_groups,
    )

    pseudo_seen = _pseudo_seen_from_appearances(
        appearances=appearances,
        game_id=game_id,
        battle_turns=battle_turns,
    )
    factual_sites = _factual_sites(game_id=game_id, seen=pseudo_seen)
    factual_queues = baseline_module._factual_queue_by_site(
        game_id=game_id,
        seen=pseudo_seen,
    )
    controls = _build_independent_controls(
        game_id=game_id,
        seen=pseudo_seen,
        ship_groups=ship_groups,
        relations=relations,
    )

    rows_by_turn: dict[int, dict[int, tuple[int, Mapping[str, Any]]]] = {}
    predictions_by_battle_turn: dict[int, dict[int, dict[str, Any]]] = {}
    visited_sites = 0

    for site_key in sorted(targets):
        target_game, battle_turn, x, y = site_key
        if int(target_game) != game_id:
            continue
        before_turn = int(battle_turn) - 1
        factual = factual_sites.get((int(battle_turn), int(x), int(y)))
        factual_queue = factual_queues.get(
            (int(battle_turn), int(x), int(y)),
            [],
        )
        if not isinstance(factual, Mapping) or not factual_queue:
            continue

        if before_turn not in rows_by_turn:
            rows_by_turn[before_turn] = _owner_rows_for_turn(
                ship_groups,
                before_turn,
            )
        owner_rows = rows_by_turn[before_turn]

        if int(battle_turn) not in predictions_by_battle_turn:
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
            if int(battle_turn) in storm_conflicts:
                storms = None
                storm_issue = "storm_context_conflict"
            elif int(battle_turn) in storm_invalid:
                storms = None
                storm_issue = "storm_context_invalid"
            else:
                storms = storms_by_turn.get(int(battle_turn), ())
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
                pre_mine_position = predicted
                pre_mine_source = source
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
                    "hull_can_cloak": (
                        hull.can_cloak if hull is not None else None
                    ),
                    "position": predicted,
                    "source": source,
                }
                # A counterfactual in which the independent NORMAL movement
                # planner runs but the foreign-mine risk mask is *not* applied.
                # It does not assert that a real ship avoided a mine hit.
                if (collect_pre_mine_counterfactual and
                        source == "normal_mine_route_risk" and
                        pre_mine_position is not None):
                    predicted_rows[ship_id]["diagnostic_no_mine_hit_destination"] = tuple(pre_mine_position)
                    predicted_rows[ship_id]["diagnostic_no_mine_hit_source"] = pre_mine_source

            overlay = special_movement_module.special_position_overlay(
                {
                    "game_id": game_id,
                    "battle_turn": int(battle_turn),
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
            baseline_module._merge_prediction_overlay(predicted_rows, overlay)
            predictions_by_battle_turn[int(battle_turn)] = predicted_rows

        predictions = predictions_by_battle_turn[int(battle_turn)]
        site = (int(x), int(y))
        site_ship_rows = {
            ship_id: entry
            for ship_id, entry in predictions.items()
            if entry.get("position") == site
        }
        observer(
            {
                "game_id": game_id,
                "battle_turn": int(battle_turn),
                "before_turn": before_turn,
                "x": int(x),
                "y": int(y),
                "site": site,
                "site_ship_rows": site_ship_rows,
                "predictions": predictions,
                "relations": relations,
                "controls": controls,
                "start_stacks": start_stacks,
                "factual": factual,
                "factual_queue": factual_queue,
            }
        )
        visited_sites += 1

    return {
        "targeted_snapshot_count": len(snapshots),
        "targeted_archive_turns": sorted(
            {snapshot.archive_turn for snapshot in snapshots}
        ),
        "pseudo_vcr_count": len(pseudo_seen),
        "visited_sites": visited_sites,
    }


def _capture_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ship_id": row.get("captured_ship_id"),
        "captor_ship_id": row.get("captor_ship_id"),
        "captor_owner_id": row.get("captor_owner_id"),
        "current_opponent_ship_id": row.get("next_opponent_ship_id"),
        "from_vcr_id": row.get("capture_vcr_id"),
        "to_vcr_id": row.get("next_vcr_id"),
        "current_side": row.get("captured_ship_side_next"),
    }


def _identity_anchor_factual_opponent(
    *,
    active_result: Mapping[str, Any],
    factual_opponent_id: int,
) -> dict[str, Any]:
    """Condition the external cursor on the factual N+1 opponent identity only.

    The observed N+1 VCR proves that this ship is active and strictly eligible
    for that combat step. This helper intentionally injects only that identity /
    eligibility fact. It does not read or inject the factual LEFT/RIGHT side.
    The result is therefore a side-only discriminator, not an independent queue
    predictor.
    """

    anchored = dict(active_result)
    active_ids_raw = active_result.get("active_ship_ids")
    active_ids = [
        int(value)
        for value in active_ids_raw
        if isinstance(value, int) and not isinstance(value, bool)
    ] if isinstance(active_ids_raw, list) else []
    if factual_opponent_id not in active_ids:
        active_ids.append(factual_opponent_id)
    anchored["active_ship_ids"] = active_ids

    candidate_rows_raw = active_result.get("candidates")
    candidate_rows = [
        dict(row)
        for row in candidate_rows_raw
        if isinstance(row, Mapping)
    ] if isinstance(candidate_rows_raw, list) else []
    factual_row = next(
        (
            row
            for row in candidate_rows
            if row.get("ship_id") == factual_opponent_id
        ),
        None,
    )
    if factual_row is None:
        candidate_rows.append(
            {
                "ship_id": factual_opponent_id,
                "requests_new_owner": True,
                "strict_permission": True,
                "identity_anchored_from_factual_nplus1": True,
            }
        )
    else:
        factual_row["requests_new_owner"] = True
        factual_row["strict_permission"] = True
        factual_row["identity_anchored_from_factual_nplus1"] = True
    anchored["candidates"] = candidate_rows
    return anchored


def run(args: argparse.Namespace) -> dict[str, Any]:
    partition = str(getattr(args, "partition", "discovery"))
    capture_partition = (
        "all" if partition in {"independent", "prospective"} else partition
    )
    capture_side_report = _load_capture_side_report(
        args.capture_side_report,
        expected_partition=capture_partition,
    )
    observations = [
        dict(row)
        for row in capture_side_report["observations"]
        if isinstance(row, Mapping)
    ]
    scan_ids_raw = capture_side_report.get("scanned_game_ids")
    if (
        not isinstance(scan_ids_raw, Sequence)
        or isinstance(scan_ids_raw, (str, bytes))
    ):
        raise ValueError("capture-side scanned_game_ids missing")
    full_scan_ids = {
        int(value)
        for value in scan_ids_raw
        if isinstance(value, int) and not isinstance(value, bool)
    }
    if not full_scan_ids:
        raise ValueError("capture-side game population is empty")

    requested_game_id = getattr(args, "game_id", None)
    if requested_game_id is not None:
        if requested_game_id not in full_scan_ids:
            raise ValueError(
                f"game {requested_game_id} is not in the {partition} partition"
            )
        observations = [
            row
            for row in observations
            if int(row["game_id"]) == int(requested_game_id)
        ]
        scan_ids = {int(requested_game_id)}
    else:
        scan_ids = set(full_scan_ids)

    targets = _targets_by_site(observations)
    battle_turns_by_game: dict[int, set[int]] = defaultdict(set)
    for game_id, battle_turn, _x, _y in targets:
        battle_turns_by_game[int(game_id)].add(int(battle_turn))

    if args.corpus_db_generation is not None:
        connection, database_path = connect_compact_generation_read_only(
            args.corpus_db_generation,
            args.corpus_db_root,
        )
    else:
        connection, database_path = connect_current_compact_read_only(
            args.corpus_db_root
        )
    try:
        appearances: list[dict[str, Any]] = []
        appearance_summary: Counter[str] = Counter()
        for game_id in sorted(scan_ids):
            game_appearances, game_summary = _collect_targeted_appearances_from_db(
                connection=connection,
                game_id=game_id,
                battle_turns=battle_turns_by_game.get(game_id, set()),
            )
            appearances.extend(game_appearances)
            for key, value in game_summary.items():
                if isinstance(value, int) and not isinstance(value, bool):
                    appearance_summary[str(key)] += int(value)
        appearances_by_key = _appearance_mapping(appearances)

        counts: Counter[str] = Counter()
        examples: list[dict[str, Any]] = []
        seen: set[tuple[int, int, int, int]] = set()

        def observer(context: Mapping[str, Any]) -> None:
            site_key = (
                int(context["game_id"]),
                int(context["battle_turn"]),
                int(context["x"]),
                int(context["y"]),
            )
            rows = targets.get(site_key, ())
            for row in rows:
                capture = _capture_projection(row)
                from_vcr_id = capture.get("from_vcr_id")
                prize_id = capture.get("ship_id")
                if (
                    isinstance(from_vcr_id, bool)
                    or not isinstance(from_vcr_id, int)
                    or isinstance(prize_id, bool)
                    or not isinstance(prize_id, int)
                ):
                    counts["status:unresolved"] += 1
                    continue
                seen.add(
                    (
                        site_key[0],
                        site_key[1],
                        int(from_vcr_id),
                        int(prize_id),
                    )
                )

                active_result = active_module._simulate_capture(
                    context=context,
                    capture=capture,
                    appearances=appearances_by_key,
                )
                factual_opponent_id = row.get("next_opponent_ship_id")
                site_ship_rows = context.get("site_ship_rows")
                site_ship_rows = (
                    site_ship_rows if isinstance(site_ship_rows, Mapping) else {}
                )
                predictions = context.get("predictions")
                predictions = (
                    predictions if isinstance(predictions, Mapping) else {}
                )
                factual_prediction = (
                    predictions.get(factual_opponent_id)
                    if isinstance(factual_opponent_id, int)
                    and not isinstance(factual_opponent_id, bool)
                    else None
                )
                factual_prediction = (
                    factual_prediction
                    if isinstance(factual_prediction, Mapping)
                    else {}
                )
                active_ids = active_result.get("active_ship_ids")
                removed_ids = active_result.get("removed_ship_ids")
                owner_changed_ids = active_result.get("owner_changed_ship_ids")
                anchored_ids = active_result.get("history_anchored_ship_ids")
                active_dependency = {
                    "status": active_result.get("status"),
                    "reason": active_result.get("reason"),
                    "factual_opponent_site_predicted": (
                        factual_opponent_id in site_ship_rows
                        if isinstance(factual_opponent_id, int)
                        and not isinstance(factual_opponent_id, bool)
                        else None
                    ),
                    "factual_opponent_prediction_position": factual_prediction.get(
                        "position"
                    ),
                    "factual_opponent_position_source": factual_prediction.get(
                        "source"
                    ),
                    "factual_opponent_history_anchored": (
                        factual_opponent_id in anchored_ids
                        if isinstance(anchored_ids, list)
                        and isinstance(factual_opponent_id, int)
                        and not isinstance(factual_opponent_id, bool)
                        else None
                    ),
                    "factual_opponent_removed_before_next": (
                        factual_opponent_id in removed_ids
                        if isinstance(removed_ids, list)
                        and isinstance(factual_opponent_id, int)
                        and not isinstance(factual_opponent_id, bool)
                        else None
                    ),
                    "factual_opponent_owner_changed_before_next": (
                        factual_opponent_id in owner_changed_ids
                        if isinstance(owner_changed_ids, list)
                        and isinstance(factual_opponent_id, int)
                        and not isinstance(factual_opponent_id, bool)
                        else None
                    ),
                    "factual_opponent_active": active_result.get(
                        "factual_opponent_active"
                    ),
                    "factual_opponent_candidate_resolved": active_result.get(
                        "factual_opponent_candidate_resolved"
                    ),
                    "factual_opponent_requests_new_owner": active_result.get(
                        "factual_opponent_requests_new_owner"
                    ),
                    "factual_opponent_strict_permission": active_result.get(
                        "factual_opponent_strict_permission"
                    ),
                    "factual_opponent_requester_rank": active_result.get(
                        "factual_opponent_requester_rank"
                    ),
                    "factual_opponent_strict_rank": active_result.get(
                        "factual_opponent_strict_rank"
                    ),
                }
                for name in (
                    "factual_opponent_active",
                    "factual_opponent_candidate_resolved",
                    "factual_opponent_requests_new_owner",
                    "factual_opponent_strict_permission",
                ):
                    value = active_dependency.get(name)
                    if value is True:
                        counts[f"active_dependency:{name}:true"] += 1
                    elif value is False:
                        counts[f"active_dependency:{name}:false"] += 1
                    else:
                        counts[f"active_dependency:{name}:unknown"] += 1
                if active_dependency.get("factual_opponent_requester_rank") is not None:
                    counts["active_dependency:requester_rank_present"] += 1
                else:
                    counts["active_dependency:requester_rank_missing"] += 1
                if active_dependency.get("factual_opponent_strict_rank") is not None:
                    counts["active_dependency:strict_rank_present"] += 1
                else:
                    counts["active_dependency:strict_rank_missing"] += 1
                if active_result.get("status") != "resolved":
                    result = {
                        "status": "unresolved",
                        "reason": "active_membership_dependency_unresolved",
                        "active_status": active_result.get("status"),
                        "active_reason": active_result.get("reason"),
                    }
                    identity_anchored_result = {
                        "status": "unresolved",
                        "reason": "active_membership_dependency_unresolved",
                    }
                else:
                    result = _external_c2ng_original_order_prize_continuation(
                        context=context,
                        capture=capture,
                        active_result=active_result,
                        capture_prize_side=str(row.get("capture_side")),
                    )
                    identity_anchored_result = (
                        _external_c2ng_original_order_prize_continuation(
                            context=context,
                            capture=capture,
                            active_result=_identity_anchor_factual_opponent(
                                active_result=active_result,
                                factual_opponent_id=int(factual_opponent_id),
                            ),
                            capture_prize_side=str(row.get("capture_side")),
                        )
                    )

                status = str(result.get("status", "unknown"))
                counts[f"status:{status}"] += 1
                factual_side = row.get("captured_ship_side_next")
                if factual_side in {"left", "right"}:
                    counts[f"factual_side:{factual_side}"] += 1

                identity_anchored_split: dict[str, Any] | None = None
                if identity_anchored_result.get("status") == "resolved":
                    anchored_pair_exact = identity_anchored_result.get("pair_exact")
                    order_context = row.get("order_context")
                    order_context = (
                        order_context if isinstance(order_context, Mapping) else {}
                    )
                    anchored_side_controls = order_context.get("side_controls")
                    anchored_side_controls = (
                        anchored_side_controls
                        if isinstance(anchored_side_controls, Mapping)
                        else {}
                    )
                    anchored_side = predict_frozen_capture_side(
                        identity_anchored_o_pair_reachable=anchored_pair_exact,
                        capture_side=row.get("capture_side"),
                        neutral_fresh_fc_side=anchored_side_controls.get(
                            "neutral_orders_fresh_fc"
                        ),
                    )
                    if anchored_pair_exact is True:
                        anchored_source = "frozen_identity_anchored_o_reachable_sticky_capture_side"
                    elif anchored_pair_exact is False:
                        anchored_source = "frozen_identity_anchored_o_not_reachable_neutral_fresh_fc"
                    else:
                        anchored_source = "frozen_identity_anchored_pair_unresolved"
                    identity_anchored_split = {
                        "source": anchored_source,
                        "predicted_side": anchored_side,
                        "factual_side": factual_side,
                        "pair_exact": anchored_pair_exact,
                        "exact": (
                            anchored_side == factual_side
                            if anchored_side in {"left", "right"}
                            and factual_side in {"left", "right"}
                            else None
                        ),
                    }
                    if identity_anchored_split["exact"] is True:
                        counts["identity_anchored_split_exact"] += 1
                    elif identity_anchored_split["exact"] is False:
                        counts["identity_anchored_split_mismatch"] += 1
                    else:
                        counts["identity_anchored_split_unresolved"] += 1
                    if anchored_pair_exact is True:
                        counts["identity_anchored_o_pair_reachable"] += 1
                    elif anchored_pair_exact is False:
                        counts["identity_anchored_o_pair_not_reachable"] += 1

                postheldout_candidate_validation: dict[str, Any] | None = None
                postindependent_candidate_validation: dict[str, Any] | None = None
                capture_vcr_id = row.get("capture_vcr_id")
                next_vcr_id = row.get("next_vcr_id")
                adjacent_row = (
                    isinstance(capture_vcr_id, int)
                    and not isinstance(capture_vcr_id, bool)
                    and isinstance(next_vcr_id, int)
                    and not isinstance(next_vcr_id, bool)
                    and int(next_vcr_id) == int(capture_vcr_id) + 1
                )
                if partition in {"independent", "prospective"}:
                    anchored_pair_exact = (
                        identity_anchored_result.get("pair_exact")
                        if identity_anchored_result.get("status") == "resolved"
                        else None
                    )
                    order_context = row.get("order_context")
                    order_context = (
                        order_context if isinstance(order_context, Mapping) else {}
                    )
                    opponent_tminus1 = order_context.get("opponent_tminus1")
                    opponent_tminus1 = (
                        opponent_tminus1
                        if isinstance(opponent_tminus1, Mapping)
                        else {}
                    )
                    opponent_priority = opponent_tminus1.get("priority")
                    opponent_priority_group = (
                        int(opponent_priority[0])
                        if isinstance(opponent_priority, Sequence)
                        and not isinstance(opponent_priority, (str, bytes))
                        and len(opponent_priority) >= 1
                        and isinstance(opponent_priority[0], int)
                        and not isinstance(opponent_priority[0], bool)
                        else None
                    )
                    opponent_mission_raw = opponent_tminus1.get("mission")
                    opponent_mission = (
                        int(opponent_mission_raw)
                        if isinstance(opponent_mission_raw, int)
                        and not isinstance(opponent_mission_raw, bool)
                        else None
                    )
                    side_controls = order_context.get("side_controls")
                    side_controls = (
                        side_controls if isinstance(side_controls, Mapping) else {}
                    )
                    prior_same_pair = row.get("prior_same_pair_occurrences")
                    prior_same_pair = (
                        int(prior_same_pair)
                        if isinstance(prior_same_pair, int)
                        and not isinstance(prior_same_pair, bool)
                        else -1
                    )

                    if partition == "independent":
                        if not adjacent_row:
                            counts["postheldout_candidate_not_comparable"] += 1
                        else:
                            counts["postheldout_candidate_rows"] += 1
                            postheldout_candidate_validation = (
                                evaluate_frozen_postheldout_candidate(
                                    prior_same_pair_occurrences=prior_same_pair,
                                    next_opponent_previous_side=row.get(
                                        "next_opponent_previous_side"
                                    ),
                                    identity_anchored_o_pair_reachable=(
                                        anchored_pair_exact
                                        if isinstance(anchored_pair_exact, bool)
                                        else None
                                    ),
                                    capture_side=row.get("capture_side"),
                                    opponent_priority_group=opponent_priority_group,
                                    neutral_fresh_fc_side=side_controls.get(
                                        "neutral_orders_fresh_fc"
                                    ),
                                    factual_side=factual_side,
                                )
                            )
                            branch_name = str(
                                postheldout_candidate_validation.get(
                                    "branch",
                                    "unknown",
                                )
                            )
                            counts[f"postheldout_branch:{branch_name}"] += 1
                            candidate_exact = postheldout_candidate_validation.get(
                                "exact"
                            )
                            if candidate_exact is True:
                                counts["postheldout_candidate_exact"] += 1
                            elif candidate_exact is False:
                                counts["postheldout_candidate_mismatch"] += 1
                            else:
                                counts["postheldout_candidate_unresolved"] += 1

                    if partition == "prospective":
                        if not adjacent_row:
                            counts["postindependent_candidate_not_comparable"] += 1
                        else:
                            counts["postindependent_candidate_rows"] += 1
                            postindependent_candidate_validation = (
                                evaluate_frozen_postindependent_candidate(
                                    prior_same_pair_occurrences=prior_same_pair,
                                    next_opponent_previous_side=row.get(
                                        "next_opponent_previous_side"
                                    ),
                                    identity_anchored_o_pair_reachable=(
                                        anchored_pair_exact
                                        if isinstance(anchored_pair_exact, bool)
                                        else None
                                    ),
                                    capture_side=row.get("capture_side"),
                                    opponent_priority_group=opponent_priority_group,
                                    opponent_mission=opponent_mission,
                                    neutral_fresh_fc_side=side_controls.get(
                                        "neutral_orders_fresh_fc"
                                    ),
                                    factual_side=factual_side,
                                )
                            )
                            branch_name = str(
                                postindependent_candidate_validation.get(
                                    "branch",
                                    "unknown",
                                )
                            )
                            counts[f"postindependent_branch:{branch_name}"] += 1
                            candidate_exact = (
                                postindependent_candidate_validation.get("exact")
                            )
                            if candidate_exact is True:
                                counts["postindependent_candidate_exact"] += 1
                            elif candidate_exact is False:
                                counts["postindependent_candidate_mismatch"] += 1
                            else:
                                counts["postindependent_candidate_unresolved"] += 1

                split_candidate: dict[str, Any] | None = None
                if status == "resolved":
                    dependency_qualified = all(
                        active_dependency.get(name) is True
                        for name in (
                            "factual_opponent_active",
                            "factual_opponent_candidate_resolved",
                            "factual_opponent_requests_new_owner",
                            "factual_opponent_strict_permission",
                        )
                    )
                    if dependency_qualified:
                        counts["resolved_dependency:qualified"] += 1
                    else:
                        counts["resolved_dependency:blocked"] += 1
                        for name in (
                            "factual_opponent_site_predicted",
                            "factual_opponent_history_anchored",
                            "factual_opponent_removed_before_next",
                            "factual_opponent_owner_changed_before_next",
                        ):
                            value = active_dependency.get(name)
                            if value is True:
                                suffix = "true"
                            elif value is False:
                                suffix = "false"
                            else:
                                suffix = "unknown"
                            counts[f"blocked_dependency:{name}:{suffix}"] += 1

                    pair_exact = result.get("pair_exact")
                    order_context = row.get("order_context")
                    order_context = (
                        order_context if isinstance(order_context, Mapping) else {}
                    )
                    side_controls = order_context.get("side_controls")
                    side_controls = (
                        side_controls if isinstance(side_controls, Mapping) else {}
                    )
                    if pair_exact is True:
                        candidate_side = row.get("capture_side")
                        candidate_source = "o_reachable_sticky_capture_side"
                    elif pair_exact is False:
                        candidate_side = side_controls.get(
                            "neutral_orders_fresh_fc"
                        )
                        candidate_source = "o_not_reachable_neutral_fresh_fc"
                    else:
                        candidate_side = None
                        candidate_source = "pair_reachability_unresolved"

                    split_candidate = {
                        "source": candidate_source,
                        "predicted_side": candidate_side,
                        "factual_side": factual_side,
                        "exact": (
                            candidate_side == factual_side
                            if candidate_side in {"left", "right"}
                            and factual_side in {"left", "right"}
                            else None
                        ),
                    }
                    if split_candidate["exact"] is True:
                        counts["split_candidate_exact"] += 1
                        counts[
                            "split_candidate_exact:"
                            + ("qualified" if dependency_qualified else "blocked")
                        ] += 1
                    elif split_candidate["exact"] is False:
                        counts["split_candidate_mismatch"] += 1
                        counts[
                            "split_candidate_mismatch:"
                            + ("qualified" if dependency_qualified else "blocked")
                        ] += 1
                    else:
                        counts["split_candidate_unresolved"] += 1
                        counts[
                            "split_candidate_unresolved:"
                            + ("qualified" if dependency_qualified else "blocked")
                        ] += 1

                    exact = result.get("exact")
                    if pair_exact is True:
                        counts["o_pair_reachable"] += 1
                        if factual_side in {"left", "right"}:
                            counts[f"o_pair_reachable:{factual_side}"] += 1
                    elif pair_exact is False:
                        counts["o_pair_not_reachable"] += 1
                        if factual_side in {"left", "right"}:
                            counts[f"o_pair_not_reachable:{factual_side}"] += 1
                    if exact is True:
                        counts["external_o_exact"] += 1
                    elif exact is False:
                        counts["external_o_mismatch"] += 1

                if len(examples) < args.example_limit:
                    examples.append(
                        {
                            "game_id": site_key[0],
                            "turn": site_key[1],
                            "x": site_key[2],
                            "y": site_key[3],
                            "capture_vcr_id": row.get("capture_vcr_id"),
                            "next_vcr_id": row.get("next_vcr_id"),
                            "captured_ship_id": row.get("captured_ship_id"),
                            "next_opponent_ship_id": row.get(
                                "next_opponent_ship_id"
                            ),
                            "capture_side": row.get("capture_side"),
                            "factual_prize_side": factual_side,
                            "active_dependency": active_dependency,
                            "identity_anchored_result": identity_anchored_result,
                            "identity_anchored_split": identity_anchored_split,
                            "postheldout_candidate_validation": (
                                postheldout_candidate_validation
                            ),
                            "postindependent_candidate_validation": (
                                postindependent_candidate_validation
                            ),
                            "split_candidate": split_candidate,
                            "result": result,
                        }
                    )

        print(
            "progress: stage=o_layer_site_context "
            f"games={len(scan_ids)} sites={len(targets)} "
            "backend=corpus-db status=start",
            flush=True,
        )
        targeted_summaries: list[dict[str, Any]] = []
        for game_id in sorted(scan_ids):
            print(
                "progress: stage=site_context "
                f"game_id={game_id} mode=corpus-db-targeted status=start",
                flush=True,
            )
            targeted_summary = _visit_targeted_site_contexts(
                connection=connection,
                game_id=game_id,
                targets=targets,
                appearances=appearances,
                observer=observer,
            )
            targeted_summaries.append(
                {"game_id": game_id, **targeted_summary}
            )
            print(
                "progress: stage=site_context "
                f"game_id={game_id} mode=corpus-db-targeted "
                f"snapshots={targeted_summary['targeted_snapshot_count']} "
                f"sites={targeted_summary['visited_sites']} status=done",
                flush=True,
            )
        print(
            "progress: stage=o_layer_site_context "
            f"games={len(scan_ids)} sites={len(targets)} "
            "backend=corpus-db status=done",
            flush=True,
        )

        counts["capture_ship_rows"] = len(observations)
        if partition == "discovery":
            counts["discovery_ship_rows"] = len(observations)
        elif partition == "heldout":
            counts["heldout_ship_rows"] = len(observations)
        elif partition == "independent":
            counts["independent_ship_rows"] = len(observations)
        elif partition == "prospective":
            counts["prospective_ship_rows"] = len(observations)
        counts["observations_seen"] = len(seen)
        counts["adjacent_rows"] = sum(
            1
            for row in observations
            if isinstance(row.get("capture_vcr_id"), int)
            and isinstance(row.get("next_vcr_id"), int)
            and not isinstance(row.get("capture_vcr_id"), bool)
            and not isinstance(row.get("next_vcr_id"), bool)
            and int(row["next_vcr_id"]) == int(row["capture_vcr_id"]) + 1
        )

        return {
            "schema": SCHEMA,
            "evidence_status": {
                "discovery": "DISCOVERY_ONLY_FROZEN_SIDE_CANDIDATE",
                "heldout": "HELDOUT_VALIDATION_FROZEN_SIDE_CANDIDATE",
                "independent": "INDEPENDENT_VALIDATION_POSTHELDOUT_CANDIDATE",
                "prospective": "PROSPECTIVE_VALIDATION_POSTINDEPENDENT_CANDIDATE",
            }[partition],
            "partition": partition,
            "source_capture_side_report": str(args.capture_side_report),
            "database_path": str(database_path),
            "scanned_game_ids": sorted(full_scan_ids),
            "probe_game_ids": sorted(scan_ids),
            "summary": {
                "counts": dict(sorted(counts.items())),
                "appearance_summary": dict(sorted(appearance_summary.items())),
                "targeted_site_context": targeted_summaries,
            },
            "observations": examples,
            "evidence_boundary": (
                (
                    "Independent short-public validation of the already frozen "
                    "post-heldout capture-side candidate. The source capture report "
                    "contains all indexed games from the independent short32 "
                    "manifest. Only globally adjacent capture->next VCR rows enter "
                    "the candidate gate. Pair reachability is identity-anchored on "
                    "the factual N+1 opponent identity/eligibility but never its "
                    "side. Repeated-pair reversal is evaluated before O-layer "
                    "reachability, matching the frozen candidate branch order. "
                    "Unknown opponent priority on a reachable first-occurrence row "
                    "fails closed. No candidate parameter is fitted from this "
                    "population."
                )
                if partition == "independent"
                else (
                    "Prospective validation of the frozen post-independent "
                    "Kill-sensitive capture-side candidate against a fresh "
                    "32-game population selected before outcomes were opened. "
                    "Only globally adjacent rows are candidate-comparable. "
                    "The immutable public100 generation is read explicitly; "
                    "CURRENT is not consulted. No candidate parameter is fitted "
                    "from this population."
                    if partition == "prospective"
                    else (
                    f"{partition.capitalize()} bounded O-layer comparator. The "
                    "frozen-order cursor is transcribed from the separately audited "
                    "external c2ng/THost path and is not NuHost authority. Only "
                    "globally adjacent capture->next VCR rows are comparable; "
                    "nonadjacent rows fail closed. Capture VCR N anchors the "
                    "existing cursor, independently reconstructed movement/site "
                    "state comes from only required T-1/T members of the active "
                    "exact-parity Corpus DB, strict post-capture attackers determine "
                    "reachability, and factual N+1 supplies only the final "
                    "opponent/side comparator. The split side candidate retains its "
                    "original discovery/heldout evidence boundary."
                )
                )
            ),
        }
    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Test a bounded external original-order cursor against the sealed "
            "selected public capture partition."
        )
    )
    parser.add_argument(
        "--capture-side-report",
        "--discovery",
        dest="capture_side_report",
        type=Path,
        default=DEFAULT_DISCOVERY,
    )
    parser.add_argument(
        "--partition",
        choices=("discovery", "heldout", "independent", "prospective"),
        default="discovery",
    )
    parser.add_argument(
        "--corpus-db-root",
        type=Path,
        default=None,
        help="Shared corpus DB root; defaults to PLANETS_CORPUS_DB_ROOT.",
    )
    parser.add_argument(
        "--corpus-db-generation",
        default=None,
        help=(
            "Explicit generation path relative to the corpus DB root. "
            "When set, CURRENT is not consulted."
        ),
    )
    parser.add_argument("--example-limit", type=int, default=80)
    parser.add_argument("--game-id", type=int)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        counts = report["summary"]["counts"]
        print(
            "===== PUBLIC CAPTURE O-LAYER "
            f"{str(report.get('partition', 'discovery')).upper()} ====="
        )
        print(f"capture_ship_rows:    {counts.get('capture_ship_rows', 0)}")
        print(f"adjacent_rows:        {counts.get('adjacent_rows', 0)}")
        print(f"resolved:             {counts.get('status:resolved', 0)}")
        print(f"not_comparable:       {counts.get('status:not_comparable', 0)}")
        print(f"unresolved:           {counts.get('status:unresolved', 0)}")
        print(f"O pair reachable:     {counts.get('o_pair_reachable', 0)}")
        print(
            "  factual LEFT/RIGHT: "
            f"{counts.get('o_pair_reachable:left', 0)} / "
            f"{counts.get('o_pair_reachable:right', 0)}"
        )
        print(f"O pair not reachable: {counts.get('o_pair_not_reachable', 0)}")
        print(
            "  factual LEFT/RIGHT: "
            f"{counts.get('o_pair_not_reachable:left', 0)} / "
            f"{counts.get('o_pair_not_reachable:right', 0)}"
        )
        print(f"external O exact:     {counts.get('external_o_exact', 0)}")
        print(f"external O mismatch:  {counts.get('external_o_mismatch', 0)}")
        print(f"split candidate exact:{counts.get('split_candidate_exact', 0):>4}")
        print(f"split candidate mismatch:{counts.get('split_candidate_mismatch', 0):>2}")
        print(
            "factual opponent active T/F/U: "
            f"{counts.get('active_dependency:factual_opponent_active:true', 0)} / "
            f"{counts.get('active_dependency:factual_opponent_active:false', 0)} / "
            f"{counts.get('active_dependency:factual_opponent_active:unknown', 0)}"
        )
        print(
            "strict permission T/F/U: "
            f"{counts.get('active_dependency:factual_opponent_strict_permission:true', 0)} / "
            f"{counts.get('active_dependency:factual_opponent_strict_permission:false', 0)} / "
            f"{counts.get('active_dependency:factual_opponent_strict_permission:unknown', 0)}"
        )
        print(
            "resolved dependency qualified/blocked: "
            f"{counts.get('resolved_dependency:qualified', 0)} / "
            f"{counts.get('resolved_dependency:blocked', 0)}"
        )
        print(
            "split exact qualified/blocked: "
            f"{counts.get('split_candidate_exact:qualified', 0)} / "
            f"{counts.get('split_candidate_exact:blocked', 0)}"
        )
        print(
            "split mismatch qualified/blocked: "
            f"{counts.get('split_candidate_mismatch:qualified', 0)} / "
            f"{counts.get('split_candidate_mismatch:blocked', 0)}"
        )
        print(
            "identity-anchored O reachable/not: "
            f"{counts.get('identity_anchored_o_pair_reachable', 0)} / "
            f"{counts.get('identity_anchored_o_pair_not_reachable', 0)}"
        )
        print(
            "identity-anchored split exact/mismatch/unresolved: "
            f"{counts.get('identity_anchored_split_exact', 0)} / "
            f"{counts.get('identity_anchored_split_mismatch', 0)} / "
            f"{counts.get('identity_anchored_split_unresolved', 0)}"
        )
        if report.get("partition") == "independent":
            print(
                "postheldout candidate exact/mismatch/unresolved: "
                f"{counts.get('postheldout_candidate_exact', 0)} / "
                f"{counts.get('postheldout_candidate_mismatch', 0)} / "
                f"{counts.get('postheldout_candidate_unresolved', 0)}"
            )
            for branch_name in (
                "reachable_sticky",
                "nonreachable_neutral_fresh_fc",
                "second_occurrence_reversal",
                "reachable_numeric_opponent_override",
            ):
                print(
                    f"postheldout branch {branch_name}: "
                    f"{counts.get('postheldout_branch:' + branch_name, 0)}"
                )
        for label, key in (
            ("blocked site predicted T/F/U", "factual_opponent_site_predicted"),
            ("blocked history anchored T/F/U", "factual_opponent_history_anchored"),
            ("blocked removed before next T/F/U", "factual_opponent_removed_before_next"),
            ("blocked owner changed T/F/U", "factual_opponent_owner_changed_before_next"),
        ):
            print(
                f"{label}: "
                f"{counts.get(f'blocked_dependency:{key}:true', 0)} / "
                f"{counts.get(f'blocked_dependency:{key}:false', 0)} / "
                f"{counts.get(f'blocked_dependency:{key}:unknown', 0)}"
            )
        print(f"output:               {args.output}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
