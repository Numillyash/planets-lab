#!/usr/bin/env python3
"""Held-out-safe probe for capture continuation availability at V593.

Target default:
    game 400330, turn 141, site (1674, 2363), capture VCR 593

The probe reconstructs only state through V593.  It does not read V594 pair
identity when classifying whether the captured prize has an immediate O/C
continuation.  The frozen site order is taken from the independently validated
mainline fixture for the same game/turn/site population.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.rules.combat.selection import decide_ship_combat_pair

import combat_host_post_capture_active_membership_audit as active_module
import combat_host_post_capture_pair_recomposition_audit as pair_module
import combat_public_capture_o_layer_probe as o_layer_module
from combat_host_candidate_set_audit import _candidate_input
from combat_postcapture_o_c_forward_selector import CandidateState, select_o_then_c_forward


SCHEMA = "planets-lab.capture-immediate-continuation-gate.v1"
FIXTURE = (
    REPO_ROOT
    / "validation"
    / "combat"
    / "postcapture-o-c-forward-independent-fixture.json"
)
SENTINEL_HELDOUT_OPPONENT_ID = 2_000_000_001


def _appearance_map(
    appearances: Sequence[Mapping[str, Any]],
) -> dict[tuple[int, int, int, int], Mapping[str, Any]]:
    return {
        (
            int(row["game_id"]),
            int(row["turn"]),
            int(row["vcr_id"]),
            int(row["ship_id"]),
        ): row
        for row in appearances
        if all(
            isinstance(row.get(key), int) and not isinstance(row.get(key), bool)
            for key in ("game_id", "turn", "vcr_id", "ship_id")
        )
    }


def _fixture_order(*, game_id: int, turn: int) -> tuple[int, ...]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    orders = {
        tuple(int(value) for value in row["external_order"])
        for row in payload.get("cases", [])
        if row.get("game_id") == game_id and row.get("turn") == turn
    }
    if len(orders) != 1:
        raise ValueError(
            f"expected exactly one frozen order anchor for game={game_id} turn={turn}, "
            f"got {len(orders)}"
        )
    return next(iter(orders))


def _pair_occurrences(
    factual_queue: Sequence[Mapping[str, Any]],
    *,
    through_vcr_id: int,
) -> dict[tuple[int, int], int]:
    counts: dict[tuple[int, int], int] = {}
    for row in factual_queue:
        vcr_id = row.get("vcr_id")
        pair = row.get("pair")
        if (
            isinstance(vcr_id, bool)
            or not isinstance(vcr_id, int)
            or vcr_id > through_vcr_id
            or not isinstance(pair, tuple)
            or len(pair) != 2
        ):
            continue
        a, b = int(pair[0]), int(pair[1])
        key = (a, b) if a < b else (b, a)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _terminal_capture_identity(
    *,
    game_id: int,
    battle_turn: int,
    vcr_row: Mapping[str, Any],
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
) -> dict[str, Any]:
    terminals, transfers, issue = active_module._terminal_batch_with_transfer(
        game_id=game_id,
        battle_turn=battle_turn,
        factual_vcr=vcr_row,
        appearances=appearances,
    )
    if issue is not None or terminals is None or transfers is None:
        raise ValueError(issue or "terminal_batch_unresolved")

    captured = [
        ship_id
        for ship_id, terminal in terminals.items()
        if terminal.get("captured") is True
    ]
    if len(captured) != 1:
        raise ValueError(f"expected one captured ship at VCR {vcr_row['vcr_id']}, got {captured}")
    prize_id = int(captured[0])

    pair = vcr_row.get("pair")
    if not isinstance(pair, tuple) or len(pair) != 2:
        raise ValueError("capture VCR pair malformed")
    captor_id = int(pair[1]) if int(pair[0]) == prize_id else int(pair[0])

    transfer = transfers.get(prize_id)
    if transfer is None:
        raise ValueError("capture transfer missing")

    prize_appearance = appearances.get(
        (game_id, battle_turn, int(vcr_row["vcr_id"]), prize_id)
    )
    captor_appearance = appearances.get(
        (game_id, battle_turn, int(vcr_row["vcr_id"]), captor_id)
    )
    if not isinstance(prize_appearance, Mapping) or not isinstance(captor_appearance, Mapping):
        raise ValueError("capture appearance missing")

    hull_id = prize_appearance.get("hull_id")
    if isinstance(hull_id, bool) or not isinstance(hull_id, int) or hull_id <= 0:
        raise ValueError("captured prize hull unresolved")

    return {
        "prize_id": prize_id,
        "captor_id": captor_id,
        "new_owner_id": transfer.new_owner_id,
        "new_race_id": transfer.new_race_id,
        "prize_hull_id": int(hull_id),
        "terminals": terminals,
        "transfers": transfers,
    }


def _pair_disposition(
    *,
    game_id: int,
    before_turn: int,
    prize_id: int,
    prize_owner: int,
    prize_race: int,
    prize_hull: int,
    candidate_id: int,
    candidate_row: Mapping[str, Any],
    predictions: Mapping[int, Mapping[str, Any]],
    start_stacks: Mapping[str, Any],
) -> tuple[str, str | None]:
    entry = predictions.get(candidate_id)
    prize_entry = predictions.get(prize_id)
    if not isinstance(entry, Mapping) or not isinstance(prize_entry, Mapping):
        return "unresolved", "prediction_missing"

    candidate_raw = entry.get("raw")
    prize_old_raw = prize_entry.get("raw")
    if not isinstance(candidate_raw, Mapping) or not isinstance(prize_old_raw, Mapping):
        return "unresolved", "tminus1_orders_missing"

    candidate_owner = entry.get("owner_id")
    candidate_hull = entry.get("hull_id")
    if (
        isinstance(candidate_owner, bool)
        or not isinstance(candidate_owner, int)
        or candidate_owner <= 0
        or isinstance(candidate_hull, bool)
        or not isinstance(candidate_hull, int)
        or candidate_hull <= 0
    ):
        return "unresolved", "candidate_identity_unresolved"

    candidate_race = entry.get("race_id")
    strict_permission = candidate_row.get("strict_permission")
    if strict_permission is not True:
        return "unresolved", "strict_permission_not_true"

    prize_interference = pair_module._interference_state(
        game_id=game_id,
        before_turn=before_turn,
        owner_id=prize_owner,
        raw=prize_old_raw,
        start_stacks=start_stacks,
    )
    candidate_interference = pair_module._interference_state(
        game_id=game_id,
        before_turn=before_turn,
        owner_id=int(candidate_owner),
        raw=candidate_raw,
        start_stacks=start_stacks,
    )

    old_fc = prize_old_raw.get("friendlycode")
    fresh_fc = pair_module._nonmatching_symbolic_fc(candidate_raw.get("friendlycode"))

    def decide(prize_fc: Any):
        prize_raw = pair_module._neutral_prize_raw(
            prize_old_raw,
            friendly_code=prize_fc,
        )
        prize_side = _candidate_input(
            game_id=game_id,
            ship_id=prize_id,
            owner_id=prize_owner,
            raw=prize_raw,
            race_id=prize_race,
            hull_id=prize_hull,
            hull_can_cloak=(
                bool(prize_entry.get("hull_can_cloak"))
                if isinstance(prize_entry.get("hull_can_cloak"), bool)
                else None
            ),
            diplomacy_allows_attack=False,
            interference_protected=prize_interference,
        )
        candidate_side = _candidate_input(
            game_id=game_id,
            ship_id=candidate_id,
            owner_id=int(candidate_owner),
            raw=candidate_raw,
            race_id=(
                int(candidate_race)
                if isinstance(candidate_race, int)
                and not isinstance(candidate_race, bool)
                and candidate_race > 0
                else None
            ),
            hull_id=int(candidate_hull),
            hull_can_cloak=(
                bool(entry.get("hull_can_cloak"))
                if isinstance(entry.get("hull_can_cloak"), bool)
                else None
            ),
            diplomacy_allows_attack=True,
            interference_protected=candidate_interference,
        )
        return decide_ship_combat_pair(
            left=prize_side,
            right=candidate_side,
            same_location=True,
        )

    preserved = decide(old_fc)
    fresh = decide(fresh_fc)

    preserved_eligible = preserved.engagement_eligible
    fresh_eligible = fresh.engagement_eligible
    if preserved_eligible is True and fresh_eligible is True:
        if (
            preserved.phase == fresh.phase
            and preserved.prestandard_kind == fresh.prestandard_kind
        ):
            return "eligible", None
        return "unresolved", "pair_phase_fc_sensitive"

    if preserved_eligible is False and fresh_eligible is False:
        return "pair_blocked", "pair_ineligible_under_both_fc_bounds"

    return "unresolved", "pair_eligibility_fc_sensitive_or_unknown"


def run(args: argparse.Namespace) -> dict[str, Any]:
    connection, database_path = connect_compact_generation_read_only(
        args.corpus_db_generation,
        args.corpus_db_root,
    )
    try:
        appearances_list, appearance_summary = (
            o_layer_module._collect_targeted_appearances_from_db(
                connection=connection,
                game_id=args.game_id,
                battle_turns={args.battle_turn},
            )
        )
        appearances = _appearance_map(appearances_list)
        site_key = (args.game_id, args.battle_turn, args.x, args.y)
        captured_context: dict[str, Any] = {}

        def observer(context: Mapping[str, Any]) -> None:
            key = (
                int(context["game_id"]),
                int(context["battle_turn"]),
                int(context["x"]),
                int(context["y"]),
            )
            if key == site_key:
                captured_context.update(dict(context))

        visit_summary = o_layer_module._visit_targeted_site_contexts(
            connection=connection,
            game_id=args.game_id,
            targets={site_key: ()},
            appearances=appearances_list,
            observer=observer,
        )
    finally:
        connection.close()

    if not captured_context:
        raise ValueError("target site context missing")

    factual_queue = captured_context.get("factual_queue")
    if not isinstance(factual_queue, Sequence) or isinstance(factual_queue, (str, bytes)):
        raise ValueError("factual queue missing")

    current = next(
        (
            row for row in factual_queue
            if isinstance(row, Mapping) and row.get("vcr_id") == args.capture_vcr_id
        ),
        None,
    )
    if not isinstance(current, Mapping):
        raise ValueError(f"VCR {args.capture_vcr_id} missing from target site queue")

    identity = _terminal_capture_identity(
        game_id=args.game_id,
        battle_turn=args.battle_turn,
        vcr_row=current,
        appearances=appearances,
    )
    prize_id = int(identity["prize_id"])
    captor_id = int(identity["captor_id"])

    capture = {
        "from_vcr_id": args.capture_vcr_id,
        "to_vcr_id": args.capture_vcr_id + 1,
        "ship_id": prize_id,
        "captor_ship_id": captor_id,
        "captor_owner_id": int(identity["new_owner_id"]),
        "current_opponent_ship_id": SENTINEL_HELDOUT_OPPONENT_ID,
    }
    active_result = active_module._simulate_capture(
        context=captured_context,
        capture=capture,
        appearances=appearances,
    )
    if active_result.get("status") != "resolved":
        return {
            "schema": SCHEMA,
            "status": "unresolved",
            "reason": active_result.get("reason"),
            "active_result": active_result,
        }

    order = _fixture_order(game_id=args.game_id, turn=args.battle_turn)
    if prize_id not in order or captor_id not in order:
        raise ValueError("capture pair missing from frozen site order")

    active_ids = {
        int(value)
        for value in active_result.get("active_ship_ids", [])
        if isinstance(value, int) and not isinstance(value, bool)
    }
    candidates = {
        int(row["ship_id"]): row
        for row in active_result.get("candidates", [])
        if isinstance(row, Mapping)
        and isinstance(row.get("ship_id"), int)
        and not isinstance(row.get("ship_id"), bool)
    }
    unresolved_foreign = {
        int(row["ship_id"]): str(row.get("reason") or "unresolved_foreign_candidate")
        for row in active_result.get("unresolved_foreign_candidates", [])
        if isinstance(row, Mapping)
        and isinstance(row.get("ship_id"), int)
        and not isinstance(row.get("ship_id"), bool)
    }
    occurrences = _pair_occurrences(
        factual_queue,
        through_vcr_id=args.capture_vcr_id,
    )
    predictions = captured_context.get("predictions")
    start_stacks = captured_context.get("start_stacks")
    if not isinstance(predictions, Mapping) or not isinstance(start_stacks, Mapping):
        raise ValueError("prediction/start-stack context missing")

    states: dict[int, CandidateState] = {}
    state_details: dict[str, Any] = {}
    for ship_id in order:
        if ship_id == prize_id:
            continue
        pair = (prize_id, ship_id) if prize_id < ship_id else (ship_id, prize_id)
        prior = int(occurrences.get(pair, 0))

        if ship_id not in active_ids:
            disposition, reason = "inactive", None
        elif prior >= 2:
            disposition, reason = "pair_exhausted", None
        elif ship_id in unresolved_foreign:
            disposition, reason = "unresolved", unresolved_foreign[ship_id]
        elif ship_id not in candidates:
            disposition, reason = "same_owner", None
        else:
            row = candidates[ship_id]
            request = row.get("requests_new_owner")
            permission = row.get("strict_permission")
            if request is False:
                disposition, reason = "no_request", None
            elif request is not True:
                disposition, reason = "unresolved", "combat_request_unresolved"
            elif permission is False:
                disposition, reason = "permission_denied", None
            elif permission is not True:
                disposition, reason = "unresolved", "strict_permission_unresolved"
            else:
                disposition, reason = _pair_disposition(
                    game_id=args.game_id,
                    before_turn=int(captured_context["before_turn"]),
                    prize_id=prize_id,
                    prize_owner=int(identity["new_owner_id"]),
                    prize_race=int(identity["new_race_id"]),
                    prize_hull=int(identity["prize_hull_id"]),
                    candidate_id=ship_id,
                    candidate_row=row,
                    predictions=predictions,
                    start_stacks=start_stacks,
                )

        states[ship_id] = CandidateState(
            ship_id=ship_id,
            disposition=disposition,
            reason=reason,
        )
        state_details[str(ship_id)] = {
            "disposition": disposition,
            "reason": reason,
            "prior_pair_occurrences": prior,
        }

    selection = select_o_then_c_forward(
        order=order,
        prize_ship_id=prize_id,
        captor_ship_id=captor_id,
        states=states,
    )

    status = (
        "IMMEDIATE_CONTINUATION_RESOLVED"
        if selection.status == "resolved"
        else (
            "NO_IMMEDIATE_CONTINUATION_PARENT_RESUME_REQUIRED"
            if selection.status == "no_pair"
            else "IMMEDIATE_CONTINUATION_UNRESOLVED"
        )
    )

    return {
        "schema": SCHEMA,
        "status": status,
        "evidence_status": "HELD_OUT_NEXT_PAIR_NOT_USED",
        "database_path": str(database_path),
        "target": {
            "game_id": args.game_id,
            "battle_turn": args.battle_turn,
            "x": args.x,
            "y": args.y,
            "capture_vcr_id": args.capture_vcr_id,
        },
        "capture": {
            "prize_ship_id": prize_id,
            "captor_ship_id": captor_id,
            "new_owner_id": identity["new_owner_id"],
            "new_race_id": identity["new_race_id"],
            "prize_hull_id": identity["prize_hull_id"],
        },
        "frozen_order": list(order),
        "active_after_capture": active_result.get("active_ship_ids"),
        "mutation_trace": active_result.get("mutation_trace"),
        "candidate_states": state_details,
        "selection": {
            "status": selection.status,
            "branch": selection.branch,
            "predicted_ship_id": selection.predicted_ship_id,
            "unresolved_ship_id": selection.unresolved_ship_id,
            "reason": selection.reason,
            "trace": list(selection.trace),
        },
        "appearance_summary": appearance_summary,
        "visit_summary": visit_summary,
        "held_out_boundary": (
            "No VCR N+1 ship id, pair, side or terminal state is consumed by the "
            "capture mutation, candidate-state reconstruction, or O/C selector. "
            "The active-membership helper receives a sentinel comparator id only "
            "to satisfy its historical report shape."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-db-root", type=Path, required=True)
    parser.add_argument("--corpus-db-generation", required=True)
    parser.add_argument("--game-id", type=int, default=400330)
    parser.add_argument("--battle-turn", type=int, default=141)
    parser.add_argument("--x", type=int, default=1674)
    parser.add_argument("--y", type=int, default=2363)
    parser.add_argument("--capture-vcr-id", type=int, default=593)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("===== CAPTURE IMMEDIATE CONTINUATION GATE =====")
    print(f"target:    {report.get('target')}")
    print(f"capture:   {report.get('capture')}")
    print(f"status:    {report.get('status')}")
    print(f"selection: {report.get('selection')}")
    print(f"output:    {args.output}")

    return 0 if report.get("status") != "IMMEDIATE_CONTINUATION_UNRESOLVED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
