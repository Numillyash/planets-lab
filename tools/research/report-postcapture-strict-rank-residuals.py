#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import sys
from typing import Any

DEFAULT_O_LAYER = Path(
    "/root/projects/planets-lab/artifacts/public-capture-side/"
    "discovery-o-layer-probe.json"
)
DEFAULT_STRICT = Path(
    "artifacts/external-sources/afsim-r1/"
    "discovery-strict-rank-analysis.json"
)


def _load(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _key(row: Mapping[str, Any]) -> tuple[int, int, int, int, int, int] | None:
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


def _o_layer_index(payload: Mapping[str, Any]) -> dict[
    tuple[int, int, int, int, int, int],
    Mapping[str, Any],
]:
    rows = payload.get("observations")
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        raise ValueError("O-layer observations missing or malformed")
    result = {}
    for row in rows:
        key = _key(row)
        if key is not None:
            result[key] = row
    return result


def _rank_cases(payload: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    rows = payload.get("cases")
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        raise ValueError("strict-rank cases missing or malformed")
    return rows


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def run(
    *,
    o_layer: Mapping[str, Any],
    strict: Mapping[str, Any],
) -> dict[str, Any]:
    if strict.get("partition") != "discovery":
        raise ValueError("strict-rank artifact must be discovery")

    o_index = _o_layer_index(o_layer)
    counts: Counter[str] = Counter()
    rank_gt1: list[dict[str, Any]] = []
    rank_missing: list[dict[str, Any]] = []

    for case in _rank_cases(strict):
        key = _key(case)
        if key is None:
            counts["case_shape_unresolved"] += 1
            continue
        source = o_index.get(key)
        if source is None:
            counts["o_layer_join_missing"] += 1
            continue
        active = source.get("active_dependency")
        active = active if isinstance(active, Mapping) else {}

        strict_rank = case.get("strict_rank")
        row = {
            "game_id": key[0],
            "turn": key[1],
            "capture_vcr_id": key[2],
            "next_vcr_id": key[3],
            "captured_ship_id": key[4],
            "next_opponent_ship_id": key[5],
            "factual_prize_side": case.get("factual_prize_side"),
            "strict_rank": strict_rank if _is_int(strict_rank) else None,
            "requester_rank": (
                case.get("requester_rank")
                if _is_int(case.get("requester_rank"))
                else None
            ),
            "dependency_qualified": case.get("dependency_qualified"),
            "afsim_pair_category": case.get("afsim_pair_category"),
            "afsim_phase": case.get("afsim_phase"),
            "active_status": active.get("status"),
            "active_reason": active.get("reason"),
            "site_predicted": active.get("factual_opponent_site_predicted"),
            "prediction_position": active.get(
                "factual_opponent_prediction_position"
            ),
            "prediction_source": active.get(
                "factual_opponent_position_source"
            ),
            "history_anchored": active.get(
                "factual_opponent_history_anchored"
            ),
            "removed_before_next": active.get(
                "factual_opponent_removed_before_next"
            ),
            "owner_changed_before_next": active.get(
                "factual_opponent_owner_changed_before_next"
            ),
            "active": active.get("factual_opponent_active"),
            "candidate_resolved": active.get(
                "factual_opponent_candidate_resolved"
            ),
            "requests_new_owner": active.get(
                "factual_opponent_requests_new_owner"
            ),
            "strict_permission": active.get(
                "factual_opponent_strict_permission"
            ),
        }

        if _is_int(strict_rank) and int(strict_rank) > 1:
            rank_gt1.append(row)
            counts["strict_rank_gt1"] += 1
            counts[f"strict_rank_gt1:{int(strict_rank)}"] += 1
            counts[
                "strict_rank_gt1:afsim:" + str(case.get("afsim_pair_category"))
            ] += 1
        elif strict_rank is None:
            rank_missing.append(row)
            counts["strict_rank_missing"] += 1
            counts[
                "strict_rank_missing:active_status:" + str(active.get("status"))
            ] += 1
            counts[
                "strict_rank_missing:reason:" + str(active.get("reason"))
            ] += 1
            counts[
                "strict_rank_missing:prediction_source:"
                + str(active.get("factual_opponent_position_source"))
            ] += 1
            counts[
                "strict_rank_missing:site_predicted:"
                + str(active.get("factual_opponent_site_predicted"))
            ] += 1

    return {
        "schema": "planets-lab.postcapture-strict-rank-residual-report.v1",
        "partition": "discovery",
        "summary": dict(sorted(counts.items())),
        "rank_gt1": rank_gt1,
        "rank_missing": rank_missing,
        "heldout": "not_read",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Print the exact discovery rows where the factual post-capture "
            "opponent is strict-rank >1, plus dependency diagnostics for rows "
            "whose rank is missing."
        )
    )
    parser.add_argument("--o-layer", type=Path, default=DEFAULT_O_LAYER)
    parser.add_argument("--strict-rank", type=Path, default=DEFAULT_STRICT)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(
            o_layer=_load(args.o_layer),
            strict=_load(args.strict_rank),
        )

        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        print("===== STRICT-RANK >1 RESIDUALS =====")
        if not report["rank_gt1"]:
            print("none")
        for row in report["rank_gt1"]:
            print(
                f"{row['game_id']}/T{row['turn']} "
                f"VCR {row['capture_vcr_id']}->{row['next_vcr_id']} "
                f"prize={row['captured_ship_id']} "
                f"opp={row['next_opponent_ship_id']} "
                f"strict_rank={row['strict_rank']} "
                f"requester_rank={row['requester_rank']} "
                f"side={row['factual_prize_side']} "
                f"afsim={row['afsim_pair_category']}/{row['afsim_phase']}"
            )
            print(
                "  dependency: "
                f"status={_fmt(row['active_status'])} "
                f"site_predicted={_fmt(row['site_predicted'])} "
                f"source={_fmt(row['prediction_source'])} "
                f"active={_fmt(row['active'])} "
                f"candidate={_fmt(row['candidate_resolved'])} "
                f"request={_fmt(row['requests_new_owner'])} "
                f"strict={_fmt(row['strict_permission'])}"
            )

        print()
        print("===== STRICT-RANK MISSING DEPENDENCIES =====")
        missing = report["rank_missing"]
        print(f"rows: {len(missing)}")
        source_counts = Counter(
            str(row.get("prediction_source")) for row in missing
        )
        reason_counts = Counter(
            str(row.get("active_reason")) for row in missing
        )
        site_counts = Counter(
            str(row.get("site_predicted")) for row in missing
        )
        print("prediction_source:")
        for key, value in sorted(source_counts.items()):
            print(f"  {key}: {value}")
        print("active_reason:")
        for key, value in sorted(reason_counts.items()):
            print(f"  {key}: {value}")
        print("site_predicted:")
        for key, value in sorted(site_counts.items()):
            print(f"  {key}: {value}")

        print()
        print("missing rows:")
        for row in missing:
            print(
                f"  {row['game_id']}/T{row['turn']} "
                f"VCR {row['capture_vcr_id']}->{row['next_vcr_id']} "
                f"prize={row['captured_ship_id']} "
                f"opp={row['next_opponent_ship_id']} "
                f"source={_fmt(row['prediction_source'])} "
                f"reason={_fmt(row['active_reason'])} "
                f"site={_fmt(row['site_predicted'])} "
                f"afsim={row['afsim_pair_category']}/{row['afsim_phase']}"
            )

        if args.output is not None:
            print()
            print(f"output: {args.output}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
