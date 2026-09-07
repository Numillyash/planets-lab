from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Mapping

# Direct execution (`python tools/diagnostics/...py`) puts only this directory on
# sys.path. Add the repository root so the src package and sibling diagnostics
# are importable in the normal lab container workflow.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import duckdb

from planets_lab.corpus.archive import read_archive_members, turn_members
from planets_lab.corpus.movement_chunnel_context import _sample_from_transition
from planets_lab.corpus.movement_differential import _entity_map, _intish
from planets_lab.corpus.movement_residual_context import GRAVITONIC_HULL_IDS
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.normalizer import _decode_member_json
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.movement import max_nominal_distance
from planets_lab.sim.normal_movement import plan_full_normal_move, project_toward_waypoint

from generic_fuel_limited_residual_audit import _static_specs
from mine_hit_hostorder_differential_audit import _owner_states


DEFAULT_DATABASE = Path("validation/corpus/compiled/v1/corpus.duckdb")
RAW_DIR = Path("validation/corpus/cache/loadall")
PREPARED_DIR = Path("validation/corpus/cache/prepared-v1")
INTERCEPT_MISSION_ID = 7
TOW_MISSION_ID = 6

# Fields that must be present in the controlling player's own raw ship record
# before the canonical importer may be used for a movement-mass differential.
# This prevents importer defaults from silently turning missing private state
# into factual zero mass/cargo.
MASS_REQUIRED_FIELDS = (
    "hullid",
    "engineid",
    "beams",
    "torps",
    "bays",
    "ammo",
    "neutronium",
    "duranium",
    "tritanium",
    "molybdenum",
    "supplies",
    "clans",
)


def _settings_unlimited_fuel(archive_data: bytes) -> bool | None:
    members = turn_members(archive_data)
    if not members:
        return None
    member = members[0]
    raw = read_archive_members(archive_data, [member.name])[member.name]
    payload, _ = _decode_member_json(raw, member)
    settings = payload.get("settings")
    if not isinstance(settings, Mapping):
        return None
    value = settings.get("unlimitedfuel")
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1"}:
            return True
        if normalized in {"false", "0"}:
            return False
    return None


def _raw_field_present(raw: Mapping[str, Any], key: str) -> bool:
    if key in raw and raw.get(key) is not None:
        return True
    aliases = {
        "hullid": ("hull_id",),
        "engineid": ("engine_id",),
    }
    return any(alias in raw and raw.get(alias) is not None for alias in aliases.get(key, ()))


def _mass_state_complete(raw: Mapping[str, Any]) -> bool:
    if not all(_raw_field_present(raw, key) for key in MASS_REQUIRED_FIELDS):
        return False
    beams = _intish(raw.get("beams")) or 0
    torps = _intish(raw.get("torps")) or 0
    if beams > 0 and _intish(raw.get("beamid", raw.get("beam_id"))) is None:
        return False
    if torps > 0 and _intish(raw.get("torpedoid", raw.get("torpedo_id"))) is None:
        return False
    return True


def _mission(raw: Mapping[str, Any] | None) -> int | None:
    return _intish(raw.get("mission")) if raw is not None else None


def _target_id(raw: Mapping[str, Any]) -> int | None:
    value = _intish(
        raw.get(
            "mission1target",
            raw.get("mission1_target_id", raw.get("mission1targetid")),
        )
    )
    return value if value is not None and value > 0 else None


def _post_reset(after_raw: Mapping[str, Any] | None, observed: tuple[int, int]) -> bool:
    if after_raw is None:
        return False
    fuel = _intish(after_raw.get("neutronium"))
    warp = _intish(after_raw.get("warp"))
    target_x = _intish(after_raw.get("targetx", after_raw.get("waypointx")))
    target_y = _intish(after_raw.get("targety", after_raw.get("waypointy")))
    return fuel == 0 and warp == 0 and (target_x, target_y) == observed


def _geometry_endpoint(
    *,
    x: int,
    y: int,
    target_x: int,
    target_y: int,
    warp: int,
    gravitonic: bool,
) -> tuple[int, int]:
    max_distance = max_nominal_distance(warp, gravitonic=gravitonic)
    distance = hypot(target_x - x, target_y - y)
    if distance <= max_distance:
        return target_x, target_y
    return project_toward_waypoint(
        x=x,
        y=y,
        target_x=target_x,
        target_y=target_y,
        distance=max_distance,
    )


def _snapshot_by_owner(prepared: Any) -> dict[tuple[int, int], Any]:
    result: dict[tuple[int, int], Any] = {}
    for snapshot in prepared.snapshots:
        result[(int(snapshot.archive_turn), int(snapshot.player_id))] = snapshot
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Historical differential for owner-visible Intercept (mission 7). "
            "It compares geometry-only movement toward the target's observed "
            "post-Move-Most position with the existing Nu fuel/proration candidate. "
            "Only non-sphere, same-identity, non-Intercept targets enter the strict "
            "fuel differential. Snapshot fuel is never promoted to Intercept-phase "
            "fact; exact matches are evidence candidates until earlier Host fuel "
            "mutations are excluded."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--examples", type=int, default=50)
    args = parser.parse_args()

    con = duckdb.connect(str(args.database), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT
                game_id,
                before_archive_turn,
                after_archive_turn,
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

    print("===== INTERCEPT FUEL HISTORICAL DIFFERENTIAL =====")
    print("source_view= movement_transitions")
    print("owner_visible_ready_intercept_rows=", len(rows))

    by_game: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_game[int(row[0])].append(row)

    totals = Counter()
    signatures = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for game_id in sorted(by_game):
        archive_path = RAW_DIR / f"game-{game_id}.zip"
        if not archive_path.exists():
            totals["missing_archive"] += len(by_game[game_id])
            print(f"game={game_id} missing_archive rows={len(by_game[game_id])}")
            continue

        archive_data = archive_path.read_bytes()
        prepared, cache_hit = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=PREPARED_DIR / f"game-{game_id}.pickle",
        )
        specs = _static_specs(archive_data)
        raw_topology = extract_map_topology(archive_data)
        topology = effective_sphere_topology(game_id=game_id, topology=raw_topology)
        unlimited_fuel = _settings_unlimited_fuel(archive_data)
        entities = _entity_map(prepared.snapshots)
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        snapshots = _snapshot_by_owner(prepared)
        transition_by_key = {
            (item.before_archive_turn, item.after_archive_turn, item.entity_id): item
            for item in prepared.movement_geometry_readiness.results
        }

        print(
            f"game={game_id} cache_hit={cache_hit} rows={len(by_game[game_id])} "
            f"sphere={topology.sphere} unlimitedfuel={unlimited_fuel}"
        )

        for row in by_game[game_id]:
            (
                _game_id,
                before_turn,
                after_turn,
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
            ship_id = int(ship_id)
            hull_id = int(hull_id)
            warp = int(warp)
            observed = (int(next_x), int(next_y))
            totals["rows"] += 1

            if topology.sphere is True:
                totals["sphere_excluded"] += 1
                continue
            if unlimited_fuel is True:
                totals["unlimited_fuel_excluded"] += 1
                continue
            if unlimited_fuel is None:
                totals["fuel_setting_unknown"] += 1

            owner_id, before_raw, after_raw, same_identity = _owner_states(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=ship_id,
            )
            if owner_id is None or before_raw is None:
                totals["interceptor_owner_state_missing"] += 1
                continue
            if not same_identity or after_raw is None:
                totals["interceptor_identity_break"] += 1
                continue
            if _mission(before_raw) != INTERCEPT_MISSION_ID:
                totals["interceptor_mission_mismatch"] += 1
                continue
            if str(before_raw.get("friendlycode", "")).strip().lower() == "hyp":
                totals["interceptor_hyp_excluded"] += 1
                continue

            target_id = _target_id(before_raw)
            if target_id is None or target_id == ship_id:
                totals["invalid_or_missing_target"] += 1
                continue
            totals["valid_target_id"] += 1

            target_transition = transition_by_key.get((before_turn, after_turn, target_id))
            if target_transition is None:
                totals["target_transition_missing"] += 1
                continue
            target_sample = _sample_from_transition(target_transition, entities)
            if target_sample is None:
                totals["target_geometry_missing"] += 1
                continue

            target_owner_id, target_before_raw, target_after_raw, target_same_identity = _owner_states(
                ship_groups=ship_groups,
                before_turn=before_turn,
                after_turn=after_turn,
                ship_id=target_id,
            )
            if target_owner_id is None or target_before_raw is None:
                totals["target_owner_state_missing"] += 1
                continue
            if not target_same_identity or target_after_raw is None:
                totals["target_identity_break"] += 1
                continue
            if _mission(target_before_raw) == INTERCEPT_MISSION_ID:
                totals["target_intercept_excluded"] += 1
                continue

            target_final = target_sample.observed_destination
            totals["strict_target_post_move_known"] += 1

            geometry_endpoint = _geometry_endpoint(
                x=int(x),
                y=int(y),
                target_x=int(target_final[0]),
                target_y=int(target_final[1]),
                warp=warp,
                gravitonic=hull_id in GRAVITONIC_HULL_IDS,
            )
            geometry_exact = geometry_endpoint == observed
            if geometry_exact:
                totals["geometry_endpoint_exact"] += 1
            else:
                totals["geometry_endpoint_differs"] += 1

            if not _mass_state_complete(before_raw):
                totals["mass_state_incomplete"] += 1
                continue

            snapshot = snapshots.get((before_turn, owner_id))
            if snapshot is None:
                totals["owner_snapshot_missing"] += 1
                continue
            try:
                state = snapshot.import_state()
                interceptor = state.ships.get(ship_id)
                if interceptor is None or interceptor.owner_id != owner_id:
                    totals["owner_snapshot_ship_missing"] += 1
                    continue
                plan = plan_full_normal_move(
                    interceptor,
                    specs,
                    target_x=int(target_final[0]),
                    target_y=int(target_final[1]),
                    warp=warp,
                    gravitonic=hull_id in GRAVITONIC_HULL_IDS,
                    allow_partial=True,
                    allow_fuel_proration=True,
                )
            except (KeyError, ValueError) as exc:
                totals["fuel_plan_error"] += 1
                if len(examples["plan_error"]) < args.examples:
                    examples["plan_error"].append(
                        {"game": game_id, "turn": before_turn, "ship": ship_id, "error": str(exc)}
                    )
                continue

            totals["fuel_formula_ready"] += 1
            if plan.fuel_limited:
                totals["snapshot_fuel_limited"] += 1
            else:
                totals["snapshot_fuel_sufficient"] += 1

            if not plan.executable:
                totals[f"fuel_plan_unresolved:{plan.reason}"] += 1
                signature = ("geometry_exact" if geometry_exact else "geometry_diff", "fuel_unresolved")
                signatures[signature] += 1
                continue

            fuel_endpoint = (plan.destination_x, plan.destination_y)
            fuel_exact = fuel_endpoint == observed
            if fuel_exact:
                totals["fuel_endpoint_exact"] += 1
            else:
                totals["fuel_endpoint_differs"] += 1

            signature = (
                "geometry_exact" if geometry_exact else "geometry_diff",
                "fuel_exact" if fuel_exact else "fuel_diff",
                "limited" if plan.fuel_limited else "sufficient",
            )
            signatures[signature] += 1

            discriminating_support = plan.fuel_limited and fuel_exact and not geometry_exact
            discriminating_contradiction = plan.fuel_limited and geometry_exact and not fuel_exact
            if discriminating_support:
                totals["fuel_limited_discriminating_support"] += 1
            if discriminating_contradiction:
                totals["fuel_limited_discriminating_contradiction"] += 1

            reset_support = _post_reset(after_raw, observed)
            if reset_support:
                totals["after_reset_supporting_only"] += 1
            if discriminating_support and reset_support:
                totals["fuel_limited_support_with_after_reset"] += 1

            bucket = (
                "support"
                if discriminating_support
                else "contradiction"
                if discriminating_contradiction
                else "fuel_limited"
                if plan.fuel_limited
                else "ordinary"
            )
            if len(examples[bucket]) < args.examples:
                examples[bucket].append(
                    {
                        "game": game_id,
                        "turn": before_turn,
                        "after_turn": after_turn,
                        "ship": ship_id,
                        "hull": hull_id,
                        "warp": warp,
                        "fuel_before_snapshot": _intish(before_raw.get("neutronium")),
                        "movement_mass": plan.total_mass,
                        "fuel_required_candidate": plan.fuel_required,
                        "fuel_used_candidate": plan.fuel_used,
                        "fuel_limited_candidate": plan.fuel_limited,
                        "target_ship": target_id,
                        "target_final_observed": target_final,
                        "origin": (int(x), int(y)),
                        "observed": observed,
                        "geometry_endpoint": geometry_endpoint,
                        "fuel_endpoint": fuel_endpoint,
                        "geometry_exact": geometry_exact,
                        "fuel_exact": fuel_exact,
                        "after_reset_supporting_only": reset_support,
                    }
                )

    print("\n===== POPULATION =====")
    for key in (
        "rows",
        "sphere_excluded",
        "unlimited_fuel_excluded",
        "fuel_setting_unknown",
        "interceptor_owner_state_missing",
        "interceptor_identity_break",
        "interceptor_mission_mismatch",
        "interceptor_hyp_excluded",
        "invalid_or_missing_target",
        "valid_target_id",
        "target_transition_missing",
        "target_geometry_missing",
        "target_owner_state_missing",
        "target_identity_break",
        "target_intercept_excluded",
        "strict_target_post_move_known",
        "geometry_endpoint_exact",
        "geometry_endpoint_differs",
        "mass_state_incomplete",
        "owner_snapshot_missing",
        "owner_snapshot_ship_missing",
        "fuel_plan_error",
        "fuel_formula_ready",
        "snapshot_fuel_sufficient",
        "snapshot_fuel_limited",
        "fuel_endpoint_exact",
        "fuel_endpoint_differs",
        "fuel_limited_discriminating_support",
        "fuel_limited_discriminating_contradiction",
        "after_reset_supporting_only",
        "fuel_limited_support_with_after_reset",
    ):
        print(f"{key}=", totals[key])

    print("\n===== UNRESOLVED FUEL PLANS =====")
    for key, count in sorted(
        ((key, count) for key, count in totals.items() if key.startswith("fuel_plan_unresolved:")),
        key=lambda item: (-item[1], item[0]),
    ):
        print(f"{key}=", count)

    print("\n===== DIFFERENTIAL SIGNATURES =====")
    for signature, count in sorted(signatures.items(), key=lambda item: (-item[1], str(item[0]))):
        print(signature, "=", count)

    print("\n===== EXAMPLES =====")
    for bucket in ("support", "contradiction", "fuel_limited", "ordinary", "plan_error"):
        print(f"-- {bucket} --")
        for item in examples[bucket]:
            print(item)

    print("\n===== INTERPRETATION =====")
    print(
        "fuel_limited_discriminating_support means the existing Nu fuel/proration candidate "
        "matches the factual Intercept endpoint while unlimited geometry does not."
    )
    print(
        "fuel_limited_discriminating_contradiction means unlimited geometry matches while the "
        "snapshot-fuel candidate does not; this can reflect earlier Host fuel mutation and is "
        "not by itself a falsification of Intercept fuel burn."
    )
    print(
        "Snapshot neutronium is pre-Host evidence, not Intercept-phase fuel. Production must "
        "remain fail-closed until supporting cases also exclude relevant earlier fuel mutations."
    )
    print(
        "Target final positions are accepted only for same-identity targets whose own mission "
        "is not Intercept, avoiding Classic Intercept order-dependence in this first differential."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
