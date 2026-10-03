#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


def _load(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    rows = payload.get("observations")
    if not isinstance(rows, list):
        raise ValueError(f"{path}: observations missing")
    return payload


def _rows(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = payload.get("observations")
    assert isinstance(rows, list)
    return [row for row in rows if isinstance(row, Mapping)]


def _identity_residuals(
    payload: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    result: list[Mapping[str, Any]] = []
    for row in _rows(payload):
        split = row.get("identity_anchored_split")
        if split is None:
            anchored = row.get("identity_anchored_result")
            if (
                isinstance(anchored, Mapping)
                and anchored.get("status") == "resolved"
            ):
                result.append(row)
            continue
        if isinstance(split, Mapping) and split.get("exact") is not True:
            result.append(row)
    return result


def _fmt(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _print_cursor_trace(row: Mapping[str, Any]) -> None:
    anchored = row.get("identity_anchored_result")
    if not isinstance(anchored, Mapping):
        print("cursor_trace: unavailable")
        return
    trace = anchored.get("cursor_trace")
    if not isinstance(trace, Sequence) or isinstance(trace, (str, bytes)):
        print("cursor_trace: unavailable")
        return
    print(f"cursor_trace_rows: {len(trace)}")
    for position, raw in enumerate(trace, start=1):
        if not isinstance(raw, Mapping):
            continue
        print(
            "  "
            f"{position:02d}: "
            f"R[{raw.get('right_index')}]={raw.get('right_ship_id')} "
            f"L[{raw.get('left_index')}]={raw.get('left_ship_id')} "
            f"active={raw.get('other_active')} "
            f"strict={raw.get('other_strict_attacker')} "
            f"accepted={raw.get('accepted')}"
        )


def _print_row(label: str, row: Mapping[str, Any]) -> None:
    print(f"===== {label} =====")
    print(
        "identity: "
        f"game={row.get('game_id')} "
        f"turn={row.get('turn')} "
        f"capture_vcr={row.get('capture_vcr_id')} "
        f"next_vcr={row.get('next_vcr_id')} "
        f"prize={row.get('captured_ship_id')} "
        f"opponent={row.get('next_opponent_ship_id')}"
    )
    print(
        "side: "
        f"capture={row.get('capture_side')} "
        f"factual={row.get('factual_prize_side')}"
    )
    print(
        "identity_anchored_split: "
        f"{_fmt(row.get('identity_anchored_split'))}"
    )
    anchored = row.get("identity_anchored_result")
    if isinstance(anchored, Mapping):
        print(
            "cursor: "
            f"capture={_fmt(anchored.get('capture_cursor'))} "
            f"predicted={_fmt(anchored.get('predicted_cursor'))}"
        )
        print(
            "order: "
            f"{_fmt(anchored.get('external_order'))}"
        )
        print(
            "order_keys: "
            f"{_fmt(anchored.get('external_order_keys'))}"
        )
        print(
            "anchored_result: "
            f"status={anchored.get('status')} "
            f"reason={anchored.get('reason')} "
            f"pair_exact={anchored.get('pair_exact')} "
            f"predicted_side={anchored.get('predicted_prize_side')}"
        )
    print(f"dependency: {_fmt(row.get('active_dependency'))}")
    _print_cursor_trace(row)
    print()


def _print_repeated_capture_chain(
    payload: Mapping[str, Any],
    *,
    game_id: int,
    turn: int,
    ship_id: int,
) -> None:
    rows = [
        row
        for row in _rows(payload)
        if row.get("game_id") == game_id
        and row.get("turn") == turn
        and row.get("captured_ship_id") == ship_id
    ]
    rows.sort(key=lambda row: int(row.get("capture_vcr_id", -1)))
    print(
        "===== REPEATED CAPTURE CHAIN "
        f"game={game_id} turn={turn} ship={ship_id} ====="
    )
    if not rows:
        print("no rows")
        return
    for row in rows:
        print(
            f"VCR {row.get('capture_vcr_id')} -> {row.get('next_vcr_id')}: "
            f"capture_side={row.get('capture_side')} "
            f"factual_next_side={row.get('factual_prize_side')} "
            f"next_opponent={row.get('next_opponent_ship_id')}"
        )
        print(
            "  identity_anchored_split="
            f"{_fmt(row.get('identity_anchored_split'))}"
        )
        anchored = row.get("identity_anchored_result")
        if isinstance(anchored, Mapping):
            print(
                "  anchored="
                f"status={anchored.get('status')} "
                f"reason={anchored.get('reason')} "
                f"pair_exact={anchored.get('pair_exact')}"
            )
        print(
            "  dependency="
            f"{_fmt(row.get('active_dependency'))}"
        )
    print()


def run(args: argparse.Namespace) -> int:
    mismatch = _load(args.mismatch_report)
    repeated = _load(args.repeated_capture_report)

    mismatch_rows = [
        row
        for row in _identity_residuals(mismatch)
        if row.get("game_id") == 476380
        and row.get("turn") == 223
        and row.get("capture_vcr_id") == 903
    ]
    if len(mismatch_rows) != 1:
        raise ValueError(
            "expected exactly one 476380/T223/VCR903 residual, "
            f"found {len(mismatch_rows)}"
        )
    _print_row("HELDOUT SIDE COUNTEREXAMPLE", mismatch_rows[0])

    _print_repeated_capture_chain(
        repeated,
        game_id=257776,
        turn=230,
        ship_id=71,
    )

    repeated_rows = [
        row
        for row in _identity_residuals(repeated)
        if row.get("game_id") == 257776
        and row.get("turn") == 230
        and row.get("capture_vcr_id") == 1645
    ]
    if len(repeated_rows) != 1:
        raise ValueError(
            "expected exactly one 257776/T230/VCR1645 residual, "
            f"found {len(repeated_rows)}"
        )
    _print_row("REPEATED-CAPTURE UNRESOLVED", repeated_rows[0])
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Print the two post-heldout capture-side residuals without "
            "rerunning Corpus DB mechanics probes."
        )
    )
    parser.add_argument(
        "--mismatch-report",
        type=Path,
        default=Path(
            "artifacts/public-capture-side/heldout-residual-476380.json"
        ),
    )
    parser.add_argument(
        "--repeated-capture-report",
        type=Path,
        default=Path(
            "artifacts/public-capture-side/heldout-residual-257776.json"
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
