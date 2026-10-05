#!/usr/bin/env python3
"""Open-population differential for the frozen O -> C-forward selector.

The structural O/C topology was independently supported before this predictor
was frozen. This probe evaluates the concrete selector on an already-open
population; it is fitting/differential evidence, not new validation.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
import importlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

from postcapture_o_c_forward_selector import (
    CandidateState,
    select_o_then_c_forward,
)
from postcapture_pair_bounds import (
    candidate_by_id,
    compose_candidate_pair,
    history_pair_occurrences,
    is_int,
)


DEFAULT_MAIN_ROOT = Path("/workspace")
DEFAULT_CORPUS_DB_ROOT = Path("/corpus-db")


def _load_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _load_topology_module():
    path = Path(__file__).resolve().parent / "analyze-postcapture-o-c-topology.py"
    spec = importlib.util.spec_from_file_location(
        "postcapture_o_c_topology_for_open_selector",
        path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load topology helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_main_modules(main_root: Path):
    diagnostics = main_root / "tools" / "diagnostics"
    source = main_root / "src"
    if not diagnostics.is_dir() or not source.is_dir():
        raise ValueError(f"canonical main checkout incomplete: {main_root}")
    sys.path.insert(0, str(diagnostics))
    sys.path.insert(0, str(source))
    oprobe = importlib.import_module("combat_public_capture_o_layer_probe")
    active = importlib.import_module(
        "combat_host_post_capture_active_membership_audit"
    )
    pair = importlib.import_module(
        "combat_host_post_capture_pair_recomposition_audit"
    )
    return oprobe, active, pair


def _row_key(
    row: Mapping[str, Any],
) -> tuple[int, int, int, int, int, int] | None:
    values = (
        row.get("game_id"),
        row.get("turn"),
        row.get("capture_vcr_id"),
        row.get("next_vcr_id"),
        row.get("captured_ship_id"),
        row.get("next_opponent_ship_id"),
    )
    if not all(is_int(value) for value in values):
        return None
    return tuple(int(value) for value in values)  # type: ignore[return-value]


def _dependency_qualified(row: Mapping[str, Any]) -> bool:
    dep = row.get("active_dependency")
    if not isinstance(dep, Mapping):
        return False
    return all(
        dep.get(key) is True
        for key in (
            "factual_opponent_active",
            "factual_opponent_candidate_resolved",
            "factual_opponent_requests_new_owner",
            "factual_opponent_strict_permission",
        )
    )


def _qualified_o_layer_keys(
    *,
    payload: Mapping[str, Any],
    expected_partition: str,
) -> set[tuple[int, int, int, int, int, int]]:
    topology = _load_topology_module()
    if not topology._matches_partition(payload, expected=expected_partition):
        raise ValueError(
            f"O-layer artifact is not recognizable as {expected_partition}"
        )
    rows = payload.get("observations")
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
    ):
        raise ValueError("O-layer observations missing")

    keys: set[tuple[int, int, int, int, int, int]] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        capture_vcr = row.get("capture_vcr_id")
        next_vcr = row.get("next_vcr_id")
        if not is_int(capture_vcr) or not is_int(next_vcr):
            continue
        if int(next_vcr) != int(capture_vcr) + 1:
            continue
        if row.get("capture_side") != "right":
            continue
        if not _dependency_qualified(row):
            continue
        key = _row_key(row)
        if key is not None:
            keys.add(key)
    return keys


def _build_external_order(
    *,
    pair_module: Any,
    context: Mapping[str, Any],
    active_result: Mapping[str, Any],
    prize_id: int,
    captor_id: int,
) -> dict[str, Any]:
    predictions = context.get("predictions")
    site_rows = context.get("site_ship_rows")
    if not isinstance(predictions, Mapping) or not isinstance(site_rows, Mapping):
        return {"status": "unresolved", "reason": "site_order_context_missing"}

    initial_ids = {
        int(value)
        for value in site_rows
        if is_int(value) and int(value) > 0
    }
    for key in (
        "active_ship_ids",
        "removed_ship_ids",
        "history_anchored_ship_ids",
    ):
        rows = active_result.get(key)
        if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)):
            for value in rows:
                if is_int(value) and int(value) > 0:
                    initial_ids.add(int(value))
    initial_ids.update((prize_id, captor_id))

    ordered: list[tuple[tuple[int, int], int]] = []
    missing: list[int] = []
    for ship_id in sorted(initial_ids):
        entry = predictions.get(ship_id)
        raw = entry.get("raw") if isinstance(entry, Mapping) else None
        if not isinstance(raw, Mapping):
            missing.append(ship_id)
            continue
        key = pair_module._c2ng_thost_sim_battle_value(
            ship_id=ship_id,
            raw=raw,
        )
        if key is None:
            missing.append(ship_id)
            continue
        ordered.append((key, ship_id))

    if missing:
        return {
            "status": "unresolved",
            "reason": "external_order_input_missing",
            "ship_ids": missing,
        }

    ordered.sort(key=lambda item: item[0])
    order = [ship_id for _key, ship_id in ordered]
    if prize_id not in order or captor_id not in order:
        return {
            "status": "unresolved",
            "reason": "capture_pair_missing_from_external_order",
        }
    return {
        "status": "resolved",
        "order": order,
        "keys": {str(ship_id): list(key) for key, ship_id in ordered},
        "prize_index": order.index(prize_id),
        "captor_index": order.index(captor_id),
    }


def _unresolved_foreign_map(
    active_result: Mapping[str, Any],
) -> dict[int, str]:
    result: dict[int, str] = {}
    rows = active_result.get("unresolved_foreign_candidates")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return result
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        ship_id = row.get("ship_id")
        if is_int(ship_id):
            result[int(ship_id)] = str(row.get("reason") or "foreign_unresolved")
    return result


def _candidate_states(
    *,
    permission_mode: str,
    order: Sequence[int],
    prize_id: int,
    captor_id: int,
    capture_vcr_id: int,
    pair_counts: Mapping[tuple[int, int], int],
    pair_module: Any,
    active_module: Any,
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
    context: Mapping[str, Any],
    capture: Mapping[str, Any],
    active_result: Mapping[str, Any],
) -> tuple[dict[int, CandidateState], dict[str, Any]]:
    if permission_mode not in {"strict", "request_anchored"}:
        raise ValueError(f"unknown permission mode: {permission_mode}")

    active_raw = active_result.get("active_ship_ids")
    active_ids = {
        int(value)
        for value in active_raw
        if is_int(value)
    } if isinstance(active_raw, Sequence) and not isinstance(active_raw, (str, bytes)) else set()

    owner_changed_raw = active_result.get("owner_changed_ship_ids")
    owner_changed = {
        int(value)
        for value in owner_changed_raw
        if is_int(value)
    } if isinstance(owner_changed_raw, Sequence) and not isinstance(owner_changed_raw, (str, bytes)) else set()

    prize_owner = active_result.get("prize_owner_id_after_capture")
    predictions = context.get("predictions")
    predictions = predictions if isinstance(predictions, Mapping) else {}
    unresolved_foreign = _unresolved_foreign_map(active_result)

    states: dict[int, CandidateState] = {}
    details: dict[str, Any] = {}

    for ship_id in order:
        if ship_id == prize_id:
            continue

        pair_key = tuple(sorted((prize_id, ship_id)))
        prior_count = int(pair_counts.get(pair_key, 0))

        if ship_id not in active_ids:
            states[ship_id] = CandidateState(
                ship_id=ship_id,
                disposition="inactive",
                reason="not_active_after_capture",
            )
            details[str(ship_id)] = {
                "prior_pair_occurrences": prior_count,
                "disposition": "inactive",
            }
            continue

        if ship_id == captor_id:
            states[ship_id] = CandidateState(
                ship_id=ship_id,
                disposition="same_owner",
                reason="captor_is_new_owner_side",
            )
            details[str(ship_id)] = {
                "prior_pair_occurrences": prior_count,
                "disposition": "same_owner",
            }
            continue

        candidate = candidate_by_id(active_result, ship_id)
        if not isinstance(candidate, Mapping):
            entry = predictions.get(ship_id)
            predicted_owner = (
                entry.get("owner_id")
                if isinstance(entry, Mapping)
                else None
            )
            if (
                is_int(prize_owner)
                and is_int(predicted_owner)
                and int(predicted_owner) == int(prize_owner)
                and ship_id not in owner_changed
            ):
                disposition = "same_owner"
                reason = "tminus1_owner_matches_prize_owner"
            else:
                disposition = "unresolved"
                reason = unresolved_foreign.get(
                    ship_id,
                    "active_foreign_candidate_missing",
                )
            states[ship_id] = CandidateState(
                ship_id=ship_id,
                disposition=disposition,
                reason=reason,
            )
            details[str(ship_id)] = {
                "prior_pair_occurrences": prior_count,
                "disposition": disposition,
                "reason": reason,
            }
            continue

        if prior_count >= 2:
            states[ship_id] = CandidateState(
                ship_id=ship_id,
                disposition="pair_exhausted",
                reason="pair_occurrence_cap_reached",
            )
            details[str(ship_id)] = {
                "prior_pair_occurrences": prior_count,
                "candidate": dict(candidate),
                "disposition": "pair_exhausted",
            }
            continue

        request = candidate.get("requests_new_owner")
        strict_permission = candidate.get("strict_permission")

        if request is False:
            states[ship_id] = CandidateState(
                ship_id=ship_id,
                disposition="no_request",
                reason="does_not_request_new_owner",
            )
            details[str(ship_id)] = {
                "prior_pair_occurrences": prior_count,
                "candidate": dict(candidate),
                "disposition": "no_request",
            }
            continue
        if request is not True:
            states[ship_id] = CandidateState(
                ship_id=ship_id,
                disposition="unresolved",
                reason="request_unresolved",
            )
            details[str(ship_id)] = {
                "prior_pair_occurrences": prior_count,
                "candidate": dict(candidate),
                "disposition": "unresolved",
                "reason": "request_unresolved",
            }
            continue

        if strict_permission is False:
            states[ship_id] = CandidateState(
                ship_id=ship_id,
                disposition="permission_denied",
                reason="strict_permission_false",
            )
            details[str(ship_id)] = {
                "prior_pair_occurrences": prior_count,
                "candidate": dict(candidate),
                "disposition": "permission_denied",
            }
            continue

        if strict_permission is not True and permission_mode == "strict":
            states[ship_id] = CandidateState(
                ship_id=ship_id,
                disposition="unresolved",
                reason="strict_permission_unresolved",
            )
            details[str(ship_id)] = {
                "prior_pair_occurrences": prior_count,
                "candidate": dict(candidate),
                "disposition": "unresolved",
                "reason": "strict_permission_unresolved",
            }
            continue

        pair_result = compose_candidate_pair(
            pair_module=pair_module,
            active_module=active_module,
            appearances=appearances,
            context=context,
            capture=capture,
            active_result=active_result,
            opponent_id=ship_id,
        )

        if pair_result.get("status") != "resolved":
            disposition = "unresolved"
            reason = str(pair_result.get("reason") or "pair_input_unresolved")
        elif pair_result.get("definitely_eligible") is True:
            disposition = "eligible"
            reason = None
        elif pair_result.get("definitely_blocked") is True:
            disposition = "pair_blocked"
            reason = "pair_blocked_under_both_fc_bounds"
        else:
            disposition = "unresolved"
            reason = "pair_fc_or_phase_bounds_unresolved"

        states[ship_id] = CandidateState(
            ship_id=ship_id,
            disposition=disposition,
            reason=reason,
        )
        details[str(ship_id)] = {
            "prior_pair_occurrences": prior_count,
            "candidate": dict(candidate),
            "permission_mode": permission_mode,
            "permission_anchored": (
                permission_mode == "request_anchored"
                and strict_permission is not True
            ),
            "pair_result": pair_result,
            "disposition": disposition,
            "reason": reason,
        }

    return states, details


def _selection_projection(result: Any) -> dict[str, Any]:
    return {
        "status": result.status,
        "branch": result.branch,
        "predicted_ship_id": result.predicted_ship_id,
        "unresolved_ship_id": result.unresolved_ship_id,
        "reason": result.reason,
        "trace": list(result.trace),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    oprobe, active_module, pair_module = _load_main_modules(args.main_root)

    capture_report = oprobe._load_capture_side_report(
        args.capture_report,
        expected_partition=args.capture_partition,
    )
    o_layer = _load_json(args.o_layer_report)
    qualified_keys = _qualified_o_layer_keys(
        payload=o_layer,
        expected_partition=args.o_layer_partition,
    )
    if not qualified_keys:
        raise ValueError("no frozen dependency-qualified RIGHT rows")

    observations = [
        dict(row)
        for row in capture_report["observations"]
        if isinstance(row, Mapping)
        and _row_key(row) in qualified_keys
    ]
    if len(observations) != len(qualified_keys):
        raise ValueError(
            "capture/O-layer qualified join incomplete: "
            f"capture={len(observations)} o_layer={len(qualified_keys)}"
        )

    targets = oprobe._targets_by_site(observations)
    battle_turns_by_game: dict[int, set[int]] = defaultdict(set)
    for game_id, battle_turn, _x, _y in targets:
        battle_turns_by_game[int(game_id)].add(int(battle_turn))

    game_ids = sorted({int(row["game_id"]) for row in observations})
    connection, database_path = oprobe.connect_current_compact_read_only(
        args.corpus_db_root
    )
    try:
        appearances: list[dict[str, Any]] = []
        for game_id in game_ids:
            rows, _summary = oprobe._collect_targeted_appearances_from_db(
                connection=connection,
                game_id=game_id,
                battle_turns=battle_turns_by_game.get(game_id, set()),
            )
            appearances.extend(rows)
        appearances_by_key = oprobe._appearance_mapping(appearances)

        counts: Counter[str] = Counter()
        cases: list[dict[str, Any]] = []

        def observer(context: Mapping[str, Any]) -> None:
            site_key = (
                int(context["game_id"]),
                int(context["battle_turn"]),
                int(context["x"]),
                int(context["y"]),
            )
            factual_queue_raw = context.get("factual_queue")
            factual_queue = [
                item
                for item in factual_queue_raw
                if isinstance(item, Mapping)
            ] if isinstance(factual_queue_raw, Sequence) and not isinstance(factual_queue_raw, (str, bytes)) else []

            for row in targets.get(site_key, ()):
                key = _row_key(row)
                if key not in qualified_keys:
                    continue

                capture = oprobe._capture_projection(row)
                active_result = active_module._simulate_capture(
                    context=context,
                    capture=capture,
                    appearances=appearances_by_key,
                )
                if active_result.get("status") != "resolved":
                    counts["primary:active_replay_unresolved"] += 1
                    cases.append(
                        {
                            "key": list(key),
                            "status": "active_replay_unresolved",
                            "reason": active_result.get("reason"),
                        }
                    )
                    continue

                prize_id = int(row["captured_ship_id"])
                captor_id = int(row["captor_ship_id"])
                factual_id = int(row["next_opponent_ship_id"])
                capture_vcr_id = int(row["capture_vcr_id"])

                order_result = _build_external_order(
                    pair_module=pair_module,
                    context=context,
                    active_result=active_result,
                    prize_id=prize_id,
                    captor_id=captor_id,
                )
                if order_result.get("status") != "resolved":
                    counts["primary:order_unresolved"] += 1
                    cases.append(
                        {
                            "key": list(key),
                            "status": "order_unresolved",
                            "reason": order_result.get("reason"),
                        }
                    )
                    continue

                order = [int(value) for value in order_result["order"]]
                pair_counts = history_pair_occurrences(
                    factual_queue=factual_queue,
                    through_vcr_id=capture_vcr_id,
                )

                strict_states, strict_details = _candidate_states(
                    permission_mode="strict",
                    order=order,
                    prize_id=prize_id,
                    captor_id=captor_id,
                    capture_vcr_id=capture_vcr_id,
                    pair_counts=pair_counts,
                    pair_module=pair_module,
                    active_module=active_module,
                    appearances=appearances_by_key,
                    context=context,
                    capture=capture,
                    active_result=active_result,
                )
                strict_selection = select_o_then_c_forward(
                    order=order,
                    prize_ship_id=prize_id,
                    captor_ship_id=captor_id,
                    states=strict_states,
                )

                relaxed_states, relaxed_details = _candidate_states(
                    permission_mode="request_anchored",
                    order=order,
                    prize_id=prize_id,
                    captor_id=captor_id,
                    capture_vcr_id=capture_vcr_id,
                    pair_counts=pair_counts,
                    pair_module=pair_module,
                    active_module=active_module,
                    appearances=appearances_by_key,
                    context=context,
                    capture=capture,
                    active_result=active_result,
                )
                relaxed_selection = select_o_then_c_forward(
                    order=order,
                    prize_ship_id=prize_id,
                    captor_ship_id=captor_id,
                    states=relaxed_states,
                )

                strict_exact = (
                    strict_selection.status == "resolved"
                    and strict_selection.predicted_ship_id == factual_id
                )
                relaxed_exact = (
                    relaxed_selection.status == "resolved"
                    and relaxed_selection.predicted_ship_id == factual_id
                )

                counts[f"primary:status:{strict_selection.status}"] += 1
                if strict_selection.status == "resolved":
                    counts[
                        "primary:exact" if strict_exact else "primary:mismatch"
                    ] += 1
                    counts[f"primary:branch:{strict_selection.branch}"] += 1

                counts[f"diagnostic:status:{relaxed_selection.status}"] += 1
                if relaxed_selection.status == "resolved":
                    counts[
                        "diagnostic:exact" if relaxed_exact else "diagnostic:mismatch"
                    ] += 1
                    counts[
                        f"diagnostic:branch:{relaxed_selection.branch}"
                    ] += 1

                cases.append(
                    {
                        "game_id": int(row["game_id"]),
                        "turn": int(row["turn"]),
                        "x": row.get("x"),
                        "y": row.get("y"),
                        "capture_vcr_id": capture_vcr_id,
                        "next_vcr_id": int(row["next_vcr_id"]),
                        "captured_ship_id": prize_id,
                        "captor_ship_id": captor_id,
                        "factual_opponent_ship_id": factual_id,
                        "external_order": order,
                        "external_order_keys": order_result.get("keys"),
                        "positions": {
                            "prize": order_result.get("prize_index"),
                            "captor": order_result.get("captor_index"),
                            "factual": (
                                order.index(factual_id)
                                if factual_id in order
                                else None
                            ),
                        },
                        "primary": {
                            **_selection_projection(strict_selection),
                            "exact": strict_exact,
                            "candidate_details": strict_details,
                        },
                        "request_anchored_diagnostic": {
                            **_selection_projection(relaxed_selection),
                            "exact": relaxed_exact,
                            "candidate_details": relaxed_details,
                        },
                        "current_active_factual_dependency": {
                            "active": active_result.get(
                                "factual_opponent_active"
                            ),
                            "candidate_resolved": active_result.get(
                                "factual_opponent_candidate_resolved"
                            ),
                            "requests_new_owner": active_result.get(
                                "factual_opponent_requests_new_owner"
                            ),
                            "strict_permission": active_result.get(
                                "factual_opponent_strict_permission"
                            ),
                        },
                    }
                )

        for game_id in game_ids:
            print(
                f"progress: label={args.label} game_id={game_id} status=start",
                flush=True,
            )
            summary = oprobe._visit_targeted_site_contexts(
                connection=connection,
                game_id=game_id,
                targets=targets,
                appearances=appearances,
                observer=observer,
            )
            print(
                f"progress: label={args.label} game_id={game_id} "
                f"sites={summary['visited_sites']} status=done",
                flush=True,
            )

        return {
            "schema": "planets-lab.postcapture-o-c-forward-open.v1",
            "label": args.label,
            "capture_partition": args.capture_partition,
            "o_layer_partition": args.o_layer_partition,
            "evidence_status": "OPEN_POPULATION_FITTING_DIFFERENTIAL",
            "database_path": str(database_path),
            "frozen_qualified_rows": len(qualified_keys),
            "summary": {"counts": dict(sorted(counts.items()))},
            "cases": sorted(
                cases,
                key=lambda row: (
                    int(row.get("game_id") or 0),
                    int(row.get("turn") or 0),
                    int(row.get("capture_vcr_id") or 0),
                ),
            ),
            "evidence_boundary": (
                "Evaluates the O->C-forward selector frozen after independent "
                "topology validation. The population is already open and this "
                "is not new validation. Factual N+1 opponent identity is used "
                "only as comparator and to select the previously frozen "
                "dependency-qualified topology rows. LEFT/RIGHT is not used. "
                "Primary prediction fails closed on unresolved strict "
                "permission; request-anchored output is diagnostic only."
            ),
        }
    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-root", type=Path, default=DEFAULT_MAIN_ROOT)
    parser.add_argument(
        "--corpus-db-root",
        type=Path,
        default=DEFAULT_CORPUS_DB_ROOT,
    )
    parser.add_argument("--capture-report", type=Path, required=True)
    parser.add_argument("--capture-partition", required=True)
    parser.add_argument("--o-layer-report", type=Path, required=True)
    parser.add_argument("--o-layer-partition", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        c = report["summary"]["counts"]
        print(f"===== O/C FORWARD SELECTOR / {args.label} =====")
        print(f"frozen qualified rows: {report['frozen_qualified_rows']}")
        print(
            "primary resolved/exact/mismatch/unresolved/no_pair: "
            f"{c.get('primary:status:resolved', 0)} / "
            f"{c.get('primary:exact', 0)} / "
            f"{c.get('primary:mismatch', 0)} / "
            f"{c.get('primary:status:unresolved', 0)} / "
            f"{c.get('primary:status:no_pair', 0)}"
        )
        print(
            "primary O / C: "
            f"{c.get('primary:branch:O', 0)} / "
            f"{c.get('primary:branch:C', 0)}"
        )
        print(
            "request-anchored resolved/exact/mismatch/unresolved/no_pair: "
            f"{c.get('diagnostic:status:resolved', 0)} / "
            f"{c.get('diagnostic:exact', 0)} / "
            f"{c.get('diagnostic:mismatch', 0)} / "
            f"{c.get('diagnostic:status:unresolved', 0)} / "
            f"{c.get('diagnostic:status:no_pair', 0)}"
        )

        problem_rows = [
            row
            for row in report["cases"]
            if isinstance(row, Mapping)
            and isinstance(row.get("primary"), Mapping)
            and (
                row["primary"].get("status") != "resolved"
                or row["primary"].get("exact") is not True
            )
        ]
        if problem_rows:
            print()
            print("PRIMARY NON-EXACT / UNRESOLVED:")
            for row in problem_rows:
                primary = row["primary"]
                print(
                    f"  {row.get('game_id')}/T{row.get('turn')} "
                    f"VCR {row.get('capture_vcr_id')}->{row.get('next_vcr_id')} "
                    f"prize={row.get('captured_ship_id')} "
                    f"captor={row.get('captor_ship_id')} "
                    f"factual={row.get('factual_opponent_ship_id')} "
                    f"status={primary.get('status')} "
                    f"branch={primary.get('branch')} "
                    f"predicted={primary.get('predicted_ship_id')} "
                    f"unresolved_ship={primary.get('unresolved_ship_id')} "
                    f"reason={primary.get('reason')}"
                )
                print(f"    order={row.get('external_order')}")
                print(f"    positions={row.get('positions')}")
                print(f"    trace={primary.get('trace')}")
                diagnostic = row.get("request_anchored_diagnostic", {})
                print(
                    "    request-anchored: "
                    f"status={diagnostic.get('status')} "
                    f"branch={diagnostic.get('branch')} "
                    f"predicted={diagnostic.get('predicted_ship_id')} "
                    f"exact={diagnostic.get('exact')} "
                    f"reason={diagnostic.get('reason')}"
                )

        print()
        print(f"output: {args.output}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, ImportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
