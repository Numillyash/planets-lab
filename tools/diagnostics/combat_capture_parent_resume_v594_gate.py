#!/usr/bin/env python3
"""Held-out parent-queue resume gate after exhausted capture continuation.

Default target:
    game 400330 / turn 141 / site (1674, 2363)
    capture VCR 593
    held-out comparator VCR 594

Evidence boundary:

* the V593 immediate-continuation gate is evaluated first and must return
  NO_IMMEDIATE_CONTINUATION_PARENT_RESUME_REQUIRED;
* T-1 site inputs and relations are used for non-prize ships;
* every diplomacy calibration row from battle turn 141 is removed before
  candidate evaluation;
* factual queue history is consumed only through V593 when building pair
  occurrence and first-pass side history;
* the captured prize's temporary capture order is removed from parent
  selection only after its immediate O/C gate has definitely exhausted with
  no unresolved dependency;
* V594 pair/sides are read only after a parent selection has been produced,
  solely as the comparator.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from itertools import combinations
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.rules.combat.host_queue import (
    StandardQueueState,
    select_next_plain_standard,
)
from planets_lab.rules.combat.queue import InitialStandardPairInput
from planets_lab.rules.combat.selection import decide_ship_combat_pair

import combat_capture_immediate_continuation_gate as immediate_gate
import combat_host_initial_standard_target_audit as baseline_module
import combat_public_capture_o_layer_probe as o_layer_module
from combat_host_candidate_set_audit import (
    _independent_permission,
    _relation_signature,
    _requests_combat,
)


SCHEMA = "planets-lab.capture-parent-resume-v594-gate.v1"


def _pair(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _filtered_controls(
    controls: Mapping[Any, Any],
    *,
    excluded_battle_turn: int,
) -> dict[Any, set[Any]]:
    """Remove every calibration row from the target battle turn.

    This is intentionally broader than pair-specific held-out exclusion.  The
    held-out V594 pair is therefore not needed even negatively to prepare
    diplomacy permission.
    """

    filtered: dict[Any, set[Any]] = {}
    for key, rows in controls.items():
        if not isinstance(rows, set):
            rows = set(rows)
        filtered[key] = {
            row
            for row in rows
            if (
                not isinstance(row, tuple)
                or not row
                or row[0] != excluded_battle_turn
            )
        }
    return filtered


def _queue_state_through(
    factual_queue: Sequence[Mapping[str, Any]],
    *,
    through_vcr_id: int,
) -> StandardQueueState:
    occurrences: dict[tuple[int, int], int] = {}
    first_sides: dict[tuple[int, int], tuple[int, int]] = {}

    for row in factual_queue:
        vcr_id = row.get("vcr_id")
        if (
            isinstance(vcr_id, bool)
            or not isinstance(vcr_id, int)
            or vcr_id > through_vcr_id
        ):
            continue

        left = row.get("left_ship_id")
        right = row.get("right_ship_id")
        pair_raw = row.get("pair")
        if (
            isinstance(left, bool)
            or not isinstance(left, int)
            or isinstance(right, bool)
            or not isinstance(right, int)
            or not isinstance(pair_raw, tuple)
            or len(pair_raw) != 2
        ):
            raise ValueError(f"VCR {vcr_id}: factual queue row malformed")

        pair = _pair(int(pair_raw[0]), int(pair_raw[1]))
        if set(pair) != {int(left), int(right)}:
            raise ValueError(f"VCR {vcr_id}: pair/side identity mismatch")

        prior = occurrences.get(pair, 0)
        occurrence = prior + 1
        if occurrence > 2:
            raise ValueError(
                f"VCR {vcr_id}: pair {pair} exceeds supported occurrence cap"
            )
        occurrences[pair] = occurrence

        if occurrence == 1:
            first_sides[pair] = (int(left), int(right))
        else:
            anchor = first_sides.get(pair)
            if anchor is None:
                raise ValueError(
                    f"VCR {vcr_id}: second occurrence missing first-pass side anchor"
                )
            if (int(left), int(right)) != (anchor[1], anchor[0]):
                raise ValueError(
                    f"VCR {vcr_id}: second occurrence not factual side reversal"
                )

    return StandardQueueState(
        pair_occurrences=occurrences,
        first_pass_sides=first_sides,
    )


def _pair_inputs_for_parent(
    *,
    context: Mapping[str, Any],
    active_parent_ids: set[int],
    excluded_battle_turn: int,
) -> tuple[list[InitialStandardPairInput], dict[str, Any]]:
    predictions = context.get("predictions")
    relations = context.get("relations")
    controls_raw = context.get("controls")
    start_stacks = context.get("start_stacks")
    before_turn = context.get("before_turn")
    game_id = context.get("game_id")

    if (
        not isinstance(predictions, Mapping)
        or not isinstance(relations, Mapping)
        or not isinstance(controls_raw, Mapping)
        or not isinstance(start_stacks, Mapping)
        or isinstance(before_turn, bool)
        or not isinstance(before_turn, int)
        or isinstance(game_id, bool)
        or not isinstance(game_id, int)
    ):
        raise ValueError("parent queue site context incomplete")

    controls = _filtered_controls(
        controls_raw,
        excluded_battle_turn=excluded_battle_turn,
    )

    rows: dict[int, Mapping[str, Any]] = {}
    for ship_id in sorted(active_parent_ids):
        entry = predictions.get(ship_id)
        if not isinstance(entry, Mapping):
            raise ValueError(f"ship {ship_id}: T-1 prediction missing")
        owner_id = entry.get("owner_id")
        raw = entry.get("raw")
        if (
            isinstance(owner_id, bool)
            or not isinstance(owner_id, int)
            or owner_id <= 0
            or not isinstance(raw, Mapping)
        ):
            raise ValueError(f"ship {ship_id}: T-1 identity/orders missing")
        rows[ship_id] = entry

    inputs: list[InitialStandardPairInput] = []
    diagnostics: dict[str, Any] = {
        "pair_rows": [],
        "diplomacy_target_turn_excluded": excluded_battle_turn,
    }

    for a_id, b_id in combinations(sorted(rows), 2):
        a = rows[a_id]
        b = rows[b_id]
        a_owner = int(a["owner_id"])
        b_owner = int(b["owner_id"])
        if a_owner == b_owner:
            continue

        signature = _relation_signature(
            relations.get(int(before_turn), {}),
            a_owner,
            b_owner,
        )
        a_request = _requests_combat(a["raw"], b_owner)
        b_request = _requests_combat(b["raw"], a_owner)

        a_permission = _independent_permission(
            request=a_request,
            owner_id=a_owner,
            opponent_owner_id=b_owner,
            signature=signature,
            controls=controls,
            excluded_rows=frozenset(),
        )
        b_permission = _independent_permission(
            request=b_request,
            owner_id=b_owner,
            opponent_owner_id=a_owner,
            signature=signature,
            controls=controls,
            excluded_rows=frozenset(),
        )

        a_interference = baseline_module._interference_state(
            game_id=int(game_id),
            before_turn=int(before_turn),
            owner_id=a_owner,
            raw=a["raw"],
            start_stacks=start_stacks,
        )
        b_interference = baseline_module._interference_state(
            game_id=int(game_id),
            before_turn=int(before_turn),
            owner_id=b_owner,
            raw=b["raw"],
            start_stacks=start_stacks,
        )

        a_side = baseline_module._candidate_input(
            game_id=int(game_id),
            ship_id=a_id,
            owner_id=a_owner,
            raw=a["raw"],
            race_id=a.get("race_id"),
            hull_id=a.get("hull_id"),
            hull_can_cloak=a.get("hull_can_cloak"),
            diplomacy_allows_attack=a_permission,
            interference_protected=a_interference,
        )
        b_side = baseline_module._candidate_input(
            game_id=int(game_id),
            ship_id=b_id,
            owner_id=b_owner,
            raw=b["raw"],
            race_id=b.get("race_id"),
            hull_id=b.get("hull_id"),
            hull_can_cloak=b.get("hull_can_cloak"),
            diplomacy_allows_attack=b_permission,
            interference_protected=b_interference,
        )

        decision = decide_ship_combat_pair(
            left=a_side,
            right=b_side,
            same_location=True,
        )
        inputs.append(
            InitialStandardPairInput(
                left=a_side,
                right=b_side,
                decision=decision,
            )
        )
        diagnostics["pair_rows"].append(
            {
                "pair": [a_id, b_id],
                "owners": [a_owner, b_owner],
                "requests": [a_request, b_request],
                "permissions": [a_permission, b_permission],
                "engagement_eligible": decision.engagement_eligible,
                "phase": decision.phase,
                "prestandard_kind": decision.prestandard_kind,
            }
        )

    return inputs, diagnostics


def _target_context(
    *,
    connection: Any,
    game_id: int,
    battle_turn: int,
    x: int,
    y: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], Mapping[str, Any], Mapping[str, Any]]:
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


def run(args: argparse.Namespace) -> dict[str, Any]:
    immediate_args = argparse.Namespace(
        corpus_db_root=args.corpus_db_root,
        corpus_db_generation=args.corpus_db_generation,
        game_id=args.game_id,
        battle_turn=args.battle_turn,
        x=args.x,
        y=args.y,
        capture_vcr_id=args.capture_vcr_id,
        output=Path("/dev/null"),
    )
    immediate = immediate_gate.run(immediate_args)
    if immediate.get("status") != "NO_IMMEDIATE_CONTINUATION_PARENT_RESUME_REQUIRED":
        return {
            "schema": SCHEMA,
            "status": "PARENT_RESUME_PRECONDITION_NOT_MET",
            "immediate_continuation": immediate,
        }

    prize_id = int(immediate["capture"]["prize_ship_id"])
    active_after_capture = {
        int(value)
        for value in immediate.get("active_after_capture", [])
        if isinstance(value, int) and not isinstance(value, bool)
    }
    if prize_id not in active_after_capture:
        raise ValueError("captured prize missing from physical active set")

    unresolved_states = [
        [ship_id, row]
        for ship_id, row in immediate.get("candidate_states", {}).items()
        if isinstance(row, Mapping) and row.get("disposition") == "unresolved"
    ]
    if unresolved_states:
        return {
            "schema": SCHEMA,
            "status": "PARENT_RESUME_UNRESOLVED_PRIZE_DEPENDENCY",
            "unresolved_prize_candidates": unresolved_states,
            "immediate_continuation": immediate,
        }

    # The prize remains physically active, but its temporary capture-order has
    # been proven exhausted.  Excluding it from parent STANDARD selection is the
    # bounded orchestration hypothesis under test.  All prize pair states are
    # already definitely same-owner/no-request/inactive/exhausted, not unknown.
    active_parent_ids = set(active_after_capture)
    active_parent_ids.remove(prize_id)

    connection, database_path = connect_compact_generation_read_only(
        args.corpus_db_generation,
        args.corpus_db_root,
    )
    try:
        context, _appearances, appearance_summary, visit_summary = _target_context(
            connection=connection,
            game_id=args.game_id,
            battle_turn=args.battle_turn,
            x=args.x,
            y=args.y,
        )
    finally:
        connection.close()

    factual_queue = context.get("factual_queue")
    if not isinstance(factual_queue, Sequence) or isinstance(factual_queue, (str, bytes)):
        raise ValueError("factual queue missing")

    state = _queue_state_through(
        factual_queue,
        through_vcr_id=args.capture_vcr_id,
    )
    pair_inputs, pair_diagnostics = _pair_inputs_for_parent(
        context=context,
        active_parent_ids=active_parent_ids,
        excluded_battle_turn=args.battle_turn,
    )

    selection = select_next_plain_standard(
        pair_inputs=pair_inputs,
        active_ship_ids=active_parent_ids,
        state=state,
    )

    predicted = {
        "engagement_available": selection.engagement_available,
        "pair": list(selection.pair) if selection.pair is not None else None,
        "occurrence_index": selection.occurrence_index,
        "left_ship_id": selection.left_ship_id,
        "right_ship_id": selection.right_ship_id,
        "inactive_pair_count": selection.inactive_pair_count,
        "exhausted_pair_count": selection.exhausted_pair_count,
        "unresolved_reasons": list(selection.unresolved_reasons),
    }

    # Held-out comparator is opened only after selection has been produced.
    comparator = next(
        (
            row
            for row in factual_queue
            if isinstance(row, Mapping)
            and row.get("vcr_id") == args.capture_vcr_id + 1
        ),
        None,
    )
    if not isinstance(comparator, Mapping):
        raise ValueError("held-out next VCR comparator missing")

    factual_pair = comparator.get("pair")
    if not isinstance(factual_pair, tuple) or len(factual_pair) != 2:
        raise ValueError("held-out comparator pair malformed")
    factual_pair_key = _pair(int(factual_pair[0]), int(factual_pair[1]))
    factual_left = int(comparator["left_ship_id"])
    factual_right = int(comparator["right_ship_id"])

    pair_exact = selection.pair == factual_pair_key
    side_exact = (
        selection.left_ship_id == factual_left
        and selection.right_ship_id == factual_right
        if selection.engagement_available is True
        else None
    )
    exact = bool(pair_exact and side_exact)

    if selection.engagement_available is None:
        status = "PARENT_RESUME_UNRESOLVED"
    elif selection.engagement_available is False:
        status = "PARENT_RESUME_NO_PAIR_MISMATCH"
    elif exact:
        status = "PARENT_RESUME_EXACT"
    else:
        status = "PARENT_RESUME_MISMATCH"

    return {
        "schema": SCHEMA,
        "status": status,
        "evidence_status": "HELD_OUT_V594_COMPARATOR",
        "database_path": str(database_path),
        "target": {
            "game_id": args.game_id,
            "battle_turn": args.battle_turn,
            "x": args.x,
            "y": args.y,
            "through_vcr_id": args.capture_vcr_id,
            "held_out_vcr_id": args.capture_vcr_id + 1,
        },
        "capture_prize_ship_id": prize_id,
        "physical_active_after_v593": sorted(active_after_capture),
        "parent_queue_active_ship_ids": sorted(active_parent_ids),
        "immediate_continuation_status": immediate["status"],
        "queue_state": {
            "pair_occurrences": {
                f"{a}-{b}": count
                for (a, b), count in sorted(state.pair_occurrences.items())
            },
            "first_pass_sides": {
                f"{a}-{b}": list(sides)
                for (a, b), sides in sorted(state.first_pass_sides.items())
            },
        },
        "prediction": predicted,
        "held_out_comparator": {
            "pair": list(factual_pair_key),
            "left_ship_id": factual_left,
            "right_ship_id": factual_right,
        },
        "pair_exact": pair_exact,
        "side_exact": side_exact,
        "exact": exact,
        "pair_input_diagnostics": pair_diagnostics,
        "appearance_summary": appearance_summary,
        "visit_summary": visit_summary,
        "held_out_boundary": (
            "All diplomacy controls from battle turn 141 are removed before "
            "candidate evaluation. Pair history consumes factual VCRs only "
            "through V593. The V594 pair and sides are read only after "
            "select_next_plain_standard returns, solely for comparison."
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

    print("===== CAPTURE PARENT QUEUE RESUME V594 =====")
    print(f"status:     {report.get('status')}")
    print(f"prediction: {report.get('prediction')}")
    print(f"factual:    {report.get('held_out_comparator')}")
    print(f"pair_exact: {report.get('pair_exact')}")
    print(f"side_exact: {report.get('side_exact')}")
    print(f"output:     {args.output}")

    return 0 if report.get("status") == "PARENT_RESUME_EXACT" else 3


if __name__ == "__main__":
    raise SystemExit(main())
