#!/usr/bin/env python3
"""History-anchored mutable capture-site loop v1.

This composes already bounded one-step gates across a contiguous factual site
sequence.  It is deliberately not yet a fully generative combat executor:
terminal VCR N is factual input for mutation, while pair N+1 is held out until
after prediction.

Supported v1 transition modes:

* capture -> immediate C continuation;
* capture -> exhausted immediate continuation -> parent STANDARD resume.

Immediate O-branch continuation fails closed in this v1 because independent
fresh coverage for O remains absent.
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

import combat_capture_immediate_continuation_gate as immediate_gate
import combat_capture_parent_resume_v594_gate as parent_resume_gate
import combat_public_capture_o_layer_probe as o_layer_module


SCHEMA = "planets-lab.capture-mutable-site-loop.v1"


def _pair(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _target_queue(
    *,
    connection: Any,
    game_id: int,
    battle_turn: int,
    x: int,
    y: int,
) -> tuple[list[Mapping[str, Any]], Mapping[str, Any], Mapping[str, Any]]:
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
    factual = captured.get("factual_queue")
    if not isinstance(factual, Sequence) or isinstance(factual, (str, bytes)):
        raise ValueError("target factual queue missing")
    return list(factual), appearance_summary, visit_summary


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


def _capture_side(
    current: Mapping[str, Any],
    *,
    prize_ship_id: int,
) -> str:
    left = current.get("left_ship_id")
    right = current.get("right_ship_id")
    if left == prize_ship_id:
        return "left"
    if right == prize_ship_id:
        return "right"
    raise ValueError(
        f"captured prize {prize_ship_id} missing from VCR {current.get('vcr_id')}"
    )


def _c_prediction(
    *,
    current: Mapping[str, Any],
    immediate: Mapping[str, Any],
) -> dict[str, Any]:
    capture = immediate.get("capture")
    selection = immediate.get("selection")
    if not isinstance(capture, Mapping) or not isinstance(selection, Mapping):
        raise ValueError("immediate continuation report incomplete")

    prize = int(capture["prize_ship_id"])
    opponent = selection.get("predicted_ship_id")
    if isinstance(opponent, bool) or not isinstance(opponent, int) or opponent <= 0:
        raise ValueError("C continuation opponent unresolved")
    if selection.get("branch") != "C":
        raise ValueError(
            "mutable-site loop v1 supports independently covered C branch only"
        )

    capture_side = _capture_side(current, prize_ship_id=prize)
    prize_next_side = "right" if capture_side == "left" else "left"
    if prize_next_side == "left":
        left, right = prize, int(opponent)
    else:
        left, right = int(opponent), prize

    return {
        "mode": "capture_immediate_C",
        "pair": list(_pair(prize, int(opponent))),
        "left_ship_id": left,
        "right_ship_id": right,
        "capture_prize_ship_id": prize,
        "capture_side": capture_side,
        "prize_next_side": prize_next_side,
        "capture_branch": "C",
    }


def _compare(
    predicted: Mapping[str, Any],
    factual_next: Mapping[str, Any],
) -> dict[str, Any]:
    factual_pair_raw = factual_next.get("pair")
    if not isinstance(factual_pair_raw, tuple) or len(factual_pair_raw) != 2:
        raise ValueError(f"VCR {factual_next.get('vcr_id')}: pair malformed")
    factual_pair = _pair(int(factual_pair_raw[0]), int(factual_pair_raw[1]))
    factual_left = int(factual_next["left_ship_id"])
    factual_right = int(factual_next["right_ship_id"])

    predicted_pair_raw = predicted.get("pair")
    predicted_pair = (
        tuple(int(value) for value in predicted_pair_raw)
        if isinstance(predicted_pair_raw, list) and len(predicted_pair_raw) == 2
        else None
    )
    pair_exact = predicted_pair == factual_pair
    side_exact = (
        predicted.get("left_ship_id") == factual_left
        and predicted.get("right_ship_id") == factual_right
    )
    return {
        "factual_pair": list(factual_pair),
        "factual_left_ship_id": factual_left,
        "factual_right_ship_id": factual_right,
        "pair_exact": pair_exact,
        "side_exact": side_exact,
        "exact": bool(pair_exact and side_exact),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    connection, database_path = connect_compact_generation_read_only(
        args.corpus_db_generation,
        args.corpus_db_root,
    )
    try:
        factual_queue, appearance_summary, visit_summary = _target_queue(
            connection=connection,
            game_id=args.game_id,
            battle_turn=args.battle_turn,
            x=args.x,
            y=args.y,
        )
    finally:
        connection.close()

    vcr_ids = [
        int(row["vcr_id"])
        for row in factual_queue
        if (
            isinstance(row, Mapping)
            and isinstance(row.get("vcr_id"), int)
            and not isinstance(row.get("vcr_id"), bool)
            and args.start_vcr_id <= int(row["vcr_id"]) <= args.end_vcr_id
        )
    ]
    if vcr_ids != list(range(args.start_vcr_id, args.end_vcr_id + 1)):
        raise ValueError(
            f"target window is not globally contiguous: observed={vcr_ids}"
        )

    transitions: list[dict[str, Any]] = []
    all_exact = True

    for current_vcr_id in range(args.start_vcr_id, args.end_vcr_id):
        current = _row_by_vcr(factual_queue, current_vcr_id)

        immediate_args = argparse.Namespace(
            corpus_db_root=args.corpus_db_root,
            corpus_db_generation=args.corpus_db_generation,
            game_id=args.game_id,
            battle_turn=args.battle_turn,
            x=args.x,
            y=args.y,
            capture_vcr_id=current_vcr_id,
            output=Path("/dev/null"),
        )
        immediate = immediate_gate.run(immediate_args)
        immediate_status = immediate.get("status")

        if immediate_status == "IMMEDIATE_CONTINUATION_RESOLVED":
            predicted = _c_prediction(
                current=current,
                immediate=immediate,
            )
            dependency_status = "resolved"
        elif (
            immediate_status
            == "NO_IMMEDIATE_CONTINUATION_PARENT_RESUME_REQUIRED"
        ):
            parent = parent_resume_gate.run(immediate_args)
            prediction = parent.get("prediction")
            if not isinstance(prediction, Mapping):
                raise ValueError(
                    f"VCR {current_vcr_id}: parent resume prediction missing"
                )
            predicted = {
                "mode": "capture_parent_resume",
                "pair": prediction.get("pair"),
                "left_ship_id": prediction.get("left_ship_id"),
                "right_ship_id": prediction.get("right_ship_id"),
                "engagement_available": prediction.get("engagement_available"),
                "occurrence_index": prediction.get("occurrence_index"),
                "unresolved_reasons": prediction.get("unresolved_reasons"),
            }
            dependency_status = parent.get("status")
            if parent.get("status") != "PARENT_RESUME_EXACT":
                # The one-step gate may already have opened its comparator, but
                # an unresolved/mismatching parent step cannot be promoted into
                # a site-loop transition.
                all_exact = False
        else:
            transitions.append(
                {
                    "from_vcr_id": current_vcr_id,
                    "to_vcr_id": current_vcr_id + 1,
                    "status": "unresolved",
                    "mode": None,
                    "immediate_status": immediate_status,
                    "immediate_selection": immediate.get("selection"),
                    "exact": None,
                }
            )
            all_exact = False
            break

        # The next factual row is opened only after the transition prediction.
        factual_next = _row_by_vcr(
            factual_queue,
            current_vcr_id + 1,
        )
        comparison = _compare(predicted, factual_next)
        if not comparison["exact"]:
            all_exact = False

        transitions.append(
            {
                "from_vcr_id": current_vcr_id,
                "to_vcr_id": current_vcr_id + 1,
                "status": "resolved",
                "mode": predicted["mode"],
                "dependency_status": dependency_status,
                "prediction": predicted,
                **comparison,
            }
        )
        if not comparison["exact"]:
            break

    expected = args.end_vcr_id - args.start_vcr_id
    evaluated = len(transitions)
    exact_count = sum(row.get("exact") is True for row in transitions)
    status = (
        "SITE_LOOP_EXACT"
        if all_exact and evaluated == expected and exact_count == expected
        else "SITE_LOOP_FAILED_OR_UNRESOLVED"
    )

    return {
        "schema": SCHEMA,
        "status": status,
        "evidence_status": "COMPOSITIONAL_HISTORY_ANCHORED",
        "database_path": str(database_path),
        "target": {
            "game_id": args.game_id,
            "battle_turn": args.battle_turn,
            "x": args.x,
            "y": args.y,
            "start_vcr_id": args.start_vcr_id,
            "end_vcr_id": args.end_vcr_id,
        },
        "window_vcr_ids": vcr_ids,
        "transitions": transitions,
        "summary": {
            "expected_transitions": expected,
            "evaluated_transitions": evaluated,
            "exact_transitions": exact_count,
            "all_exact": status == "SITE_LOOP_EXACT",
            "modes": [row.get("mode") for row in transitions],
        },
        "appearance_summary": appearance_summary,
        "visit_summary": visit_summary,
        "evidence_boundary": (
            "History-anchored compositional loop. Each factual VCR N supplies "
            "terminal/mutation history through N only. Immediate capture "
            "continuation is selected before opening N+1. If that capture cursor "
            "is exhausted, the held-out-safe parent resume gate is used. "
            "Immediate C sides use the post-prospective C-order side-flip "
            "candidate (opposite the capture side); this side rule remains a "
            "research candidate rather than independently promoted canonical "
            "mechanics. The loop does not generate combat terminal outcomes."
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

    print("===== MUTABLE CAPTURE SITE LOOP V1 =====")
    print(f"status:  {report['status']}")
    print(f"summary: {report['summary']}")
    for row in report["transitions"]:
        print(
            f"V{row['from_vcr_id']}->V{row['to_vcr_id']} "
            f"mode={row.get('mode')} "
            f"predicted={row.get('prediction', {}).get('pair')} "
            f"factual={row.get('factual_pair')} "
            f"pair_exact={row.get('pair_exact')} "
            f"side_exact={row.get('side_exact')}"
        )
    print(f"output:  {args.output}")

    return 0 if report["status"] == "SITE_LOOP_EXACT" else 3


if __name__ == "__main__":
    raise SystemExit(main())
