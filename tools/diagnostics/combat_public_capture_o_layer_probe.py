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
from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.corpus_db_compact import reconstruct_compact_member
from planets_lab.corpus.corpus_db_runtime import (
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


def _load_discovery(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("discovery artifact must be a JSON object")
    if payload.get("partition") != "discovery":
        raise ValueError("O-layer probe requires partition=discovery")
    observations = payload.get("observations")
    if (
        not isinstance(observations, Sequence)
        or isinstance(observations, (str, bytes))
        or not all(isinstance(row, Mapping) for row in observations)
    ):
        raise ValueError("discovery observations are missing or malformed")
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
) -> dict[str, Any]:
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


def run(args: argparse.Namespace) -> dict[str, Any]:
    discovery = _load_discovery(args.discovery)
    observations = [
        dict(row)
        for row in discovery["observations"]
        if isinstance(row, Mapping)
    ]
    scan_ids_raw = discovery.get("scanned_game_ids")
    if (
        not isinstance(scan_ids_raw, Sequence)
        or isinstance(scan_ids_raw, (str, bytes))
    ):
        raise ValueError("discovery scanned_game_ids missing")
    full_scan_ids = {
        int(value)
        for value in scan_ids_raw
        if isinstance(value, int) and not isinstance(value, bool)
    }
    if not full_scan_ids:
        raise ValueError("discovery game population is empty")

    requested_game_id = getattr(args, "game_id", None)
    if requested_game_id is not None:
        if requested_game_id not in full_scan_ids:
            raise ValueError(
                f"game {requested_game_id} is not in the discovery partition"
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
                if active_result.get("status") != "resolved":
                    result = {
                        "status": "unresolved",
                        "reason": "active_membership_dependency_unresolved",
                        "active_status": active_result.get("status"),
                        "active_reason": active_result.get("reason"),
                    }
                else:
                    result = _external_c2ng_original_order_prize_continuation(
                        context=context,
                        capture=capture,
                        active_result=active_result,
                        capture_prize_side=str(row.get("capture_side")),
                    )

                status = str(result.get("status", "unknown"))
                counts[f"status:{status}"] += 1
                factual_side = row.get("captured_ship_side_next")
                if factual_side in {"left", "right"}:
                    counts[f"factual_side:{factual_side}"] += 1

                if status == "resolved":
                    pair_exact = result.get("pair_exact")
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

        counts["discovery_ship_rows"] = len(observations)
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
            "evidence_status": "DISCOVERY_ONLY_EXTERNAL_REFERENCE_NOT_PROMOTED",
            "source_discovery": str(args.discovery),
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
                "Discovery-only bounded O-layer comparator. The frozen-order "
                "cursor is transcribed from the separately audited external "
                "c2ng/THost path and is not NuHost authority. Only globally "
                "adjacent capture->next VCR rows are comparable; nonadjacent "
                "rows fail closed. Capture VCR N anchors the existing cursor, "
                "independently reconstructed movement/site state comes from "
                "only required T-1/T members of the active exact-parity Corpus "
                "DB, strict post-capture attackers determine reachability, and "
                "factual N+1 supplies only the final opponent/side comparator. "
                "Held-out games are not included."
            ),
        }
    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Test a bounded external original-order cursor against the sealed "
            "public discovery capture population."
        )
    )
    parser.add_argument("--discovery", type=Path, default=DEFAULT_DISCOVERY)
    parser.add_argument(
        "--corpus-db-root",
        type=Path,
        default=None,
        help="Shared corpus DB root; defaults to PLANETS_CORPUS_DB_ROOT.",
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
        print("===== PUBLIC CAPTURE O-LAYER DISCOVERY =====")
        print(f"discovery_ship_rows:  {counts.get('discovery_ship_rows', 0)}")
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
        print(f"output:               {args.output}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
