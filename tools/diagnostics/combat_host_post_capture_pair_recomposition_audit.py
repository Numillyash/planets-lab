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

from planets_lab.corpus.feature_scope import DEFAULT_FEATURE_INDEX_PATH, load_feature_scope
from planets_lab.corpus.movement_differential import _intish
from planets_lab.rules.combat.order import standard_battle_priority_key
from planets_lab.rules.combat.queue import standard_pair_sides_for_occurrence
from planets_lab.rules.combat.selection import decide_ship_combat_pair

import combat_host_capture_continuation_audit as capture_module
import combat_host_initial_standard_target_audit as baseline_module
import combat_host_post_capture_active_membership_audit as active_module
import combat_host_post_capture_ship_candidate_audit as candidate_module
import combat_host_post_capture_special_movement_audit as special_movement_module
import combat_host_post_mutation_next_pair_audit as mutation_audit
from combat_host_candidate_set_audit import _candidate_input, _pair
from combat_host_factual_queue_selection_audit import (
    _decision_projection,
    _interference_state,
)
from combat_host_priority_intercept_audit import PREPARED_DIR, RAW_DIR


SCHEMA = "planets-lab.combat-host-post-capture-pair-recomposition-audit.v2"
DEFAULT_EXAMPLE_LIMIT = 80

# External reference only: c2ng/THost-derived makeShipShipVcr rejects a ship
# marked fl_WasCaptured when that ship is supplied as LEFT. With simulator
# random-left/right disabled, a subsequent captured-ship fight in that audited
# path therefore requires the captured/prize ship to be RIGHT. This constant is
# a comparator, not a NuHost mechanics rule.
EXTERNAL_C2NG_CAPTURED_PRIZE_SIDE = "right"


def _priority_from_raw(
    ship_id: int,
    raw: Mapping[str, Any],
) -> tuple[int, int, int] | None:
    return standard_battle_priority_key(
        ship_id=ship_id,
        mission=_intish(raw.get("mission")),
        primary_enemy=_intish(raw.get("enemy")),
        friendly_code=raw.get("friendlycode"),
    )


def _neutral_prize_raw(
    raw: Mapping[str, Any],
    *,
    friendly_code: Any,
) -> dict[str, Any]:
    result = dict(raw)
    result["mission"] = 0
    result["mission1target"] = 0
    result["enemy"] = 0
    result["friendlycode"] = friendly_code
    return result


def _nonmatching_symbolic_fc(opponent_fc: Any) -> str:
    for value in ("c@p", "p@c", "x@x"):
        if not isinstance(opponent_fc, str) or opponent_fc.strip().lower() != value:
            return value
    return "r@r"


def _side_from_priority_keys(
    *,
    prize_ship_id: int,
    opponent_ship_id: int,
    prize_key: tuple[int, int, int] | None,
    opponent_key: tuple[int, int, int] | None,
    occurrence_index: int,
) -> str | None:
    if prize_key is None or opponent_key is None or prize_key == opponent_key:
        return None

    if prize_key < opponent_key:
        first_sides = (opponent_ship_id, prize_ship_id)
    else:
        first_sides = (prize_ship_id, opponent_ship_id)

    if occurrence_index == 1:
        sides = first_sides
    else:
        sides = standard_pair_sides_for_occurrence(
            first_pass_left_ship_id=first_sides[0],
            first_pass_right_ship_id=first_sides[1],
            occurrence_index=occurrence_index,
        )
        if sides is None:
            return None

    return "left" if sides[0] == prize_ship_id else "right"


def _prior_pair_occurrences(
    *,
    factual_queue: Sequence[Mapping[str, Any]],
    pair: tuple[int, int],
    before_vcr_id: int,
) -> int:
    count = 0
    for row in factual_queue:
        vcr_id = row.get("vcr_id")
        pair_raw = row.get("pair")
        if (
            isinstance(vcr_id, bool)
            or not isinstance(vcr_id, int)
            or int(vcr_id) >= before_vcr_id
            or not isinstance(pair_raw, tuple)
            or len(pair_raw) != 2
        ):
            continue
        if _pair(int(pair_raw[0]), int(pair_raw[1])) == pair:
            count += 1
    return count


def _pair_recomposition(
    *,
    context: Mapping[str, Any],
    capture: Mapping[str, Any],
    active_result: Mapping[str, Any],
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
) -> dict[str, Any]:
    game_id = int(context["game_id"])
    battle_turn = int(context["battle_turn"])
    before_turn = int(context["before_turn"])
    prize_id = int(capture["ship_id"])
    opponent_id = int(capture["current_opponent_ship_id"])
    from_vcr_id = int(capture["from_vcr_id"])
    to_vcr_id = int(capture["to_vcr_id"])

    predictions = context.get("predictions")
    start_stacks = context.get("start_stacks")
    factual_queue = context.get("factual_queue")
    if (
        not isinstance(predictions, Mapping)
        or not isinstance(start_stacks, Mapping)
        or not isinstance(factual_queue, Sequence)
        or isinstance(factual_queue, (str, bytes))
    ):
        return {"status": "unresolved", "reason": "site_context_incomplete"}

    prize_entry = predictions.get(prize_id)
    opponent_entry = predictions.get(opponent_id)
    if not isinstance(prize_entry, Mapping):
        return {"status": "unresolved", "reason": "prize_tminus1_prediction_missing"}
    if not isinstance(opponent_entry, Mapping):
        return {"status": "unresolved", "reason": "opponent_prediction_missing"}

    prize_old_raw = prize_entry.get("raw")
    opponent_raw = opponent_entry.get("raw")
    if not isinstance(prize_old_raw, Mapping):
        return {"status": "unresolved", "reason": "prize_tminus1_orders_missing"}
    if not isinstance(opponent_raw, Mapping):
        return {"status": "unresolved", "reason": "opponent_tminus1_orders_missing"}

    candidate_rows = active_result.get("candidates")
    candidate_rows = candidate_rows if isinstance(candidate_rows, list) else []
    factual_candidate = next(
        (
            row
            for row in candidate_rows
            if isinstance(row, Mapping) and row.get("ship_id") == opponent_id
        ),
        None,
    )
    if not isinstance(factual_candidate, Mapping):
        return {"status": "unresolved", "reason": "active_factual_candidate_missing"}
    strict_permission = factual_candidate.get("strict_permission")
    if strict_permission is not True:
        return {
            "status": "unresolved",
            "reason": "factual_candidate_strict_permission_not_true",
            "strict_permission": strict_permission,
        }

    prize_owner = active_result.get("prize_owner_id_after_capture")
    prize_race = capture.get("race_id_after")
    prize_hull = capture.get("hull_id_after")
    opponent_owner = opponent_entry.get("owner_id")
    opponent_race = opponent_entry.get("race_id")
    opponent_hull = opponent_entry.get("hull_id")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
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
            "reason": "post_capture_identity_or_hull_unresolved",
        }

    prize_hull_can_cloak = prize_entry.get("hull_can_cloak")
    opponent_hull_can_cloak = opponent_entry.get("hull_can_cloak")
    opponent_interference = _interference_state(
        game_id=game_id,
        before_turn=before_turn,
        owner_id=int(opponent_owner),
        raw=opponent_raw,
        start_stacks=start_stacks,
    )
    prize_interference = _interference_state(
        game_id=game_id,
        before_turn=before_turn,
        owner_id=int(prize_owner),
        raw=prize_old_raw,
        start_stacks=start_stacks,
    )

    old_fc = prize_old_raw.get("friendlycode")
    fresh_fc = _nonmatching_symbolic_fc(opponent_raw.get("friendlycode"))

    def decision_for(prize_fc: Any) -> dict[str, Any]:
        prize_raw = _neutral_prize_raw(prize_old_raw, friendly_code=prize_fc)
        prize_side = _candidate_input(
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
        opponent_side = _candidate_input(
            game_id=game_id,
            ship_id=opponent_id,
            owner_id=int(opponent_owner),
            raw=opponent_raw,
            race_id=(
                int(opponent_race)
                if isinstance(opponent_race, int)
                and not isinstance(opponent_race, bool)
                and opponent_race > 0
                else None
            ),
            hull_id=int(opponent_hull),
            hull_can_cloak=(
                bool(opponent_hull_can_cloak)
                if isinstance(opponent_hull_can_cloak, bool)
                else None
            ),
            diplomacy_allows_attack=True,
            interference_protected=opponent_interference,
        )
        return _decision_projection(
            decide_ship_combat_pair(
                left=prize_side,
                right=opponent_side,
                same_location=True,
            )
        )

    preserved_fc_decision = decision_for(old_fc)
    fresh_fc_decision = decision_for(fresh_fc)

    pair_phase_invariant = (
        preserved_fc_decision.get("engagement_eligible") is True
        and fresh_fc_decision.get("engagement_eligible") is True
        and preserved_fc_decision.get("phase") == fresh_fc_decision.get("phase")
        and preserved_fc_decision.get("prestandard_kind")
        == fresh_fc_decision.get("prestandard_kind")
    )

    previous_appearance = active_module._appearance_index(
        appearances,
        game_id=game_id,
        battle_turn=battle_turn,
        vcr_id=from_vcr_id,
        ship_id=prize_id,
    )
    previous_side = (
        previous_appearance.get("side")
        if isinstance(previous_appearance, Mapping)
        else None
    )
    factual_side = capture.get("current_side")
    if factual_side not in {"left", "right"}:
        return {"status": "unresolved", "reason": "factual_post_capture_side_missing"}
    if previous_side not in {"left", "right"}:
        return {"status": "unresolved", "reason": "capture_engagement_side_missing"}

    pair = _pair(prize_id, opponent_id)
    prior_occurrences = _prior_pair_occurrences(
        factual_queue=factual_queue,
        pair=pair,
        before_vcr_id=to_vcr_id,
    )
    occurrence_index = prior_occurrences + 1

    opponent_key = _priority_from_raw(opponent_id, opponent_raw)
    frozen_prize_key = _priority_from_raw(prize_id, prize_old_raw)
    neutral_preserved_raw = _neutral_prize_raw(
        prize_old_raw,
        friendly_code=old_fc,
    )
    neutral_fresh_raw = _neutral_prize_raw(
        prize_old_raw,
        friendly_code=fresh_fc,
    )
    neutral_preserved_key = _priority_from_raw(prize_id, neutral_preserved_raw)
    neutral_fresh_key = _priority_from_raw(prize_id, neutral_fresh_raw)

    controls = {
        "sticky_capture_side": previous_side,
        "opponent_initiator_right": "left",
        "external_c2ng_captured_right": EXTERNAL_C2NG_CAPTURED_PRIZE_SIDE,
        "frozen_tminus1_priority": _side_from_priority_keys(
            prize_ship_id=prize_id,
            opponent_ship_id=opponent_id,
            prize_key=frozen_prize_key,
            opponent_key=opponent_key,
            occurrence_index=occurrence_index,
        ),
        "neutral_orders_preserve_fc": _side_from_priority_keys(
            prize_ship_id=prize_id,
            opponent_ship_id=opponent_id,
            prize_key=neutral_preserved_key,
            opponent_key=opponent_key,
            occurrence_index=occurrence_index,
        ),
        "neutral_orders_fresh_fc": _side_from_priority_keys(
            prize_ship_id=prize_id,
            opponent_ship_id=opponent_id,
            prize_key=neutral_fresh_key,
            opponent_key=opponent_key,
            occurrence_index=occurrence_index,
        ),
    }

    exact_controls = {
        name: value == factual_side if value in {"left", "right"} else None
        for name, value in controls.items()
    }

    return {
        "status": "resolved" if pair_phase_invariant else "unresolved",
        "reason": None if pair_phase_invariant else "pair_phase_not_fc_invariant",
        "prize_ship_id": prize_id,
        "opponent_ship_id": opponent_id,
        "post_capture_owner_id": int(prize_owner),
        "factual_post_capture_side": factual_side,
        "capture_engagement_side": previous_side,
        "prior_pair_occurrences": prior_occurrences,
        "occurrence_index": occurrence_index,
        "opponent_priority": list(opponent_key) if opponent_key is not None else None,
        "frozen_prize_priority": (
            list(frozen_prize_key) if frozen_prize_key is not None else None
        ),
        "neutral_preserved_fc_priority": (
            list(neutral_preserved_key)
            if neutral_preserved_key is not None
            else None
        ),
        "neutral_fresh_fc_priority": (
            list(neutral_fresh_key) if neutral_fresh_key is not None else None
        ),
        "preserved_fc_decision": preserved_fc_decision,
        "fresh_fc_decision": fresh_fc_decision,
        "pair_phase_invariant": pair_phase_invariant,
        "side_controls": controls,
        "side_control_exact": exact_controls,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    feature_scope = load_feature_scope(
        args.feature_index,
        profile=args.scope_profile,
    )
    capture_report = capture_module.run(
        argparse.Namespace(
            archive_dir=args.archive_dir,
            feature_index=args.feature_index,
            scope_profile=args.scope_profile,
            example_limit=10000,
            output=None,
        )
    )
    targets = candidate_module._capture_targets(capture_report)
    appearances, chain_summary = mutation_audit._collect_replay_appearances(args)

    target_turns = {
        (game_id, battle_turn)
        for game_id, battle_turn, _x, _y in targets
    }
    counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    seen: set[tuple[int, int, int, int, int]] = set()

    def prediction_overlay(
        context: Mapping[str, Any],
    ) -> dict[int, dict[str, Any]]:
        key = (int(context["game_id"]), int(context["battle_turn"]))
        if key not in target_turns:
            return {}
        return special_movement_module.special_position_overlay(context)

    def observer(context: Mapping[str, Any]) -> None:
        site_key = (
            int(context["game_id"]),
            int(context["battle_turn"]),
            int(context["x"]),
            int(context["y"]),
        )
        captures = targets.get(site_key)
        if not captures:
            return

        for capture in captures:
            observation_key = (
                site_key[0],
                site_key[1],
                int(capture["from_vcr_id"]),
                int(capture["to_vcr_id"]),
                int(capture["ship_id"]),
            )
            seen.add(observation_key)
            active_result = active_module._simulate_capture(
                context=context,
                capture=capture,
                appearances=appearances,
            )
            if active_result.get("status") != "resolved":
                counts["active_membership_unresolved"] += 1
                result = {
                    "status": "unresolved",
                    "reason": "active_membership_dependency_unresolved",
                    "active_membership": active_result,
                }
            else:
                result = _pair_recomposition(
                    context=context,
                    capture=capture,
                    active_result=active_result,
                    appearances=appearances,
                )

            status = str(result.get("status", "unknown"))
            counts[f"status:{status}"] += 1
            if status == "resolved":
                if result.get("pair_phase_invariant") is True:
                    counts["pair_phase_fc_invariant"] += 1
                phase = result.get("preserved_fc_decision", {}).get("phase")
                counts[f"pair_phase:{phase}"] += 1
                factual_side = result.get("factual_post_capture_side")
                if factual_side in {"left", "right"}:
                    counts[f"factual_prize_side:{factual_side}"] += 1
                for name, exact in result.get("side_control_exact", {}).items():
                    if exact is True:
                        counts[f"side:{name}:exact"] += 1
                    elif exact is False:
                        counts[f"side:{name}:mismatch"] += 1
                    else:
                        counts[f"side:{name}:unresolved"] += 1
                if int(result.get("prior_pair_occurrences") or 0) > 0:
                    counts["observations_with_prior_pair_occurrence"] += 1

            if len(examples) < args.example_limit:
                examples.append(
                    {
                        "game_id": site_key[0],
                        "battle_turn": site_key[1],
                        "x": site_key[2],
                        "y": site_key[3],
                        "capture": {
                            "ship_id": capture.get("ship_id"),
                            "captor_owner_id": capture.get("captor_owner_id"),
                            "current_opponent_ship_id": capture.get(
                                "current_opponent_ship_id"
                            ),
                            "from_vcr_id": capture.get("from_vcr_id"),
                            "to_vcr_id": capture.get("to_vcr_id"),
                            "current_side": capture.get("current_side"),
                        },
                        "result": result,
                    }
                )

    baseline = baseline_module.run(
        argparse.Namespace(
            archive_dir=args.archive_dir,
            prepared_dir=args.prepared_dir,
            feature_index=args.feature_index,
            scope_profile=args.scope_profile,
            example_limit=0,
            output=None,
            site_observer=observer,
            prediction_overlay=prediction_overlay,
        )
    )

    population = sum(len(rows) for rows in targets.values())
    counts["ship_capture_observations"] = population
    counts["observations_seen"] = len(seen)

    def control_exact(name: str) -> bool:
        return (
            population > 0
            and int(counts[f"side:{name}:exact"]) == population
            and int(counts[f"side:{name}:mismatch"]) == 0
            and int(counts[f"side:{name}:unresolved"]) == 0
        )

    acceptance = {
        "population_present": population > 0,
        "all_observations_seen": len(seen) == population,
        "active_membership_dependency_exact": (
            int(counts["active_membership_unresolved"]) == 0
        ),
        "all_pair_recompositions_resolved": (
            int(counts["status:resolved"]) == population
        ),
        "all_pair_phases_fc_invariant": (
            int(counts["pair_phase_fc_invariant"]) == population
        ),
        "all_pair_phases_standard": (
            int(counts["pair_phase:standard"]) == population
        ),
        "sticky_capture_side_exact": control_exact("sticky_capture_side"),
        "opponent_initiator_right_exact": control_exact("opponent_initiator_right"),
        "external_c2ng_captured_right_exact": control_exact(
            "external_c2ng_captured_right"
        ),
        "frozen_tminus1_priority_exact": control_exact("frozen_tminus1_priority"),
        "neutral_orders_preserve_fc_exact": control_exact(
            "neutral_orders_preserve_fc"
        ),
        "neutral_orders_fresh_fc_exact": control_exact(
            "neutral_orders_fresh_fc"
        ),
    }

    return {
        "schema": SCHEMA,
        "read_only": True,
        "summary": {
            "feature_scope": feature_scope.to_dict(),
            "counts": dict(sorted(counts.items())),
            "chain_audit_summary": chain_summary,
            "baseline_initial_standard": baseline.get("summary"),
            "acceptance": acceptance,
        },
        "examples": examples,
        "evidence_boundary": (
            "Post-capture ship-pair recomposition diagnostic. Active membership "
            "and factual opponent rank are inherited from the separately validated "
            "mutable-history gate. Captured T-1 mission/Primary Enemy are never "
            "allowed to initiate the new-owner engagement. The factual opponent "
            "uses its independently reconstructed T-1 orders and strict diplomacy "
            "permission. Pair eligibility/phase is recomputed through production "
            "decide_ship_combat_pair under two captured-Friendly-Code bounds: the "
            "T-1 FC and a guaranteed nonmatching symbolic FC; phase is accepted "
            "only if invariant. LEFT/RIGHT is not promoted here. Five internal "
            "side controls are compared independently: capture-side carry, generic "
            "opponent-initiator-right, frozen T-1 combat priority, and neutral "
            "captured orders with preserved/fresh FC. A sixth control, "
            "external_c2ng_captured_right, is an explicitly non-authoritative "
            "historical comparator for the c2ng/THost captured-LEFT suppression "
            "behavior and must never be treated as a Nu rule. Elapsed factual "
            "VCRs before N+1 may supply pair occurrence history; N+1 supplies only "
            "the held-out side comparator."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Recompose the held-out post-capture ship pair and compare bounded "
            "LEFT/RIGHT control hypotheses."
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
    print("===== HOST COMBAT POST-CAPTURE PAIR RECOMPOSITION AUDIT =====")
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
