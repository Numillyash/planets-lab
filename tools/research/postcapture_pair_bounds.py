#!/usr/bin/env python3
"""Shared post-capture pair-composition helpers for research probes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def int_positive(value: Any) -> int | None:
    if is_int(value) and int(value) > 0:
        return int(value)
    return None


def candidate_by_id(
    active_result: Mapping[str, Any],
    ship_id: int,
) -> Mapping[str, Any] | None:
    rows = active_result.get("candidates")
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
    ):
        return None
    for row in rows:
        if isinstance(row, Mapping) and row.get("ship_id") == ship_id:
            return row
    return None


def history_pair_occurrences(
    *,
    factual_queue: Sequence[Mapping[str, Any]],
    through_vcr_id: int,
) -> dict[tuple[int, int], int]:
    counts: dict[tuple[int, int], int] = {}
    for row in factual_queue:
        vcr_id = row.get("vcr_id")
        pair = row.get("pair")
        if not is_int(vcr_id) or int(vcr_id) > through_vcr_id:
            continue
        if (
            not isinstance(pair, Sequence)
            or isinstance(pair, (str, bytes))
            or len(pair) != 2
            or not all(is_int(value) for value in pair)
        ):
            continue
        a, b = int(pair[0]), int(pair[1])
        key = tuple(sorted((a, b)))
        counts[key] = counts.get(key, 0) + 1
    return counts


def compose_candidate_pair(
    *,
    pair_module: Any,
    active_module: Any,
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
    context: Mapping[str, Any],
    capture: Mapping[str, Any],
    active_result: Mapping[str, Any],
    opponent_id: int,
) -> dict[str, Any]:
    game_id = int(context["game_id"])
    before_turn = int(context["before_turn"])
    prize_id = int(capture["ship_id"])

    predictions = context.get("predictions")
    start_stacks = context.get("start_stacks")
    if not isinstance(predictions, Mapping) or not isinstance(start_stacks, Mapping):
        return {"status": "unresolved", "reason": "site_context_incomplete"}

    prize_entry = predictions.get(prize_id)
    opponent_entry = predictions.get(opponent_id)
    if not isinstance(prize_entry, Mapping):
        return {"status": "unresolved", "reason": "prize_prediction_missing"}
    if not isinstance(opponent_entry, Mapping):
        return {"status": "unresolved", "reason": "opponent_prediction_missing"}

    prize_old_raw = prize_entry.get("raw")
    opponent_raw = opponent_entry.get("raw")
    if not isinstance(prize_old_raw, Mapping):
        return {"status": "unresolved", "reason": "prize_orders_missing"}
    if not isinstance(opponent_raw, Mapping):
        return {"status": "unresolved", "reason": "opponent_orders_missing"}

    prize_owner = int_positive(active_result.get("prize_owner_id_after_capture"))
    prize_hull = int_positive(prize_entry.get("hull_id"))
    opponent_owner = int_positive(opponent_entry.get("owner_id"))
    opponent_hull = int_positive(opponent_entry.get("hull_id"))
    opponent_race = int_positive(opponent_entry.get("race_id"))

    captor_id = int_positive(capture.get("captor_ship_id"))
    capture_vcr_id = int_positive(capture.get("from_vcr_id"))
    if captor_id is None or capture_vcr_id is None:
        return {
            "status": "unresolved",
            "reason": "capture_identity_missing_for_postcapture_race",
        }

    captor_appearance = active_module._appearance_index(
        appearances,
        game_id=game_id,
        battle_turn=int(context["battle_turn"]),
        vcr_id=capture_vcr_id,
        ship_id=captor_id,
    )
    if not isinstance(captor_appearance, Mapping):
        return {
            "status": "unresolved",
            "reason": "captor_appearance_missing_for_postcapture_race",
            "captor_ship_id": captor_id,
            "capture_vcr_id": capture_vcr_id,
        }
    prize_race = int_positive(captor_appearance.get("race_id"))

    if any(
        value is None
        for value in (
            prize_owner,
            prize_race,
            prize_hull,
            opponent_owner,
            opponent_hull,
        )
    ):
        return {
            "status": "unresolved",
            "reason": "identity_or_hull_unresolved",
            "prize_owner": prize_owner,
            "prize_race_from_captor": prize_race,
            "prize_hull": prize_hull,
            "opponent_owner": opponent_owner,
            "opponent_race": opponent_race,
            "opponent_hull": opponent_hull,
        }

    candidate = candidate_by_id(active_result, opponent_id)
    if not isinstance(candidate, Mapping):
        return {"status": "unresolved", "reason": "candidate_missing"}

    opponent_interference = pair_module._interference_state(
        game_id=game_id,
        before_turn=before_turn,
        owner_id=int(opponent_owner),
        raw=opponent_raw,
        start_stacks=start_stacks,
    )
    prize_interference = pair_module._interference_state(
        game_id=game_id,
        before_turn=before_turn,
        owner_id=int(prize_owner),
        raw=prize_old_raw,
        start_stacks=start_stacks,
    )

    prize_hull_can_cloak = prize_entry.get("hull_can_cloak")
    opponent_hull_can_cloak = opponent_entry.get("hull_can_cloak")

    old_fc = prize_old_raw.get("friendlycode")
    fresh_fc = pair_module._nonmatching_symbolic_fc(
        opponent_raw.get("friendlycode")
    )

    def decision_for(prize_fc: Any) -> dict[str, Any]:
        prize_raw = pair_module._neutral_prize_raw(
            prize_old_raw,
            friendly_code=prize_fc,
        )
        prize_side = pair_module._candidate_input(
            game_id=game_id,
            ship_id=prize_id,
            owner_id=int(prize_owner),
            raw=prize_raw,
            race_id=int(prize_race),
            hull_id=int(prize_hull),
            hull_can_cloak=(
                bool(prize_hull_can_cloak)
                if isinstance(prize_hull_can_cloak, bool)
                else None
            ),
            diplomacy_allows_attack=False,
            interference_protected=prize_interference,
        )
        opponent_side = pair_module._candidate_input(
            game_id=game_id,
            ship_id=opponent_id,
            owner_id=int(opponent_owner),
            raw=opponent_raw,
            race_id=opponent_race,
            hull_id=int(opponent_hull),
            hull_can_cloak=(
                bool(opponent_hull_can_cloak)
                if isinstance(opponent_hull_can_cloak, bool)
                else None
            ),
            diplomacy_allows_attack=True,
            interference_protected=opponent_interference,
        )
        return pair_module._decision_projection(
            pair_module.decide_ship_combat_pair(
                left=prize_side,
                right=opponent_side,
                same_location=True,
            )
        )

    preserved = decision_for(old_fc)
    fresh = decision_for(fresh_fc)

    phase_invariant = (
        preserved.get("phase") == fresh.get("phase")
        and preserved.get("prestandard_kind") == fresh.get("prestandard_kind")
    )
    definitely_eligible = (
        preserved.get("engagement_eligible") is True
        and fresh.get("engagement_eligible") is True
        and phase_invariant
    )
    definitely_blocked = (
        preserved.get("engagement_eligible") is False
        and fresh.get("engagement_eligible") is False
    )

    return {
        "status": "resolved",
        "postcapture_identity": {
            "prize_owner_id": prize_owner,
            "prize_race_id_from_captor_vcr": prize_race,
            "prize_hull_id_preserved": prize_hull,
            "captor_ship_id": captor_id,
            "capture_vcr_id": capture_vcr_id,
        },
        "candidate": {
            "ship_id": opponent_id,
            "requests_new_owner": candidate.get("requests_new_owner"),
            "strict_permission": candidate.get("strict_permission"),
            "priority": candidate.get("priority"),
            "position_source": candidate.get("position_source"),
        },
        "opponent_orders": {
            key: opponent_raw.get(key)
            for key in (
                "mission",
                "enemy",
                "friendlycode",
                "neutronium",
                "warp",
                "mission1target",
            )
        },
        "prize_old_friendly_code": old_fc,
        "fresh_prize_friendly_code": fresh_fc,
        "preserved_fc_decision": preserved,
        "fresh_fc_decision": fresh,
        "phase_invariant": phase_invariant,
        "definitely_eligible": definitely_eligible,
        "definitely_blocked": definitely_blocked,
        "fc_sensitive_or_unresolved": not (
            definitely_eligible or definitely_blocked
        ),
    }
