from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import duckdb

from planets_lab.corpus.movement_chunnel_context import (
    _sample_from_transition,
    discover_observed_chunnel_events,
    extract_stable_chunnel_abilities,
)
from planets_lab.corpus.movement_context import MovementMissionConvention
from planets_lab.corpus.movement_differential import (
    GEOMETRY_EXPLAINED_CATEGORIES,
    _entity_map,
    _intish,
    _movement_category,
    _planet_tuples_by_turn,
)
from planets_lab.corpus.movement_mine_context import (
    build_mine_evidence_context,
    classify_strong_mine_hit_transition,
)
from planets_lab.corpus.movement_residual_context import (
    GRAVITONIC_HULL_IDS,
    _observed_tow_targets,
    _storm_consensus_by_turn,
    _storm_expected_category,
)
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.sim.normal_movement import plan_full_normal_move
from planets_lab.validation.movement_geometry import MovementSample

from damage_limited_warp_residual_audit import _max_warp_from_damage, _race_map
from generic_fuel_limited_residual_audit import _static_specs
from intercept_fuel_historical_differential_audit import (
    DEFAULT_DATABASE,
    INTERCEPT_MISSION_ID,
    PREPARED_DIR,
    RAW_DIR,
    _mass_state_complete,
    _mission,
    _settings_unlimited_fuel,
    _snapshot_by_owner,
    _target_id,
)
from mine_hit_hostorder_differential_audit import _owner_states


def _effective_damage_sample(
    sample: MovementSample,
    *,
    effective_warp: int,
) -> MovementSample:
    return MovementSample(
        turn=sample.turn,
        ship_id=sample.ship_id,
        x=sample.x,
        y=sample.y,
        target_x=sample.target_x,
        target_y=sample.target_y,
        warp=effective_warp,
        next_x=sample.next_x,
        next_y=sample.next_y,
        hull_id=sample.hull_id,
        gravitonic=sample.gravitonic,
        game_id=sample.game_id,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the strict snapshot-fuel-limited Intercept cases for already-known external "
            "movement mechanics before treating a fuel differential as causal. The diagnostic "
            "checks the production-verified mine classifier, damage-limited warp, warp wells, "
            "ion-storm drag, observed Tow routes and observed Chunnel target routes."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    con = duckdb.connect(str(args.database), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT
                game_id,
                before_archive_turn,
                after_archive_turn,
                before_embedded_turn,
                ship_id,
                hull_id,
                warp,
                x_before,
                y_before,
                x_after,
                y_after
            FROM movement_transitions
            WHERE intent_class = 'intercept'
              AND readiness_status = 'ready'
            ORDER BY game_id, before_archive_turn, after_archive_turn, ship_id
            """
        ).fetchall()
    finally:
        con.close()

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    totals = Counter()
    cases: list[dict[str, Any]] = []

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        if not archive_path.exists():
            continue
        archive_data = archive_path.read_bytes()
        if _settings_unlimited_fuel(archive_data) is True:
            continue

        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        topology = effective_sphere_topology(
            game_id=game_id,
            topology=extract_map_topology(archive_data),
        )
        if topology.sphere is True:
            continue

        specs = _static_specs(archive_data)
        entities = _entity_map(prepared.snapshots)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        snapshots = _snapshot_by_owner(prepared)
        planets_by_turn = _planet_tuples_by_turn(entities)
        races = _race_map(prepared.snapshots)
        storms_by_turn, storm_conflicts, storm_invalid = _storm_consensus_by_turn(prepared.snapshots)
        mine_context = build_mine_evidence_context(
            game_id=game_id,
            archive_data=archive_data,
            snapshots=prepared.snapshots,
        )
        transition_by_key = {
            (item.before_archive_turn, item.after_archive_turn, item.entity_id): item
            for item in prepared.movement_geometry_readiness.results
        }
        valid_pairs = {
            (item.before_archive_turn, item.after_archive_turn)
            for item in prepared.movement_geometry_readiness.results
        }
        tow_targets, _ = _observed_tow_targets(
            entities=entities,
            ship_groups=ship_groups,
            valid_pairs=valid_pairs,
            convention=MovementMissionConvention(),
        )
        abilities = extract_stable_chunnel_abilities(archive_data)
        chunnel_events, _ = discover_observed_chunnel_events(prepared.snapshots, abilities)
        chunnel_target_events: dict[tuple[int, int], list[Any]] = defaultdict(list)
        for event in chunnel_events:
            chunnel_target_events[(event.before_archive_turn, event.target_ship_id)].append(event)

        for row in by_game[game_id]:
            (
                _game_id,
                before_turn,
                after_turn,
                embedded_turn,
                ship_id,
                hull_id,
                warp,
                x,
                y,
                next_x,
                next_y,
            ) = row
            before_turn = int(before_turn)
            after_turn = int(after_turn)
            embedded_turn = int(embedded_turn)
            ship_id = int(ship_id)
            hull_id = int(hull_id)
            warp = int(warp)
            origin = (int(x), int(y))
            observed = (int(next_x), int(next_y))

            owner_id, before_raw, after_raw, same_identity = _owner_states(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=ship_id,
            )
            if owner_id is None or before_raw is None or after_raw is None or not same_identity:
                continue
            if _mission(before_raw) != INTERCEPT_MISSION_ID:
                continue
            if str(before_raw.get("friendlycode", "")).strip().lower() == "hyp":
                continue
            if not _mass_state_complete(before_raw):
                continue

            target_id = _target_id(before_raw)
            if target_id is None or target_id == ship_id:
                continue
            target_transition = transition_by_key.get((before_turn, after_turn, target_id))
            if target_transition is None:
                continue
            target_sample = _sample_from_transition(target_transition, entities)
            if target_sample is None:
                continue
            target_owner_id, target_before_raw, target_after_raw, target_same_identity = _owner_states(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=target_id,
            )
            if (
                target_owner_id is None
                or target_before_raw is None
                or target_after_raw is None
                or not target_same_identity
                or _mission(target_before_raw) == INTERCEPT_MISSION_ID
            ):
                continue

            snapshot = snapshots.get((before_turn, owner_id))
            if snapshot is None:
                continue
            state = snapshot.import_state()
            interceptor = state.ships.get(ship_id)
            if interceptor is None or interceptor.owner_id != owner_id:
                continue

            target_final = tuple(int(value) for value in target_sample.observed_destination)
            fuel_plan = plan_full_normal_move(
                interceptor,
                specs,
                target_x=target_final[0],
                target_y=target_final[1],
                warp=warp,
                gravitonic=hull_id in GRAVITONIC_HULL_IDS,
                allow_partial=True,
                allow_fuel_proration=True,
            )
            if not fuel_plan.fuel_limited:
                continue

            totals["strict_snapshot_fuel_limited"] += 1
            sample = MovementSample(
                turn=embedded_turn,
                ship_id=ship_id,
                x=origin[0],
                y=origin[1],
                target_x=target_final[0],
                target_y=target_final[1],
                warp=warp,
                next_x=observed[0],
                next_y=observed[1],
                hull_id=hull_id,
                gravitonic=hull_id in GRAVITONIC_HULL_IDS,
                game_id=game_id,
            )
            planets = planets_by_turn.get(before_turn, ())
            baseline_category = _movement_category(sample, planets=planets)

            mine_evidence = classify_strong_mine_hit_transition(
                context=mine_context,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=ship_id,
                owner_id=owner_id,
                before_raw=before_raw,
                sample=sample,
            )
            if mine_evidence is not None:
                totals[f"mine:{mine_evidence.category}"] += 1

            race_id = races.get(owner_id)
            before_damage = _intish(before_raw.get("damage"))
            after_damage = _intish(after_raw.get("damage"))
            damage_limit = _max_warp_from_damage(before_damage, race_id)
            damage_effective_warp = min(warp, damage_limit) if damage_limit is not None else None
            damage_category = None
            if damage_effective_warp is not None and damage_effective_warp < warp:
                damage_sample = _effective_damage_sample(sample, effective_warp=damage_effective_warp)
                damage_category = _movement_category(damage_sample, planets=planets)
                if damage_category in GEOMETRY_EXPLAINED_CATEGORIES:
                    totals["damage_limited_exact"] += 1

            storm_category = None
            storm_status = None
            if after_turn in storm_conflicts:
                storm_status = "conflict"
            elif after_turn in storm_invalid:
                storm_status = "invalid"
            else:
                storm_category, storm_status = _storm_expected_category(
                    sample,
                    storms=storms_by_turn.get(after_turn, ()),
                    planets=planets,
                )
                if storm_category is not None:
                    totals[f"storm:{storm_category}"] += 1

            tow_route_towers = tow_targets.get((before_turn, ship_id), ())
            if tow_route_towers:
                totals["observed_tow_route"] += 1

            chunnel_matches = tuple(chunnel_target_events.get((before_turn, ship_id), ()))
            if chunnel_matches:
                totals["observed_chunnel_target_route"] += 1

            flags: list[str] = []
            if baseline_category in GEOMETRY_EXPLAINED_CATEGORIES:
                flags.append(f"baseline:{baseline_category}")
            if mine_evidence is not None:
                flags.append(f"mine:{mine_evidence.category}")
            if damage_category in GEOMETRY_EXPLAINED_CATEGORIES:
                flags.append(f"damage:{damage_category}")
            if storm_category is not None:
                flags.append(f"storm:{storm_category}")
            if tow_route_towers:
                flags.append("observed_tow_route")
            if chunnel_matches:
                flags.append("observed_chunnel_target_route")
            if flags:
                totals["cases_with_known_external_explanation"] += 1
            else:
                totals["cases_without_known_external_explanation"] += 1

            cases.append(
                {
                    "game": game_id,
                    "turn": before_turn,
                    "after_turn": after_turn,
                    "ship": ship_id,
                    "hull": hull_id,
                    "owner_race": race_id,
                    "warp": warp,
                    "target_ship": target_id,
                    "origin": origin,
                    "target_final_observed": target_final,
                    "observed": observed,
                    "observed_distance": round(
                        hypot(observed[0] - origin[0], observed[1] - origin[1]), 3
                    ),
                    "snapshot_fuel": _intish(before_raw.get("neutronium")),
                    "snapshot_fuel_required": fuel_plan.fuel_required,
                    "snapshot_fuel_plan_executable": fuel_plan.executable,
                    "snapshot_fuel_plan_reason": fuel_plan.reason,
                    "snapshot_fuel_endpoint": (
                        (fuel_plan.destination_x, fuel_plan.destination_y)
                        if fuel_plan.executable
                        else None
                    ),
                    "before_damage": before_damage,
                    "after_damage": after_damage,
                    "damage_warp_limit": damage_limit,
                    "damage_effective_warp": damage_effective_warp,
                    "damage_category": damage_category,
                    "baseline_category": baseline_category,
                    "mine_evidence": (
                        {
                            "category": mine_evidence.category,
                            "damage_hits": mine_evidence.damage_hits,
                            "slowdown_hits": mine_evidence.slowdown_hits,
                        }
                        if mine_evidence is not None
                        else None
                    ),
                    "storm_status": storm_status,
                    "storm_category": storm_category,
                    "observed_tow_route_towers": tuple(tow_route_towers),
                    "observed_chunnel_target_events": tuple(
                        {
                            "initiator_ship": event.initiator_ship_id,
                            "destination": event.destination,
                            "pre_chunnel_position": event.pre_chunnel_position,
                        }
                        for event in chunnel_matches
                    ),
                    "known_external_flags": tuple(flags),
                }
            )

    print("===== INTERCEPT FUEL EXTERNAL CONFOUNDER AUDIT =====")
    print("strict_snapshot_fuel_limited=", totals["strict_snapshot_fuel_limited"])
    print("cases_with_known_external_explanation=", totals["cases_with_known_external_explanation"])
    print("cases_without_known_external_explanation=", totals["cases_without_known_external_explanation"])
    print("damage_limited_exact=", totals["damage_limited_exact"])
    print("observed_tow_route=", totals["observed_tow_route"])
    print("observed_chunnel_target_route=", totals["observed_chunnel_target_route"])
    for key, count in sorted(totals.items()):
        if key.startswith("mine:") or key.startswith("storm:"):
            print(f"{key}=", count)

    print("\n===== CASES =====")
    for case in cases:
        print(case)

    print("\n===== INTERPRETATION =====")
    print(
        "A fuel match is not promoted to causal evidence when an already-verified external "
        "movement mechanic also explains the same factual endpoint."
    )
    print(
        "The mine result uses the current production-verified strong mine classifier from "
        "movement_mine_context rather than a new ad-hoc Intercept-only rule."
    )
    print(
        "Observed Tow/Chunnel route matches preserve their existing evidentiary limits: they "
        "are route evidence, not proof of hidden Host causality."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
