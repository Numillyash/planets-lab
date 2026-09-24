from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.core import GameState, Planet, Player
from planets_lab.corpus.feature_scope import DEFAULT_FEATURE_INDEX_PATH, load_feature_scope
from planets_lab.corpus.movement_differential import (
    _entity_map,
    _intish,
    _planet_tuples_by_turn,
    _settings_warp_well_state_by_turn,
)
from planets_lab.corpus.movement_mine_context import build_mine_evidence_context
from planets_lab.corpus.movement_residual_context import GRAVITONIC_HULL_IDS
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.data.nu_loadturn import NuLoadTurnError, _ship
from planets_lab.sim import (
    HostEngine,
    InterceptMovementPhase,
    NormalMovementPhase,
    TowMovementPhase,
    TurnOrders,
)

import combat_host_capture_continuation_audit as capture_module
from combat_host_candidate_set_audit import _owner_rows_for_turn
from combat_host_candidate_set_v2_audit import _foreign_mine_route_risk
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_normal_movement_position_audit import (
    _archive_nuionstorms_consensus,
    _inbound_transfer_targets,
    _nonzero_transfer_amount,
)
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR, _static_specs


SCHEMA = "planets-lab.combat-host-post-capture-special-movement-audit.v2"
DEFAULT_EXAMPLE_LIMIT = 40
TOW_MISSION_ID = 6
INTERCEPT_MISSION_ID = 7
SUPPORTED_SPECIAL_MISSIONS = frozenset({TOW_MISSION_ID, INTERCEPT_MISSION_ID})
TRANSFER_FIELDS = (
    ("transferneutronium", "neutronium"),
    ("transferduranium", "duranium"),
    ("transfertritanium", "tritanium"),
    ("transfermolybdenum", "molybdenum"),
    ("transfersupplies", "supplies"),
    ("transferclans", "clans"),
    ("transfermegacredits", "megacredits"),
)
BULK_CARGO_FIELDS = frozenset(
    {"duranium", "tritanium", "molybdenum", "supplies", "clans"}
)


def _capture_ship_rows(
    capture_report: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    rows = capture_report.get("examples")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return []
    return [
        row
        for row in rows
        if isinstance(row, Mapping)
        and row.get("status") == "capture_continuation"
        and row.get("current_opponent_is_planet") is False
    ]


def _special_movement_kind(raw: Mapping[str, Any]) -> str | None:
    mission = _intish(raw.get("mission"))
    if mission == TOW_MISSION_ID:
        return "tow"
    if mission == INTERCEPT_MISSION_ID:
        return "intercept"
    return None


def _strict_same_owner_ship_transfer(
    *,
    sender_id: int,
    sender_owner_id: int,
    sender_raw: Mapping[str, Any],
    owner_rows: Mapping[int, tuple[int, Mapping[str, Any]]],
    specs: Any,
) -> dict[str, Any]:
    amounts: dict[str, int] = {}
    malformed: list[str] = []
    for raw_field, cargo_field in TRANSFER_FIELDS:
        value = _intish(sender_raw.get(raw_field))
        if value is None:
            if sender_raw.get(raw_field) not in (None, "", 0, "0"):
                malformed.append(raw_field)
            continue
        if value < 0:
            malformed.append(raw_field)
        elif value > 0:
            amounts[cargo_field] = int(value)

    projection: dict[str, Any] = {
        "sender_ship_id": sender_id,
        "sender_owner_id": sender_owner_id,
        "target_id": _intish(sender_raw.get("transfertargetid")),
        "target_type_raw": _intish(sender_raw.get("transfertargettype")),
        "amounts": dict(sorted(amounts.items())),
        "applicable": False,
        "reason": None,
    }
    if malformed:
        projection["reason"] = "transfer_amount_malformed"
        projection["malformed_fields"] = sorted(malformed)
        return projection
    if not amounts:
        projection["reason"] = "no_outbound_transfer"
        return projection

    target_id = projection["target_id"]
    if isinstance(target_id, bool) or not isinstance(target_id, int) or target_id <= 0:
        projection["reason"] = "transfer_target_id_missing"
        return projection
    if target_id == sender_id:
        projection["reason"] = "transfer_target_self"
        return projection

    receiver_entry = owner_rows.get(target_id)
    if receiver_entry is None:
        projection["reason"] = "transfer_target_ship_not_current_visible"
        return projection
    receiver_owner_id, receiver_raw = receiver_entry
    projection["receiver_owner_id"] = int(receiver_owner_id)
    if int(receiver_owner_id) != sender_owner_id:
        projection["reason"] = "foreign_ship_transfer_not_integrated"
        return projection

    sender_x = _intish(sender_raw.get("x"))
    sender_y = _intish(sender_raw.get("y"))
    receiver_x = _intish(receiver_raw.get("x"))
    receiver_y = _intish(receiver_raw.get("y"))
    projection["sender_position"] = [sender_x, sender_y]
    projection["receiver_position"] = [receiver_x, receiver_y]
    if None in (sender_x, sender_y, receiver_x, receiver_y):
        projection["reason"] = "transfer_position_unresolved"
        return projection
    if (sender_x, sender_y) != (receiver_x, receiver_y):
        projection["reason"] = "transfer_target_not_colocated"
        return projection

    sender_before: dict[str, int] = {}
    receiver_before: dict[str, int] = {}
    for _raw_field, cargo_field in TRANSFER_FIELDS:
        sender_value = _intish(sender_raw.get(cargo_field))
        receiver_value = _intish(receiver_raw.get(cargo_field))
        if sender_value is None or sender_value < 0:
            projection["reason"] = f"sender_{cargo_field}_unresolved"
            return projection
        if receiver_value is None or receiver_value < 0:
            projection["reason"] = f"receiver_{cargo_field}_unresolved"
            return projection
        sender_before[cargo_field] = int(sender_value)
        receiver_before[cargo_field] = int(receiver_value)

    for cargo_field, amount in amounts.items():
        if amount > sender_before[cargo_field]:
            projection["reason"] = f"sender_{cargo_field}_insufficient"
            return projection

    receiver_hull_id = _intish(
        receiver_raw.get("hullid", receiver_raw.get("hull_id"))
    )
    hull = specs.hulls.get(receiver_hull_id) if receiver_hull_id is not None else None
    if hull is None:
        projection["reason"] = "receiver_hull_unresolved"
        return projection

    resulting_fuel = receiver_before["neutronium"] + amounts.get("neutronium", 0)
    if resulting_fuel > hull.fuel_tank:
        projection["reason"] = "receiver_fuel_capacity_exceeded"
        return projection

    resulting_bulk = sum(receiver_before[name] for name in BULK_CARGO_FIELDS) + sum(
        amounts.get(name, 0) for name in BULK_CARGO_FIELDS
    )
    if resulting_bulk > hull.cargo_capacity:
        projection["reason"] = "receiver_bulk_capacity_exceeded"
        return projection

    projection.update(
        {
            "receiver_ship_id": int(target_id),
            "receiver_hull_id": int(receiver_hull_id),
            "sender_before": sender_before,
            "receiver_before": receiver_before,
            "receiver_fuel_tank": int(hull.fuel_tank),
            "receiver_cargo_capacity": int(hull.cargo_capacity),
            "applicable": True,
            "reason": "strict_same_owner_ship_transfer",
        }
    )
    return projection


def _apply_transfer_projection(
    state: GameState,
    projection: Mapping[str, Any],
) -> None:
    if projection.get("applicable") is not True:
        raise ValueError("transfer projection is not applicable")
    sender_id = int(projection["sender_ship_id"])
    receiver_id = int(projection["receiver_ship_id"])
    amounts = projection.get("amounts")
    if not isinstance(amounts, Mapping):
        raise ValueError("transfer projection amounts missing")

    sender = state.ships[sender_id]
    receiver = state.ships[receiver_id]
    for cargo_field, raw_amount in amounts.items():
        amount = int(raw_amount)
        setattr(sender.cargo, cargo_field, getattr(sender.cargo, cargo_field) - amount)
        setattr(receiver.cargo, cargo_field, getattr(receiver.cargo, cargo_field) + amount)


def _event_dict(event: Any) -> dict[str, Any]:
    details = {}
    for key, value in getattr(event, "details", ()):
        details[str(key)] = str(value)
    return {
        "phase": getattr(event, "phase", None),
        "kind": getattr(event, "kind", None),
        "entity_id": getattr(event, "entity_id", None),
        "details": details,
    }


def _build_state(
    *,
    game_id: int,
    before_turn: int,
    owner_rows: Mapping[int, tuple[int, Mapping[str, Any]]],
    planets: Sequence[tuple[int, int, int]],
) -> tuple[GameState | None, tuple[str, ...]]:
    ships = {}
    failures: list[str] = []
    for ship_id, (_owner_id, raw) in sorted(owner_rows.items()):
        try:
            ship = _ship(raw)
        except (NuLoadTurnError, KeyError, TypeError, ValueError) as exc:
            failures.append(f"ship_{ship_id}:{type(exc).__name__}:{exc}")
            continue
        ships[int(ship_id)] = ship

    if failures:
        return None, tuple(failures)

    players = {
        int(ship.owner_id): Player(id=int(ship.owner_id))
        for ship in ships.values()
        if ship.owner_id is not None and int(ship.owner_id) > 0
    }
    state = GameState(
        game_id=game_id,
        turn=before_turn,
        players=players,
        planets={
            int(planet_id): Planet(id=int(planet_id), x=int(x), y=int(y))
            for planet_id, x, y in planets
        },
        ships=ships,
    )
    try:
        state.validate()
    except ValueError as exc:
        return None, (f"state_validate:{exc}",)
    return state, ()


def _preflight_subject(
    *,
    subject_id: int,
    subject_owner_id: int,
    subject_raw: Mapping[str, Any],
    owner_rows: Mapping[int, tuple[int, Mapping[str, Any]]],
    before_turn: int,
    races: Mapping[int, int],
    mine_context: Any,
) -> tuple[str, ...]:
    issues: list[str] = []

    if _nonzero_transfer_amount(subject_raw):
        issues.append("subject_outbound_transfer")
    inbound = _inbound_transfer_targets(owner_rows)
    if subject_id in inbound:
        issues.append("subject_inbound_transfer")

    fc = subject_raw.get("friendlycode")
    if isinstance(fc, str) and fc.strip().lower() == "mkt":
        issues.append("subject_pre_move_mkt_mass_change")

    hull_id = _intish(subject_raw.get("hullid", subject_raw.get("hull_id")))
    race_id = races.get(subject_owner_id)
    mine_risk = _foreign_mine_route_risk(
        context=mine_context,
        before_turn=before_turn,
        owner_id=subject_owner_id,
        raw=subject_raw,
        race_id=race_id,
        hull_id=hull_id,
    )
    if mine_risk is not None:
        issues.append(f"subject_{mine_risk}")

    return tuple(issues)


def _simulate_special_subject(
    *,
    game_id: int,
    battle_turn: int,
    site: tuple[int, int],
    subject_id: int,
    subject_owner_id: int,
    subject_raw: Mapping[str, Any],
    owner_rows: Mapping[int, tuple[int, Mapping[str, Any]]],
    specs: Any,
    planets: Sequence[tuple[int, int, int]],
    warp_wells_enabled: bool | None,
    eligible_warp_well_planet_ids: frozenset[int] | None,
    races: Mapping[int, int],
    mine_context: Any,
) -> dict[str, Any]:
    kind = _special_movement_kind(subject_raw)
    if kind is None:
        return {
            "status": "not_applicable",
            "reason": "opponent_not_tow_or_intercept",
        }

    before_turn = battle_turn - 1
    preflight = list(
        _preflight_subject(
            subject_id=subject_id,
            subject_owner_id=subject_owner_id,
            subject_raw=subject_raw,
            owner_rows=owner_rows,
            before_turn=before_turn,
            races=races,
            mine_context=mine_context,
        )
    )

    mission_target_id = _intish(subject_raw.get("mission1target"))
    target_transfer: dict[str, Any] | None = None
    if mission_target_id is None or mission_target_id <= 0:
        preflight.append("subject_mission_target_missing")
    elif mission_target_id not in owner_rows:
        preflight.append("subject_mission_target_owner_record_missing")
    else:
        target_owner_id, target_raw = owner_rows[mission_target_id]
        if _nonzero_transfer_amount(target_raw):
            target_transfer = _strict_same_owner_ship_transfer(
                sender_id=int(mission_target_id),
                sender_owner_id=int(target_owner_id),
                sender_raw=target_raw,
                owner_rows=owner_rows,
                specs=specs,
            )
            if target_transfer.get("applicable") is not True:
                preflight.append("target_outbound_transfer_unresolved")
        inbound = _inbound_transfer_targets(owner_rows)
        if mission_target_id in inbound:
            preflight.append("target_inbound_transfer")
        target_fc = target_raw.get("friendlycode")
        if kind == "intercept" and isinstance(target_fc, str) and target_fc.strip().lower() == "hyp":
            preflight.append("intercept_target_hyp_not_integrated")
        target_hull_id = _intish(target_raw.get("hullid", target_raw.get("hull_id")))
        target_mine_risk = _foreign_mine_route_risk(
            context=mine_context,
            before_turn=before_turn,
            owner_id=int(target_owner_id),
            raw=target_raw,
            race_id=races.get(int(target_owner_id)),
            hull_id=target_hull_id,
        )
        if target_mine_risk is not None:
            preflight.append(f"target_{target_mine_risk}")

    if warp_wells_enabled is None:
        preflight.append("warp_well_setting_unresolved")
    elif warp_wells_enabled is True and eligible_warp_well_planet_ids is None:
        preflight.append("warp_well_eligibility_unresolved")

    if preflight:
        return {
            "status": "unresolved",
            "movement_kind": kind,
            "mission_target_id": mission_target_id,
            "target_outbound_transfer": target_transfer,
            "preflight_issues": sorted(set(preflight)),
        }

    state, state_issues = _build_state(
        game_id=game_id,
        before_turn=before_turn,
        owner_rows=owner_rows,
        planets=planets,
    )
    if state is None:
        return {
            "status": "unresolved",
            "movement_kind": kind,
            "mission_target_id": mission_target_id,
            "target_outbound_transfer": target_transfer,
            "preflight_issues": list(state_issues),
        }

    if target_transfer is not None and target_transfer.get("applicable") is True:
        try:
            _apply_transfer_projection(state, target_transfer)
        except (KeyError, TypeError, ValueError) as exc:
            return {
                "status": "unresolved",
                "movement_kind": kind,
                "mission_target_id": mission_target_id,
                "target_outbound_transfer": target_transfer,
                "preflight_issues": [
                    f"target_outbound_transfer_apply:{type(exc).__name__}:{exc}"
                ],
            }

    all_planet_ids = frozenset(int(planet_id) for planet_id, _x, _y in planets)
    excluded_well_ids = (
        all_planet_ids.difference(eligible_warp_well_planet_ids or frozenset())
        if warp_wells_enabled is True
        else frozenset()
    )

    engine = HostEngine(
        (
            TowMovementPhase(
                specs=specs,
                gravitonic_hull_ids=GRAVITONIC_HULL_IDS,
                enable_expanded_movement=True,
                enable_warp_wells=warp_wells_enabled is True,
                excluded_warp_well_planet_ids=excluded_well_ids,
                allow_deferred=True,
            ),
            NormalMovementPhase(
                specs=specs,
                gravitonic_hull_ids=GRAVITONIC_HULL_IDS,
                allow_deferred=True,
                enable_expanded_movement=True,
                enable_warp_wells=warp_wells_enabled is True,
                non_warp_well_planet_ids=excluded_well_ids,
            ),
            InterceptMovementPhase(
                specs=specs,
                gravitonic_hull_ids=GRAVITONIC_HULL_IDS,
                allow_deferred=True,
                enable_expanded_movement=True,
                enable_warp_wells=warp_wells_enabled is True,
                non_warp_well_planet_ids=excluded_well_ids,
            ),
        )
    )

    try:
        next_state, events = engine.step(state, TurnOrders.empty())
    except Exception as exc:  # diagnostic must preserve the concrete unsupported boundary
        return {
            "status": "unresolved",
            "movement_kind": kind,
            "mission_target_id": mission_target_id,
            "target_outbound_transfer": target_transfer,
            "preflight_issues": [
                f"movement_pipeline:{type(exc).__name__}:{exc}",
            ],
        }

    subject = next_state.ships.get(subject_id)
    if subject is None:
        return {
            "status": "unresolved",
            "movement_kind": kind,
            "mission_target_id": mission_target_id,
            "target_outbound_transfer": target_transfer,
            "preflight_issues": ["subject_missing_after_pipeline"],
        }

    predicted = (int(subject.x), int(subject.y))
    exact = predicted == site
    relevant_ids = {subject_id}
    if mission_target_id is not None and mission_target_id > 0:
        relevant_ids.add(mission_target_id)
    if (
        target_transfer is not None
        and isinstance(target_transfer.get("receiver_ship_id"), int)
    ):
        relevant_ids.add(int(target_transfer["receiver_ship_id"]))

    return {
        "status": "exact" if exact else "mismatch",
        "movement_kind": kind,
        "mission_target_id": mission_target_id,
        "target_outbound_transfer": target_transfer,
        "origin": [
            _intish(subject_raw.get("x")),
            _intish(subject_raw.get("y")),
        ],
        "waypoint": [
            _intish(subject_raw.get("targetx")),
            _intish(subject_raw.get("targety")),
        ],
        "warp": _intish(subject_raw.get("warp")),
        "predicted_position": list(predicted),
        "factual_site": list(site),
        "events": [
            _event_dict(event)
            for event in events
            if getattr(event, "entity_id", None) in relevant_ids
        ],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    feature_scope = load_feature_scope(
        args.feature_index,
        profile=args.scope_profile,
    )
    selected = set(feature_scope.selected_ids)

    capture_report = capture_module.run(
        argparse.Namespace(
            archive_dir=args.archive_dir,
            feature_index=args.feature_index,
            scope_profile=args.scope_profile,
            example_limit=10000,
            output=None,
        )
    )
    capture_rows = _capture_ship_rows(capture_report)

    by_game: dict[int, list[Mapping[str, Any]]] = {}
    for row in capture_rows:
        game_id = int(row["game_id"])
        if game_id in selected:
            by_game.setdefault(game_id, []).append(row)

    counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []

    for game_id, rows in sorted(by_game.items()):
        archive_path = args.archive_dir / f"game-{game_id}.zip"
        archive_data = archive_path.read_bytes()
        prepared, _ = load_or_build_prepared_game_cache(
            archive_data,
            game_id=game_id,
            cache_path=args.prepared_dir / f"game-{game_id}.pickle",
        )
        ship_groups = group_perspective_records(prepared.snapshots, "ship")
        races, _ = _player_races(prepared.snapshots)
        specs = _static_specs(archive_data)
        entities = _entity_map(prepared.snapshots)
        planets_by_turn = _planet_tuples_by_turn(entities, include_ineligible=True)
        warp_wells_by_turn, _ = _settings_warp_well_state_by_turn(prepared.snapshots)
        eligible_by_turn = getattr(entities, "warp_well_planet_ids_by_turn", {})
        mine_context = build_mine_evidence_context(
            game_id=game_id,
            archive_data=archive_data,
            snapshots=prepared.snapshots,
        )
        # Read once to keep the raw game-mode dependency visible in evidence.
        nuionstorms, raw_nuionstorms = _archive_nuionstorms_consensus(archive_data)

        owner_rows_by_turn: dict[int, dict[int, tuple[int, Mapping[str, Any]]]] = {}

        for capture in sorted(
            rows,
            key=lambda row: (
                int(row["turn"]),
                int(row["from_vcr_id"]),
                int(row["to_vcr_id"]),
            ),
        ):
            battle_turn = int(capture["turn"])
            before_turn = battle_turn - 1
            opponent_id = capture.get("current_opponent_ship_id")
            if isinstance(opponent_id, bool) or not isinstance(opponent_id, int) or opponent_id <= 0:
                counts["unresolved:factual_opponent_missing"] += 1
                continue

            if before_turn not in owner_rows_by_turn:
                owner_rows_by_turn[before_turn] = _owner_rows_for_turn(ship_groups, before_turn)
            owner_rows = owner_rows_by_turn[before_turn]
            opponent_entry = owner_rows.get(opponent_id)
            if opponent_entry is None:
                counts["unresolved:opponent_owner_record_missing"] += 1
                continue
            opponent_owner_id, opponent_raw = opponent_entry
            kind = _special_movement_kind(opponent_raw)
            if kind is None:
                counts["ordinary_opponent"] += 1
                continue

            counts["special_movement_opponent"] += 1
            counts[f"special_kind:{kind}"] += 1
            site_raw = capture.get("position")
            if (
                not isinstance(site_raw, Sequence)
                or isinstance(site_raw, (str, bytes))
                or len(site_raw) != 2
            ):
                counts["unresolved:site_missing"] += 1
                continue
            site = (int(site_raw[0]), int(site_raw[1]))

            eligible_raw = eligible_by_turn.get(before_turn)
            eligible_ids = (
                frozenset(int(value) for value in eligible_raw)
                if eligible_raw is not None
                else None
            )
            result = _simulate_special_subject(
                game_id=game_id,
                battle_turn=battle_turn,
                site=site,
                subject_id=opponent_id,
                subject_owner_id=int(opponent_owner_id),
                subject_raw=opponent_raw,
                owner_rows=owner_rows,
                specs=specs,
                planets=tuple(planets_by_turn.get(before_turn, ())),
                warp_wells_enabled=warp_wells_by_turn.get(before_turn),
                eligible_warp_well_planet_ids=eligible_ids,
                races=races,
                mine_context=mine_context,
            )
            status = str(result.get("status", "unresolved"))
            counts[f"status:{status}"] += 1
            if len(examples) < args.example_limit:
                examples.append(
                    {
                        "game_id": game_id,
                        "battle_turn": battle_turn,
                        "captured_ship_id": int(capture["ship_id"]),
                        "from_vcr_id": int(capture["from_vcr_id"]),
                        "to_vcr_id": int(capture["to_vcr_id"]),
                        "opponent_ship_id": opponent_id,
                        "opponent_owner_id": int(opponent_owner_id),
                        "opponent_mission": _intish(opponent_raw.get("mission")),
                        "opponent_enemy": _intish(opponent_raw.get("enemy")),
                        "opponent_friendlycode": opponent_raw.get("friendlycode"),
                        "nuionstorms": nuionstorms,
                        "raw_nuionstorms": list(raw_nuionstorms),
                        "result": result,
                    }
                )

    special_population = int(counts["special_movement_opponent"])
    acceptance = {
        "special_movement_population_present": special_population > 0,
        "all_special_movement_positions_exact": (
            special_population > 0
            and int(counts["status:exact"]) == special_population
            and int(counts["status:mismatch"]) == 0
            and int(counts["status:unresolved"]) == 0
        ),
    }
    acceptance["special_movement_gate_passed"] = all(acceptance.values())

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "feature_scope": feature_scope.to_dict(),
            "counts": dict(sorted(counts.items())),
            "acceptance": acceptance,
        },
        "examples": examples,
        "evidence_boundary": (
            "Read-only bridge diagnostic for ship post-capture continuations whose "
            "factual next opponent is absent from the ordinary per-ship position "
            "adapter solely because its T-1 mission is Tow or Intercept. It builds "
            "owner-current T-1 GameState and runs the existing production movement "
            "phases in Host order Tow -> Move Most -> Intercept. A target-side "
            "outbound transfer is applied only as a bounded hypothesis when it is "
            "a fully observable co-located same-owner ship transfer with sufficient "
            "sender cargo and receiver capacity; foreign/ambiguous transfers, MKT "
            "mass changes, mine-risk routes, unresolved warp-well context and HYP "
            "intercept targets fail closed. Factual combat-site coordinates are "
            "used only as the held-out comparator. This diagnostic does not alter "
            "combat selection and does not yet claim full movement-pipeline closure "
            "for ion-storm/chunnel/special-movement combinations."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare production Tow/Move Most/Intercept positions with the "
            "post-capture factual combat site for special-movement opponents."
        )
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--feature-index", type=Path, default=DEFAULT_FEATURE_INDEX_PATH)
    parser.add_argument("--scope-profile", default="combat-planar-no-horwasp")
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT POST-CAPTURE SPECIAL MOVEMENT AUDIT =====")
    print("summary:", report["summary"])
    if report["examples"]:
        print()
        print("EXAMPLES:")
        for row in report["examples"]:
            print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("output:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
