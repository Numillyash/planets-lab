from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from planets_lab.corpus.movement_chunnel_context import (
    _numeric_friendly_code,
    discover_observed_chunnel_events,
    extract_stable_chunnel_abilities,
)
from planets_lab.corpus.movement_differential import _entity_map, _intish, _resolved_value
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records

from intercept_fuel_historical_differential_audit import PREPARED_DIR, RAW_DIR
from tow_finite_fuel_classic_multiroot_audit import _remaining_cases, _xy


EXAMPLE_LIMIT = 100


def _entity_xy(entity: Any) -> tuple[int, int] | None:
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


def _owner_state(
    *,
    ship_groups: Mapping[tuple[int, int], Sequence[Any]],
    entities: Mapping[tuple[str, int, int], Any],
    turn: int,
    ship_id: int,
) -> tuple[int | None, Any | None]:
    owner_id, owner = _owner_record(ship_groups.get((turn, ship_id), ()))
    if owner_id is not None and owner_id > 0:
        return owner_id, owner
    entity = entities.get(("ship", turn, ship_id))
    fallback = _resolved_int(entity, "ownerid")
    if fallback is None or fallback <= 0:
        return None, None
    return fallback, None


def _fuel(owner: Any | None, entity: Any) -> int | None:
    if owner is not None:
        value = _intish(owner.raw.get("neutronium"))
        if value is not None:
            return value
    return _resolved_int(entity, "neutronium")


def _position_index(
    entities: Mapping[tuple[str, int, int], Any],
) -> Mapping[tuple[int, tuple[int, int]], tuple[int, ...]]:
    grouped: dict[tuple[int, tuple[int, int]], list[int]] = defaultdict(list)
    for (kind, turn, ship_id), entity in entities.items():
        if kind != "ship":
            continue
        xy = _entity_xy(entity)
        if xy is not None:
            grouped[(turn, xy)].append(ship_id)
    return {key: tuple(sorted(set(values))) for key, values in grouped.items()}


def _ship_detail(
    *,
    entities: Mapping[tuple[str, int, int], Any],
    ship_groups: Mapping[tuple[int, int], Sequence[Any]],
    turn: int,
    ship_id: int,
    after_turn: int,
) -> dict[str, Any]:
    before = entities.get(("ship", turn, ship_id))
    after = entities.get(("ship", after_turn, ship_id))
    owner_id, owner = _owner_state(
        ship_groups=ship_groups,
        entities=entities,
        turn=turn,
        ship_id=ship_id,
    )
    numeric_fc = _numeric_friendly_code(owner) if owner is not None else None
    return {
        "ship": ship_id,
        "hull": _resolved_int(before, "hullid"),
        "owner": owner_id,
        "warp": _resolved_int(before, "warp"),
        "fuel": _fuel(owner, before),
        "numeric_fc": numeric_fc,
        "before": _entity_xy(before),
        "after": _entity_xy(after),
    }


def _structural_origin_pairs(
    *,
    origin: tuple[int, int],
    destination: tuple[int, int],
    before_turn: int,
    after_turn: int,
    position_index: Mapping[tuple[int, tuple[int, int]], tuple[int, ...]],
    entities: Mapping[tuple[str, int, int], Any],
    ship_groups: Mapping[tuple[int, int], Sequence[Any]],
    initiator_hulls: frozenset[int],
    target_hulls: frozenset[int],
) -> tuple[dict[str, Any], ...]:
    initiators: list[dict[str, Any]] = []
    for ship_id in position_index.get((before_turn, origin), ()):
        detail = _ship_detail(
            entities=entities,
            ship_groups=ship_groups,
            turn=before_turn,
            ship_id=ship_id,
            after_turn=after_turn,
        )
        if detail["hull"] not in initiator_hulls:
            continue
        if detail["after"] != destination:
            continue
        if detail["owner"] is None:
            continue
        if detail["fuel"] is not None and int(detail["fuel"]) < 50:
            continue
        initiators.append(detail)

    targets: list[dict[str, Any]] = []
    for ship_id in position_index.get((before_turn, destination), ()):
        detail = _ship_detail(
            entities=entities,
            ship_groups=ship_groups,
            turn=before_turn,
            ship_id=ship_id,
            after_turn=after_turn,
        )
        if detail["hull"] not in target_hulls:
            continue
        if detail["after"] != destination:
            continue
        if detail["owner"] is None or detail["warp"] != 0:
            continue
        if detail["fuel"] is not None and int(detail["fuel"]) < 1:
            continue
        targets.append(detail)

    pairs: list[dict[str, Any]] = []
    for initiator in initiators:
        for target in targets:
            if initiator["ship"] == target["ship"]:
                continue
            if initiator["owner"] != target["owner"]:
                continue
            numeric_fc = initiator["numeric_fc"]
            fc_match = None if numeric_fc is None else int(numeric_fc) == int(target["ship"]) % 1000
            pairs.append(
                {
                    "initiator": initiator,
                    "target": target,
                    "numeric_fc_match": fc_match,
                }
            )
    return tuple(pairs)


def _event_detail(event: Any, tower_id: int, tow_target_id: int) -> dict[str, Any]:
    roles: list[str] = []
    if int(event.initiator_ship_id) == tower_id:
        roles.append("tower_is_initiator")
    if int(event.target_ship_id) == tower_id:
        roles.append("tower_is_chunnel_target")
    if int(event.initiator_ship_id) == tow_target_id:
        roles.append("tow_target_is_initiator")
    if int(event.target_ship_id) == tow_target_id:
        roles.append("tow_target_is_chunnel_target")
    return {
        "initiator": int(event.initiator_ship_id),
        "target": int(event.target_ship_id),
        "owner": int(event.owner_id),
        "pre_chunnel_position": event.pre_chunnel_position,
        "destination": event.destination,
        "roles": tuple(roles),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect the exact nine-row post-classic-storm finite-fuel Tow residual for passenger "
            "Chunnel / special relocation context. Strong evidence is kept separate from weaker "
            "co-movement and structural leads; no hidden Chunnel event is inferred from distance alone."
        )
    )
    parser.add_argument("--reclassification-log", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=EXAMPLE_LIMIT)
    args = parser.parse_args()
    if args.examples < 0:
        raise SystemExit("--examples must be non-negative")

    expected, cases = _remaining_cases(args.reclassification_log)
    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        by_game[int(case["game"])].append(case)

    totals: Counter[str] = Counter()
    totals["post_classic_storm_input"] = expected
    examples: list[dict[str, Any]] = []

    print("===== FINITE-FUEL TOW PASSENGER CHUNNEL CONTEXT AUDIT =====")
    print("reclassification_log=", args.reclassification_log)
    print("post_classic_storm_input=", expected)

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        if not archive_path.is_file():
            raise FileNotFoundError(archive_path)
        archive_data = archive_path.read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        abilities = extract_stable_chunnel_abilities(archive_data)
        if not abilities.ability_sets_consistent:
            raise ValueError(f"game {game_id}: Chunnel ability catalog changed across archive")

        entities = _entity_map(prepared.snapshots)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        positions = _position_index(entities)
        events, event_counts = discover_observed_chunnel_events(prepared.snapshots, abilities)
        events_by_turn_destination: dict[tuple[int, tuple[int, int]], list[Any]] = defaultdict(list)
        for event in events:
            events_by_turn_destination[(event.before_archive_turn, event.destination)].append(event)

        game_counts: Counter[str] = Counter()
        print(
            {
                "game": game_id,
                "cache_hit": cache_hit,
                "cases": len(by_game[game_id]),
                "initiator_hulls": tuple(sorted(abilities.initiator_hull_ids)),
                "target_hulls": tuple(sorted(abilities.target_hull_ids)),
                "self_hulls": tuple(sorted(abilities.self_hull_ids)),
                "observed_chunnel_events": len(events),
                "event_counts": dict(event_counts),
            },
            flush=True,
        )

        for case in by_game[game_id]:
            before_turn = int(case["turn"])
            after_turn = int(case["after_turn"])
            tower_id = int(case["tower_ship"])
            tow_target_id = int(case["target_ship"])
            origin = _xy(case["origin"], "origin")
            geometry = _xy(case["geometry_endpoint"], "geometry_endpoint")
            observed = _xy(case["observed"], "observed")

            totals["cases"] += 1
            game_counts["cases"] += 1

            route_events = tuple(
                events_by_turn_destination.get((before_turn, observed), ())
            )
            event_details = tuple(
                _event_detail(event, tower_id, tow_target_id) for event in route_events
            )
            origin_events = tuple(
                detail for detail in event_details if detail["pre_chunnel_position"] == origin
            )
            geometry_events = tuple(
                detail for detail in event_details if detail["pre_chunnel_position"] == geometry
            )
            role_events = tuple(detail for detail in event_details if detail["roles"])

            if route_events:
                totals["rows_with_observed_chunnel_destination"] += 1
                game_counts["rows_with_observed_chunnel_destination"] += 1
            if origin_events:
                totals["rows_with_observed_chunnel_origin_route"] += 1
                game_counts["rows_with_observed_chunnel_origin_route"] += 1
            if geometry_events:
                totals["rows_with_observed_chunnel_geometry_route"] += 1
                game_counts["rows_with_observed_chunnel_geometry_route"] += 1
            if role_events:
                totals["rows_where_tow_pair_has_direct_chunnel_role"] += 1
                game_counts["rows_where_tow_pair_has_direct_chunnel_role"] += 1

            structural_pairs = _structural_origin_pairs(
                origin=origin,
                destination=observed,
                before_turn=before_turn,
                after_turn=after_turn,
                position_index=positions,
                entities=entities,
                ship_groups=ship_groups,
                initiator_hulls=abilities.initiator_hull_ids,
                target_hulls=abilities.target_hull_ids,
            )
            numeric_pairs = tuple(
                pair for pair in structural_pairs if pair["numeric_fc_match"] is True
            )
            if structural_pairs:
                totals["rows_with_structural_origin_chunnel"] += 1
                game_counts["rows_with_structural_origin_chunnel"] += 1
            if numeric_pairs:
                totals["rows_with_numeric_fc_structural_origin_chunnel"] += 1
                game_counts["rows_with_numeric_fc_structural_origin_chunnel"] += 1

            same_origin_comovers: list[dict[str, Any]] = []
            for ship_id in positions.get((before_turn, origin), ()):
                if ship_id in {tower_id, tow_target_id}:
                    continue
                detail = _ship_detail(
                    entities=entities,
                    ship_groups=ship_groups,
                    turn=before_turn,
                    ship_id=ship_id,
                    after_turn=after_turn,
                )
                if detail["after"] == observed:
                    same_origin_comovers.append(detail)
            if same_origin_comovers:
                totals["rows_with_same_origin_comovers"] += 1
                game_counts["rows_with_same_origin_comovers"] += 1

            observed_route_exact = bool(origin_events or geometry_events)
            strong_structural = bool(numeric_pairs)
            comovement = bool(same_origin_comovers)
            if observed_route_exact:
                lead = "observed_chunnel_route_exact"
                totals["observed_chunnel_route_exact_lead"] += 1
            elif strong_structural:
                lead = "numeric_fc_structural_origin_chunnel"
                totals["numeric_fc_structural_origin_chunnel_lead"] += 1
            elif structural_pairs:
                lead = "structural_origin_chunnel"
                totals["structural_origin_chunnel_lead"] += 1
            elif comovement:
                lead = "same_origin_comovement_only"
                totals["same_origin_comovement_only_lead"] += 1
            elif route_events:
                lead = "same_destination_observed_chunnel_only"
                totals["same_destination_observed_chunnel_only_lead"] += 1
            else:
                lead = "no_chunnel_lead"
                totals["no_chunnel_lead"] += 1
            game_counts[f"lead:{lead}"] += 1

            if len(examples) < args.examples:
                examples.append(
                    {
                        "game": game_id,
                        "turn": before_turn,
                        "after_turn": after_turn,
                        "tower_ship": tower_id,
                        "target_ship": tow_target_id,
                        "hull": case.get("hull"),
                        "race": case.get("race"),
                        "warp": case.get("warp"),
                        "direction": case.get("direction"),
                        "origin": origin,
                        "geometry": geometry,
                        "observed": observed,
                        "residual_vector": case.get("residual_vector"),
                        "lead": lead,
                        "observed_chunnel_destination_events": event_details,
                        "origin_route_events": origin_events,
                        "geometry_route_events": geometry_events,
                        "structural_origin_pairs": structural_pairs,
                        "numeric_fc_structural_origin_pairs": numeric_pairs,
                        "same_origin_comovers": tuple(same_origin_comovers),
                    }
                )

        print({"game_summary": game_id, **dict(sorted(game_counts.items()))}, flush=True)

    if totals["cases"] != totals["post_classic_storm_input"]:
        raise AssertionError(
            f"case accounting mismatch: input={totals['post_classic_storm_input']} cases={totals['cases']}"
        )

    lead_total = sum(
        totals[key]
        for key in (
            "observed_chunnel_route_exact_lead",
            "numeric_fc_structural_origin_chunnel_lead",
            "structural_origin_chunnel_lead",
            "same_origin_comovement_only_lead",
            "same_destination_observed_chunnel_only_lead",
            "no_chunnel_lead",
        )
    )
    if lead_total != totals["cases"]:
        raise AssertionError(f"lead accounting mismatch: {lead_total} != {totals['cases']}")

    print("\n===== SUMMARY =====")
    for key in (
        "post_classic_storm_input",
        "cases",
        "rows_with_observed_chunnel_destination",
        "rows_with_observed_chunnel_origin_route",
        "rows_with_observed_chunnel_geometry_route",
        "rows_where_tow_pair_has_direct_chunnel_role",
        "rows_with_structural_origin_chunnel",
        "rows_with_numeric_fc_structural_origin_chunnel",
        "rows_with_same_origin_comovers",
        "observed_chunnel_route_exact_lead",
        "numeric_fc_structural_origin_chunnel_lead",
        "structural_origin_chunnel_lead",
        "same_origin_comovement_only_lead",
        "same_destination_observed_chunnel_only_lead",
        "no_chunnel_lead",
    ):
        print(f"{key}= {totals[key]}")

    print("\n===== CASES =====")
    for item in sorted(
        examples,
        key=lambda row: (
            int(row["game"]),
            int(row["turn"]),
            int(row["tower_ship"]),
            int(row["target_ship"]),
        ),
    ):
        print(item)

    print("\n===== INTERPRETATION =====")
    print(
        "observed_chunnel_route_exact means an independently discovered active Chunnel event in the same Host transition "
        "has the Tow row's factual destination and an existing reconstructed pre-Chunnel position equal to either the Tow origin "
        "or its direct geometry endpoint. This is a strong external-relocation lead, not a new Host-order rule."
    )
    print(
        "numeric-FC structural origin evidence requires an initiator-ability ship at the factual Tow origin that ends at the same "
        "destination plus a stationary target-ability ship already there with same known owner and matching numeric friendly code."
    )
    print(
        "Same-destination events and co-movement without an exact event route are weaker leads only. Distance alone is never used "
        "to infer a hidden Chunnel. Unknown fuel or phase state is not converted to known sufficient state."
    )
    print("finite-fuel Tow remains OPEN; no planets-intel change is made here.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
