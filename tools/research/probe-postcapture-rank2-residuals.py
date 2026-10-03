#!/usr/bin/env python3
"""Targeted discovery-only probe for the two qualified strict-rank>1 residuals.

This does not search for a new rule.  It reconstructs the exact mutable site
state from canonical main/Corpus DB and exposes the competing rank-1 attacker,
elapsed local VCR history, pair-occurrence counts, candidate priorities, and
mutation trace.

Held-out is never read.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
import importlib
import json
from pathlib import Path
import sys
from typing import Any


DEFAULT_MAIN_ROOT = Path("/workspace")
DEFAULT_CORPUS_DB_ROOT = Path("/corpus-db")
DEFAULT_O_LAYER = Path(
    "/workspace/artifacts/public-capture-side/discovery-o-layer-probe.json"
)
DEFAULT_RESIDUALS = Path(
    "/research/artifacts/external-sources/afsim-r1/"
    "discovery-strict-rank-residuals.json"
)
DEFAULT_OUTPUT = Path(
    "/research/artifacts/external-sources/afsim-r1/"
    "discovery-rank2-targeted.json"
)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _load(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _key(row: Mapping[str, Any]) -> tuple[int, int, int, int, int, int] | None:
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
    return oprobe, active


def _raw_order_projection(entry: Any) -> dict[str, Any] | None:
    if not isinstance(entry, Mapping):
        return None
    raw = entry.get("raw")
    if not isinstance(raw, Mapping):
        return None
    result: dict[str, Any] = {}
    for key in (
        "mission",
        "enemy",
        "friendlycode",
        "neutronium",
        "warp",
        "targetx",
        "targety",
        "mission1target",
    ):
        value = raw.get(key)
        if isinstance(value, (str, int, bool)) or value is None:
            result[key] = value
    result["position_source"] = entry.get("source")
    result["predicted_position"] = entry.get("position")
    result["tminus1_owner_id"] = entry.get("owner_id")
    return result


def _pair_tuple(row: Mapping[str, Any]) -> tuple[int, int] | None:
    pair = row.get("pair")
    if (
        isinstance(pair, Sequence)
        and not isinstance(pair, (str, bytes))
        and len(pair) == 2
        and all(_is_int(value) for value in pair)
    ):
        return (int(pair[0]), int(pair[1]))
    return None


def _history_projection(
    *,
    factual_queue: Sequence[Mapping[str, Any]],
    through_vcr: int,
    prize_id: int,
    rank1_id: int,
    factual_id: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    pair_counts: Counter[tuple[int, int]] = Counter()
    ship_appearances: Counter[int] = Counter()

    for row in factual_queue:
        vcr_id = row.get("vcr_id")
        if not _is_int(vcr_id) or int(vcr_id) > through_vcr:
            continue
        pair = _pair_tuple(row)
        if pair is None:
            continue
        canonical = tuple(sorted(pair))
        pair_counts[canonical] += 1
        ship_appearances[pair[0]] += 1
        ship_appearances[pair[1]] += 1
        rows.append(
            {
                "vcr_id": int(vcr_id),
                "pair": list(pair),
                "contains_prize": prize_id in pair,
                "contains_rank1": rank1_id in pair,
                "contains_factual": factual_id in pair,
            }
        )

    def count(a: int, b: int) -> int:
        return int(pair_counts[tuple(sorted((a, b)))])

    return {
        "rows": rows,
        "pair_occurrences_before_or_at_capture": {
            "prize_rank1": count(prize_id, rank1_id),
            "prize_factual": count(prize_id, factual_id),
            "rank1_factual": count(rank1_id, factual_id),
        },
        "ship_appearances_before_or_at_capture": {
            "prize": int(ship_appearances[prize_id]),
            "rank1": int(ship_appearances[rank1_id]),
            "factual": int(ship_appearances[factual_id]),
        },
    }


def _candidate_projection(
    candidate: Mapping[str, Any],
    predictions: Mapping[int, Any],
) -> dict[str, Any]:
    ship_id = candidate.get("ship_id")
    raw_projection = (
        _raw_order_projection(predictions.get(int(ship_id)))
        if _is_int(ship_id)
        else None
    )
    return {
        "ship_id": int(ship_id) if _is_int(ship_id) else None,
        "owner_id": candidate.get("owner_id"),
        "requests_new_owner": candidate.get("requests_new_owner"),
        "strict_permission": candidate.get("strict_permission"),
        "priority": candidate.get("priority"),
        "position_source": candidate.get("position_source"),
        "is_factual_next_opponent": candidate.get(
            "is_factual_next_opponent"
        ),
        "tminus1_orders": raw_projection,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    oprobe, active_module = _load_main_modules(args.main_root)
    o_layer = _load(args.o_layer)
    residuals = _load(args.residuals)

    if o_layer.get("partition") not in {None, "discovery"}:
        raise ValueError("O-layer artifact is not discovery")
    if residuals.get("partition") != "discovery":
        raise ValueError("residual artifact is not discovery")

    raw_rank2 = residuals.get("rank_gt1")
    if (
        not isinstance(raw_rank2, Sequence)
        or isinstance(raw_rank2, (str, bytes))
        or not all(isinstance(row, Mapping) for row in raw_rank2)
    ):
        raise ValueError("rank_gt1 residual list missing or malformed")
    if len(raw_rank2) != 2:
        raise ValueError(f"expected exactly 2 rank>1 residuals, got {len(raw_rank2)}")

    residual_keys = {_key(row) for row in raw_rank2}
    if None in residual_keys:
        raise ValueError("rank>1 residual identity malformed")

    observations = o_layer.get("observations")
    if (
        not isinstance(observations, Sequence)
        or isinstance(observations, (str, bytes))
        or not all(isinstance(row, Mapping) for row in observations)
    ):
        raise ValueError("O-layer observations missing or malformed")

    selected_rows: list[Mapping[str, Any]] = []
    for row in observations:
        if _key(row) in residual_keys:
            selected_rows.append(row)
    if len(selected_rows) != 2:
        raise ValueError(
            f"expected 2 matching O-layer observations, got {len(selected_rows)}"
        )

    targets: dict[
        tuple[int, int, int, int],
        list[Mapping[str, Any]],
    ] = defaultdict(list)
    for row in selected_rows:
        game_id = row.get("game_id")
        turn = row.get("turn")
        x = row.get("x")
        y = row.get("y")
        if not all(_is_int(value) for value in (game_id, turn, x, y)):
            raise ValueError("selected O-layer row lacks site coordinates")
        targets[(int(game_id), int(turn), int(x), int(y))].append(row)

    game_ids = sorted({key[0] for key in targets})
    if game_ids != [486109]:
        raise ValueError(f"unexpected target games: {game_ids}")

    battle_turns = {key[1] for key in targets}
    connection, database_path = oprobe.connect_current_compact_read_only(
        args.corpus_db_root
    )
    try:
        appearances, appearance_summary = (
            oprobe._collect_targeted_appearances_from_db(
                connection=connection,
                game_id=486109,
                battle_turns=set(battle_turns),
            )
        )
        appearances_by_key = oprobe._appearance_mapping(appearances)

        cases: list[dict[str, Any]] = []

        def observer(context: Mapping[str, Any]) -> None:
            site_key = (
                int(context["game_id"]),
                int(context["battle_turn"]),
                int(context["x"]),
                int(context["y"]),
            )
            for row in targets.get(site_key, ()):
                capture = oprobe._capture_projection(row)
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

                prize_id = int(row["captured_ship_id"])
                factual_id = int(row["next_opponent_ship_id"])
                strict_order_raw = active_result.get("strict_requester_order")
                requester_order_raw = active_result.get("requester_order")
                if (
                    not isinstance(strict_order_raw, Sequence)
                    or isinstance(strict_order_raw, (str, bytes))
                    or len(strict_order_raw) < 2
                    or not all(_is_int(v) for v in strict_order_raw)
                ):
                    raise ValueError("strict requester order missing")
                strict_order = [int(v) for v in strict_order_raw]
                requester_order = (
                    [int(v) for v in requester_order_raw]
                    if isinstance(requester_order_raw, Sequence)
                    and not isinstance(requester_order_raw, (str, bytes))
                    and all(_is_int(v) for v in requester_order_raw)
                    else []
                )
                rank1_id = strict_order[0]

                candidates_raw = active_result.get("candidates")
                candidates = (
                    [
                        _candidate_projection(candidate, context["predictions"])
                        for candidate in candidates_raw
                        if isinstance(candidate, Mapping)
                    ]
                    if isinstance(candidates_raw, Sequence)
                    and not isinstance(candidates_raw, (str, bytes))
                    else []
                )
                candidate_by_id = {
                    int(candidate["ship_id"]): candidate
                    for candidate in candidates
                    if _is_int(candidate.get("ship_id"))
                }

                factual_queue = context.get("factual_queue")
                if (
                    not isinstance(factual_queue, Sequence)
                    or isinstance(factual_queue, (str, bytes))
                ):
                    raise ValueError("factual queue missing")

                history = _history_projection(
                    factual_queue=[
                        item for item in factual_queue if isinstance(item, Mapping)
                    ],
                    through_vcr=int(row["capture_vcr_id"]),
                    prize_id=prize_id,
                    rank1_id=rank1_id,
                    factual_id=factual_id,
                )

                c2ng_result = row.get("identity_anchored_result")
                c2ng_result = (
                    c2ng_result if isinstance(c2ng_result, Mapping) else {}
                )

                cases.append(
                    {
                        "game_id": int(row["game_id"]),
                        "turn": int(row["turn"]),
                        "x": int(row["x"]),
                        "y": int(row["y"]),
                        "capture_vcr_id": int(row["capture_vcr_id"]),
                        "next_vcr_id": int(row["next_vcr_id"]),
                        "captured_ship_id": prize_id,
                        "factual_next_opponent_id": factual_id,
                        "factual_prize_side": row.get("factual_prize_side"),
                        "requester_order": requester_order,
                        "strict_requester_order": strict_order,
                        "rank1_competitor_id": rank1_id,
                        "rank1_candidate": candidate_by_id.get(rank1_id),
                        "factual_candidate": candidate_by_id.get(factual_id),
                        "all_candidates": candidates,
                        "elapsed_history": history,
                        "mutation_trace": active_result.get("mutation_trace"),
                        "active_ship_ids": active_result.get("active_ship_ids"),
                        "removed_ship_ids": active_result.get("removed_ship_ids"),
                        "owner_changed_ship_ids": active_result.get(
                            "owner_changed_ship_ids"
                        ),
                        "history_anchored_ship_ids": active_result.get(
                            "history_anchored_ship_ids"
                        ),
                        "c2ng_identity_anchored": {
                            "status": c2ng_result.get("status"),
                            "pair_exact": c2ng_result.get("pair_exact"),
                            "predicted_opponent_ship_id": c2ng_result.get(
                                "predicted_opponent_ship_id"
                            ),
                            "predicted_prize_side": c2ng_result.get(
                                "predicted_prize_side"
                            ),
                            "capture_cursor": c2ng_result.get("capture_cursor"),
                            "predicted_cursor": c2ng_result.get(
                                "predicted_cursor"
                            ),
                            "cursor_trace": c2ng_result.get("cursor_trace"),
                        },
                    }
                )

        visit_summary = oprobe._visit_targeted_site_contexts(
            connection=connection,
            game_id=486109,
            targets=targets,
            appearances=appearances,
            observer=observer,
        )

        if len(cases) != 2:
            raise ValueError(f"expected 2 targeted cases, got {len(cases)}")

        cases.sort(key=lambda row: (row["turn"], row["capture_vcr_id"]))
        return {
            "schema": "planets-lab.postcapture-rank2-targeted.v1",
            "partition": "discovery",
            "game_id": 486109,
            "database_path": str(database_path),
            "appearance_summary": appearance_summary,
            "visit_summary": visit_summary,
            "cases": cases,
            "evidence_boundary": (
                "Discovery-only targeted reconstruction of the two already "
                "identified qualified strict-rank>1 residuals. Factual VCR "
                "history is used only through the capture VCR. The factual N+1 "
                "opponent identity remains the comparator from the discovery "
                "row. Held-out is not read."
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
    parser.add_argument("--o-layer", type=Path, default=DEFAULT_O_LAYER)
    parser.add_argument("--residuals", type=Path, default=DEFAULT_RESIDUALS)
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

        print("===== POST-CAPTURE RANK>1 TARGETED DISCOVERY =====")
        for case in report["cases"]:
            hist = case["elapsed_history"]
            occ = hist["pair_occurrences_before_or_at_capture"]
            apps = hist["ship_appearances_before_or_at_capture"]
            rank1 = case.get("rank1_candidate") or {}
            factual = case.get("factual_candidate") or {}
            print(
                f"{case['game_id']}/T{case['turn']} "
                f"VCR {case['capture_vcr_id']}->{case['next_vcr_id']} "
                f"prize={case['captured_ship_id']} "
                f"rank1={case['rank1_competitor_id']} "
                f"factual={case['factual_next_opponent_id']}"
            )
            print(
                "  strict order: "
                + ", ".join(str(v) for v in case["strict_requester_order"])
            )
            print(
                "  priority rank1/factual: "
                f"{rank1.get('priority')} / {factual.get('priority')}"
            )
            print(
                "  prior pair occurrences prize-rank1 / prize-factual: "
                f"{occ['prize_rank1']} / {occ['prize_factual']}"
            )
            print(
                "  prior ship appearances prize / rank1 / factual: "
                f"{apps['prize']} / {apps['rank1']} / {apps['factual']}"
            )
            print(
                "  rank1 orders:  "
                f"{rank1.get('tminus1_orders')}"
            )
            print(
                "  factual orders:"
                f" {factual.get('tminus1_orders')}"
            )
            print("  elapsed local VCRs:")
            for row in hist["rows"]:
                marks = []
                if row["contains_prize"]:
                    marks.append("prize")
                if row["contains_rank1"]:
                    marks.append("rank1")
                if row["contains_factual"]:
                    marks.append("factual")
                suffix = ",".join(marks) if marks else "-"
                print(
                    f"    VCR {row['vcr_id']}: {row['pair']} [{suffix}]"
                )
            print()

        print(f"output: {args.output}")
        print("Held-out was not read.")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, ImportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
