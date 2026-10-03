from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for _path in (REPO_ROOT / "src", DIAGNOSTICS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


import combat_host_initial_standard_target_audit as baseline_module
import combat_host_post_capture_active_membership_audit as active_module
import combat_host_post_capture_special_movement_audit as special_movement_module
import combat_ship_chain_audit as chain_module
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
    _inbound_transfer_targets,
    _normal_position_prediction,
)
from combat_host_post_capture_pair_recomposition_audit import (
    _external_c2ng_original_order_prize_continuation,
)
from combat_host_post_mutation_next_pair_audit import _appearance_key
from combat_public_capture_o_layer_probe import (
    SCHEMA,
    _capture_projection,
    _load_discovery,
    _nuionstorms_from_payloads,
    _pseudo_seen_from_appearances,
    _targets_by_site,
    _topology_from_payloads,
)
from planets_lab.corpus.archive import TurnMember
from planets_lab.corpus.corpus_db import CorpusDbError, resolve_current_generation
from planets_lab.corpus.corpus_db_compact import (
    CORPUS_DB_COMPACT_SCHEMA,
    _load_specs,
    reconstruct_compact_member,
)
from planets_lab.corpus.movement_differential import (
    _entity_map,
    _intish,
    _planet_tuples_by_turn,
    _settings_warp_well_state_by_turn,
)
from planets_lab.corpus.movement_mine_context import MineEvidenceContext
from planets_lab.corpus.movement_residual_context import _storm_consensus_by_turn
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.normalizer import ArchiveTurnSnapshot, mechanics_projection
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.data.nu_static import import_static_all
from planets_lab.rules.combat import ReplayUnsupported, replay_nuhost_from_nu_catalog


DEFAULT_DISCOVERY = Path("artifacts/public-capture-side/discovery-capture-side.json")
DEFAULT_OUTPUT = Path("artifacts/public-capture-side/discovery-o-layer-probe-db.json")
CORPUS_DB_ROOT_ENV = "PLANETS_CORPUS_DB_ROOT"


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


def _corpus_db_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    raw = os.environ.get(CORPUS_DB_ROOT_ENV)
    if not raw:
        raise ValueError(
            f"{CORPUS_DB_ROOT_ENV} is required for the Corpus DB O-layer probe"
        )
    return Path(raw)


def _open_current_compact(
    root: Path,
) -> tuple[duckdb.DuckDBPyConnection, Path, Mapping[str, Any]]:
    database_path = resolve_current_generation(root)
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        row = connection.execute(
            "SELECT schema_version FROM corpus_metadata"
        ).fetchone()
        schema = None if row is None else str(row[0])
        if schema != CORPUS_DB_COMPACT_SCHEMA:
            raise CorpusDbError(
                f"expected {CORPUS_DB_COMPACT_SCHEMA}, got {schema!r}"
            )
        specs = _load_specs(connection)
    except Exception:
        connection.close()
        raise
    return connection, database_path, specs


def _member_rows(
    connection: duckdb.DuckDBPyConnection,
    *,
    game_id: int,
    archive_turns: set[int] | None = None,
) -> list[tuple[Any, ...]]:
    sql = """
        SELECT member_id,
               source_member_name,
               perspective_player_id,
               archive_turn,
               embedded_turn,
               decoded_payload_sha256,
               member_ordinal
        FROM source_members
        WHERE game_id = ?
    """
    params: list[Any] = [game_id]
    if archive_turns is not None:
        turns = sorted(int(value) for value in archive_turns)
        if not turns:
            return []
        sql += " AND archive_turn IN (" + ",".join("?" for _ in turns) + ")"
        params.extend(turns)
    sql += " ORDER BY member_ordinal"
    return connection.execute(sql, params).fetchall()


def _member_record(
    connection: duckdb.DuckDBPyConnection,
    specs: Mapping[str, Any],
    row: Sequence[Any],
) -> dict[str, Any]:
    (
        member_id,
        source_member_name,
        perspective_player_id,
        archive_turn,
        embedded_turn,
        decoded_payload_sha256,
        member_ordinal,
    ) = row
    member = TurnMember(
        player=int(perspective_player_id),
        turn=int(archive_turn),
        name=str(source_member_name),
    )
    payload = reconstruct_compact_member(
        connection,
        int(member_id),
        specs=specs,
    )
    return {
        "member_id": int(member_id),
        "member": member,
        "embedded_turn": int(embedded_turn),
        "snapshot_hash": str(decoded_payload_sha256),
        "member_ordinal": int(member_ordinal),
        "payload": payload,
    }


def _first_last_member_records(
    connection: duckdb.DuckDBPyConnection,
    specs: Mapping[str, Any],
    *,
    game_id: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = _member_rows(connection, game_id=game_id)
    if not rows:
        raise ValueError(f"game {game_id}: no source members in Corpus DB")
    first = _member_record(connection, specs, rows[0])
    last = first if len(rows) == 1 else _member_record(connection, specs, rows[-1])
    return first, last


def _targeted_vcr_appearances(
    *,
    game_id: int,
    records: Sequence[Mapping[str, Any]],
    battle_turns: set[int],
) -> tuple[list[dict[str, Any]], Mapping[str, Any]]:
    cases: dict[tuple[int, int, int], dict[str, Any]] = {}
    conflicts: set[tuple[int, int, int]] = set()
    raw_observations = 0

    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, Mapping):
            continue
        game = payload.get("game")
        game_turn = _intish(game.get("turn")) if isinstance(game, Mapping) else None
        beams = chain_module._objects(payload, "beams")
        torpedoes = chain_module._objects(payload, "torpedos")
        settings = payload.get("settings")
        settings = dict(settings) if isinstance(settings, Mapping) else {}

        for raw_vcr in chain_module._objects(payload, "vcrs"):
            vcr_id = chain_module._int(raw_vcr, "id")
            battle_turn = chain_module._int(raw_vcr, "turn") or game_turn
            if (
                vcr_id is None
                or battle_turn is None
                or int(battle_turn) not in battle_turns
            ):
                continue
            raw_observations += 1
            key = (game_id, int(battle_turn), int(vcr_id))
            payload_hash = chain_module._canonical_hash(raw_vcr)
            existing = cases.get(key)
            if existing is None:
                cases[key] = {
                    "payload": dict(raw_vcr),
                    "payload_hash": payload_hash,
                    "beams": beams,
                    "torpedoes": torpedoes,
                    "settings": settings,
                    "observations": 1,
                }
            else:
                existing["observations"] = int(existing["observations"]) + 1
                if existing["payload_hash"] != payload_hash:
                    conflicts.add(key)

    if conflicts:
        sample = sorted(conflicts)[:8]
        raise ValueError(
            "Corpus DB targeted VCR payload conflicts: "
            + ", ".join(f"{g}/T{t}/V{v}" for g, t, v in sample)
        )

    appearances: list[dict[str, Any]] = []
    replay_unsupported = 0
    for (case_game_id, turn, vcr_id), case in sorted(cases.items()):
        try:
            replay = replay_nuhost_from_nu_catalog(
                case["payload"],
                beams=case["beams"],
                torpedoes=case["torpedoes"],
                settings=case["settings"],
            )
        except ReplayUnsupported as exc:
            replay_unsupported += 1
            raise ValueError(
                f"{case_game_id}/T{turn}/V{vcr_id}: replay unsupported: {exc}"
            ) from exc

        position = chain_module._position(case["payload"])
        for side_name in ("left", "right"):
            raw_side = case["payload"].get(side_name)
            replay_side = replay.get(side_name)
            if not isinstance(raw_side, Mapping) or not isinstance(replay_side, Mapping):
                continue
            appearance = chain_module._appearance(
                game_id=case_game_id,
                turn=turn,
                vcr_id=vcr_id,
                position=position,
                side_name=side_name,
                raw_side=raw_side,
                replay_side=replay_side,
            )
            if appearance is not None:
                appearances.append(appearance)

    return appearances, {
        "raw_vcr_observations": raw_observations,
        "unique_vcrs": len(cases),
        "payload_conflicts": len(conflicts),
        "replay_unsupported": replay_unsupported,
        "ship_appearances": len(appearances),
    }


def _targeted_corpus_db_context(
    *,
    connection: duckdb.DuckDBPyConnection,
    db_specs: Mapping[str, Any],
    game_id: int,
    battle_turns: set[int],
) -> dict[str, Any]:
    before_turns = {turn - 1 for turn in battle_turns}
    wanted_turns = before_turns | battle_turns

    first_record, last_record = _first_last_member_records(
        connection,
        db_specs,
        game_id=game_id,
    )
    first_payload = first_record["payload"]
    last_payload = last_record["payload"]
    if not isinstance(first_payload, Mapping) or not isinstance(last_payload, Mapping):
        raise ValueError(f"game {game_id}: first/last payload reconstruction failed")

    specs = NuStaticSpecs.from_catalog(import_static_all(first_payload))
    topology = effective_sphere_topology(
        game_id=game_id,
        topology=_topology_from_payloads(
            first_member=first_record["member"],
            first_payload=first_payload,
            last_member=last_record["member"],
            last_payload=last_payload,
        ),
    )
    nuionstorms = _nuionstorms_from_payloads(first_payload, last_payload)

    rows = _member_rows(
        connection,
        game_id=game_id,
        archive_turns=wanted_turns,
    )
    if not rows:
        raise ValueError(
            f"game {game_id}: no T-1/T source members for turns {sorted(wanted_turns)}"
        )

    records = [
        _member_record(connection, db_specs, row)
        for row in rows
    ]

    snapshots: list[ArchiveTurnSnapshot] = []
    relations: dict[
        int,
        dict[tuple[int, int], set[tuple[int | None, int | None, int | None]]],
    ] = defaultdict(lambda: defaultdict(set))

    for record in records:
        member = record["member"]
        payload = record["payload"]
        if not isinstance(member, TurnMember) or not isinstance(payload, Mapping):
            raise ValueError(f"game {game_id}: malformed reconstructed member record")
        projection = mechanics_projection(payload, member=member.name)
        projection_game = projection.get("game")
        projection_player = projection.get("player")
        observed_game_id = (
            projection_game.get("id")
            if isinstance(projection_game, Mapping)
            else None
        )
        observed_player_id = (
            projection_player.get("id")
            if isinstance(projection_player, Mapping)
            else None
        )
        observed_turn = (
            projection_game.get("turn")
            if isinstance(projection_game, Mapping)
            else None
        )
        if (
            observed_game_id != game_id
            or isinstance(observed_player_id, bool)
            or not isinstance(observed_player_id, int)
            or isinstance(observed_turn, bool)
            or not isinstance(observed_turn, int)
        ):
            raise ValueError(
                f"{member.name}: Corpus DB targeted snapshot identity mismatch"
            )
        snapshots.append(
            ArchiveTurnSnapshot(
                member=member,
                game_id=game_id,
                player_id=int(observed_player_id),
                embedded_turn=int(observed_turn),
                snapshot_hash=str(record["snapshot_hash"]),
                mechanics_payload=projection,
            )
        )

        if member.turn in before_turns:
            raw_relations = payload.get("relations")
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

    appearances, appearance_summary = _targeted_vcr_appearances(
        game_id=game_id,
        records=records,
        battle_turns=battle_turns,
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
        "appearances": appearances,
        "appearance_summary": dict(appearance_summary),
        "source_member_count": len(records),
    }


def _evaluate_site_observations(
    *,
    context: Mapping[str, Any],
    targets: Mapping[tuple[int, int, int, int], Sequence[Mapping[str, Any]]],
    appearances_by_key: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
    counts: Counter[str],
    examples: list[dict[str, Any]],
    seen: set[tuple[int, int, int, int]],
    example_limit: int,
) -> None:
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

        if len(examples) < example_limit:
            examples.append(
                {
                    "game_id": site_key[0],
                    "turn": site_key[1],
                    "x": site_key[2],
                    "y": site_key[3],
                    "capture_vcr_id": row.get("capture_vcr_id"),
                    "next_vcr_id": row.get("next_vcr_id"),
                    "captured_ship_id": row.get("captured_ship_id"),
                    "next_opponent_ship_id": row.get("next_opponent_ship_id"),
                    "capture_side": row.get("capture_side"),
                    "factual_prize_side": factual_side,
                    "result": result,
                }
            )


def _visit_targeted_db_site_contexts(
    *,
    connection: duckdb.DuckDBPyConnection,
    db_specs: Mapping[str, Any],
    game_id: int,
    targets: Mapping[tuple[int, int, int, int], Sequence[Mapping[str, Any]]],
    counts: Counter[str],
    examples: list[dict[str, Any]],
    seen: set[tuple[int, int, int, int]],
    example_limit: int,
) -> dict[str, Any]:
    battle_turns = {
        int(turn)
        for target_game, turn, _x, _y in targets
        if int(target_game) == game_id
    }
    targeted = _targeted_corpus_db_context(
        connection=connection,
        db_specs=db_specs,
        game_id=game_id,
        battle_turns=battle_turns,
    )
    snapshots = targeted["snapshots"]
    specs = targeted["specs"]
    topology = targeted["topology"]
    relations = targeted["relations"]
    nuionstorms = targeted["nuionstorms"]
    appearances = targeted["appearances"]
    appearances_by_key = _appearance_mapping(appearances)

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

        _evaluate_site_observations(
            context={
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
            },
            targets=targets,
            appearances_by_key=appearances_by_key,
            counts=counts,
            examples=examples,
            seen=seen,
            example_limit=example_limit,
        )
        visited_sites += 1

    return {
        "backend": "corpus-db",
        "targeted_snapshot_count": len(snapshots),
        "targeted_archive_turns": sorted(
            {snapshot.archive_turn for snapshot in snapshots}
        ),
        "source_member_count": int(targeted["source_member_count"]),
        "pseudo_vcr_count": len(pseudo_seen),
        "visited_sites": visited_sites,
        "appearance_summary": dict(targeted["appearance_summary"]),
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
        scan_ids = {
            int(row["game_id"])
            for row in observations
            if isinstance(row.get("game_id"), int)
            and not isinstance(row.get("game_id"), bool)
        }

    targets = _targets_by_site(observations)
    counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    seen: set[tuple[int, int, int, int]] = set()

    root = _corpus_db_root(args.corpus_db_root)
    connection, database_path, db_specs = _open_current_compact(root)
    try:
        available_games = {
            int(row[0])
            for row in connection.execute(
                "SELECT DISTINCT game_id FROM source_members"
            ).fetchall()
        }
        missing_games = sorted(scan_ids - available_games)
        if missing_games:
            raise ValueError(
                "discovery games missing from current Corpus DB: "
                + ", ".join(map(str, missing_games))
            )

        print(
            "progress: stage=o_layer_site_context "
            f"backend=corpus-db games={len(scan_ids)} sites={len(targets)} status=start",
            flush=True,
        )
        targeted_summaries: list[dict[str, Any]] = []
        for game_id in sorted(scan_ids):
            print(
                "progress: stage=site_context "
                f"backend=corpus-db game_id={game_id} status=start",
                flush=True,
            )
            summary = _visit_targeted_db_site_contexts(
                connection=connection,
                db_specs=db_specs,
                game_id=game_id,
                targets=targets,
                counts=counts,
                examples=examples,
                seen=seen,
                example_limit=args.example_limit,
            )
            targeted_summaries.append({"game_id": game_id, **summary})
            print(
                "progress: stage=site_context "
                f"backend=corpus-db game_id={game_id} "
                f"snapshots={summary['targeted_snapshot_count']} "
                f"vcrs={summary['appearance_summary'].get('unique_vcrs', 0)} "
                f"sites={summary['visited_sites']} status=done",
                flush=True,
            )
        print(
            "progress: stage=o_layer_site_context "
            f"backend=corpus-db games={len(scan_ids)} sites={len(targets)} status=done",
            flush=True,
        )
    finally:
        connection.close()

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
        "backend": "corpus-db",
        "database_schema": CORPUS_DB_COMPACT_SCHEMA,
        "database_path": str(database_path),
        "evidence_status": "DISCOVERY_ONLY_EXTERNAL_REFERENCE_NOT_PROMOTED",
        "source_discovery": str(args.discovery),
        "scanned_game_ids": sorted(full_scan_ids),
        "probe_game_ids": sorted(scan_ids),
        "summary": {
            "counts": dict(sorted(counts.items())),
            "targeted_site_context": targeted_summaries,
        },
        "observations": examples,
        "evidence_boundary": (
            "Discovery-only bounded O-layer comparator using the active compact "
            "Corpus DB as the normal research backend. The DB generation is opened "
            "read-only and was independently validated for full ZIP semantic parity. "
            "Only T-1/T source members required by the discovery observations are "
            "reconstructed; immutable ZIP archives are not read by this diagnostic. "
            "The frozen c2ng/THost cursor remains external reference only. Only "
            "globally adjacent capture->next VCR rows are comparable; nonadjacent "
            "rows fail closed. The discovery artifact controls the mechanics "
            "population, so the sealed held-out partition is not inspected."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Test the bounded external O-layer cursor against the public discovery "
            "capture population using the active compact Corpus DB."
        )
    )
    parser.add_argument("--discovery", type=Path, default=DEFAULT_DISCOVERY)
    parser.add_argument("--corpus-db-root", type=Path)
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
        print("===== PUBLIC CAPTURE O-LAYER DISCOVERY: CORPUS DB =====")
        print(f"database:             {report['database_path']}")
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
    except (OSError, ValueError, CorpusDbError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
