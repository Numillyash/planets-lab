from __future__ import annotations

from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping

import duckdb

from planets_lab.corpus.movement_chunnel_context import (
    _numeric_friendly_code,
    discover_observed_chunnel_events,
    extract_stable_chunnel_abilities,
)
from planets_lab.corpus.movement_differential import _entity_map, _intish, _resolved_value
from planets_lab.corpus.movement_horwasp_trajectory import _vector
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.readiness import MOVEMENT_GEOMETRY, READY, evaluate_readiness
from planets_lab.corpus.reconstruction import group_perspective_records


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")


def _xy(entity: Any) -> tuple[int, int] | None:
    if entity is None:
        return None
    x = _intish(_resolved_value(entity, "x"))
    y = _intish(_resolved_value(entity, "y"))
    if x is None or y is None:
        return None
    return x, y


def _resolved_int(entity: Any, field: str) -> int | None:
    if entity is None:
        return None
    return _intish(_resolved_value(entity, field))


def _owner_id(
    *,
    ship_groups: Mapping[tuple[int, int], tuple[Any, ...]],
    entities: Mapping[tuple[str, int, int], Any],
    turn: int,
    ship_id: int,
) -> tuple[int | None, Any | None]:
    owner_id, owner = _owner_record(ship_groups.get((turn, ship_id), ()))
    if owner_id is not None and owner_id > 0:
        return owner_id, owner
    entity = entities.get(("ship", turn, ship_id))
    fallback = _resolved_int(entity, "ownerid")
    return fallback, None


def _fuel(owner: Any | None, entity: Any) -> int | None:
    if owner is not None:
        value = _intish(owner.raw.get("neutronium"))
        if value is not None:
            return value
    return _resolved_int(entity, "neutronium")


def main() -> int:
    con = duckdb.connect(str(DEFAULT_DATABASE), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT
                game_id,
                before_archive_turn,
                after_archive_turn,
                ship_id,
                hull_id,
                x_before,
                y_before,
                x_after,
                y_after
            FROM movement_post_horwasp_strong_residual
            WHERE hull_id NOT BETWEEN 201 AND 213
              AND baseline_category = 'warp_zero_external_move'
              AND warp = 0
              AND x_before = target_x
              AND y_before = target_y
            ORDER BY game_id, before_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()

    print("===== WARP-ZERO MISSED-CHUNNEL GAP AUDIT =====")
    print("candidate_rows=", len(rows))

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    counts = Counter()
    structural_hulls = Counter()
    structural_games = Counter()
    fc_hulls = Counter()
    fc_games = Counter()
    group_rows: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        archive_data = archive_path.read_bytes()
        prepared, prepared_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        abilities = extract_stable_chunnel_abilities(archive_data)
        raw_topology = extract_map_topology(archive_data)
        topology = effective_sphere_topology(game_id=game_id, topology=raw_topology)
        entities = _entity_map(prepared.snapshots)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        readiness = evaluate_readiness(prepared.snapshots, MOVEMENT_GEOMETRY)
        ready_by_key = {
            (item.before_archive_turn, item.after_archive_turn, item.entity_id): item
            for item in readiness.results
            if item.status == READY
        }
        discovered_events, event_counts = discover_observed_chunnel_events(
            prepared.snapshots,
            abilities,
        )
        discovered_keys = {
            (
                event.before_archive_turn,
                event.initiator_ship_id,
                event.target_ship_id,
                event.destination,
            )
            for event in discovered_events
        }

        print(
            f"prepared game={game_id} cache_hit={prepared_hit} rows={len(by_game[game_id])} "
            f"initiator_hulls={sorted(abilities.initiator_hull_ids)} "
            f"target_hulls={sorted(abilities.target_hull_ids)} "
            f"existing_events={len(discovered_events)} "
            f"raw_map=({raw_topology.mapwidth},{raw_topology.mapheight}) "
            f"effective_map=({topology.mapwidth},{topology.mapheight})"
        )
        if event_counts:
            print("  existing_event_counts=", dict(sorted(event_counts.items())))

        ship_ids_by_before_position: dict[tuple[int, tuple[int, int]], list[int]] = defaultdict(list)
        ship_ids_by_after_position: dict[tuple[int, tuple[int, int]], list[int]] = defaultdict(list)
        for kind, turn, ship_id in entities:
            if kind != "ship":
                continue
            before_xy = _xy(entities.get(("ship", turn, ship_id)))
            if before_xy is not None:
                ship_ids_by_before_position[(turn, before_xy)].append(ship_id)

        for transition in readiness.results:
            if transition.status != READY:
                continue
            after_xy = _xy(entities.get(("ship", transition.after_archive_turn, transition.entity_id)))
            if after_xy is not None:
                ship_ids_by_after_position[(transition.after_archive_turn, after_xy)].append(
                    transition.entity_id
                )

        for row in by_game[game_id]:
            (
                _gid,
                before_turn,
                after_turn,
                ship_id,
                hull_id,
                x_before,
                y_before,
                x_after,
                y_after,
            ) = row
            before_turn = int(before_turn)
            after_turn = int(after_turn)
            ship_id = int(ship_id)
            hull_id = int(hull_id)
            origin = (int(x_before), int(y_before))
            destination = (int(x_after), int(y_after))
            counts["rows"] += 1

            before_here = sorted(ship_ids_by_before_position.get((before_turn, origin), ()))
            after_there = sorted(ship_ids_by_after_position.get((after_turn, destination), ()))

            initiator_candidates: list[dict[str, Any]] = []
            for initiator_id in before_here:
                before_entity = entities.get(("ship", before_turn, initiator_id))
                after_entity = entities.get(("ship", after_turn, initiator_id))
                initiator_hull = _resolved_int(before_entity, "hullid")
                if initiator_hull not in abilities.initiator_hull_ids:
                    continue
                if _xy(after_entity) != destination:
                    continue

                initiator_owner_id, initiator_owner = _owner_id(
                    ship_groups=ship_groups,
                    entities=entities,
                    turn=before_turn,
                    ship_id=initiator_id,
                )
                initiator_fuel = _fuel(initiator_owner, before_entity)
                numeric_fc = _numeric_friendly_code(initiator_owner) if initiator_owner is not None else None
                initiator_candidates.append(
                    {
                        "ship_id": initiator_id,
                        "hull_id": initiator_hull,
                        "owner_id": initiator_owner_id,
                        "fuel": initiator_fuel,
                        "numeric_fc": numeric_fc,
                    }
                )

            target_candidates: list[dict[str, Any]] = []
            # A Chunnel Target must already be at the destination before the chunnel,
            # remain there afterwards, have target ability, Warp 0 and some fuel.
            for target_id in sorted(ship_ids_by_before_position.get((before_turn, destination), ())):
                before_entity = entities.get(("ship", before_turn, target_id))
                after_entity = entities.get(("ship", after_turn, target_id))
                target_hull = _resolved_int(before_entity, "hullid")
                if target_hull not in abilities.target_hull_ids:
                    continue
                if _xy(after_entity) != destination:
                    continue
                target_warp = _resolved_int(before_entity, "warp")
                target_owner_id, target_owner = _owner_id(
                    ship_groups=ship_groups,
                    entities=entities,
                    turn=before_turn,
                    ship_id=target_id,
                )
                target_fuel = _fuel(target_owner, before_entity)
                target_candidates.append(
                    {
                        "ship_id": target_id,
                        "hull_id": target_hull,
                        "owner_id": target_owner_id,
                        "fuel": target_fuel,
                        "warp": target_warp,
                    }
                )

            structural_pairs: list[tuple[dict[str, Any], dict[str, Any], float, bool | None]] = []
            for initiator in initiator_candidates:
                for target in target_candidates:
                    if initiator["ship_id"] == target["ship_id"]:
                        continue
                    if (
                        initiator["owner_id"] is None
                        or target["owner_id"] is None
                        or initiator["owner_id"] != target["owner_id"]
                    ):
                        continue
                    if initiator["fuel"] is not None and initiator["fuel"] < 50:
                        continue
                    if target["fuel"] is not None and target["fuel"] < 1:
                        continue
                    if target["warp"] != 0:
                        continue

                    vector = _vector(origin, destination, topology)
                    distance = hypot(*vector)
                    if distance < 100.0:
                        continue

                    numeric_fc = initiator["numeric_fc"]
                    fc_match = None if numeric_fc is None else numeric_fc == target["ship_id"] % 1000
                    structural_pairs.append((initiator, target, distance, fc_match))

            existing_match = False
            numeric_fc_match = False
            for initiator, target, _distance, fc_match in structural_pairs:
                if fc_match is True:
                    numeric_fc_match = True
                key = (before_turn, initiator["ship_id"], target["ship_id"], destination)
                if key in discovered_keys:
                    existing_match = True

            if structural_pairs:
                counts["structural_chunnel_match"] += 1
                structural_hulls[hull_id] += 1
                structural_games[game_id] += 1
                if numeric_fc_match:
                    counts["numeric_fc_structural_match"] += 1
                    fc_hulls[hull_id] += 1
                    fc_games[game_id] += 1
                else:
                    counts["structural_without_numeric_fc_match"] += 1
                if existing_match:
                    counts["existing_classifier_event_match"] += 1
                else:
                    counts["missed_by_existing_event_discovery"] += 1

            group_key = (game_id, before_turn, origin, destination)
            detail = {
                "game": game_id,
                "turn": before_turn,
                "ship": ship_id,
                "hull": hull_id,
                "origin": origin,
                "destination": destination,
                "distance": round(hypot(*_vector(origin, destination, topology)), 3),
                "before_group_size": len(before_here),
                "after_group_size": len(after_there),
                "initiators": [
                    {
                        "ship": item["ship_id"],
                        "hull": item["hull_id"],
                        "owner_known": item["owner_id"] is not None,
                        "fuel_ge_50": None if item["fuel"] is None else item["fuel"] >= 50,
                        "numeric_fc_known": item["numeric_fc"] is not None,
                    }
                    for item in initiator_candidates
                ],
                "targets": [
                    {
                        "ship": item["ship_id"],
                        "hull": item["hull_id"],
                        "owner_known": item["owner_id"] is not None,
                        "fuel_ge_1": None if item["fuel"] is None else item["fuel"] >= 1,
                        "warp": item["warp"],
                    }
                    for item in target_candidates
                ],
                "structural_pair_count": len(structural_pairs),
                "numeric_fc_match": numeric_fc_match,
                "existing_event_match": existing_match,
            }
            group_rows[group_key].append(detail)

            bucket = (
                "numeric_fc"
                if numeric_fc_match
                else "structural"
                if structural_pairs
                else "other"
            )
            if len(examples[bucket]) < 30:
                examples[bucket].append(detail)

    multi_candidate_groups = [
        (key, values)
        for key, values in group_rows.items()
        if len(values) >= 2
    ]
    structural_groups = [
        (key, values)
        for key, values in group_rows.items()
        if any(value["structural_pair_count"] > 0 for value in values)
    ]

    print("\n===== POPULATION =====")
    for key in (
        "rows",
        "structural_chunnel_match",
        "numeric_fc_structural_match",
        "structural_without_numeric_fc_match",
        "existing_classifier_event_match",
        "missed_by_existing_event_discovery",
    ):
        print(f"{key}=", counts[key])
    print("multi_candidate_same_route_groups=", len(multi_candidate_groups))
    print("structural_chunnel_route_groups=", len(structural_groups))

    print("\n===== STRUCTURAL MATCH BY HULL =====")
    for hull_id, n in structural_hulls.most_common():
        print(hull_id, n)
    print("structural_match_games=", sorted(structural_games))

    print("\n===== NUMERIC-FC MATCH BY HULL =====")
    for hull_id, n in fc_hulls.most_common():
        print(hull_id, n)
    print("numeric_fc_match_games=", sorted(fc_games))

    print("\n===== MULTI-CANDIDATE SAME-ROUTE GROUPS =====")
    for key, values in sorted(multi_candidate_groups, key=lambda item: (-len(item[1]), item[0]))[:30]:
        game_id, turn, origin, destination = key
        print(
            {
                "game": game_id,
                "turn": turn,
                "origin": origin,
                "destination": destination,
                "candidate_rows": len(values),
                "candidate_hulls": sorted(value["hull"] for value in values),
                "structural": any(value["structural_pair_count"] > 0 for value in values),
                "numeric_fc": any(value["numeric_fc_match"] for value in values),
                "existing_event": any(value["existing_event_match"] for value in values),
            }
        )

    print("\n===== NUMERIC-FC STRUCTURAL EXAMPLES =====")
    for row in examples["numeric_fc"]:
        print(row)

    print("\n===== STRUCTURAL WITHOUT NUMERIC-FC EXAMPLES =====")
    for row in examples["structural"]:
        print(row)

    print("\n===== OTHER EXAMPLES =====")
    for row in examples["other"]:
        print(row)

    print("\n===== INTERPRETATION GUARDRAIL =====")
    print(
        "Structural chunnel evidence requires an initiator-ability ship leaving the candidate origin "
        "for the same destination and a stationary target-ability ship already at that destination, "
        "with same known owner, target Warp 0, fuel eligibility and >=100 ly effective-topology distance."
    )
    print(
        "A numeric friendly-code match is stronger evidence. Structural matches without visible numeric "
        "friendly code are evidence of an event-discovery visibility gap, not permission to infer private FC values."
    )
    print(
        "This first pass intentionally tests same-origin initiators. If it explains a material fraction, "
        "the production fix should generalize through a mode/topology-aware pre-chunnel-position model rather than hard-code groups."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
