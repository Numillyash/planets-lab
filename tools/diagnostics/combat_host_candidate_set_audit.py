from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.combat.order import (
    CLOAK_INTERCEPT_MISSION_ID,
    INTERCEPT_MISSION_ID,
    orders_request_ship_combat,
)
from planets_lab.rules.combat.selection import ShipCombatSideInput, decide_ship_combat_pair

from combat_host_factual_queue_selection_audit import (
    _build_start_stack_index,
    _c_and_i_inputs,
    _decision_projection,
    _galactic_power_state,
    _hwm_state,
    _interference_state,
)
from combat_host_matching_fc_suppression_audit import (
    RelationSignature,
    _relation_inventory,
    _relation_signature,
    _safe_signature,
    _unique_relation_signature,
)
from combat_host_mission20_cloak_intercept_audit import _player_races
from combat_host_mission7_matched_control_audit import _dedup_vcrs
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    SPECIAL_GAME_ID,
    _int,
    _owner_raw,
    _ship_side,
    _static_specs,
)
from combat_host_residual_physical_stack_audit import _xy


DEFAULT_EXAMPLE_LIMIT = 60
TOW_MISSION_ID = 6
FIRECLOUD_HULL_ID = 56


def _pair(a: int, b: int) -> tuple[int, int]:
    return tuple(sorted((int(a), int(b))))


def _serialize(counter: Counter[Any]) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    }


def _request_direction(owner_id: int, opponent_owner_id: int) -> str:
    low = min(owner_id, opponent_owner_id)
    return "low_to_high" if owner_id == low else "high_to_low"


def _requests_combat(raw: Mapping[str, Any], opponent_owner_id: int) -> bool:
    return orders_request_ship_combat(
        mission=_intish(raw.get("mission")),
        primary_enemy=_intish(raw.get("enemy")),
        opponent_owner_id=opponent_owner_id,
    )


def _owner_rows_for_turn(
    ship_groups: Mapping[tuple[int, int], Sequence[Any]],
    turn: int,
) -> dict[int, tuple[int, Mapping[str, Any]]]:
    rows: dict[int, tuple[int, Mapping[str, Any]]] = {}
    for grouped_turn, ship_id in sorted(ship_groups):
        if grouped_turn != turn:
            continue
        owner_id, raw = _owner_raw(ship_groups, turn, ship_id)
        if owner_id is None or owner_id <= 0 or raw is None:
            continue
        rows[int(ship_id)] = (int(owner_id), raw)
    return rows


def _tow_target_ids(rows: Mapping[int, tuple[int, Mapping[str, Any]]]) -> frozenset[int]:
    targets: set[int] = set()
    for _ship_id, (_owner_id, raw) in rows.items():
        if _intish(raw.get("mission")) != TOW_MISSION_ID:
            continue
        target_id = _intish(raw.get("mission1target"))
        if target_id is not None and target_id > 0:
            targets.add(target_id)
    return frozenset(targets)


def _potential_chunnel_source_sites(
    rows: Mapping[int, tuple[int, Mapping[str, Any]]],
) -> frozenset[tuple[int, int]]:
    """Return obvious ordinary Firecloud source coordinates, conservatively.

    This is not a full Chunnel resolver. It merely prevents the stationary v1
    candidate gate from treating a Warp-0 stack as position-proven when an
    owner-current Firecloud at that same location visibly names another
    Firecloud ship id through its three-digit FC.
    """

    firecloud_ids = {
        ship_id
        for ship_id, (_owner_id, raw) in rows.items()
        if _intish(raw.get("hullid", raw.get("hull_id"))) == FIRECLOUD_HULL_ID
    }
    sites: set[tuple[int, int]] = set()
    for ship_id in firecloud_ids:
        _owner_id, raw = rows[ship_id]
        fc = raw.get("friendlycode")
        if not isinstance(fc, str) or len(fc) != 3 or not fc.isdigit():
            continue
        target_id = int(fc)
        if target_id <= 0 or target_id == ship_id or target_id not in firecloud_ids:
            continue
        xy = _xy(raw)
        if xy[0] is not None and xy[1] is not None:
            sites.add((int(xy[0]), int(xy[1])))
    return frozenset(sites)


def _intrinsic_stationary_reason(
    *,
    ship_id: int,
    raw: Mapping[str, Any],
    tow_targets: frozenset[int],
    chunnel_source_sites: frozenset[tuple[int, int]],
) -> str | None:
    """Return None only for the conservative T-1 stationary-position scope."""

    warp = _intish(raw.get("warp"))
    if warp is None:
        return "warp_unknown"
    if warp != 0:
        return "self_movement_possible"

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


def _fuel_input(raw: Mapping[str, Any]) -> bool | None:
    """Return only a positive-fuel fact that is safe enough for this v1 gate.

    T-1 zero fuel is not treated as a combat blocker because transfers and other
    pre-combat Host phases are not reconstructed here. Positive fuel on an
    intrinsically stationary ship is used as a positive fact; any later drain
    can only create extra eligible candidates, not a hard false-negative claim.
    """

    fuel = _intish(raw.get("neutronium"))
    if fuel is None or fuel <= 0:
        return None
    return True


def _candidate_input(
    *,
    game_id: int,
    ship_id: int,
    owner_id: int,
    raw: Mapping[str, Any],
    race_id: int | None,
    hull_id: int | None,
    hull_can_cloak: bool | None,
    diplomacy_allows_attack: bool | None,
    interference_protected: bool | None,
) -> ShipCombatSideInput:
    mission = _intish(raw.get("mission"))
    c_and_i_enabled, c_and_i_hull_eligible, active_cloak = _c_and_i_inputs(
        race_id=race_id,
        mission=mission,
    )
    return ShipCombatSideInput(
        ship_id=ship_id,
        owner_id=owner_id,
        race_id=race_id,
        hull_id=hull_id,
        mission=mission,
        mission_target_id=_intish(raw.get("mission1target")),
        primary_enemy=_intish(raw.get("enemy")),
        friendly_code=raw.get("friendlycode"),
        hull_can_cloak=hull_can_cloak,
        has_fuel=_fuel_input(raw),
        diplomacy_allows_attack=diplomacy_allows_attack,
        harmonic_weapon_modulation_enabled=_hwm_state(race_id),
        cloak_and_intercept_enabled=c_and_i_enabled,
        cloak_and_intercept_hull_eligible=c_and_i_hull_eligible,
        active_cloak_at_intercept=active_cloak,
        intercept_interference_protected=interference_protected,
        galactic_power_enabled=(
            _galactic_power_state(game_id=game_id, race_id=race_id, hull_id=hull_id)
            if hull_id is not None
            else None
        ),
    )


def _build_independent_controls(
    *,
    game_id: int,
    seen: Mapping[Any, Any],
    ship_groups: Mapping[tuple[int, int], Sequence[Any]],
    relations: Mapping[int, Any],
) -> Mapping[tuple[RelationSignature, str], set[tuple[int, int, tuple[int, int]]]]:
    """Build directed diplomacy controls from other factual engagements.

    A control contributes only when exactly one T-1 Kill!/PE direction requests
    combat. Candidate evaluation later removes every VCR belonging to the exact
    candidate pair at the current site, so a factual pair never proves its own
    directed permission. Owner-current T-1 owners must match factual VCR owners,
    excluding capture/reinsertion rows from the calibration population.
    """

    controls: dict[
        tuple[RelationSignature, str], set[tuple[int, int, tuple[int, int]]]
    ] = defaultdict(set)
    for (seen_game, battle_turn, vcr_id), (_digest, vcr) in sorted(seen.items()):
        if seen_game != game_id:
            continue
        left = _ship_side(vcr, "left")
        right = _ship_side(vcr, "right")
        if left is None or right is None:
            continue
        left_id = int(left["ship_id"])
        right_id = int(right["ship_id"])
        before_turn = int(battle_turn) - 1
        left_owner, left_raw = _owner_raw(ship_groups, before_turn, left_id)
        right_owner, right_raw = _owner_raw(ship_groups, before_turn, right_id)
        if (
            left_owner is None
            or right_owner is None
            or left_owner <= 0
            or right_owner <= 0
            or left_owner == right_owner
            or left_raw is None
            or right_raw is None
        ):
            continue
        if left_owner != left.get("owner_id") or right_owner != right.get("owner_id"):
            continue
        signature = _relation_signature(relations.get(before_turn, {}), left_owner, right_owner)
        if not _unique_relation_signature(signature):
            continue
        left_request = _requests_combat(left_raw, right_owner)
        right_request = _requests_combat(right_raw, left_owner)
        if left_request == right_request:
            continue
        owner = left_owner if left_request else right_owner
        opponent = right_owner if left_request else left_owner
        direction = _request_direction(owner, opponent)
        controls[(signature, direction)].add(
            (int(battle_turn), int(vcr_id), _pair(left_id, right_id))
        )
    return controls


def _independent_permission(
    *,
    request: bool,
    owner_id: int,
    opponent_owner_id: int,
    signature: RelationSignature,
    controls: Mapping[tuple[RelationSignature, str], set[tuple[int, int, tuple[int, int]]]],
    excluded_rows: frozenset[tuple[int, int, tuple[int, int]]],
) -> bool | None:
    if not request:
        return False
    if not _unique_relation_signature(signature):
        return None
    direction = _request_direction(owner_id, opponent_owner_id)
    usable = controls.get((signature, direction), set()) - set(excluded_rows)
    return True if usable else None


def _factual_sites(
    *,
    game_id: int,
    seen: Mapping[Any, Any],
) -> dict[tuple[int, int, int], dict[str, Any]]:
    sites: dict[tuple[int, int, int], dict[str, Any]] = {}
    for (seen_game, battle_turn, vcr_id), (_digest, vcr) in sorted(seen.items()):
        if seen_game != game_id:
            continue
        left = _ship_side(vcr, "left")
        right = _ship_side(vcr, "right")
        x = _int(vcr, "x")
        y = _int(vcr, "y")
        if left is None or right is None or x is None or y is None:
            continue
        key = (int(battle_turn), int(x), int(y))
        site = sites.setdefault(
            key,
            {"vcr_ids": [], "pairs": set(), "pair_rows": defaultdict(set)},
        )
        pair = _pair(int(left["ship_id"]), int(right["ship_id"]))
        site["vcr_ids"].append(int(vcr_id))
        site["pairs"].add(pair)
        site["pair_rows"][pair].add((int(battle_turn), int(vcr_id), pair))
    return sites


def _scope_summary(rows: Sequence[Mapping[str, Any]], profile: str) -> dict[str, Any]:
    status = Counter()
    factual_status = Counter()
    for row in rows:
        decision = row[profile]
        value = decision.get("engagement_eligible")
        label = "eligible" if value is True else ("blocked" if value is False else "unresolved")
        status[label] += 1
        if row["factual_pair"]:
            factual_status[label] += 1
    return {
        "candidate_pairs": len(rows),
        "status": _serialize(status),
        "factual_pair_status": _serialize(factual_status),
        "eligible_nonfactual": sum(
            1
            for row in rows
            if row[profile].get("engagement_eligible") is True and not row["factual_pair"]
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    archives_considered = 0
    payload_conflicts = 0
    all_candidate_rows: list[dict[str, Any]] = []
    site_reports: list[dict[str, Any]] = []
    movement_uncovered_reasons: Counter[str] = Counter()
    factual_pair_counts = Counter()

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
        relations = _relation_inventory(archive_data)
        start_stacks = _build_start_stack_index(ship_groups)
        seen, conflicts = _dedup_vcrs(archive_data)
        payload_conflicts += conflicts

        sites = _factual_sites(game_id=game_id, seen=seen)
        controls = _build_independent_controls(
            game_id=game_id,
            seen=seen,
            ship_groups=ship_groups,
            relations=relations,
        )
        rows_by_turn: dict[int, dict[int, tuple[int, Mapping[str, Any]]]] = {}
        tow_targets_by_turn: dict[int, frozenset[int]] = {}
        chunnel_sites_by_turn: dict[int, frozenset[tuple[int, int]]] = {}

        for (battle_turn, x, y), factual in sorted(sites.items()):
            before_turn = battle_turn - 1
            if before_turn not in rows_by_turn:
                owner_rows = _owner_rows_for_turn(ship_groups, before_turn)
                rows_by_turn[before_turn] = owner_rows
                tow_targets_by_turn[before_turn] = _tow_target_ids(owner_rows)
                chunnel_sites_by_turn[before_turn] = _potential_chunnel_source_sites(owner_rows)
            owner_rows = rows_by_turn[before_turn]
            tow_targets = tow_targets_by_turn[before_turn]
            chunnel_sites = chunnel_sites_by_turn[before_turn]

            site_ship_rows: dict[int, dict[str, Any]] = {}
            for ship_id, (owner_id, raw) in owner_rows.items():
                sx, sy = _xy(raw)
                if sx is None or sy is None or (int(sx), int(sy)) != (x, y):
                    continue
                reason = _intrinsic_stationary_reason(
                    ship_id=ship_id,
                    raw=raw,
                    tow_targets=tow_targets,
                    chunnel_source_sites=chunnel_sites,
                )
                if reason is not None:
                    movement_uncovered_reasons[reason] += 1
                    continue
                hull_id = _intish(raw.get("hullid", raw.get("hull_id")))
                hull = specs.hulls.get(hull_id) if hull_id is not None else None
                site_ship_rows[ship_id] = {
                    "ship_id": ship_id,
                    "owner_id": owner_id,
                    "raw": raw,
                    "race_id": races.get(owner_id),
                    "hull_id": hull_id,
                    "hull_can_cloak": hull.can_cloak if hull is not None else None,
                    "fuel_input": _fuel_input(raw),
                }

            candidate_rows: list[dict[str, Any]] = []
            for a_id, b_id in combinations(sorted(site_ship_rows), 2):
                a = site_ship_rows[a_id]
                b = site_ship_rows[b_id]
                if a["owner_id"] == b["owner_id"]:
                    continue
                pair = _pair(a_id, b_id)
                signature = _relation_signature(
                    relations.get(before_turn, {}), int(a["owner_id"]), int(b["owner_id"])
                )
                a_request = _requests_combat(a["raw"], int(b["owner_id"]))
                b_request = _requests_combat(b["raw"], int(a["owner_id"]))
                excluded = frozenset(factual["pair_rows"].get(pair, set()))
                a_strict = _independent_permission(
                    request=a_request,
                    owner_id=int(a["owner_id"]),
                    opponent_owner_id=int(b["owner_id"]),
                    signature=signature,
                    controls=controls,
                    excluded_rows=excluded,
                )
                b_strict = _independent_permission(
                    request=b_request,
                    owner_id=int(b["owner_id"]),
                    opponent_owner_id=int(a["owner_id"]),
                    signature=signature,
                    controls=controls,
                    excluded_rows=excluded,
                )

                a_interference = _interference_state(
                    game_id=game_id,
                    before_turn=before_turn,
                    owner_id=int(a["owner_id"]),
                    raw=a["raw"],
                    start_stacks=start_stacks,
                )
                b_interference = _interference_state(
                    game_id=game_id,
                    before_turn=before_turn,
                    owner_id=int(b["owner_id"]),
                    raw=b["raw"],
                    start_stacks=start_stacks,
                )

                strict_a_input = _candidate_input(
                    game_id=game_id,
                    ship_id=a_id,
                    owner_id=int(a["owner_id"]),
                    raw=a["raw"],
                    race_id=a["race_id"],
                    hull_id=a["hull_id"],
                    hull_can_cloak=a["hull_can_cloak"],
                    diplomacy_allows_attack=a_strict,
                    interference_protected=a_interference,
                )
                strict_b_input = _candidate_input(
                    game_id=game_id,
                    ship_id=b_id,
                    owner_id=int(b["owner_id"]),
                    raw=b["raw"],
                    race_id=b["race_id"],
                    hull_id=b["hull_id"],
                    hull_can_cloak=b["hull_can_cloak"],
                    diplomacy_allows_attack=b_strict,
                    interference_protected=b_interference,
                )
                conditional_a_input = _candidate_input(
                    game_id=game_id,
                    ship_id=a_id,
                    owner_id=int(a["owner_id"]),
                    raw=a["raw"],
                    race_id=a["race_id"],
                    hull_id=a["hull_id"],
                    hull_can_cloak=a["hull_can_cloak"],
                    diplomacy_allows_attack=True if a_request else False,
                    interference_protected=a_interference,
                )
                conditional_b_input = _candidate_input(
                    game_id=game_id,
                    ship_id=b_id,
                    owner_id=int(b["owner_id"]),
                    raw=b["raw"],
                    race_id=b["race_id"],
                    hull_id=b["hull_id"],
                    hull_can_cloak=b["hull_can_cloak"],
                    diplomacy_allows_attack=True if b_request else False,
                    interference_protected=b_interference,
                )

                strict = _decision_projection(
                    decide_ship_combat_pair(
                        left=strict_a_input,
                        right=strict_b_input,
                        same_location=True,
                    )
                )
                conditional = _decision_projection(
                    decide_ship_combat_pair(
                        left=conditional_a_input,
                        right=conditional_b_input,
                        same_location=True,
                    )
                )
                row = {
                    "game_id": game_id,
                    "battle_turn": battle_turn,
                    "x": x,
                    "y": y,
                    "pair": list(pair),
                    "factual_pair": pair in factual["pairs"],
                    "relation_signature": _safe_signature(signature),
                    "left": {
                        "ship_id": a_id,
                        "owner_id": a["owner_id"],
                        "race_id": a["race_id"],
                        "hull_id": a["hull_id"],
                        "mission": _intish(a["raw"].get("mission")),
                        "mission1target": _intish(a["raw"].get("mission1target")),
                        "enemy": _intish(a["raw"].get("enemy")),
                        "friendlycode": a["raw"].get("friendlycode"),
                        "fuel_input": a["fuel_input"],
                        "strict_diplomacy_allows_attack": a_strict,
                    },
                    "right": {
                        "ship_id": b_id,
                        "owner_id": b["owner_id"],
                        "race_id": b["race_id"],
                        "hull_id": b["hull_id"],
                        "mission": _intish(b["raw"].get("mission")),
                        "mission1target": _intish(b["raw"].get("mission1target")),
                        "enemy": _intish(b["raw"].get("enemy")),
                        "friendlycode": b["raw"].get("friendlycode"),
                        "fuel_input": b["fuel_input"],
                        "strict_diplomacy_allows_attack": b_strict,
                    },
                    "strict": strict,
                    "conditional": conditional,
                }
                candidate_rows.append(row)
                all_candidate_rows.append(row)

            candidate_pairs = {tuple(row["pair"]) for row in candidate_rows}
            factual_pairs = set(factual["pairs"])
            covered_factual = factual_pairs & candidate_pairs
            uncovered_factual = factual_pairs - candidate_pairs
            factual_pair_counts["total"] += len(factual_pairs)
            factual_pair_counts["candidate_covered"] += len(covered_factual)
            factual_pair_counts["movement_uncovered"] += len(uncovered_factual)

            strict_eligible = {
                tuple(row["pair"])
                for row in candidate_rows
                if row["strict"].get("engagement_eligible") is True
            }
            strict_blocked = {
                tuple(row["pair"])
                for row in candidate_rows
                if row["strict"].get("engagement_eligible") is False
            }
            strict_unresolved = candidate_pairs - strict_eligible - strict_blocked
            conditional_eligible = {
                tuple(row["pair"])
                for row in candidate_rows
                if row["conditional"].get("engagement_eligible") is True
            }
            conditional_blocked = {
                tuple(row["pair"])
                for row in candidate_rows
                if row["conditional"].get("engagement_eligible") is False
            }
            conditional_unresolved = candidate_pairs - conditional_eligible - conditional_blocked

            all_factual_position_covered = factual_pairs <= candidate_pairs
            all_strict_resolved = not strict_unresolved
            all_conditional_resolved = not conditional_unresolved
            site_reports.append(
                {
                    "game_id": game_id,
                    "battle_turn": battle_turn,
                    "x": x,
                    "y": y,
                    "factual_vcr_ids": sorted(factual["vcr_ids"]),
                    "factual_pairs": [list(pair) for pair in sorted(factual_pairs)],
                    "intrinsic_stationary_ship_ids": sorted(site_ship_rows),
                    "candidate_pairs": [list(pair) for pair in sorted(candidate_pairs)],
                    "factual_candidate_covered": len(covered_factual),
                    "factual_movement_uncovered": len(uncovered_factual),
                    "all_factual_position_covered": all_factual_position_covered,
                    "strict_all_candidate_resolved": all_strict_resolved,
                    "strict_factual_subset_of_eligible": (
                        factual_pairs <= strict_eligible
                        if all_factual_position_covered and all_strict_resolved
                        else None
                    ),
                    "strict_eligible_exact_factual": (
                        strict_eligible == factual_pairs
                        if all_factual_position_covered and all_strict_resolved
                        else None
                    ),
                    "conditional_all_candidate_resolved": all_conditional_resolved,
                    "conditional_factual_subset_of_eligible": (
                        factual_pairs <= conditional_eligible
                        if all_factual_position_covered and all_conditional_resolved
                        else None
                    ),
                    "conditional_eligible_exact_factual": (
                        conditional_eligible == factual_pairs
                        if all_factual_position_covered and all_conditional_resolved
                        else None
                    ),
                }
            )

    site_counts = Counter()
    for site in site_reports:
        site_counts["sites"] += 1
        if site["all_factual_position_covered"]:
            site_counts["all_factual_position_covered"] += 1
        if site["strict_all_candidate_resolved"]:
            site_counts["strict_all_candidate_resolved"] += 1
        if site["strict_factual_subset_of_eligible"] is True:
            site_counts["strict_factual_subset_of_eligible"] += 1
        elif site["strict_factual_subset_of_eligible"] is False:
            site_counts["strict_factual_not_subset_of_eligible"] += 1
        if site["strict_eligible_exact_factual"] is True:
            site_counts["strict_eligible_exact_factual"] += 1
        if site["conditional_all_candidate_resolved"]:
            site_counts["conditional_all_candidate_resolved"] += 1
        if site["conditional_factual_subset_of_eligible"] is True:
            site_counts["conditional_factual_subset_of_eligible"] += 1
        elif site["conditional_factual_subset_of_eligible"] is False:
            site_counts["conditional_factual_not_subset_of_eligible"] += 1
        if site["conditional_eligible_exact_factual"] is True:
            site_counts["conditional_eligible_exact_factual"] += 1

    priority_examples = [
        row
        for row in all_candidate_rows
        if row["factual_pair"]
        and (
            row["conditional"].get("engagement_eligible") is not True
            or row["strict"].get("engagement_eligible") is False
        )
    ]
    extra_examples = [
        row
        for row in all_candidate_rows
        if not row["factual_pair"] and row["conditional"].get("engagement_eligible") is True
    ]
    examples = (priority_examples + extra_examples)[: args.example_limit]

    summary = {
        "archives_considered": archives_considered,
        "special_game_591478_excluded": True,
        "payload_conflicts": payload_conflicts,
        "factual_ship_combat_sites": len(site_reports),
        "factual_unique_pairs": int(factual_pair_counts["total"]),
        "factual_pairs_candidate_covered": int(factual_pair_counts["candidate_covered"]),
        "factual_pairs_movement_uncovered": int(factual_pair_counts["movement_uncovered"]),
        "candidate_pairs": len(all_candidate_rows),
        "movement_uncovered_ship_reasons": _serialize(movement_uncovered_reasons),
        "strict": _scope_summary(all_candidate_rows, "strict"),
        "conditional": _scope_summary(all_candidate_rows, "conditional"),
        "sites": _serialize(site_counts),
    }

    return {
        "schema": "planets-lab.combat-host-candidate-set-audit.v1",
        "read_only": True,
        "summary": summary,
        "examples": examples,
        "evidence_boundary": (
            "Site-conditioned candidate-set differential. Factual VCRs supply only ordinary battle-site coordinates and "
            "the held-out comparison pair set; they are not used as positive eligibility or per-ship position inputs. "
            "Candidate ships must be owner-current T-1 records already at the site and intrinsically stationary under a "
            "conservative Warp-0/no-Tow/no-Intercept/no-C&I/no-HYP/no-obvious-Tow-target/no-obvious-Chunnel-source filter. "
            "T-1 nonpositive fuel remains unresolved rather than blocked. Strict diplomacy is leave-pair-out and requires "
            "another owner-aligned one-sided factual combat with the same raw directed relation signature; conditional "
            "diplomacy is an upper-bound composition profile, not an independent predictor. Extra eligible nonfactual pairs "
            "are not treated as pair-eligibility errors because mutable Host target selection can legitimately choose only "
            "a subset. Game 591478 is excluded. This v1 gate does not claim full post-movement stack reconstruction."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit conservative T-1 stationary ship combat candidate sets against factual ordinary VCR pairs."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT CANDIDATE-SET AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("EXAMPLES:")
    for row in report["examples"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: conservative site-conditioned stationary candidate-set gate; not a full mutable Host queue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
