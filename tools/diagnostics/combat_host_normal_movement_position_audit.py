from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_damage_context import max_warp_from_damage
from planets_lab.corpus.movement_differential import (
    _entity_map,
    _intish,
    _planet_tuples_by_turn,
    _settings_warp_well_state_by_turn,
)
from planets_lab.corpus.movement_residual_context import GRAVITONIC_HULL_IDS
from planets_lab.corpus.movement_sphere_context import effective_sphere_topology
from planets_lab.corpus.movement_topology_diagnostics import extract_map_topology
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.data.nu_loadturn import NuLoadTurnError, _ship
from planets_lab.rules.combat.order import CLOAK_INTERCEPT_MISSION_ID, INTERCEPT_MISSION_ID
from planets_lab.rules.movement import WarpWellAmbiguityError, warp_well_planet_id
from planets_lab.sim.normal_movement import plan_full_normal_move

from combat_host_candidate_set_audit import (
    TOW_MISSION_ID,
    _factual_sites,
    _intrinsic_stationary_reason,
    _owner_rows_for_turn,
    _potential_chunnel_source_sites,
    _serialize,
    _tow_target_ids,
)
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_mission7_matched_control_audit import _dedup_vcrs
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
    _static_specs,
)
from combat_host_residual_physical_stack_audit import _xy


DEFAULT_EXAMPLE_LIMIT = 80
TRANSFER_AMOUNT_FIELDS = (
    "transferneutronium",
    "transferduranium",
    "transfertritanium",
    "transfermolybdenum",
    "transfersupplies",
    "transferclans",
    "transfermegacredits",
)


def _nonzero_transfer_amount(raw: Mapping[str, Any]) -> bool:
    for field in TRANSFER_AMOUNT_FIELDS:
        value = _intish(raw.get(field))
        if value is not None and value != 0:
            return True
    return False


def _inbound_transfer_targets(
    rows: Mapping[int, tuple[int, Mapping[str, Any]]],
) -> frozenset[int]:
    targets: set[int] = set()
    for _ship_id, (_owner_id, raw) in rows.items():
        if not _nonzero_transfer_amount(raw):
            continue
        target_id = _intish(raw.get("transfertargetid"))
        if target_id is not None and target_id > 0:
            targets.add(target_id)
    return frozenset(targets)


def _effective_requested_warp(
    raw: Mapping[str, Any],
    *,
    race_id: int | None,
) -> tuple[int | None, str | None]:
    requested = _intish(raw.get("warp"))
    if requested is None or not 0 <= requested <= 9:
        return None, "warp_unknown_or_invalid"
    if requested == 0:
        return 0, None

    damage = _intish(raw.get("damage"))
    if damage is None or damage < 0:
        return None, "damage_unknown"

    # Both ordinary and Lizard damage tables permit Warp 9 at <=19%, so race
    # resolution is unnecessary in this low-damage band.
    if damage <= 19:
        return requested, None

    max_warp = max_warp_from_damage(damage, race_id)
    if max_warp is None:
        return None, "damage_warp_limit_unresolved"
    if requested <= max_warp:
        return requested, None

    # Existing differential evidence only promotes the raw-damage limiting
    # branch when visible supplies cannot repair even 1% before movement.
    supplies = _intish(raw.get("supplies"))
    if supplies is None or supplies < 0 or supplies >= 5:
        return None, "damage_repair_can_change_warp"
    return max_warp, None


def _special_movement_reason(
    *,
    ship_id: int,
    raw: Mapping[str, Any],
    tow_targets: frozenset[int],
    chunnel_source_sites: frozenset[tuple[int, int]],
) -> str | None:
    """Fail closed on movement branches that supersede ordinary self-movement.

    This guard is intentionally independent of the stationary-v1 reason order:
    a moving ship can still be a Tow target, Tow/Intercept/C&I actor, HYP ship,
    or passenger in an obvious Chunnel-source stack.
    """

    mission = _intish(raw.get("mission"))
    if mission == TOW_MISSION_ID:
        return "tow_attempt"
    if mission == INTERCEPT_MISSION_ID:
        return "intercept_movement"
    if mission == CLOAK_INTERCEPT_MISSION_ID:
        return "cloak_intercept_movement"

    fc = raw.get("friendlycode")
    if isinstance(fc, str) and fc.strip().lower() == "hyp":
        return "hyperjump_movement"

    if ship_id in tow_targets:
        return "tow_target"

    x, y = _xy(raw)
    if x is None or y is None:
        return "position_unknown"
    if (int(x), int(y)) in chunnel_source_sites:
        return "potential_chunnel_source_stack"

    return None


def _normal_position_prediction(
    *,
    game_id: int,
    ship_id: int,
    owner_id: int,
    raw: Mapping[str, Any],
    race_id: int | None,
    specs: Any,
    planets: tuple[tuple[int, int, int], ...],
    warp_wells_enabled: bool | None,
    eligible_warp_well_planet_ids: frozenset[int] | None,
    inbound_transfer_targets: frozenset[int],
    tow_targets: frozenset[int],
    chunnel_source_sites: frozenset[tuple[int, int]],
    sphere: bool | None,
) -> tuple[tuple[int, int] | None, str]:
    del game_id  # retained in the call surface for future game-scoped mechanics.

    special_reason = _special_movement_reason(
        ship_id=ship_id,
        raw=raw,
        tow_targets=tow_targets,
        chunnel_source_sites=chunnel_source_sites,
    )
    if special_reason is not None:
        return None, special_reason

    if sphere is True:
        return None, "sphere_topology_not_integrated"

    if _nonzero_transfer_amount(raw):
        return None, "outbound_transfer"
    if ship_id in inbound_transfer_targets:
        return None, "inbound_transfer"

    fc = raw.get("friendlycode")
    if isinstance(fc, str) and fc.strip().lower() == "mkt":
        return None, "pre_move_mkt_mass_change"

    effective_warp, warp_issue = _effective_requested_warp(raw, race_id=race_id)
    if warp_issue is not None or effective_warp is None:
        return None, warp_issue or "effective_warp_unresolved"
    if effective_warp <= 0:
        x, y = _xy(raw)
        if x is None or y is None:
            return None, "position_unknown"
        return (int(x), int(y)), "stationary_effective_warp_zero"

    raw_mass = _intish(raw.get("mass"))
    if raw_mass is None or raw_mass <= 0:
        return None, "raw_mass_missing"

    try:
        ship = _ship(raw)
    except (NuLoadTurnError, TypeError, ValueError):
        return None, "ship_import_unresolved"
    if ship.id != ship_id or ship.owner_id != owner_id:
        return None, "ship_identity_unresolved"

    target_x = _intish(raw.get("targetx"))
    target_y = _intish(raw.get("targety"))
    if target_x is None or target_y is None:
        return None, "waypoint_unknown"

    try:
        plan = plan_full_normal_move(
            ship,
            specs,
            target_x=int(target_x),
            target_y=int(target_y),
            warp=int(effective_warp),
            gravitonic=ship.hull_id in GRAVITONIC_HULL_IDS,
            allow_partial=True,
            allow_fuel_proration=False,
            movement_mass_override=int(raw_mass),
        )
    except (KeyError, TypeError, ValueError):
        return None, "normal_plan_unresolved"

    if not plan.executable:
        return None, f"normal_plan_{plan.reason or 'not_executable'}"

    destination = (int(plan.destination_x), int(plan.destination_y))
    if effective_warp <= 1 or destination == (ship.x, ship.y):
        return destination, "normal_move"
    if warp_wells_enabled is False:
        return destination, "normal_move"

    # `planets` contains all factual planet objects for the turn, not only the
    # already-recognized warp-well-eligible subset. This matters when the
    # effective warp-well state itself is unknown: a nearby planet must make the
    # endpoint unresolved rather than silently looking irrelevant.
    if warp_wells_enabled is None:
        try:
            possible_planet = warp_well_planet_id(
                origin_x=ship.x,
                origin_y=ship.y,
                end_x=destination[0],
                end_y=destination[1],
                movement_warp=int(effective_warp),
                planets=planets,
            )
        except WarpWellAmbiguityError:
            return None, "warp_well_setting_unknown"
        if possible_planet is not None:
            return None, "warp_well_setting_unknown"
        return destination, "normal_move_warp_well_irrelevant"

    eligible_ids = eligible_warp_well_planet_ids
    if eligible_ids is None:
        return None, "warp_well_eligibility_unknown"
    excluded = frozenset(
        planet_id for planet_id, _x, _y in planets if planet_id not in eligible_ids
    )
    try:
        well_planet = warp_well_planet_id(
            origin_x=ship.x,
            origin_y=ship.y,
            end_x=destination[0],
            end_y=destination[1],
            movement_warp=int(effective_warp),
            planets=planets,
            excluded_planet_ids=excluded,
        )
    except WarpWellAmbiguityError:
        return None, "warp_well_ambiguous"

    if well_planet is None:
        return destination, "normal_move"

    planet_map = {planet_id: (x, y) for planet_id, x, y in planets}
    snapped = planet_map.get(well_planet)
    if snapped is None:
        return None, "warp_well_planet_missing"
    return (int(snapped[0]), int(snapped[1])), "normal_move_warp_well"


def run(args: argparse.Namespace) -> dict[str, Any]:
    archives_considered = 0
    payload_conflicts = 0
    occurrence_counts: Counter[str] = Counter()
    normal_reasons: Counter[str] = Counter()
    pair_counts: Counter[str] = Counter()
    site_counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []

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
        seen, conflicts = _dedup_vcrs(archive_data)
        payload_conflicts += conflicts
        sites = _factual_sites(game_id=game_id, seen=seen)

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

        rows_by_turn: dict[int, dict[int, tuple[int, Mapping[str, Any]]]] = {}
        tow_targets_by_turn: dict[int, frozenset[int]] = {}
        chunnel_sites_by_turn: dict[int, frozenset[tuple[int, int]]] = {}
        inbound_targets_by_turn: dict[int, frozenset[int]] = {}

        for (battle_turn, x, y), factual in sorted(sites.items()):
            site_counts["sites"] += 1
            before_turn = battle_turn - 1
            if before_turn not in rows_by_turn:
                owner_rows = _owner_rows_for_turn(ship_groups, before_turn)
                rows_by_turn[before_turn] = owner_rows
                tow_targets_by_turn[before_turn] = _tow_target_ids(owner_rows)
                chunnel_sites_by_turn[before_turn] = _potential_chunnel_source_sites(owner_rows)
                inbound_targets_by_turn[before_turn] = _inbound_transfer_targets(owner_rows)

            owner_rows = rows_by_turn[before_turn]
            tow_targets = tow_targets_by_turn[before_turn]
            chunnel_sites = chunnel_sites_by_turn[before_turn]
            inbound_targets = inbound_targets_by_turn[before_turn]
            planets = tuple(planets_by_turn.get(before_turn, ()))
            eligible_ids_raw = eligible_by_turn.get(before_turn)
            eligible_ids = (
                frozenset(int(value) for value in eligible_ids_raw)
                if eligible_ids_raw is not None
                else None
            )
            warp_wells_enabled = warp_wells_by_turn.get(before_turn)

            factual_pairs = {tuple(pair) for pair in factual["pairs"]}
            ship_ids = sorted({ship_id for pair in factual_pairs for ship_id in pair})
            occurrence_status: dict[int, str] = {}

            for ship_id in ship_ids:
                occurrence_counts["factual_ship_occurrences"] += 1
                owner_entry = owner_rows.get(ship_id)
                if owner_entry is None:
                    occurrence_status[ship_id] = "uncovered"
                    occurrence_counts["owner_current_missing"] += 1
                    continue
                owner_id, raw = owner_entry

                stationary_reason = _intrinsic_stationary_reason(
                    ship_id=ship_id,
                    raw=raw,
                    tow_targets=tow_targets,
                    chunnel_source_sites=chunnel_sites,
                )
                predicted: tuple[int, int] | None = None
                source = ""
                if stationary_reason is None:
                    sx, sy = _xy(raw)
                    if sx is not None and sy is not None:
                        predicted = (int(sx), int(sy))
                        source = "stationary"
                    else:
                        stationary_reason = "position_unknown"
                elif stationary_reason == "self_movement_possible":
                    predicted, source = _normal_position_prediction(
                        game_id=game_id,
                        ship_id=ship_id,
                        owner_id=owner_id,
                        raw=raw,
                        race_id=races.get(owner_id),
                        specs=specs,
                        planets=planets,
                        warp_wells_enabled=warp_wells_enabled,
                        eligible_warp_well_planet_ids=eligible_ids,
                        inbound_transfer_targets=inbound_targets,
                        tow_targets=tow_targets,
                        chunnel_source_sites=chunnel_sites,
                        sphere=topology.sphere,
                    )
                    normal_reasons[source] += 1
                else:
                    source = stationary_reason

                if predicted is None:
                    occurrence_status[ship_id] = "uncovered"
                    occurrence_counts["position_uncovered"] += 1
                    occurrence_counts[
                        f"uncovered:{source or stationary_reason or 'unknown'}"
                    ] += 1
                    continue

                occurrence_counts["position_predicted"] += 1
                occurrence_counts[f"source:{source}"] += 1
                if predicted == (x, y):
                    occurrence_status[ship_id] = "exact"
                    occurrence_counts["position_exact"] += 1
                else:
                    occurrence_status[ship_id] = "mismatch"
                    occurrence_counts["position_mismatch"] += 1
                    if len(examples) < args.example_limit:
                        examples.append(
                            {
                                "game_id": game_id,
                                "battle_turn": battle_turn,
                                "ship_id": ship_id,
                                "owner_id": owner_id,
                                "source": source,
                                "predicted": list(predicted),
                                "factual_site": [x, y],
                                "warp": _intish(raw.get("warp")),
                                "mission": _intish(raw.get("mission")),
                                "damage": _intish(raw.get("damage")),
                                "fuel": _intish(raw.get("neutronium")),
                                "mass": _intish(raw.get("mass")),
                                "targetx": _intish(raw.get("targetx")),
                                "targety": _intish(raw.get("targety")),
                                "friendlycode": raw.get("friendlycode"),
                            }
                        )

            site_pair_statuses: list[str] = []
            for a_id, b_id in sorted(factual_pairs):
                pair_counts["factual_pairs"] += 1
                a_status = occurrence_status.get(a_id, "uncovered")
                b_status = occurrence_status.get(b_id, "uncovered")
                if a_status == "exact" and b_status == "exact":
                    status = "exact"
                    pair_counts["position_exact"] += 1
                elif "mismatch" in (a_status, b_status):
                    status = "mismatch"
                    pair_counts["position_mismatch"] += 1
                else:
                    status = "uncovered"
                    pair_counts["position_uncovered"] += 1
                site_pair_statuses.append(status)

            if site_pair_statuses and all(status == "exact" for status in site_pair_statuses):
                site_counts["all_factual_pairs_position_exact"] += 1
            if any(status == "mismatch" for status in site_pair_statuses):
                site_counts["has_position_mismatch"] += 1
            if any(status == "uncovered" for status in site_pair_statuses):
                site_counts["has_position_uncovered"] += 1

    summary = {
        "archives_considered": archives_considered,
        "special_game_591478_excluded": True,
        "payload_conflicts": payload_conflicts,
        "ship_occurrences": _serialize(occurrence_counts),
        "normal_prediction_reasons": _serialize(normal_reasons),
        "factual_pairs": _serialize(pair_counts),
        "sites": _serialize(site_counts),
    }
    return {
        "schema": "planets-lab.combat-host-normal-movement-position-audit.v2",
        "read_only": True,
        "summary": summary,
        "examples": examples,
        "evidence_boundary": (
            "Site-conditioned T-1 position differential for ordinary factual ship combatants. "
            "Factual VCR coordinates are comparison targets only and are never used to compute a ship endpoint. "
            "The normal-movement branch uses owner-current T-1 navigation, raw mass/fuel/components, canonical Host "
            "major/minor movement, Gravitonic distance, the strict existing raw-damage warp cap, and known warp-well "
            "state. Moving Tow/Intercept/C&I/HYP ships, Tow targets, obvious Chunnel source stacks, explicit cargo-transfer "
            "cases and sphere topology remain uncovered before ordinary geometry is attempted. Fuel proration is "
            "intentionally excluded in this first movement expansion. A mismatch is a movement-position residual to "
            "investigate before integrating the row into candidate-set prediction."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit T-1 stationary/normal-movement endpoint prediction against ordinary factual combat sites."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT NORMAL-MOVEMENT POSITION AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("MISMATCH EXAMPLES:")
    for row in report["examples"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: site-conditioned T-1 position gate; no factual T ship position is used as predictor input.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
