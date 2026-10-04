#!/usr/bin/env python3
"""Targeted cursor diagnostics for genuine post-capture queue residuals.

Targets only held-out rows where:
- the frozen history-aware selector chose the wrong competitor,
- that competitor is definitely eligible under both captured-FC bounds,
- the factual opponent is also definitely eligible.

The already-audited c2ng/THost original-order cursor is used only as a frozen
EXTERNAL_IMPLEMENTATION comparator. It is not promoted to NuHost mechanics.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping, Sequence
import importlib
import json
from pathlib import Path
import sys
from typing import Any


DEFAULT_MAIN_ROOT = Path("/workspace")
DEFAULT_CORPUS_DB_ROOT = Path("/corpus-db")
DEFAULT_CAPTURE_SIDE = Path(
    "/workspace/artifacts/public-capture-side/heldout-capture-side.json"
)
DEFAULT_PAIR_RESIDUALS = Path(
    "/research/artifacts/external-sources/postcapture-occurrence/"
    "heldout-competitor-pair-recomposition.json"
)
DEFAULT_OUTPUT = Path(
    "/research/artifacts/external-sources/postcapture-occurrence/"
    "heldout-genuine-queue-cursor-diagnostic.json"
)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _load(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


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


def _residual_key(row: Mapping[str, Any]) -> tuple[int, int, int, int, int, int] | None:
    values = (
        row.get("game_id"),
        row.get("turn"),
        row.get("capture_vcr_id"),
        row.get("next_vcr_id"),
        row.get("captured_ship_id"),
        row.get("factual_opponent_ship_id"),
    )
    if not all(_is_int(value) for value in values):
        return None
    return tuple(int(value) for value in values)  # type: ignore[return-value]


def _capture_key(row: Mapping[str, Any]) -> tuple[int, int, int, int, int, int] | None:
    values = (
        row.get("game_id"),
        row.get("turn"),
        row.get("capture_vcr_id"),
        row.get("next_vcr_id"),
        row.get("captured_ship_id"),
        row.get("next_opponent_ship_id"),
    )
    if not all(_is_int(value) for value in values):
        return None
    return tuple(int(value) for value in values)  # type: ignore[return-value]


def _genuine_residuals(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = payload.get("cases")
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
    ):
        raise ValueError("pair residual cases missing")

    result: list[Mapping[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        competitor = row.get("competitor_pair")
        factual = row.get("factual_pair")
        if (
            isinstance(competitor, Mapping)
            and isinstance(factual, Mapping)
            and competitor.get("definitely_eligible") is True
            and factual.get("definitely_eligible") is True
            and row.get("predicted_competitor_id")
            != row.get("factual_opponent_ship_id")
        ):
            result.append(row)
    return result


def _anchor_known_eligible(
    active_result: Mapping[str, Any],
    ship_ids: Sequence[int],
) -> dict[str, Any]:
    """Condition the external cursor only on independently proven eligibility."""

    anchored = dict(active_result)

    active_ids_raw = active_result.get("active_ship_ids")
    active_ids = [
        int(value)
        for value in active_ids_raw
        if _is_int(value)
    ] if isinstance(active_ids_raw, Sequence) and not isinstance(active_ids_raw, (str, bytes)) else []

    candidate_rows_raw = active_result.get("candidates")
    candidate_rows = [
        dict(row)
        for row in candidate_rows_raw
        if isinstance(row, Mapping)
    ] if isinstance(candidate_rows_raw, Sequence) and not isinstance(candidate_rows_raw, (str, bytes)) else []

    for ship_id in ship_ids:
        if ship_id not in active_ids:
            active_ids.append(ship_id)
        row = next(
            (
                candidate
                for candidate in candidate_rows
                if candidate.get("ship_id") == ship_id
            ),
            None,
        )
        if row is None:
            row = {"ship_id": ship_id}
            candidate_rows.append(row)
        row["requests_new_owner"] = True
        row["strict_permission"] = True
        row["eligibility_anchored_from_pair_recomposition"] = True

    anchored["active_ship_ids"] = active_ids
    anchored["candidates"] = candidate_rows
    return anchored


def _order_positions(
    order: Any,
    *,
    prize_id: int,
    captor_id: int | None,
    competitor_id: int,
    factual_id: int,
) -> dict[str, int | None]:
    if not isinstance(order, Sequence) or isinstance(order, (str, bytes)):
        return {
            "prize": None,
            "captor": None,
            "competitor": None,
            "factual": None,
        }
    values = [int(v) for v in order if _is_int(v)]

    def pos(ship_id: int | None) -> int | None:
        if ship_id is None:
            return None
        try:
            return values.index(ship_id)
        except ValueError:
            return None

    return {
        "prize": pos(prize_id),
        "captor": pos(captor_id),
        "competitor": pos(competitor_id),
        "factual": pos(factual_id),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    oprobe, active_module, pair_module = _load_main_modules(args.main_root)

    residual_payload = _load(args.pair_residuals)
    if residual_payload.get("partition") != "heldout":
        raise ValueError("pair residual artifact must be heldout")
    residuals = _genuine_residuals(residual_payload)
    if len(residuals) != 3:
        raise ValueError(
            f"expected exactly three genuine queue residuals, got {len(residuals)}"
        )

    residual_by_key = {
        key: row
        for row in residuals
        if (key := _residual_key(row)) is not None
    }
    if len(residual_by_key) != 3:
        raise ValueError("genuine residual key collision or malformed row")

    capture_report = oprobe._load_capture_side_report(
        args.capture_side,
        expected_partition="heldout",
    )
    capture_rows = [
        dict(row)
        for row in capture_report["observations"]
        if isinstance(row, Mapping)
        and _capture_key(row) in residual_by_key
    ]
    if len(capture_rows) != 3:
        raise ValueError(
            f"expected three capture-side join rows, got {len(capture_rows)}"
        )

    targets = oprobe._targets_by_site(capture_rows)
    battle_turns_by_game: dict[int, set[int]] = defaultdict(set)
    for game_id, battle_turn, _x, _y in targets:
        battle_turns_by_game[int(game_id)].add(int(battle_turn))

    game_ids = sorted({int(row["game_id"]) for row in capture_rows})
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

        cases: list[dict[str, Any]] = []
        exact = 0
        mismatch = 0
        unresolved = 0
        anchored_exact = 0
        anchored_mismatch = 0
        anchored_unresolved = 0

        def observer(context: Mapping[str, Any]) -> None:
            nonlocal exact, mismatch, unresolved
            nonlocal anchored_exact, anchored_mismatch, anchored_unresolved

            site_key = (
                int(context["game_id"]),
                int(context["battle_turn"]),
                int(context["x"]),
                int(context["y"]),
            )
            for capture_row in targets.get(site_key, ()):
                ckey = _capture_key(capture_row)
                if ckey is None:
                    continue
                residual = residual_by_key.get(ckey)
                if not isinstance(residual, Mapping):
                    continue

                capture = oprobe._capture_projection(capture_row)
                active_result = active_module._simulate_capture(
                    context=context,
                    capture=capture,
                    appearances=appearances_by_key,
                )
                if active_result.get("status") != "resolved":
                    raise ValueError(
                        "targeted active replay unresolved: "
                        f"{active_result.get('reason')}"
                    )

                capture_side = capture_row.get("capture_side")
                if capture_side not in {"left", "right"}:
                    raise ValueError("capture-side row lacks capture_side")

                external = (
                    pair_module._external_c2ng_original_order_prize_continuation(
                        context=context,
                        capture=capture,
                        active_result=active_result,
                        capture_prize_side=str(capture_side),
                    )
                )

                competitor_id = int(residual["predicted_competitor_id"])
                factual_id = int(residual["factual_opponent_ship_id"])
                known_eligible = _anchor_known_eligible(
                    active_result,
                    (competitor_id, factual_id),
                )
                anchored_external = (
                    pair_module._external_c2ng_original_order_prize_continuation(
                        context=context,
                        capture=capture,
                        active_result=known_eligible,
                        capture_prize_side=str(capture_side),
                    )
                )

                status = external.get("status")
                if status != "resolved":
                    unresolved += 1
                elif external.get("pair_exact") is True:
                    exact += 1
                else:
                    mismatch += 1

                anchored_status = anchored_external.get("status")
                if anchored_status != "resolved":
                    anchored_unresolved += 1
                elif anchored_external.get("pair_exact") is True:
                    anchored_exact += 1
                else:
                    anchored_mismatch += 1

                strict_order = active_result.get("strict_requester_order")
                strict_order = (
                    [int(v) for v in strict_order if _is_int(v)]
                    if isinstance(strict_order, Sequence)
                    and not isinstance(strict_order, (str, bytes))
                    else []
                )

                captor_id = capture_row.get("captor_ship_id")
                captor_int = int(captor_id) if _is_int(captor_id) else None
                positions = _order_positions(
                    anchored_external.get("external_order"),
                    prize_id=int(residual["captured_ship_id"]),
                    captor_id=captor_int,
                    competitor_id=competitor_id,
                    factual_id=factual_id,
                )

                cases.append(
                    {
                        "game_id": int(residual["game_id"]),
                        "turn": int(residual["turn"]),
                        "x": int(residual["x"]),
                        "y": int(residual["y"]),
                        "capture_vcr_id": int(residual["capture_vcr_id"]),
                        "next_vcr_id": int(residual["next_vcr_id"]),
                        "captured_ship_id": int(residual["captured_ship_id"]),
                        "captor_ship_id": capture_row.get("captor_ship_id"),
                        "capture_side": capture_side,
                        "static_history_competitor_id": competitor_id,
                        "factual_opponent_ship_id": factual_id,
                        "strict_requester_order": strict_order,
                        "external_order_positions": positions,
                        "external_c2ng_cursor": {
                            "status": external.get("status"),
                            "reason": external.get("reason"),
                            "pair_exact": external.get("pair_exact"),
                            "predicted_opponent_ship_id": external.get(
                                "predicted_opponent_ship_id"
                            ),
                            "predicted_prize_side": external.get(
                                "predicted_prize_side"
                            ),
                            "external_order": external.get("external_order"),
                            "external_order_keys": external.get(
                                "external_order_keys"
                            ),
                            "capture_cursor": external.get("capture_cursor"),
                            "predicted_cursor": external.get(
                                "predicted_cursor"
                            ),
                            "cursor_trace": external.get("cursor_trace"),
                        },
                        "eligibility_anchored_c2ng_cursor": {
                            "status": anchored_external.get("status"),
                            "reason": anchored_external.get("reason"),
                            "pair_exact": anchored_external.get("pair_exact"),
                            "predicted_opponent_ship_id": anchored_external.get(
                                "predicted_opponent_ship_id"
                            ),
                            "external_order": anchored_external.get(
                                "external_order"
                            ),
                            "capture_cursor": anchored_external.get(
                                "capture_cursor"
                            ),
                            "predicted_cursor": anchored_external.get(
                                "predicted_cursor"
                            ),
                            "cursor_trace": anchored_external.get(
                                "cursor_trace"
                            ),
                        },
                    }
                )

        for game_id in game_ids:
            print(
                "progress: stage=queue_cursor_residual "
                f"game_id={game_id} status=start",
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
                "progress: stage=queue_cursor_residual "
                f"game_id={game_id} sites={summary['visited_sites']} status=done",
                flush=True,
            )

        if len(cases) != 3:
            raise ValueError(f"expected three cursor cases, got {len(cases)}")
        cases.sort(
            key=lambda row: (
                row["game_id"],
                row["turn"],
                row["capture_vcr_id"],
            )
        )

        return {
            "schema": "planets-lab.postcapture-heldout-cursor-residuals.v1",
            "partition": "heldout",
            "evidence_status": (
                "SECONDARY_HELDOUT_EXTERNAL_CURSOR_DIAGNOSTIC"
            ),
            "database_path": str(database_path),
            "summary": {
                "genuine_queue_residuals": len(cases),
                "external_c2ng_pair_exact": exact,
                "external_c2ng_pair_mismatch": mismatch,
                "external_c2ng_unresolved": unresolved,
                "eligibility_anchored_c2ng_pair_exact": anchored_exact,
                "eligibility_anchored_c2ng_pair_mismatch": anchored_mismatch,
                "eligibility_anchored_c2ng_unresolved": anchored_unresolved,
            },
            "cases": cases,
            "evidence_boundary": (
                "Targets only the three heldout rows where both the higher-ranked "
                "competitor and factual opponent are independently recomposed as "
                "eligible STANDARD pairs under both captured-FC bounds. The "
                "c2ng/THost cursor is a previously audited frozen external "
                "implementation comparator, not NuHost authority. No new queue "
                "rule is fitted and LEFT/RIGHT is not evaluated. A second "
                "cursor pass conditions only on independently proven pair "
                "eligibility for the residual competitor and factual opponent, "
                "isolating cursor geometry from strict-permission calibration."
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
    parser.add_argument(
        "--capture-side",
        type=Path,
        default=DEFAULT_CAPTURE_SIDE,
    )
    parser.add_argument(
        "--pair-residuals",
        type=Path,
        default=DEFAULT_PAIR_RESIDUALS,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
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

        summary = report["summary"]
        print("===== GENUINE POST-CAPTURE QUEUE RESIDUAL CURSOR DIAGNOSTIC =====")
        print(f"genuine residuals:       {summary['genuine_queue_residuals']}")
        print(f"external c2ng exact:     {summary['external_c2ng_pair_exact']}")
        print(f"external c2ng mismatch:  {summary['external_c2ng_pair_mismatch']}")
        print(f"external c2ng unresolved:{summary['external_c2ng_unresolved']}")
        print(
            "eligibility-anchored exact: "
            f"{summary['eligibility_anchored_c2ng_pair_exact']}"
        )
        print(
            "eligibility-anchored mismatch: "
            f"{summary['eligibility_anchored_c2ng_pair_mismatch']}"
        )
        print(
            "eligibility-anchored unresolved: "
            f"{summary['eligibility_anchored_c2ng_unresolved']}"
        )
        print()

        for row in report["cases"]:
            ext = row["external_c2ng_cursor"]
            anchored = row["eligibility_anchored_c2ng_cursor"]
            print(
                f"{row['game_id']}/T{row['turn']} "
                f"VCR {row['capture_vcr_id']}->{row['next_vcr_id']} "
                f"prize={row['captured_ship_id']} "
                f"captor={row['captor_ship_id']} "
                f"capture_side={row['capture_side']} "
                f"static={row['static_history_competitor_id']} "
                f"factual={row['factual_opponent_ship_id']}"
            )
            print(
                "  strict order: "
                + ", ".join(str(v) for v in row["strict_requester_order"])
            )
            print(
                "  external cursor: "
                f"status={ext.get('status')} "
                f"reason={ext.get('reason')} "
                f"predicted={ext.get('predicted_opponent_ship_id')} "
                f"pair_exact={ext.get('pair_exact')}"
            )
            print(f"  external order: {ext.get('external_order')}")
            print(f"  order positions: {row.get('external_order_positions')}")
            print(f"  capture cursor: {ext.get('capture_cursor')}")
            print(f"  predicted cursor: {ext.get('predicted_cursor')}")
            print("  cursor trace:")
            for trace in ext.get("cursor_trace") or []:
                print(f"    {trace}")
            print(
                "  eligibility-anchored cursor: "
                f"status={anchored.get('status')} "
                f"reason={anchored.get('reason')} "
                f"predicted={anchored.get('predicted_opponent_ship_id')} "
                f"pair_exact={anchored.get('pair_exact')}"
            )
            print(f"  anchored predicted cursor: {anchored.get('predicted_cursor')}")
            print("  anchored cursor trace:")
            for trace in anchored.get("cursor_trace") or []:
                print(f"    {trace}")
            print()

        print(f"output: {args.output}")
        print("No new queue rule was fitted.")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, ImportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
