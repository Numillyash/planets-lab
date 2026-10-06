#!/usr/bin/env python3
"""Carried-state differential for the mutable capture site.

Unlike mutable-site-loop v1, this diagnostic reconstructs site history only
once. From the start window onward it carries SiteCombatState across factual
terminal outcomes and uses that carried state for:

* physical active membership;
* parent queue exclusions;
* pair occurrence / first-pass side history;
* temporary capture-order lifecycle.

Combat terminal outcomes remain factual inputs in this validation phase.
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
from planets_lab.rules.combat.site_executor import (
    select_parent_resume,
    select_temporary_capture_continuation,
)
from planets_lab.rules.combat.site_input_adapter import (
    build_parent_standard_pair_inputs,
    build_post_capture_candidate_states,
)
from planets_lab.rules.combat.site_state import (
    SiteCombatState,
    apply_site_terminal_batch,
    open_temporary_capture_order,
    parent_queue_active_ship_ids,
    record_factual_site_pair,
)

import combat_capture_immediate_continuation_gate as immediate_gate
import combat_host_initial_standard_target_audit as baseline_module
import combat_host_post_capture_active_membership_audit as active_module
import combat_host_post_mutation_next_pair_audit as mutation_module
import combat_public_capture_o_layer_probe as o_layer_module
from combat_host_candidate_set_audit import (
    _independent_permission,
    _relation_signature,
    _requests_combat,
)


SCHEMA = "planets-lab.site-combat-state-differential.v1"


def _pair(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _appearance_map(
    rows: Sequence[Mapping[str, Any]],
) -> dict[tuple[int, int, int, int], Mapping[str, Any]]:
    result: dict[tuple[int, int, int, int], Mapping[str, Any]] = {}
    for row in rows:
        values = tuple(row.get(key) for key in ("game_id", "turn", "vcr_id", "ship_id"))
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in values
        ):
            continue
        result[tuple(int(value) for value in values)] = row
    return result


def _target_context(
    *,
    connection: Any,
    game_id: int,
    battle_turn: int,
    x: int,
    y: int,
) -> tuple[
    dict[str, Any],
    list[Mapping[str, Any]],
    Mapping[str, Any],
    Mapping[str, Any],
]:
    appearances, appearance_summary = (
        o_layer_module._collect_targeted_appearances_from_db(
            connection=connection,
            game_id=game_id,
            battle_turns={battle_turn},
        )
    )
    key = (game_id, battle_turn, x, y)
    captured: dict[str, Any] = {}

    def observer(context: Mapping[str, Any]) -> None:
        observed = (
            int(context["game_id"]),
            int(context["battle_turn"]),
            int(context["x"]),
            int(context["y"]),
        )
        if observed == key:
            captured.update(dict(context))

    visit_summary = o_layer_module._visit_targeted_site_contexts(
        connection=connection,
        game_id=game_id,
        targets={key: ()},
        appearances=appearances,
        observer=observer,
    )
    if not captured:
        raise ValueError("target site context missing")
    return captured, appearances, appearance_summary, visit_summary


def _row_by_vcr(
    factual_queue: Sequence[Mapping[str, Any]],
    vcr_id: int,
) -> Mapping[str, Any]:
    row = next(
        (
            item
            for item in factual_queue
            if isinstance(item, Mapping) and item.get("vcr_id") == vcr_id
        ),
        None,
    )
    if not isinstance(row, Mapping):
        raise ValueError(f"VCR {vcr_id} missing from factual queue")
    return row


def _initial_state_before_window(
    *,
    context: Mapping[str, Any],
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
    start_vcr_id: int,
) -> SiteCombatState:
    game_id = int(context["game_id"])
    battle_turn = int(context["battle_turn"])
    factual_queue = context.get("factual_queue")
    predictions = context.get("predictions")
    site_rows = context.get("site_ship_rows")
    if (
        not isinstance(factual_queue, Sequence)
        or isinstance(factual_queue, (str, bytes))
        or not isinstance(predictions, Mapping)
        or not isinstance(site_rows, Mapping)
    ):
        raise ValueError("site context incomplete")

    history = [
        row
        for row in factual_queue
        if (
            isinstance(row, Mapping)
            and isinstance(row.get("vcr_id"), int)
            and not isinstance(row.get("vcr_id"), bool)
            and int(row["vcr_id"]) < start_vcr_id
        )
    ]

    initial_ids = {int(ship_id) for ship_id in site_rows}
    for row in history:
        pair_raw = row.get("pair")
        if isinstance(pair_raw, tuple) and len(pair_raw) == 2:
            initial_ids.update((int(pair_raw[0]), int(pair_raw[1])))

    active_ships: dict[int, dict[str, Any]] = {}
    for ship_id in sorted(initial_ids):
        appearance = active_module._first_appearance(
            game_id=game_id,
            battle_turn=battle_turn,
            ship_id=ship_id,
            factual_queue=history,
            appearances=appearances,
        )
        if isinstance(appearance, Mapping):
            active = mutation_module._active_ship_from_appearance(
                appearance,
                ship_id=ship_id,
            )
        else:
            entry = predictions.get(ship_id)
            if not isinstance(entry, Mapping):
                raise ValueError(f"ship {ship_id}: initial state missing")
            active = active_module._raw_active_ship(entry, ship_id=ship_id)
        active_ships[ship_id] = active

    state = SiteCombatState(active_ships=active_ships)
    for row in history:
        state = record_factual_site_pair(
            state,
            left_ship_id=int(row["left_ship_id"]),
            right_ship_id=int(row["right_ship_id"]),
        )
        terminals, transfers, issue = active_module._terminal_batch_with_transfer(
            game_id=game_id,
            battle_turn=battle_turn,
            factual_vcr=row,
            appearances=appearances,
        )
        if issue is not None or terminals is None or transfers is None:
            raise ValueError(
                f"VCR {row.get('vcr_id')}: pre-window terminal unresolved: "
                f"{issue or 'unknown'}"
            )
        transition = apply_site_terminal_batch(
            state,
            terminals_by_ship_id=terminals,
            capture_transfers_by_ship_id=transfers,
        )
        if transition.resolved is not True:
            raise ValueError(
                f"VCR {row.get('vcr_id')}: pre-window mutation unresolved: "
                f"{transition.mutation.unresolved_reasons}"
            )
        state = transition.state

    return state


def _capture_identity(
    *,
    current: Mapping[str, Any],
    terminals: Mapping[int, Mapping[str, Any]],
    transfers: Mapping[int, Any],
) -> tuple[int, int] | None:
    captured = [
        ship_id
        for ship_id, terminal in terminals.items()
        if terminal.get("captured") is True
    ]
    if not captured:
        return None
    if len(captured) != 1:
        raise ValueError(
            f"VCR {current.get('vcr_id')}: unsupported capture cardinality"
        )
    prize = int(captured[0])
    if prize not in transfers:
        raise ValueError("capture transfer missing")
    pair_raw = current.get("pair")
    if not isinstance(pair_raw, tuple) or len(pair_raw) != 2:
        raise ValueError("capture pair malformed")
    a, b = int(pair_raw[0]), int(pair_raw[1])
    if prize not in {a, b}:
        raise ValueError("captured prize missing from factual pair")
    return prize, (b if a == prize else a)


def _capture_side(
    current: Mapping[str, Any],
    *,
    prize_ship_id: int,
) -> str:
    if current.get("left_ship_id") == prize_ship_id:
        return "left"
    if current.get("right_ship_id") == prize_ship_id:
        return "right"
    raise ValueError("captured prize missing from factual sides")


def _predict_capture_continuation(
    *,
    state: SiteCombatState,
    context: Mapping[str, Any],
    current: Mapping[str, Any],
    prize_ship_id: int,
    through_vcr_id: int,
) -> tuple[dict[str, Any] | None, SiteCombatState]:
    temporary = state.temporary_capture_order
    if temporary is None:
        raise ValueError("temporary capture order missing")

    adapted = build_post_capture_candidate_states(
        state=state,
        context=context,
        prize_ship_id=prize_ship_id,
        through_vcr_id=through_vcr_id,
        requests_combat=_requests_combat,
        relation_signature=_relation_signature,
        independent_permission=_independent_permission,
        pair_disposition=immediate_gate._pair_disposition,
    )
    step = select_temporary_capture_continuation(
        state,
        candidate_states=adapted.candidate_states,
    )

    if step.status == "unresolved":
        raise ValueError(
            f"VCR {through_vcr_id}: immediate continuation unresolved: "
            f"{step.reason}"
        )
    if step.status == "parent_resume_required":
        return None, step.state
    if (
        step.branch != "C"
        or step.opponent_ship_id is None
        or step.pair is None
    ):
        raise ValueError(
            "site-state v1 capture continuation resolved without covered C pair"
        )

    opponent = int(step.opponent_ship_id)
    capture_side = _capture_side(current, prize_ship_id=prize_ship_id)
    prize_next_side = "right" if capture_side == "left" else "left"
    if prize_next_side == "left":
        left, right = prize_ship_id, opponent
    else:
        left, right = opponent, prize_ship_id

    return {
        "mode": "capture_immediate_C",
        "pair": list(_pair(prize_ship_id, opponent)),
        "left_ship_id": left,
        "right_ship_id": right,
        "capture_branch": "C",
    }, state


def _compare(
    prediction: Mapping[str, Any],
    factual_next: Mapping[str, Any],
) -> dict[str, Any]:
    pair_raw = factual_next.get("pair")
    if not isinstance(pair_raw, tuple) or len(pair_raw) != 2:
        raise ValueError("factual comparator pair malformed")
    factual_pair = _pair(int(pair_raw[0]), int(pair_raw[1]))
    predicted_pair_raw = prediction.get("pair")
    predicted_pair = (
        tuple(int(value) for value in predicted_pair_raw)
        if isinstance(predicted_pair_raw, list)
        and len(predicted_pair_raw) == 2
        else None
    )
    pair_exact = predicted_pair == factual_pair
    side_exact = (
        prediction.get("left_ship_id") == int(factual_next["left_ship_id"])
        and prediction.get("right_ship_id") == int(factual_next["right_ship_id"])
    )
    return {
        "factual_pair": list(factual_pair),
        "factual_left_ship_id": int(factual_next["left_ship_id"]),
        "factual_right_ship_id": int(factual_next["right_ship_id"]),
        "pair_exact": pair_exact,
        "side_exact": side_exact,
        "exact": bool(pair_exact and side_exact),
    }


def _state_snapshot(state: SiteCombatState) -> dict[str, Any]:
    temporary = state.temporary_capture_order
    return {
        "active_ship_ids": sorted(state.active_ships),
        "parent_queue_active_ship_ids": sorted(parent_queue_active_ship_ids(state)),
        "parent_queue_excluded_ship_ids": sorted(
            state.parent_queue_excluded_ship_ids
        ),
        "temporary_capture_order": (
            {
                "prize_ship_id": temporary.prize_ship_id,
                "captor_ship_id": temporary.captor_ship_id,
                "order": list(temporary.order),
            }
            if temporary is not None
            else None
        ),
        "pair_occurrences": {
            f"{a}-{b}": count
            for (a, b), count in sorted(
                state.standard_queue_state.pair_occurrences.items()
            )
        },
        "first_pass_sides": {
            f"{a}-{b}": list(sides)
            for (a, b), sides in sorted(
                state.standard_queue_state.first_pass_sides.items()
            )
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    connection, database_path = connect_compact_generation_read_only(
        args.corpus_db_generation,
        args.corpus_db_root,
    )
    try:
        context, appearance_rows, appearance_summary, visit_summary = _target_context(
            connection=connection,
            game_id=args.game_id,
            battle_turn=args.battle_turn,
            x=args.x,
            y=args.y,
        )
    finally:
        connection.close()

    appearances = _appearance_map(appearance_rows)
    factual_queue = context.get("factual_queue")
    if not isinstance(factual_queue, Sequence) or isinstance(
        factual_queue, (str, bytes)
    ):
        raise ValueError("factual queue missing")

    state = _initial_state_before_window(
        context=context,
        appearances=appearances,
        start_vcr_id=args.start_vcr_id,
    )
    frozen_order = immediate_gate._fixture_order(
        game_id=args.game_id,
        turn=args.battle_turn,
    )

    transitions: list[dict[str, Any]] = []
    initial_snapshot = _state_snapshot(state)

    for current_vcr_id in range(args.start_vcr_id, args.end_vcr_id):
        current = _row_by_vcr(factual_queue, current_vcr_id)

        state = record_factual_site_pair(
            state,
            left_ship_id=int(current["left_ship_id"]),
            right_ship_id=int(current["right_ship_id"]),
        )
        terminals, transfers, issue = active_module._terminal_batch_with_transfer(
            game_id=args.game_id,
            battle_turn=args.battle_turn,
            factual_vcr=current,
            appearances=appearances,
        )
        if issue is not None or terminals is None or transfers is None:
            raise ValueError(
                f"VCR {current_vcr_id}: terminal batch unresolved: "
                f"{issue or 'unknown'}"
            )

        transition = apply_site_terminal_batch(
            state,
            terminals_by_ship_id=terminals,
            capture_transfers_by_ship_id=transfers,
        )
        if transition.resolved is not True:
            raise ValueError(
                f"VCR {current_vcr_id}: site mutation unresolved: "
                f"{transition.mutation.unresolved_reasons}"
            )
        state = transition.state

        capture = _capture_identity(
            current=current,
            terminals=terminals,
            transfers=transfers,
        )
        if capture is None:
            raise ValueError(
                f"VCR {current_vcr_id}: v1 target expects capture predecessor"
            )
        prize_id, captor_id = capture
        state = open_temporary_capture_order(
            state,
            prize_ship_id=prize_id,
            captor_ship_id=captor_id,
            order=frozen_order,
        )

        prediction, state = _predict_capture_continuation(
            state=state,
            context=context,
            current=current,
            prize_ship_id=prize_id,
            through_vcr_id=current_vcr_id,
        )

        if prediction is None:
            adapted_parent = build_parent_standard_pair_inputs(
                state=state,
                context=context,
                target_battle_turn=args.battle_turn,
                through_vcr_id=current_vcr_id,
                requests_combat=_requests_combat,
                relation_signature=_relation_signature,
                independent_permission=_independent_permission,
                interference_state=baseline_module._interference_state,
                candidate_input=baseline_module._candidate_input,
            )
            pair_inputs = adapted_parent.pair_inputs
            diagnostics = adapted_parent.diagnostics
            parent_step = select_parent_resume(
                state,
                pair_inputs=pair_inputs,
            )
            if (
                parent_step.status != "resolved"
                or parent_step.pair is None
                or parent_step.left_ship_id is None
                or parent_step.right_ship_id is None
            ):
                raise ValueError(
                    f"VCR {current_vcr_id}: parent resume unresolved: "
                    f"{parent_step.reason}"
                )
            prediction = {
                "mode": "capture_parent_resume",
                "pair": list(parent_step.pair),
                "left_ship_id": parent_step.left_ship_id,
                "right_ship_id": parent_step.right_ship_id,
                "occurrence_index": parent_step.occurrence_index,
                "pair_input_count": len(pair_inputs),
                "diplomacy_cutoff_vcr_id": diagnostics[
                    "diplomacy_controls_through_vcr_id"
                ],
            }

        snapshot_after_prediction = _state_snapshot(state)

        # Factual N+1 is opened only after the carried state has produced N+1.
        factual_next = _row_by_vcr(factual_queue, current_vcr_id + 1)
        comparison = _compare(prediction, factual_next)
        transitions.append(
            {
                "from_vcr_id": current_vcr_id,
                "to_vcr_id": current_vcr_id + 1,
                "prediction": prediction,
                **comparison,
                "state_after_prediction": snapshot_after_prediction,
            }
        )
        if not comparison["exact"]:
            break

    expected = args.end_vcr_id - args.start_vcr_id
    exact_count = sum(row["exact"] is True for row in transitions)
    status = (
        "SITE_STATE_EXACT"
        if len(transitions) == expected and exact_count == expected
        else "SITE_STATE_FAILED_OR_UNRESOLVED"
    )

    return {
        "schema": SCHEMA,
        "status": status,
        "evidence_status": "CARRIED_STATE_HISTORY_ANCHORED",
        "database_path": str(database_path),
        "target": {
            "game_id": args.game_id,
            "battle_turn": args.battle_turn,
            "x": args.x,
            "y": args.y,
            "start_vcr_id": args.start_vcr_id,
            "end_vcr_id": args.end_vcr_id,
        },
        "initial_state": initial_snapshot,
        "transitions": transitions,
        "final_state": _state_snapshot(state),
        "summary": {
            "expected_transitions": expected,
            "evaluated_transitions": len(transitions),
            "exact_transitions": exact_count,
            "all_exact": status == "SITE_STATE_EXACT",
            "modes": [
                row["prediction"]["mode"]
                for row in transitions
            ],
        },
        "appearance_summary": appearance_summary,
        "visit_summary": visit_summary,
        "evidence_boundary": (
            "Site history before the target window is reconstructed once. "
            "From V592 onward, physical membership, capture exclusions, "
            "temporary capture-order lifecycle and pair history are carried in "
            "SiteCombatState. Candidate-state recomposition, temporal diplomacy "
            "cutoff and parent STANDARD pair-input assembly are delegated to the "
            "reusable evidence-scoped site_input_adapter; temporary capture "
            "lifecycle and parent selection are delegated to site_executor. "
            "Factual terminal outcomes remain injected after each observed VCR. "
            "N+1 pair/sides are opened only after selection."
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
    parser.add_argument("--start-vcr-id", type=int, default=592)
    parser.add_argument("--end-vcr-id", type=int, default=595)
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

    print("===== SITE COMBAT STATE DIFFERENTIAL V1 =====")
    print(f"status:  {report['status']}")
    print(f"summary: {report['summary']}")
    for row in report["transitions"]:
        prediction = row["prediction"]
        print(
            f"V{row['from_vcr_id']}->V{row['to_vcr_id']} "
            f"mode={prediction['mode']} "
            f"predicted={prediction['pair']} "
            f"factual={row['factual_pair']} "
            f"pair_exact={row['pair_exact']} "
            f"side_exact={row['side_exact']}"
        )
    print(f"output:  {args.output}")
    return 0 if report["status"] == "SITE_STATE_EXACT" else 3


if __name__ == "__main__":
    raise SystemExit(main())
