#!/usr/bin/env python3
"""Targeted post-capture site transition integration differential.

The first intended case is game 400330 / turn 141 / site (1674, 2363), where
two independently exact C-forward transitions surround one ordinary queue
resumption.  The tool is parameterized and fails closed outside the bounded
composition contract.

Factual VCR N contributes terminal replay state and elapsed pair history only.
The selected pair for VCR N+1 is compared only after prediction.
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping, Sequence

RESEARCH_ROOT = Path(__file__).resolve().parents[2]
RESEARCH_TOOLS = Path(__file__).resolve().parent
MAIN_DIAGNOSTICS = Path("/workspace/tools/diagnostics")
for path in (RESEARCH_ROOT, RESEARCH_TOOLS, MAIN_DIAGNOSTICS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.rules.combat.host_queue import StandardQueueState
from planets_lab.rules.combat.mutable_queue import (
    ShipCaptureTransfer,
    apply_ship_terminal_batch,
)
from planets_lab.rules.combat.queue import InitialStandardPairInput
from planets_lab.rules.combat.selection import decide_ship_combat_pair

import combat_host_initial_standard_target_audit as baseline_module
import combat_host_post_mutation_next_pair_audit as postmutation_module
import combat_public_capture_o_layer_probe as o_layer_module

from postcapture_o_c_forward_selector import CandidateState
from postcapture_site_transition_executor import (
    CaptureContinuationContext,
    record_elapsed_factual_pair,
    select_after_resolved_vcr,
)


SCHEMA = "planets-lab.postcapture-site-transition-integration.v1"


def _pair(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _load_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _selector_case_map(
    report: Mapping[str, Any],
) -> dict[tuple[int, int, int], Mapping[str, Any]]:
    result: dict[tuple[int, int, int], Mapping[str, Any]] = {}
    cases = report.get("cases")
    if not isinstance(cases, list):
        raise ValueError("selector report has no cases")
    for row in cases:
        if not isinstance(row, Mapping):
            continue
        values = (row.get("game_id"), row.get("turn"), row.get("capture_vcr_id"))
        if any(isinstance(v, bool) or not isinstance(v, int) for v in values):
            continue
        key = tuple(int(v) for v in values)
        result[key] = row
    return result


def _candidate_states_from_case(
    case: Mapping[str, Any],
) -> dict[int, CandidateState]:
    primary = case.get("primary")
    if not isinstance(primary, Mapping):
        raise ValueError("selector case has no primary result")
    details = primary.get("candidate_details")
    if not isinstance(details, Mapping):
        raise ValueError("selector case has no candidate_details")

    states: dict[int, CandidateState] = {}
    for raw_ship_id, raw in details.items():
        if not isinstance(raw, Mapping):
            continue
        try:
            ship_id = int(raw_ship_id)
        except (TypeError, ValueError):
            continue
        disposition = raw.get("disposition")
        if disposition not in {
            "inactive",
            "same_owner",
            "pair_exhausted",
            "no_request",
            "permission_denied",
            "pair_blocked",
            "eligible",
            "unresolved",
        }:
            raise ValueError(
                f"selector candidate {ship_id} has unsupported disposition "
                f"{disposition!r}"
            )
        reason = raw.get("reason")
        states[ship_id] = CandidateState(
            ship_id=ship_id,
            disposition=disposition,
            reason=str(reason) if reason is not None else None,
        )
    return states


def _appearance_map(
    rows: Sequence[Mapping[str, Any]],
) -> dict[tuple[int, int, int, int], Mapping[str, Any]]:
    return o_layer_module._appearance_mapping(rows)


def _first_appearance(
    *,
    game_id: int,
    battle_turn: int,
    ship_id: int,
    factual_queue: Sequence[Mapping[str, Any]],
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    return postmutation_module._first_appearance_for_ship(
        game_id=game_id,
        battle_turn=battle_turn,
        ship_id=ship_id,
        factual_queue=factual_queue,
        appearances=appearances,
    )


def _active_ship_from_site_row(
    *,
    row: Mapping[str, Any],
    first_appearance: Mapping[str, Any] | None,
) -> dict[str, Any]:
    ship_id = int(row["ship_id"])
    active = postmutation_module._active_ship_from_appearance(
        first_appearance,
        ship_id=ship_id,
    )
    # Queue identity starts from owner-current T-1 reconstruction, not a future
    # VCR side.  Dynamic combat values may use the first factual appearance as
    # the same bounded mutation audit did.
    active["owner_id"] = int(row["owner_id"])
    race_id = row.get("race_id")
    active["race_id"] = (
        int(race_id)
        if isinstance(race_id, int) and not isinstance(race_id, bool)
        else None
    )
    hull_id = row.get("hull_id")
    if isinstance(hull_id, int) and not isinstance(hull_id, bool) and hull_id > 0:
        active["hull_id"] = int(hull_id)
    active["federation_crew_bonus"] = active.get("race_id") == 1
    active["lizard_crew_bonus"] = active.get("race_id") == 2
    return active


def _terminal_batch_and_transfer(
    *,
    game_id: int,
    battle_turn: int,
    factual_vcr: Mapping[str, Any],
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
) -> tuple[
    dict[int, Mapping[str, Any]],
    dict[int, ShipCaptureTransfer],
    int | None,
    int | None,
]:
    vcr_id = int(factual_vcr["vcr_id"])
    pair_raw = factual_vcr.get("pair")
    if not isinstance(pair_raw, tuple) or len(pair_raw) != 2:
        raise ValueError("factual VCR pair malformed")

    terminals: dict[int, Mapping[str, Any]] = {}
    rows: dict[int, Mapping[str, Any]] = {}
    captured: list[int] = []
    for raw_ship_id in pair_raw:
        ship_id = int(raw_ship_id)
        appearance = appearances.get(
            (game_id, battle_turn, vcr_id, ship_id)
        )
        if not isinstance(appearance, Mapping):
            raise ValueError(f"VCR {vcr_id}: appearance missing for ship {ship_id}")
        terminal = appearance.get("terminal")
        if not isinstance(terminal, Mapping):
            raise ValueError(f"VCR {vcr_id}: terminal missing for ship {ship_id}")
        rows[ship_id] = appearance
        terminals[ship_id] = terminal
        if terminal.get("captured") is True:
            captured.append(ship_id)

    if len(captured) > 1:
        raise ValueError(f"VCR {vcr_id}: multiple captured ships unsupported")

    transfers: dict[int, ShipCaptureTransfer] = {}
    prize: int | None = None
    captor: int | None = None
    if captured:
        prize = captured[0]
        other = int(pair_raw[0]) if int(pair_raw[1]) == prize else int(pair_raw[1])
        captor = other
        captor_row = rows[captor]
        owner_id = captor_row.get("owner_id")
        race_id = captor_row.get("race_id")
        if (
            isinstance(owner_id, bool)
            or not isinstance(owner_id, int)
            or owner_id <= 0
            or isinstance(race_id, bool)
            or not isinstance(race_id, int)
            or race_id <= 0
        ):
            raise ValueError(f"VCR {vcr_id}: captor identity unresolved")
        transfers[prize] = ShipCaptureTransfer(
            new_owner_id=int(owner_id),
            new_race_id=int(race_id),
            new_federation_crew_bonus=int(race_id) == 1,
            new_lizard_crew_bonus=int(race_id) == 2,
        )

    return terminals, transfers, prize, captor


def _ordinary_pair_inputs(
    *,
    context: Mapping[str, Any],
    active_ships: Mapping[int, Mapping[str, Any]],
) -> tuple[list[InitialStandardPairInput] | None, str | None]:
    site_rows = context["site_ship_rows"]
    if not isinstance(site_rows, Mapping):
        return None, "site_ship_rows_missing"

    # Static T-1 pair composition is admissible only while every active ship
    # still has its T-1 owner identity.  A surviving captured ship requires a
    # future dynamic pair-recomposition layer and fails closed here.
    for ship_id, active in active_ships.items():
        source = site_rows.get(ship_id)
        if not isinstance(source, Mapping):
            continue
        if active.get("owner_id") != source.get("owner_id"):
            return None, f"active_ship_{ship_id}:dynamic_owner_requires_recomposition"

    relations = context["relations"]
    controls = context["controls"]
    start_stacks = context["start_stacks"]
    factual = context["factual"]
    before_turn = int(context["before_turn"])
    game_id = int(context["game_id"])

    active_ids = sorted(
        ship_id for ship_id in active_ships
        if ship_id in site_rows
    )
    result: list[InitialStandardPairInput] = []

    for a_id, b_id in combinations(active_ids, 2):
        a = site_rows[a_id]
        b = site_rows[b_id]
        a_owner = int(active_ships[a_id]["owner_id"])
        b_owner = int(active_ships[b_id]["owner_id"])
        if a_owner == b_owner:
            continue

        signature = baseline_module._relation_signature(
            relations.get(before_turn, {}),
            a_owner,
            b_owner,
        )
        a_request = baseline_module._requests_combat(a["raw"], b_owner)
        b_request = baseline_module._requests_combat(b["raw"], a_owner)
        pair = _pair(a_id, b_id)
        excluded = frozenset(factual["pair_rows"].get(pair, set()))

        a_strict = baseline_module._independent_permission(
            request=a_request,
            owner_id=a_owner,
            opponent_owner_id=b_owner,
            signature=signature,
            controls=controls,
            excluded_rows=excluded,
        )
        b_strict = baseline_module._independent_permission(
            request=b_request,
            owner_id=b_owner,
            opponent_owner_id=a_owner,
            signature=signature,
            controls=controls,
            excluded_rows=excluded,
        )

        a_interference = baseline_module._interference_state(
            game_id=game_id,
            before_turn=before_turn,
            owner_id=a_owner,
            raw=a["raw"],
            start_stacks=start_stacks,
        )
        b_interference = baseline_module._interference_state(
            game_id=game_id,
            before_turn=before_turn,
            owner_id=b_owner,
            raw=b["raw"],
            start_stacks=start_stacks,
        )

        a_input = baseline_module._candidate_input(
            game_id=game_id,
            ship_id=a_id,
            owner_id=a_owner,
            raw=a["raw"],
            race_id=a.get("race_id"),
            hull_id=a.get("hull_id"),
            hull_can_cloak=a.get("hull_can_cloak"),
            diplomacy_allows_attack=a_strict,
            interference_protected=a_interference,
        )
        b_input = baseline_module._candidate_input(
            game_id=game_id,
            ship_id=b_id,
            owner_id=b_owner,
            raw=b["raw"],
            race_id=b.get("race_id"),
            hull_id=b.get("hull_id"),
            hull_can_cloak=b.get("hull_can_cloak"),
            diplomacy_allows_attack=b_strict,
            interference_protected=b_interference,
        )
        result.append(
            InitialStandardPairInput(
                left=a_input,
                right=b_input,
                decision=decide_ship_combat_pair(
                    left=a_input,
                    right=b_input,
                    same_location=True,
                ),
            )
        )

    return result, None


def _capture_context(
    *,
    selector_case: Mapping[str, Any],
    prize_ship_id: int,
    captor_ship_id: int,
) -> CaptureContinuationContext:
    order_raw = selector_case.get("external_order")
    if (
        not isinstance(order_raw, list)
        or any(isinstance(v, bool) or not isinstance(v, int) for v in order_raw)
    ):
        raise ValueError("selector case external order malformed")
    if int(selector_case.get("captured_ship_id", -1)) != prize_ship_id:
        raise ValueError("selector case prize mismatch")
    if int(selector_case.get("captor_ship_id", -1)) != captor_ship_id:
        raise ValueError("selector case captor mismatch")
    return CaptureContinuationContext(
        order=tuple(int(v) for v in order_raw),
        prize_ship_id=prize_ship_id,
        captor_ship_id=captor_ship_id,
        states=_candidate_states_from_case(selector_case),
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    selector_report = _load_json(args.selector_report)
    selector_cases = _selector_case_map(selector_report)

    connection, database_path = connect_compact_generation_read_only(
        args.corpus_db_generation,
        args.corpus_db_root,
    )
    try:
        appearances, appearance_summary = (
            o_layer_module._collect_targeted_appearances_from_db(
                connection=connection,
                game_id=args.game_id,
                battle_turns={args.battle_turn},
            )
        )
        appearance_by_key = _appearance_map(appearances)
        target_key = (
            args.game_id,
            args.battle_turn,
            args.x,
            args.y,
        )
        captured_context: dict[str, Any] = {}

        def observer(context: Mapping[str, Any]) -> None:
            if (
                int(context["game_id"]),
                int(context["battle_turn"]),
                int(context["x"]),
                int(context["y"]),
            ) == target_key:
                captured_context.update(dict(context))

        visit_summary = o_layer_module._visit_targeted_site_contexts(
            connection=connection,
            game_id=args.game_id,
            targets={target_key: ()},
            appearances=appearances,
            observer=observer,
        )
    finally:
        connection.close()

    if not captured_context:
        raise ValueError("target site context was not reconstructed")

    factual_queue = captured_context.get("factual_queue")
    site_rows = captured_context.get("site_ship_rows")
    if (
        not isinstance(factual_queue, Sequence)
        or isinstance(factual_queue, (str, bytes))
        or not isinstance(site_rows, Mapping)
    ):
        raise ValueError("target site queue/context incomplete")

    window = [
        row for row in factual_queue
        if args.start_vcr <= int(row["vcr_id"]) <= args.end_vcr
    ]
    if len(window) < 2:
        raise ValueError("target VCR window has fewer than two engagements")
    ids = [int(row["vcr_id"]) for row in window]
    if ids[0] != args.start_vcr or ids[-1] != args.end_vcr:
        raise ValueError(
            f"target VCR window mismatch: observed={ids} "
            f"expected={args.start_vcr}..{args.end_vcr}"
        )
    if any(b != a + 1 for a, b in zip(ids, ids[1:])):
        raise ValueError(f"target VCR window is not globally adjacent: {ids}")

    active_ships: dict[int, dict[str, Any]] = {}
    for raw_ship_id, source in site_rows.items():
        ship_id = int(raw_ship_id)
        first = _first_appearance(
            game_id=args.game_id,
            battle_turn=args.battle_turn,
            ship_id=ship_id,
            factual_queue=factual_queue,
            appearances=appearance_by_key,
        )
        active_ships[ship_id] = _active_ship_from_site_row(
            row=source,
            first_appearance=first,
        )

    queue_state = StandardQueueState()
    for row in factual_queue:
        if int(row["vcr_id"]) >= args.start_vcr:
            break
        recorded = record_elapsed_factual_pair(
            queue_state,
            left_ship_id=int(row["left_ship_id"]),
            right_ship_id=int(row["right_ship_id"]),
        )
        if recorded.state is None:
            raise ValueError(
                f"pre-window pair history unresolved at VCR {row['vcr_id']}: "
                f"{recorded.reason}"
            )
        queue_state = recorded.state

    transitions: list[dict[str, Any]] = []
    exact_count = 0

    for current, factual_next in zip(window, window[1:]):
        terminals, transfers, prize, captor = _terminal_batch_and_transfer(
            game_id=args.game_id,
            battle_turn=args.battle_turn,
            factual_vcr=current,
            appearances=appearance_by_key,
        )

        elapsed = record_elapsed_factual_pair(
            queue_state,
            left_ship_id=int(current["left_ship_id"]),
            right_ship_id=int(current["right_ship_id"]),
        )
        if elapsed.state is None:
            raise ValueError(
                f"VCR {current['vcr_id']}: elapsed history unresolved: "
                f"{elapsed.reason}"
            )
        queue_state = elapsed.state

        mutation = apply_ship_terminal_batch(
            active_ships=active_ships,
            terminals_by_ship_id=terminals,
            capture_transfers_by_ship_id=transfers,
        )
        if mutation.resolved is not True:
            transition = {
                "from_vcr": int(current["vcr_id"]),
                "to_vcr": int(factual_next["vcr_id"]),
                "status": "mutation_unresolved",
                "reasons": list(mutation.unresolved_reasons),
                "exact": None,
            }
            transitions.append(transition)
            break

        capture_context = None
        pair_inputs: list[InitialStandardPairInput] = []
        source_expected = "ordinary_queue"
        if prize is not None:
            selector_case = selector_cases.get(
                (args.game_id, args.battle_turn, int(current["vcr_id"]))
            )
            if selector_case is None:
                transition = {
                    "from_vcr": int(current["vcr_id"]),
                    "to_vcr": int(factual_next["vcr_id"]),
                    "status": "capture_selector_case_missing",
                    "exact": None,
                }
                transitions.append(transition)
                break
            capture_context = _capture_context(
                selector_case=selector_case,
                prize_ship_id=prize,
                captor_ship_id=int(captor),
            )
            source_expected = "capture_cursor"
        else:
            pair_inputs_value, issue = _ordinary_pair_inputs(
                context=captured_context,
                active_ships=mutation.active_ships,
            )
            if issue is not None or pair_inputs_value is None:
                transition = {
                    "from_vcr": int(current["vcr_id"]),
                    "to_vcr": int(factual_next["vcr_id"]),
                    "status": "ordinary_pair_recomposition_unresolved",
                    "reason": issue,
                    "exact": None,
                }
                transitions.append(transition)
                break
            pair_inputs = pair_inputs_value

        selected = select_after_resolved_vcr(
            mutation=mutation,
            queue_state=queue_state,
            ordinary_pair_inputs=pair_inputs,
            capture_context=capture_context,
        )
        factual_pair = _pair(
            int(factual_next["left_ship_id"]),
            int(factual_next["right_ship_id"]),
        )
        pair_exact = selected.pair == factual_pair
        if selected.status == "resolved" and pair_exact:
            exact_count += 1

        side_exact: bool | None = None
        if selected.source == "ordinary_queue" and selected.status == "resolved":
            side_exact = (
                selected.predicted_left_ship_id == int(factual_next["left_ship_id"])
                and selected.predicted_right_ship_id == int(factual_next["right_ship_id"])
            )

        transitions.append(
            {
                "from_vcr": int(current["vcr_id"]),
                "to_vcr": int(factual_next["vcr_id"]),
                "predecessor_terminal": "capture" if prize is not None else "ordinary",
                "selection_source": selected.source,
                "expected_source": source_expected,
                "capture_branch": selected.branch,
                "factual_pair": list(factual_pair),
                "predicted_pair": (
                    list(selected.pair) if selected.pair is not None else None
                ),
                "pair_exact": pair_exact if selected.status == "resolved" else None,
                "ordinary_side_exact": side_exact,
                "predicted_ordinary_occurrence": selected.ordinary_occurrence_index,
                "status": selected.status,
                "reason": selected.reason,
                "active_after_mutation": sorted(mutation.active_ships),
                "removed_ship_ids": list(mutation.removed_ship_ids),
                "captured_ship_ids": list(mutation.captured_ship_ids),
            }
        )

        if selected.status != "resolved" or not pair_exact:
            break
        active_ships = mutation.active_ships

    complete = len(transitions) == len(window) - 1
    all_pair_exact = (
        complete
        and exact_count == len(transitions)
        and all(row.get("pair_exact") is True for row in transitions)
    )
    ordinary_rows = [
        row for row in transitions
        if row.get("selection_source") == "ordinary_queue"
    ]
    capture_rows = [
        row for row in transitions
        if row.get("selection_source") == "capture_cursor"
    ]

    return {
        "schema": SCHEMA,
        "evidence_status": "OPEN_POPULATION_INTEGRATION",
        "database_path": str(database_path),
        "target": {
            "game_id": args.game_id,
            "battle_turn": args.battle_turn,
            "x": args.x,
            "y": args.y,
            "start_vcr": args.start_vcr,
            "end_vcr": args.end_vcr,
        },
        "appearance_summary": appearance_summary,
        "visit_summary": visit_summary,
        "window_vcr_ids": ids,
        "transitions": transitions,
        "summary": {
            "expected_transitions": len(window) - 1,
            "transitions_evaluated": len(transitions),
            "pair_exact": exact_count,
            "pair_mismatch_or_unresolved": len(transitions) - exact_count,
            "capture_cursor_transitions": len(capture_rows),
            "ordinary_queue_transitions": len(ordinary_rows),
            "all_pair_exact": all_pair_exact,
        },
        "evidence_boundary": (
            "Open-population integration differential. Factual VCR N supplies "
            "only terminal replay state and elapsed pair history. Capture "
            "predecessors use the previously frozen O/C selector state from the "
            "independent selector report. Ordinary predecessors use production "
            "STANDARD post-mutation selection over T-1 pair inputs filtered by "
            "the mutated active set. A surviving ship whose owner changed after "
            "T-1 fails closed on the ordinary path. Factual VCR N+1 is used only "
            "after selection as the pair comparator. This integration run is not "
            "new independent evidence for already-open cases."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-db-root", type=Path, required=True)
    parser.add_argument("--corpus-db-generation", required=True)
    parser.add_argument("--selector-report", type=Path, required=True)
    parser.add_argument("--game-id", type=int, default=400330)
    parser.add_argument("--battle-turn", type=int, default=141)
    parser.add_argument("--x", type=int, default=1674)
    parser.add_argument("--y", type=int, default=2363)
    parser.add_argument("--start-vcr", type=int, default=592)
    parser.add_argument("--end-vcr", type=int, default=595)
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

    print("===== POSTCAPTURE SITE TRANSITION INTEGRATION =====")
    print(f"target:             {report['target']}")
    print(f"window_vcr_ids:     {report['window_vcr_ids']}")
    print(f"summary:            {report['summary']}")
    for row in report["transitions"]:
        print(
            f"V{row['from_vcr']}->V{row['to_vcr']} "
            f"source={row.get('selection_source')} "
            f"branch={row.get('capture_branch')} "
            f"predicted={row.get('predicted_pair')} "
            f"factual={row.get('factual_pair')} "
            f"exact={row.get('pair_exact')} "
            f"status={row.get('status')}"
        )
    print(f"output:             {args.output}")
    return 0 if report["summary"]["all_pair_exact"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
