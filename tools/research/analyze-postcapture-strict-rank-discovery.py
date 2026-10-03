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
DEFAULT_AFSIM = Path(
    "artifacts/external-sources/afsim-r1/"
    "discovery-afsim-r1-analysis.json"
)
DEFAULT_OUTPUT = Path(
    "artifacts/external-sources/afsim-r1/"
    "discovery-strict-rank-analysis.json"
)


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


def _adjacent(row: Mapping[str, Any]) -> bool:
    a = row.get("capture_vcr_id")
    b = row.get("next_vcr_id")
    return _is_int(a) and _is_int(b) and int(b) == int(a) + 1


def _load(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _discovery_artifact(payload: Mapping[str, Any]) -> bool:
    """Accept both current and legacy discovery-only O-layer schemas."""

    partition = payload.get("partition")
    if partition == "discovery":
        return True
    if partition is not None:
        return False

    evidence_status = payload.get("evidence_status")
    if isinstance(evidence_status, str) and evidence_status.startswith("DISCOVERY_"):
        return True

    # Legacy v1 O-layer artifacts were discovery-only by construction and
    # carried source_discovery/evidence_status instead of an explicit partition.
    return (
        payload.get("schema") == "planets-lab.combat-public-capture-o-layer-probe.v1"
        and isinstance(payload.get("source_discovery"), str)
        and "discovery" in str(payload.get("source_discovery")).lower()
    )


def _afsim_index(payload: Mapping[str, Any]) -> dict[
    tuple[int, int, int, int, int, int],
    Mapping[str, Any],
]:
    rows = payload.get("cases")
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        raise ValueError("AFSim analysis cases missing or malformed")
    result = {}
    for row in rows:
        key = _key(row)
        if key is not None:
            result[key] = row
    return result


def run(
    o_layer: Mapping[str, Any],
    afsim: Mapping[str, Any],
) -> dict[str, Any]:
    if not _discovery_artifact(o_layer):
        raise ValueError(
            "O-layer artifact is not recognizable as discovery-only "
            "(expected partition=discovery or legacy DISCOVERY_* evidence)"
        )
    if afsim.get("partition") != "discovery":
        raise ValueError("AFSim analysis must be partition=discovery")

    rows = o_layer.get("observations")
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        raise ValueError("O-layer observations missing or malformed")

    afsim_by_key = _afsim_index(afsim)
    counts: Counter[str] = Counter()
    cases: list[dict[str, Any]] = []

    for row in rows:
        if not _adjacent(row):
            continue
        counts["adjacent_rows"] += 1

        key = _key(row)
        if key is None:
            counts["shape_unresolved"] += 1
            continue

        active = row.get("active_dependency")
        if not isinstance(active, Mapping):
            counts["active_dependency_missing"] += 1
            continue

        strict_rank = active.get("factual_opponent_strict_rank")
        requester_rank = active.get("factual_opponent_requester_rank")

        for label, rank in (
            ("strict", strict_rank),
            ("requester", requester_rank),
        ):
            if _is_int(rank):
                counts[f"{label}_rank:present"] += 1
                counts[f"{label}_rank:{int(rank)}"] += 1
                if int(rank) == 1:
                    counts[f"{label}_rank:first"] += 1
                else:
                    counts[f"{label}_rank:not_first"] += 1
            else:
                counts[f"{label}_rank:missing"] += 1

        qualified = all(
            active.get(name) is True
            for name in (
                "factual_opponent_active",
                "factual_opponent_candidate_resolved",
                "factual_opponent_requests_new_owner",
                "factual_opponent_strict_permission",
            )
        )
        counts[
            "dependency:qualified" if qualified else "dependency:not_qualified"
        ] += 1

        afsim_row = afsim_by_key.get(key)
        afsim_category = "missing"
        afsim_phase = "missing"
        if afsim_row is not None:
            variants = afsim_row.get("variants")
            if isinstance(variants, Mapping):
                variant = variants.get("tminus1")
                if isinstance(variant, Mapping):
                    raw_category = variant.get("pair_category")
                    raw_phase = variant.get("phase")
                    if isinstance(raw_category, str):
                        afsim_category = raw_category
                    if isinstance(raw_phase, str):
                        afsim_phase = raw_phase

        counts[f"afsim_category:{afsim_category}"] += 1
        if _is_int(strict_rank) and int(strict_rank) == 1:
            counts[f"afsim_category:{afsim_category}:strict_rank1"] += 1
        elif _is_int(strict_rank):
            counts[f"afsim_category:{afsim_category}:strict_rank_gt1"] += 1
        else:
            counts[f"afsim_category:{afsim_category}:strict_rank_missing"] += 1

        if afsim_category != "exact":
            counts["afsim_nonexact"] += 1
            if _is_int(strict_rank) and int(strict_rank) == 1:
                counts["afsim_nonexact:strict_rank1"] += 1

        cases.append(
            {
                "game_id": key[0],
                "turn": key[1],
                "capture_vcr_id": key[2],
                "next_vcr_id": key[3],
                "captured_ship_id": key[4],
                "next_opponent_ship_id": key[5],
                "factual_prize_side": row.get("factual_prize_side"),
                "strict_rank": int(strict_rank) if _is_int(strict_rank) else None,
                "requester_rank": (
                    int(requester_rank) if _is_int(requester_rank) else None
                ),
                "dependency_qualified": qualified,
                "afsim_pair_category": afsim_category,
                "afsim_phase": afsim_phase,
            }
        )

    expected_adjacent = (
        o_layer.get("summary", {})
        .get("counts", {})
        .get("adjacent_rows")
        if isinstance(o_layer.get("summary"), Mapping)
        else None
    )
    if _is_int(expected_adjacent) and counts["adjacent_rows"] != int(expected_adjacent):
        raise ValueError(
            "O-layer observation examples do not cover all adjacent rows: "
            f"examples={counts['adjacent_rows']} summary={expected_adjacent}"
        )

    if counts["adjacent_rows"] > 0 and counts["active_dependency_missing"] == counts["adjacent_rows"]:
        raise ValueError(
            "legacy O-layer artifact has no active_dependency rank context; "
            "refresh it with current main before strict-rank analysis"
        )

    return {
        "schema": "planets-lab.postcapture-strict-rank-discovery-analysis.v1",
        "partition": "discovery",
        "summary": dict(sorted(counts.items())),
        "cases": cases,
        "interpretation_boundary": (
            "The strict/requester rank is computed inside the independently "
            "reconstructed post-capture candidate set targeting the prize's new "
            "owner. Rank 1 tests next-opponent selection conditional on the "
            "captured prize being the recomposed target; it is not a complete "
            "global queue predictor and does not determine LEFT/RIGHT."
        ),
        "heldout": "not_read",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Test whether the factual post-capture opponent is rank 1 in the "
            "Nu-derived reconstructed requester set, and cross-tabulate AFSim "
            "queue failures."
        )
    )
    parser.add_argument("--o-layer", type=Path, default=DEFAULT_O_LAYER)
    parser.add_argument("--afsim-analysis", type=Path, default=DEFAULT_AFSIM)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(_load(args.o_layer), _load(args.afsim_analysis))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        c = report["summary"]

        print("===== POST-CAPTURE STRICT-RANK DISCOVERY ANALYSIS =====")
        print(f"adjacent rows:                  {c.get('adjacent_rows', 0)}")
        print(
            "strict rank 1 / >1 / missing:   "
            f"{c.get('strict_rank:first', 0)} / "
            f"{c.get('strict_rank:not_first', 0)} / "
            f"{c.get('strict_rank:missing', 0)}"
        )
        print(
            "requester rank 1 / >1 / missing:"
            f" {c.get('requester_rank:first', 0)} / "
            f"{c.get('requester_rank:not_first', 0)} / "
            f"{c.get('requester_rank:missing', 0)}"
        )
        print(
            "dependency qualified / other:   "
            f"{c.get('dependency:qualified', 0)} / "
            f"{c.get('dependency:not_qualified', 0)}"
        )
        print(
            "AFSim nonexact with strict rank1:"
            f" {c.get('afsim_nonexact:strict_rank1', 0)} / "
            f"{c.get('afsim_nonexact', 0)}"
        )
        print()
        print("AFSim category -> strict-rank1:")
        for category in (
            "exact",
            "prize_with_wrong_opponent",
            "factual_opponent_without_prize",
            "unrelated_pair",
            "no_pair",
            "missing",
        ):
            print(
                f"  {category:30s} "
                f"{c.get(f'afsim_category:{category}:strict_rank1', 0)} / "
                f"{c.get(f'afsim_category:{category}', 0)}"
            )
        print()
        print(f"output: {args.output}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
