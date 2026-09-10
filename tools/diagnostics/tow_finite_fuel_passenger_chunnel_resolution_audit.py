from __future__ import annotations

import argparse
import ast
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from planets_lab.corpus.movement_chunnel_context import (
    ChunnelAbilityCatalog,
    _ability_sets,
    discover_observed_chunnel_events,
    extract_stable_chunnel_abilities,
)
from planets_lab.corpus.movement_differential import (
    _entity_map,
    _planet_tuples_by_turn,
    _warp_well_destination,
)
from planets_lab.corpus.movement_residual_context import _owner_record
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.validation.movement_geometry import MovementSample

from intercept_fuel_historical_differential_audit import PREPARED_DIR, RAW_DIR
from tow_finite_fuel_classic_multiroot_audit import _xy


EXAMPLE_LIMIT = 100


def _counter(text: str, key: str) -> int:
    matches = re.findall(rf"^{re.escape(key)}=\s*(\d+)\s*$", text, re.M)
    if not matches:
        raise ValueError(f"missing counter {key!r}")
    return int(matches[-1])


def _passenger_cases(path: Path) -> tuple[int, tuple[dict[str, Any], ...]]:
    text = path.read_text(encoding="utf-8")
    expected = _counter(text, "post_classic_storm_input")
    cases_count = _counter(text, "cases")
    if expected != 9 or cases_count != 9:
        raise ValueError(
            f"unexpected passenger population: input={expected} cases={cases_count}"
        )

    try:
        block = text.split("===== CASES =====", 1)[1].split(
            "===== INTERPRETATION =====", 1
        )[0]
    except IndexError as exc:
        raise ValueError("passenger log has no CASES block") from exc

    cases: list[dict[str, Any]] = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        parsed = ast.literal_eval(line)
        if isinstance(parsed, dict) and "game" in parsed:
            cases.append(parsed)

    if len(cases) != expected:
        raise ValueError(
            f"passenger case parsing mismatch: parsed={len(cases)} expected={expected}"
        )
    return expected, tuple(cases)


def _exact_turn_abilities(
    snapshots: Sequence[Any],
    archive_turn: int,
) -> tuple[
    ChunnelAbilityCatalog | None,
    str,
    tuple[tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]], ...],
]:
    sets_seen: set[tuple[frozenset[int], frozenset[int], frozenset[int]]] = set()
    for snapshot in snapshots:
        if int(snapshot.archive_turn) != archive_turn:
            continue
        sets_seen.add(_ability_sets(snapshot.mechanics_payload))

    if not sets_seen:
        return None, "missing", ()

    serialized = tuple(
        sorted(
            (
                tuple(sorted(initiators)),
                tuple(sorted(targets)),
                tuple(sorted(self_hulls)),
            )
            for initiators, targets, self_hulls in sets_seen
        )
    )
    if len(sets_seen) != 1:
        return None, "conflict", serialized

    initiators, targets, self_hulls = next(iter(sets_seen))
    return (
        ChunnelAbilityCatalog(
            initiator_hull_ids=initiators,
            target_hull_ids=targets,
            self_hull_ids=self_hulls,
            first_member=f"archive-turn-{archive_turn}",
            last_member=f"archive-turn-{archive_turn}",
            ability_sets_consistent=True,
        ),
        "resolved",
        serialized,
    )


def _friendly_code_inventory(
    *,
    ship_groups: Mapping[tuple[int, int], Sequence[Any]],
    turn: int,
    ship_id: int,
) -> dict[str, Any]:
    _, owner = _owner_record(ship_groups.get((turn, ship_id), ()))
    if owner is None:
        return {"status": "owner_state_missing"}

    entries: list[dict[str, Any]] = []
    for key in ("friendlycode", "friendly_code", "fc"):
        if key not in owner.raw:
            continue
        value = owner.raw.get(key)
        entries.append({"key": key, "type": type(value).__name__, "value": value})
    if not entries:
        return {"status": "field_missing"}
    return {"status": "present", "entries": tuple(entries)}


def _movement_sample(
    *,
    case: Mapping[str, Any],
    origin: tuple[int, int],
    geometry: tuple[int, int],
    observed: tuple[int, int],
) -> MovementSample:
    hull_id = int(case["hull"]) if case.get("hull") is not None else None
    return MovementSample(
        turn=int(case["turn"]),
        ship_id=int(case["tower_ship"]),
        x=origin[0],
        y=origin[1],
        target_x=geometry[0],
        target_y=geometry[1],
        warp=int(case["warp"]),
        next_x=observed[0],
        next_y=observed[1],
        hull_id=hull_id,
    )


def _event_detail(event: Any) -> dict[str, Any]:
    return {
        "initiator": int(event.initiator_ship_id),
        "target": int(event.target_ship_id),
        "owner": int(event.owner_id),
        "pre_chunnel_position": event.pre_chunnel_position,
        "destination": event.destination,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve the non-negative passenger-Chunnel leads in the exact nine-row "
            "finite-fuel Tow remainder. Checks Tow-geometry warp-well normalization, "
            "exact-turn Chunnel ability catalogs when the archive-wide catalog changed, "
            "and raw friendly-code availability for structural tow-pair roles."
        )
    )
    parser.add_argument("--passenger-log", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=EXAMPLE_LIMIT)
    args = parser.parse_args()
    if args.examples < 0:
        raise SystemExit("--examples must be non-negative")

    expected, cases = _passenger_cases(args.passenger_log)
    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        by_game[int(case["game"])].append(case)

    totals: Counter[str] = Counter()
    totals["post_classic_storm_input"] = expected
    examples: list[dict[str, Any]] = []

    print("===== FINITE-FUEL TOW PASSENGER CHUNNEL RESOLUTION AUDIT =====")
    print("passenger_log=", args.passenger_log)
    print("post_classic_storm_input=", expected)

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        cache_path = PREPARED_DIR / f"game-{game_id}.pickle"
        if not archive_path.is_file():
            raise FileNotFoundError(archive_path)
        if not cache_path.is_file():
            raise FileNotFoundError(
                f"{cache_path}; this bounded follow-up does not rebuild prepared caches"
            )

        archive_data = archive_path.read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=cache_path,
        )
        stable = extract_stable_chunnel_abilities(archive_data)
        entities = _entity_map(prepared.snapshots)
        planets_by_turn = _planet_tuples_by_turn(entities)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")

        stable_events, _ = discover_observed_chunnel_events(prepared.snapshots, stable)
        stable_by_turn_destination: dict[tuple[int, tuple[int, int]], list[Any]] = defaultdict(list)
        for event in stable_events:
            stable_by_turn_destination[
                (int(event.before_archive_turn), event.destination)
            ].append(event)

        game_counts: Counter[str] = Counter()
        print(
            {
                "game": game_id,
                "cache_hit": cache_hit,
                "cases": len(by_game[game_id]),
                "ability_sets_consistent": stable.ability_sets_consistent,
                "stable_initiator_hulls": tuple(sorted(stable.initiator_hull_ids)),
                "stable_target_hulls": tuple(sorted(stable.target_hull_ids)),
            },
            flush=True,
        )

        exact_event_cache: dict[
            int,
            tuple[str, ChunnelAbilityCatalog | None, tuple[Any, ...], tuple[Any, ...]],
        ] = {}

        for case in by_game[game_id]:
            totals["cases"] += 1
            game_counts["cases"] += 1

            before_turn = int(case["turn"])
            tower_id = int(case["tower_ship"])
            tow_target_id = int(case["target_ship"])
            origin = _xy(case["origin"], "origin")
            geometry = _xy(case["geometry"], "geometry")
            observed = _xy(case["observed"], "observed")
            original_lead = str(case.get("lead", "unknown"))

            if original_lead == "no_chunnel_lead":
                totals["background_no_chunnel_rows"] += 1
                game_counts["background_no_chunnel_rows"] += 1
            else:
                totals["resolution_target_rows"] += 1
                game_counts["resolution_target_rows"] += 1

            sample = _movement_sample(
                case=case,
                origin=origin,
                geometry=geometry,
                observed=observed,
            )
            well, well_ambiguous = _warp_well_destination(
                sample=sample,
                endpoint=geometry,
                planets=planets_by_turn.get(before_turn, ()),
            )
            geometry_after_well = well if well is not None else geometry
            if well_ambiguous:
                totals["geometry_warpwell_ambiguous_rows"] += 1
                game_counts["geometry_warpwell_ambiguous_rows"] += 1
            elif well is not None:
                totals["geometry_warpwell_rows"] += 1
                game_counts["geometry_warpwell_rows"] += 1

            stable_route_events = tuple(
                stable_by_turn_destination.get((before_turn, observed), ())
            )
            stable_warpwell_route_events = tuple(
                event
                for event in stable_route_events
                if event.pre_chunnel_position is not None
                and event.pre_chunnel_position == geometry_after_well
            )
            if stable_warpwell_route_events:
                totals["stable_observed_chunnel_warpwell_route_rows"] += 1
                game_counts["stable_observed_chunnel_warpwell_route_rows"] += 1

            exact_status = "not_needed"
            exact_sets: tuple[Any, ...] = ()
            exact_route_events: tuple[Any, ...] = ()
            exact_warpwell_route_events: tuple[Any, ...] = ()
            if not stable.ability_sets_consistent:
                totals["changed_catalog_rows"] += 1
                game_counts["changed_catalog_rows"] += 1

                if before_turn not in exact_event_cache:
                    exact_catalog, exact_status, exact_sets = _exact_turn_abilities(
                        prepared.snapshots,
                        before_turn,
                    )
                    if exact_catalog is not None:
                        exact_events, _ = discover_observed_chunnel_events(
                            prepared.snapshots,
                            exact_catalog,
                        )
                    else:
                        exact_events = ()
                    exact_event_cache[before_turn] = (
                        exact_status,
                        exact_catalog,
                        exact_sets,
                        exact_events,
                    )
                exact_status, exact_catalog, exact_sets, exact_events = exact_event_cache[
                    before_turn
                ]

                totals[f"exact_turn_catalog_{exact_status}_rows"] += 1
                game_counts[f"exact_turn_catalog_{exact_status}_rows"] += 1
                exact_route_events = tuple(
                    event
                    for event in exact_events
                    if int(event.before_archive_turn) == before_turn
                    and event.destination == observed
                )
                exact_warpwell_route_events = tuple(
                    event
                    for event in exact_route_events
                    if event.pre_chunnel_position is not None
                    and event.pre_chunnel_position == geometry_after_well
                )
                if exact_warpwell_route_events:
                    totals["exact_turn_observed_chunnel_warpwell_route_rows"] += 1
                    game_counts["exact_turn_observed_chunnel_warpwell_route_rows"] += 1

            structural_pairs = tuple(case.get("structural_origin_pairs") or ())
            pair_role_details: list[dict[str, Any]] = []
            for pair in structural_pairs:
                initiator = pair.get("initiator", {})
                target = pair.get("target", {})
                initiator_id = int(initiator["ship"])
                target_id = int(target["ship"])
                roles: list[str] = []
                if initiator_id == tower_id:
                    roles.append("tower_is_structural_initiator")
                if initiator_id == tow_target_id:
                    roles.append("tow_target_is_structural_initiator")
                if target_id == tower_id:
                    roles.append("tower_is_structural_target")
                if target_id == tow_target_id:
                    roles.append("tow_target_is_structural_target")
                if not roles:
                    continue
                pair_role_details.append(
                    {
                        "initiator": initiator_id,
                        "target": target_id,
                        "roles": tuple(roles),
                        "numeric_fc_match": pair.get("numeric_fc_match"),
                        "initiator_friendly_code": _friendly_code_inventory(
                            ship_groups=ship_groups,
                            turn=before_turn,
                            ship_id=initiator_id,
                        ),
                    }
                )

            if pair_role_details:
                totals["rows_with_tow_pair_structural_role"] += 1
                game_counts["rows_with_tow_pair_structural_role"] += 1
            if any(item["numeric_fc_match"] is True for item in pair_role_details):
                totals["rows_with_tow_pair_numeric_fc_structural_role"] += 1
                game_counts["rows_with_tow_pair_numeric_fc_structural_role"] += 1

            if stable_warpwell_route_events or exact_warpwell_route_events:
                refined_lead = "observed_chunnel_route_warpwell_exact"
                totals["refined_observed_chunnel_route_warpwell_exact"] += 1
            elif any(item["numeric_fc_match"] is True for item in pair_role_details):
                refined_lead = "tow_pair_numeric_fc_structural_chunnel"
                totals["refined_tow_pair_numeric_fc_structural_chunnel"] += 1
            elif pair_role_details:
                refined_lead = "tow_pair_structural_chunnel"
                totals["refined_tow_pair_structural_chunnel"] += 1
            elif (
                original_lead == "ability_catalog_changed_unresolved"
                and exact_status == "resolved"
            ):
                refined_lead = "exact_turn_catalog_no_chunnel_lead"
                totals["refined_exact_turn_catalog_no_chunnel_lead"] += 1
            else:
                refined_lead = original_lead
                totals[f"refined_preserved:{refined_lead}"] += 1

            if len(examples) < args.examples:
                examples.append(
                    {
                        "game": game_id,
                        "turn": before_turn,
                        "tower_ship": tower_id,
                        "target_ship": tow_target_id,
                        "original_lead": original_lead,
                        "refined_lead": refined_lead,
                        "origin": origin,
                        "geometry": geometry,
                        "geometry_after_warpwell": geometry_after_well,
                        "geometry_warpwell_ambiguous": well_ambiguous,
                        "observed": observed,
                        "stable_route_events": tuple(
                            _event_detail(event) for event in stable_route_events
                        ),
                        "stable_warpwell_route_events": tuple(
                            _event_detail(event)
                            for event in stable_warpwell_route_events
                        ),
                        "exact_turn_catalog_status": exact_status,
                        "exact_turn_ability_sets": exact_sets,
                        "exact_turn_route_events": tuple(
                            _event_detail(event) for event in exact_route_events
                        ),
                        "exact_turn_warpwell_route_events": tuple(
                            _event_detail(event)
                            for event in exact_warpwell_route_events
                        ),
                        "tow_pair_structural_roles": tuple(pair_role_details),
                    }
                )

        print({"game_summary": game_id, **dict(sorted(game_counts.items()))}, flush=True)

    if totals["cases"] != totals["post_classic_storm_input"]:
        raise AssertionError(
            f"case accounting mismatch: input={totals['post_classic_storm_input']} "
            f"cases={totals['cases']}"
        )
    if totals["resolution_target_rows"] + totals["background_no_chunnel_rows"] != totals["cases"]:
        raise AssertionError("resolution-target accounting is not closed")

    print()
    print("===== SUMMARY =====")
    for key in (
        "post_classic_storm_input",
        "cases",
        "resolution_target_rows",
        "background_no_chunnel_rows",
        "geometry_warpwell_rows",
        "geometry_warpwell_ambiguous_rows",
        "stable_observed_chunnel_warpwell_route_rows",
        "changed_catalog_rows",
        "exact_turn_catalog_resolved_rows",
        "exact_turn_catalog_missing_rows",
        "exact_turn_catalog_conflict_rows",
        "exact_turn_observed_chunnel_warpwell_route_rows",
        "rows_with_tow_pair_structural_role",
        "rows_with_tow_pair_numeric_fc_structural_role",
        "refined_observed_chunnel_route_warpwell_exact",
        "refined_tow_pair_numeric_fc_structural_chunnel",
        "refined_tow_pair_structural_chunnel",
        "refined_exact_turn_catalog_no_chunnel_lead",
    ):
        print(f"{key}= {totals[key]}")

    print()
    print("===== CASES =====")
    for item in examples:
        print(item)

    print()
    print("===== INTERPRETATION =====")
    print(
        "Warp-well route exactness requires the Tow direct geometry endpoint to resolve "
        "through the ordinary eligible-planet warp-well classifier to the independently "
        "observed Chunnel event pre-position. Mere proximity is not sufficient."
    )
    print(
        "A tow-pair structural role means the tower or factual Tow target is itself the "
        "structural Chunnel initiator/target candidate. Numeric friendly-code equality "
        "remains a stronger tier than structural geometry alone; missing FC stays unknown."
    )
    print(
        "For archive-wide ability-catalog changes, an exact archive-turn consensus may "
        "remove the catalog uncertainty for that row. It does not prove a Chunnel unless "
        "route/role evidence exists under that exact-turn catalog."
    )
    print("finite-fuel Tow remains OPEN; planets-intel is unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
