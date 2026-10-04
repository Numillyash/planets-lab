#!/usr/bin/env python3
"""Frozen external cursor diagnostic for the two discovery rank>1 residuals.

This uses the already-audited c2ng/THost original-order cursor only as an
EXTERNAL_IMPLEMENTATION comparator. It asks whether the same cursor geometry
that explains the genuine held-out queue residuals also explains the two
discovery rows that originally motivated elapsed-history ranking.
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
    "/workspace/artifacts/public-capture-side/discovery-capture-side.json"
)
DEFAULT_RANK2 = Path(
    "/research/artifacts/external-sources/afsim-r1/"
    "discovery-rank2-targeted.json"
)
DEFAULT_OUTPUT = Path(
    "/research/artifacts/external-sources/postcapture-occurrence/"
    "discovery-rank2-cursor-diagnostic.json"
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


def _rank2_key(row: Mapping[str, Any]) -> tuple[int, int, int, int, int, int] | None:
    values = (
        row.get("game_id"),
        row.get("turn"),
        row.get("capture_vcr_id"),
        row.get("next_vcr_id"),
        row.get("captured_ship_id"),
        row.get("factual_next_opponent_id"),
    )
    if not all(_is_int(v) for v in values):
        return None
    return tuple(int(v) for v in values)  # type: ignore[return-value]


def _capture_key(row: Mapping[str, Any]) -> tuple[int, int, int, int, int, int] | None:
    values = (
        row.get("game_id"),
        row.get("turn"),
        row.get("capture_vcr_id"),
        row.get("next_vcr_id"),
        row.get("captured_ship_id"),
        row.get("next_opponent_ship_id"),
    )
    if not all(_is_int(v) for v in values):
        return None
    return tuple(int(v) for v in values)  # type: ignore[return-value]


def _positions(
    order: Any,
    *,
    prize_id: int,
    captor_id: int | None,
    competitor_id: int,
    factual_id: int,
) -> dict[str, int | None]:
    if not isinstance(order, Sequence) or isinstance(order, (str, bytes)):
        return {"prize": None, "captor": None, "competitor": None, "factual": None}
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

    rank2_payload = _load(args.rank2)
    rank2_rows = rank2_payload.get("cases")
    if (
        not isinstance(rank2_rows, Sequence)
        or isinstance(rank2_rows, (str, bytes))
        or not all(isinstance(row, Mapping) for row in rank2_rows)
    ):
        raise ValueError("rank2 targeted cases missing")
    if len(rank2_rows) != 2:
        raise ValueError(f"expected two discovery rank2 cases, got {len(rank2_rows)}")

    rank2_by_key = {
        key: row
        for row in rank2_rows
        if (key := _rank2_key(row)) is not None
    }
    if len(rank2_by_key) != 2:
        raise ValueError("rank2 identity collision or malformed row")

    capture_report = oprobe._load_capture_side_report(
        args.capture_side,
        expected_partition="discovery",
    )
    capture_rows = [
        dict(row)
        for row in capture_report["observations"]
        if isinstance(row, Mapping) and _capture_key(row) in rank2_by_key
    ]
    if len(capture_rows) != 2:
        raise ValueError(
            f"expected two capture-side join rows, got {len(capture_rows)}"
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
        raw_exact = raw_mismatch = raw_unresolved = 0
        anchored_exact = anchored_mismatch = anchored_unresolved = 0

        def observer(context: Mapping[str, Any]) -> None:
            nonlocal raw_exact, raw_mismatch, raw_unresolved
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
                rank2 = rank2_by_key.get(ckey)
                if not isinstance(rank2, Mapping):
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

                raw = pair_module._external_c2ng_original_order_prize_continuation(
                    context=context,
                    capture=capture,
                    active_result=active_result,
                    capture_prize_side=str(capture_side),
                )
                factual_id = int(rank2["factual_next_opponent_id"])
                anchored_state = oprobe._identity_anchor_factual_opponent(
                    active_result=active_result,
                    factual_opponent_id=factual_id,
                )
                anchored = (
                    pair_module._external_c2ng_original_order_prize_continuation(
                        context=context,
                        capture=capture,
                        active_result=anchored_state,
                        capture_prize_side=str(capture_side),
                    )
                )

                for value, which in ((raw, "raw"), (anchored, "anchored")):
                    status = value.get("status")
                    pair_exact = value.get("pair_exact")
                    if which == "raw":
                        if status != "resolved":
                            raw_unresolved += 1
                        elif pair_exact is True:
                            raw_exact += 1
                        else:
                            raw_mismatch += 1
                    else:
                        if status != "resolved":
                            anchored_unresolved += 1
                        elif pair_exact is True:
                            anchored_exact += 1
                        else:
                            anchored_mismatch += 1

                competitor_id = int(rank2["rank1_competitor_id"])
                prize_id = int(rank2["captured_ship_id"])
                captor_raw = capture_row.get("captor_ship_id")
                captor_id = int(captor_raw) if _is_int(captor_raw) else None
                order_positions = _positions(
                    anchored.get("external_order"),
                    prize_id=prize_id,
                    captor_id=captor_id,
                    competitor_id=competitor_id,
                    factual_id=factual_id,
                )

                cases.append(
                    {
                        "game_id": int(rank2["game_id"]),
                        "turn": int(rank2["turn"]),
                        "capture_vcr_id": int(rank2["capture_vcr_id"]),
                        "next_vcr_id": int(rank2["next_vcr_id"]),
                        "captured_ship_id": prize_id,
                        "captor_ship_id": captor_id,
                        "capture_side": capture_side,
                        "rank1_competitor_id": competitor_id,
                        "factual_opponent_ship_id": factual_id,
                        "strict_requester_order": active_result.get(
                            "strict_requester_order"
                        ),
                        "external_order_positions": order_positions,
                        "raw_cursor": {
                            "status": raw.get("status"),
                            "reason": raw.get("reason"),
                            "pair_exact": raw.get("pair_exact"),
                            "predicted_opponent_ship_id": raw.get(
                                "predicted_opponent_ship_id"
                            ),
                            "external_order": raw.get("external_order"),
                            "capture_cursor": raw.get("capture_cursor"),
                            "predicted_cursor": raw.get("predicted_cursor"),
                            "cursor_trace": raw.get("cursor_trace"),
                        },
                        "factual_identity_anchored_cursor": {
                            "status": anchored.get("status"),
                            "reason": anchored.get("reason"),
                            "pair_exact": anchored.get("pair_exact"),
                            "predicted_opponent_ship_id": anchored.get(
                                "predicted_opponent_ship_id"
                            ),
                            "external_order": anchored.get("external_order"),
                            "capture_cursor": anchored.get("capture_cursor"),
                            "predicted_cursor": anchored.get("predicted_cursor"),
                            "cursor_trace": anchored.get("cursor_trace"),
                        },
                    }
                )

        for game_id in game_ids:
            print(
                "progress: stage=discovery_rank2_cursor "
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
                "progress: stage=discovery_rank2_cursor "
                f"game_id={game_id} sites={summary['visited_sites']} status=done",
                flush=True,
            )

        if len(cases) != 2:
            raise ValueError(f"expected two cursor cases, got {len(cases)}")
        cases.sort(key=lambda row: (row["turn"], row["capture_vcr_id"]))

        return {
            "schema": "planets-lab.postcapture-discovery-rank2-cursor.v1",
            "partition": "discovery",
            "evidence_status": "DISCOVERY_EXTERNAL_CURSOR_DIAGNOSTIC",
            "database_path": str(database_path),
            "summary": {
                "cases": 2,
                "raw_exact": raw_exact,
                "raw_mismatch": raw_mismatch,
                "raw_unresolved": raw_unresolved,
                "factual_identity_anchored_exact": anchored_exact,
                "factual_identity_anchored_mismatch": anchored_mismatch,
                "factual_identity_anchored_unresolved": anchored_unresolved,
            },
            "cases": cases,
            "evidence_boundary": (
                "Targets only the two discovery strict-rank>1 residuals that "
                "predated the history-aware candidate. The c2ng/THost cursor is "
                "a previously frozen external comparator. A factual-identity "
                "anchored pass conditions only on the already observed/qualified "
                "N+1 opponent identity to isolate cursor geometry; it is not an "
                "independent pair predictor and LEFT/RIGHT is not evaluated."
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
    parser.add_argument("--rank2", type=Path, default=DEFAULT_RANK2)
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
        print("===== DISCOVERY RANK>1 RESIDUAL CURSOR DIAGNOSTIC =====")
        print(
            "raw external exact/mismatch/unresolved: "
            f"{summary['raw_exact']} / {summary['raw_mismatch']} / "
            f"{summary['raw_unresolved']}"
        )
        print(
            "factual-anchored exact/mismatch/unresolved: "
            f"{summary['factual_identity_anchored_exact']} / "
            f"{summary['factual_identity_anchored_mismatch']} / "
            f"{summary['factual_identity_anchored_unresolved']}"
        )
        print()

        for row in report["cases"]:
            raw = row["raw_cursor"]
            anchored = row["factual_identity_anchored_cursor"]
            print(
                f"{row['game_id']}/T{row['turn']} "
                f"VCR {row['capture_vcr_id']}->{row['next_vcr_id']} "
                f"prize={row['captured_ship_id']} "
                f"captor={row['captor_ship_id']} "
                f"rank1={row['rank1_competitor_id']} "
                f"factual={row['factual_opponent_ship_id']}"
            )
            print(
                "  strict order: "
                + ", ".join(
                    str(v) for v in (row.get("strict_requester_order") or [])
                )
            )
            print(f"  external order: {anchored.get('external_order')}")
            print(f"  positions: {row['external_order_positions']}")
            print(f"  capture cursor: {anchored.get('capture_cursor')}")
            print(
                "  raw cursor: "
                f"predicted={raw.get('predicted_opponent_ship_id')} "
                f"exact={raw.get('pair_exact')} reason={raw.get('reason')}"
            )
            print(
                "  factual-anchored cursor: "
                f"predicted={anchored.get('predicted_opponent_ship_id')} "
                f"exact={anchored.get('pair_exact')} "
                f"reason={anchored.get('reason')}"
            )
            print("  anchored trace:")
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
