from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
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
    BIRD_RACE_ID,
    CLOAK_INTERCEPT_MISSION_ID,
    orders_request_ship_combat,
)
from planets_lab.rules.combat.selection import (
    ShipCombatPairDecision,
    ShipCombatPairPhase,
    ShipCombatSideInput,
    decide_ship_combat_pair,
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


DEFAULT_EXAMPLE_LIMIT = 50
SUPER_STAR_CRUISER_HULL_IDS = frozenset({74, 1074})

# Verified by the 2026-09-09 public /game/loadinfo gate. This mapping is
# diagnostic evidence context, not a generic game-type inference rule.
STANDARD_GAME_CONTEXT = {
    360690: False,
    511506: False,
    620694: False,
    621253: True,
    621896: True,
    680435: True,
}

TARGET_CASE1 = (511506, 19, 13)
TARGET_CASE2 = (621896, 28, 67)


def _serialize(counter: Counter[Any]) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    }


def _positive_owner(value: Any) -> int | None:
    parsed = _intish(value)
    return parsed if parsed is not None and parsed > 0 else None


def _request_direction(owner_id: int, opponent_owner_id: int) -> str:
    low, _high = sorted((owner_id, opponent_owner_id))
    return "low_to_high" if owner_id == low else "high_to_low"


def _requests_combat(raw: Mapping[str, Any], opponent_owner_id: int) -> bool:
    return orders_request_ship_combat(
        mission=_intish(raw.get("mission")),
        primary_enemy=_intish(raw.get("enemy")),
        opponent_owner_id=opponent_owner_id,
    )


def _ship_projection(
    *,
    ship_id: int,
    owner_id: int,
    race_id: int | None,
    hull_id: int,
    hull_can_cloak: bool | None,
    raw: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "ship_id": ship_id,
        "owner_id": owner_id,
        "race_id": race_id,
        "hull_id": hull_id,
        "hull_can_cloak": hull_can_cloak,
        "mission": _intish(raw.get("mission")),
        "mission1target": _intish(raw.get("mission1target")),
        "enemy": _intish(raw.get("enemy")),
        "friendlycode": raw.get("friendlycode") if isinstance(raw.get("friendlycode"), str) else None,
        "iscloaked_tminus1": raw.get("iscloaked") if isinstance(raw.get("iscloaked"), bool) else None,
        "neutronium_tminus1": _intish(raw.get("neutronium")),
    }


def _build_start_stack_index(
    ship_groups: Mapping[tuple[int, int], Sequence[Any]],
) -> dict[tuple[int, int, int, int], tuple[tuple[int, int], ...]]:
    stacks: dict[tuple[int, int, int, int], list[tuple[int, int]]] = defaultdict(list)
    for (turn, ship_id) in sorted(ship_groups):
        owner_id, raw = _owner_raw(ship_groups, turn, ship_id)
        if owner_id is None or owner_id <= 0 or raw is None:
            continue
        x, y = _xy(raw)
        hull_id = _intish(raw.get("hullid", raw.get("hull_id")))
        if x is None or y is None or hull_id is None or hull_id <= 0:
            continue
        stacks[(turn, owner_id, int(x), int(y))].append((ship_id, hull_id))
    return {key: tuple(sorted(value)) for key, value in stacks.items()}


def _interference_state(
    *,
    game_id: int,
    before_turn: int,
    owner_id: int,
    raw: Mapping[str, Any],
    start_stacks: Mapping[tuple[int, int, int, int], Sequence[tuple[int, int]]],
) -> bool | None:
    """Return independently attributable Intercept Interference protection.

    Absence of any same-owner SSC/SSC-II at the ship's start location proves no
    interference source. Presence of a source is decisive only in verified
    Standard-game contexts from the prior public metadata gate; otherwise the
    effective game ability state remains unknown.
    """

    x, y = _xy(raw)
    if x is None or y is None:
        return None
    stack = start_stacks.get((before_turn, owner_id, int(x), int(y)), ())
    has_source = any(hull_id in SUPER_STAR_CRUISER_HULL_IDS for _ship_id, hull_id in stack)
    if not has_source:
        return False
    standard = STANDARD_GAME_CONTEXT.get(game_id)
    if standard is True:
        return True
    if standard is False:
        return False
    return None


def _galactic_power_state(*, game_id: int, race_id: int | None, hull_id: int) -> bool | None:
    if race_id != 8 or hull_id != 70:
        return False
    return STANDARD_GAME_CONTEXT.get(game_id)


def _hwm_state(race_id: int | None) -> bool | None:
    # Non-Birds cannot apply HWM. Bird effective advantage state is intentionally
    # unresolved; non-matching FC and documented MKT/NTP/LFM exceptions do not
    # require this state to decide the matching-FC blocker.
    return None if race_id == BIRD_RACE_ID or race_id is None else False


def _c_and_i_inputs(
    *,
    race_id: int | None,
    mission: int | None,
) -> tuple[bool | None, bool | None, bool | None]:
    if mission != CLOAK_INTERCEPT_MISSION_ID:
        return False, False, False
    if race_id != BIRD_RACE_ID:
        return None, None, None
    # Observed mission20 establishes that the C&I order exists in the historical
    # record. Modern buildable-hull eligibility and active cloak at the later
    # Intercept step are not reconstructible from T-1 alone, so remain unknown.
    return True, None, None


def _decision_projection(decision: ShipCombatPairDecision) -> dict[str, Any]:
    return {
        "engagement_eligible": decision.engagement_eligible,
        "matching_fc_blocks": decision.matching_fc_blocks,
        "left_hwm_applies": decision.left_hwm_applies,
        "right_hwm_applies": decision.right_hwm_applies,
        "phase": decision.phase.value if decision.phase is not None else None,
        "prestandard_kind": (
            decision.prestandard_kind.value if decision.prestandard_kind is not None else None
        ),
        "phase_attacker_ship_id": decision.phase_attacker_ship_id,
        "left_ship_id": decision.left_ship_id,
        "right_ship_id": decision.right_ship_id,
        "unresolved_reasons": list(decision.unresolved_reasons),
    }


def _side_exact(
    decision: Mapping[str, Any],
    *,
    factual_left_ship_id: int,
    factual_right_ship_id: int,
) -> bool | None:
    predicted_left = decision.get("left_ship_id")
    predicted_right = decision.get("right_ship_id")
    if predicted_left is None or predicted_right is None:
        return None
    return (
        int(predicted_left) == factual_left_ship_id
        and int(predicted_right) == factual_right_ship_id
    )


def _phase_prefix_summary(rows: Sequence[Mapping[str, Any]], decision_key: str) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: int(row["vcr_id"]))
    fully_resolved = all(row[decision_key].get("phase") is not None for row in ordered)
    seen_standard = False
    known_violation = False
    resolved_sequence: list[str] = []
    for row in ordered:
        phase = row[decision_key].get("phase")
        if phase is None:
            continue
        resolved_sequence.append(str(phase))
        if phase == ShipCombatPairPhase.STANDARD.value:
            seen_standard = True
        elif seen_standard:
            known_violation = True
    return {
        "fully_resolved": fully_resolved,
        "known_prefix_violation": known_violation,
        "resolved_sequence": resolved_sequence,
    }


def _normal_pia_order_summary(rows: Sequence[Mapping[str, Any]], decision_key: str) -> dict[str, Any]:
    first_vcr_by_attacker: dict[int, int] = {}
    for row in sorted(rows, key=lambda item: int(item["vcr_id"])):
        decision = row[decision_key]
        if decision.get("prestandard_kind") != "normal_priority_intercept":
            continue
        attacker = decision.get("phase_attacker_ship_id")
        if attacker is None:
            continue
        attacker = int(attacker)
        vcr_id = int(row["vcr_id"])
        first_vcr_by_attacker[attacker] = min(vcr_id, first_vcr_by_attacker.get(attacker, vcr_id))
    factual = [
        attacker
        for attacker, _vcr_id in sorted(first_vcr_by_attacker.items(), key=lambda item: item[1])
    ]
    expected = sorted(first_vcr_by_attacker, reverse=True)
    comparable = len(factual) >= 2
    return {
        "comparable": comparable,
        "factual_attacker_order": factual,
        "expected_reverse_ship_id_order": expected,
        "exact": factual == expected if comparable else None,
    }


def _scope_summary(rows: Sequence[Mapping[str, Any]], decision_key: str) -> dict[str, Any]:
    engagement = Counter()
    phases = Counter()
    kinds = Counter()
    reasons = Counter()
    side = Counter()
    for row in rows:
        decision = row[decision_key]
        engagement[str(decision.get("engagement_eligible"))] += 1
        phases[str(decision.get("phase"))] += 1
        kinds[str(decision.get("prestandard_kind"))] += 1
        for reason in decision.get("unresolved_reasons", ()):
            reasons[str(reason)] += 1
        exact = row[f"{decision_key}_side_exact"]
        side["unresolved" if exact is None else ("exact" if exact else "mismatch")] += 1
    return {
        "rows": len(rows),
        "engagement_eligible": _serialize(engagement),
        "phase": _serialize(phases),
        "prestandard_kind": _serialize(kinds),
        "side_result": _serialize(side),
        "unresolved_reasons": _serialize(reasons),
    }


def _site_scope_summary(
    sites: Sequence[Mapping[str, Any]],
    decision_key: str,
) -> dict[str, Any]:
    counts = Counter()
    for site in sites:
        prefix = site[f"{decision_key}_phase_prefix"]
        pia_order = site[f"{decision_key}_normal_pia_order"]
        if len(site["rows"]) > 1:
            counts["multi_vcr_sites"] += 1
        if prefix["fully_resolved"]:
            counts["all_phase_resolved_sites"] += 1
            if prefix["known_prefix_violation"]:
                counts["fully_resolved_prefix_violation"] += 1
            else:
                counts["fully_resolved_prefix_exact"] += 1
        if prefix["known_prefix_violation"]:
            counts["known_prefix_violation_any_scope"] += 1
        if pia_order["comparable"]:
            counts["normal_pia_reverse_id_comparable"] += 1
            if pia_order["exact"]:
                counts["normal_pia_reverse_id_exact"] += 1
            else:
                counts["normal_pia_reverse_id_mismatch"] += 1
    counts["sites"] = len(sites)
    return _serialize(counts)


def _make_side_input(
    *,
    game_id: int,
    side: Mapping[str, Any],
    raw: Mapping[str, Any],
    race_id: int | None,
    hull_can_cloak: bool | None,
    diplomacy_allows_attack: bool | None,
    interference_protected: bool | None,
) -> ShipCombatSideInput:
    mission = _intish(raw.get("mission"))
    c_and_i_enabled, c_and_i_hull_eligible, active_cloak = _c_and_i_inputs(
        race_id=race_id,
        mission=mission,
    )
    hull_id = int(side["hull_id"])
    return ShipCombatSideInput(
        ship_id=int(side["ship_id"]),
        owner_id=int(side["owner_id"]),
        race_id=race_id,
        hull_id=hull_id,
        mission=mission,
        mission_target_id=_intish(raw.get("mission1target")),
        primary_enemy=_intish(raw.get("enemy")),
        friendly_code=raw.get("friendlycode"),
        hull_can_cloak=hull_can_cloak,
        # Factual VCR presence is the positive eligibility oracle for this audit.
        # The gate does not claim to predict engagement existence.
        has_fuel=True,
        diplomacy_allows_attack=diplomacy_allows_attack,
        harmonic_weapon_modulation_enabled=_hwm_state(race_id),
        cloak_and_intercept_enabled=c_and_i_enabled,
        cloak_and_intercept_hull_eligible=c_and_i_hull_eligible,
        active_cloak_at_intercept=active_cloak,
        intercept_interference_protected=interference_protected,
        galactic_power_enabled=_galactic_power_state(
            game_id=game_id,
            race_id=race_id,
            hull_id=hull_id,
        ),
    )


def _build_independent_diplomacy_controls(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[
    Mapping[tuple[RelationSignature, str], set[tuple[int, int, int]]],
    Mapping[tuple[int, RelationSignature, str], set[tuple[int, int, int]]],
]:
    by_game: dict[tuple[RelationSignature, str], set[tuple[int, int, int]]] = defaultdict(set)
    by_turn: dict[tuple[int, RelationSignature, str], set[tuple[int, int, int]]] = defaultdict(set)
    for row in rows:
        signature = row["relation_signature_raw"]
        if not _unique_relation_signature(signature):
            continue
        left_request = bool(row["left_request"])
        right_request = bool(row["right_request"])
        if left_request == right_request:
            # Only one-sided factual aggression proves a directed permission
            # without needing to know which side actually initiated the combat.
            continue
        owner = int(row["left_owner_id"] if left_request else row["right_owner_id"])
        opponent = int(row["right_owner_id"] if left_request else row["left_owner_id"])
        direction = _request_direction(owner, opponent)
        row_id = tuple(int(value) for value in row["row_id"])
        by_game[(signature, direction)].add(row_id)
        by_turn[(int(row["battle_turn"]), signature, direction)].add(row_id)
    return by_game, by_turn


def _independent_permission(
    *,
    row: Mapping[str, Any],
    side_name: str,
    game_controls: Mapping[tuple[RelationSignature, str], set[tuple[int, int, int]]],
    turn_controls: Mapping[tuple[int, RelationSignature, str], set[tuple[int, int, int]]],
) -> tuple[bool | None, bool]:
    request = bool(row[f"{side_name}_request"])
    if not request:
        return False, False
    signature = row["relation_signature_raw"]
    if not _unique_relation_signature(signature):
        return None, False
    owner = int(row[f"{side_name}_owner_id"])
    other_name = "right" if side_name == "left" else "left"
    opponent = int(row[f"{other_name}_owner_id"])
    direction = _request_direction(owner, opponent)
    row_id = tuple(int(value) for value in row["row_id"])
    game_ids = game_controls.get((signature, direction), set()) - {row_id}
    turn_ids = turn_controls.get((int(row["battle_turn"]), signature, direction), set()) - {row_id}
    if game_ids:
        return True, bool(turn_ids)
    return None, False


def run(args: argparse.Namespace) -> dict[str, Any]:
    all_rows: list[dict[str, Any]] = []
    payload_conflicts = 0
    archives_considered = 0

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

        archive_rows: list[dict[str, Any]] = []
        for (seen_game, battle_turn, vcr_id), (_digest, vcr) in sorted(seen.items()):
            if seen_game != game_id:
                continue
            left = _ship_side(vcr, "left")
            right = _ship_side(vcr, "right")
            x = _int(vcr, "x")
            y = _int(vcr, "y")
            if left is None or right is None or x is None or y is None:
                continue

            before_turn = battle_turn - 1
            left_id = int(left["ship_id"])
            right_id = int(right["ship_id"])
            left_owner, left_raw = _owner_raw(ship_groups, before_turn, left_id)
            right_owner, right_raw = _owner_raw(ship_groups, before_turn, right_id)
            if left_raw is None or right_raw is None or left_owner is None or right_owner is None:
                continue
            if left_owner != left.get("owner_id") or right_owner != right.get("owner_id"):
                continue
            if left_owner <= 0 or right_owner <= 0 or left_owner == right_owner:
                continue

            left_hull_id = int(left["hull_id"])
            right_hull_id = int(right["hull_id"])
            left_hull = specs.hulls.get(left_hull_id)
            right_hull = specs.hulls.get(right_hull_id)
            left_can_cloak = left_hull.can_cloak if left_hull is not None else None
            right_can_cloak = right_hull.can_cloak if right_hull is not None else None
            left_race = races.get(left_owner)
            right_race = races.get(right_owner)
            signature = _relation_signature(relations.get(before_turn, {}), left_owner, right_owner)
            row_id = (battle_turn, vcr_id, min(left_id, right_id))

            archive_rows.append(
                {
                    "game_id": game_id,
                    "battle_turn": battle_turn,
                    "vcr_id": vcr_id,
                    "x": x,
                    "y": y,
                    "row_id": row_id,
                    "left_ship_id": left_id,
                    "right_ship_id": right_id,
                    "left_owner_id": left_owner,
                    "right_owner_id": right_owner,
                    "left_request": _requests_combat(left_raw, right_owner),
                    "right_request": _requests_combat(right_raw, left_owner),
                    "relation_signature_raw": signature,
                    "relation_signature": _safe_signature(signature),
                    "left_interference": _interference_state(
                        game_id=game_id,
                        before_turn=before_turn,
                        owner_id=left_owner,
                        raw=left_raw,
                        start_stacks=start_stacks,
                    ),
                    "right_interference": _interference_state(
                        game_id=game_id,
                        before_turn=before_turn,
                        owner_id=right_owner,
                        raw=right_raw,
                        start_stacks=start_stacks,
                    ),
                    "left_side": left,
                    "right_side": right,
                    "left_raw": left_raw,
                    "right_raw": right_raw,
                    "left_race": left_race,
                    "right_race": right_race,
                    "left_can_cloak": left_can_cloak,
                    "right_can_cloak": right_can_cloak,
                }
            )

        game_controls, turn_controls = _build_independent_diplomacy_controls(archive_rows)

        for row in archive_rows:
            left_strict, left_same_turn = _independent_permission(
                row=row,
                side_name="left",
                game_controls=game_controls,
                turn_controls=turn_controls,
            )
            right_strict, right_same_turn = _independent_permission(
                row=row,
                side_name="right",
                game_controls=game_controls,
                turn_controls=turn_controls,
            )

            left_conditional = True if row["left_request"] else False
            right_conditional = True if row["right_request"] else False

            strict_left_input = _make_side_input(
                game_id=game_id,
                side=row["left_side"],
                raw=row["left_raw"],
                race_id=row["left_race"],
                hull_can_cloak=row["left_can_cloak"],
                diplomacy_allows_attack=left_strict,
                interference_protected=row["left_interference"],
            )
            strict_right_input = _make_side_input(
                game_id=game_id,
                side=row["right_side"],
                raw=row["right_raw"],
                race_id=row["right_race"],
                hull_can_cloak=row["right_can_cloak"],
                diplomacy_allows_attack=right_strict,
                interference_protected=row["right_interference"],
            )
            conditional_left_input = _make_side_input(
                game_id=game_id,
                side=row["left_side"],
                raw=row["left_raw"],
                race_id=row["left_race"],
                hull_can_cloak=row["left_can_cloak"],
                diplomacy_allows_attack=left_conditional,
                interference_protected=row["left_interference"],
            )
            conditional_right_input = _make_side_input(
                game_id=game_id,
                side=row["right_side"],
                raw=row["right_raw"],
                race_id=row["right_race"],
                hull_can_cloak=row["right_can_cloak"],
                diplomacy_allows_attack=right_conditional,
                interference_protected=row["right_interference"],
            )

            strict = _decision_projection(
                decide_ship_combat_pair(
                    left=strict_left_input,
                    right=strict_right_input,
                    same_location=True,
                )
            )
            conditional = _decision_projection(
                decide_ship_combat_pair(
                    left=conditional_left_input,
                    right=conditional_right_input,
                    same_location=True,
                )
            )

            output_row = {
                "game_id": game_id,
                "battle_turn": int(row["battle_turn"]),
                "vcr_id": int(row["vcr_id"]),
                "x": int(row["x"]),
                "y": int(row["y"]),
                "left": _ship_projection(
                    ship_id=int(row["left_ship_id"]),
                    owner_id=int(row["left_owner_id"]),
                    race_id=row["left_race"],
                    hull_id=int(row["left_side"]["hull_id"]),
                    hull_can_cloak=row["left_can_cloak"],
                    raw=row["left_raw"],
                ),
                "right": _ship_projection(
                    ship_id=int(row["right_ship_id"]),
                    owner_id=int(row["right_owner_id"]),
                    race_id=row["right_race"],
                    hull_id=int(row["right_side"]["hull_id"]),
                    hull_can_cloak=row["right_can_cloak"],
                    raw=row["right_raw"],
                ),
                "left_request": bool(row["left_request"]),
                "right_request": bool(row["right_request"]),
                "relation_signature": row["relation_signature"],
                "strict_left_diplomacy_allows_attack": left_strict,
                "strict_right_diplomacy_allows_attack": right_strict,
                "strict_same_turn_control": bool(left_same_turn or right_same_turn),
                "left_interference_protected": row["left_interference"],
                "right_interference_protected": row["right_interference"],
                "strict": strict,
                "conditional": conditional,
            }
            output_row["strict_side_exact"] = _side_exact(
                strict,
                factual_left_ship_id=int(row["left_ship_id"]),
                factual_right_ship_id=int(row["right_ship_id"]),
            )
            output_row["conditional_side_exact"] = _side_exact(
                conditional,
                factual_left_ship_id=int(row["left_ship_id"]),
                factual_right_ship_id=int(row["right_ship_id"]),
            )
            all_rows.append(output_row)

    sites_by_key: dict[tuple[int, int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in all_rows:
        sites_by_key[(row["game_id"], row["battle_turn"], row["x"], row["y"])].append(row)

    sites: list[dict[str, Any]] = []
    for (game_id, battle_turn, x, y), rows in sorted(sites_by_key.items()):
        ordered = sorted(rows, key=lambda row: row["vcr_id"])
        sites.append(
            {
                "game_id": game_id,
                "battle_turn": battle_turn,
                "x": x,
                "y": y,
                "rows": ordered,
                "strict_phase_prefix": _phase_prefix_summary(ordered, "strict"),
                "conditional_phase_prefix": _phase_prefix_summary(ordered, "conditional"),
                "strict_normal_pia_order": _normal_pia_order_summary(ordered, "strict"),
                "conditional_normal_pia_order": _normal_pia_order_summary(ordered, "conditional"),
            }
        )

    case1 = [
        row for row in all_rows
        if (row["game_id"], row["battle_turn"], row["vcr_id"]) == TARGET_CASE1
    ]
    case2 = [
        row for row in all_rows
        if (row["game_id"], row["battle_turn"], row["vcr_id"]) == TARGET_CASE2
    ]

    examples: list[dict[str, Any]] = []
    for row in all_rows:
        conditional = row["conditional"]
        if (
            row["conditional_side_exact"] is False
            or conditional.get("phase") is None
            or conditional.get("engagement_eligible") is not True
        ):
            examples.append(row)
            if len(examples) >= args.example_limit:
                break

    summary = {
        "archives_considered": archives_considered,
        "special_game_591478_excluded": True,
        "payload_conflicts": payload_conflicts,
        "factual_ship_vcr_rows": len(all_rows),
        "sites": len(sites),
        "multi_vcr_sites": sum(len(site["rows"]) > 1 for site in sites),
        "strict": _scope_summary(all_rows, "strict"),
        "conditional": _scope_summary(all_rows, "conditional"),
        "strict_sites": _site_scope_summary(sites, "strict"),
        "conditional_sites": _site_scope_summary(sites, "conditional"),
        "case1_rows": len(case1),
        "case2_rows": len(case2),
    }

    return {
        "schema": "planets-lab.combat-host-factual-queue-selection-audit.v1",
        "read_only": True,
        "summary": summary,
        "case1_reciprocal": case1,
        "case2_galactic_power": case2,
        "examples": examples,
        "evidence_boundary": (
            "This is a factual-positive ship-vs-ship queue differential, not a candidate-set predictor. Existing VCR "
            "presence is used only as an oracle that the pair reached combat eligibility; the audit asks whether the "
            "canonical pair-selection layer attributes phase and sides correctly and whether resolved pre-standard "
            "rows precede resolved standard rows. Strict directed diplomacy requires an independent one-sided factual "
            "combat control with the same T-1 relation signature and direction. C&I active-cloak/buildable-hull state "
            "remains unresolved when T-1 cannot prove it. Game 591478 is excluded."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit canonical pair-selection composition across factual ordinary ship-vs-ship VCR queues."
    )
    parser.add_argument("--archive-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--prepared-dir", type=Path, default=PREPARED_DIR)
    parser.add_argument("--example-limit", type=int, default=DEFAULT_EXAMPLE_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args)
    print("===== HOST COMBAT FACTUAL QUEUE / PAIR-SELECTION AUDIT =====")
    print(f"summary: {report['summary']}")
    print()
    print("CASE1 RECIPROCAL:")
    for row in report["case1_reciprocal"]:
        print(row)
    print()
    print("CASE2 GALACTIC POWER:")
    for row in report["case2_galactic_power"]:
        print(row)
    print()
    print("EXAMPLES:")
    for row in report["examples"]:
        print(row)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"output: {args.output}")
    print("NOTE: factual-positive queue differential only; this tool does not predict the VCR set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
