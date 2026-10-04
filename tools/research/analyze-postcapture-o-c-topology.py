#!/usr/bin/env python3
"""Position-only O/C topology census for public post-capture continuations.

This intentionally does not predict pair eligibility or LEFT/RIGHT. It only
classifies where the factual N+1 opponent sits in the already-frozen external
order topology relative to:
- the captured prize position; and
- the capture target/captor cursor position.

The c2ng/THost order vector remains EXTERNAL_IMPLEMENTATION evidence only.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import sys
from typing import Any


DEFAULT_DISCOVERY = Path(
    "/root/projects/planets-lab/artifacts/public-capture-side/"
    "discovery-o-layer-probe.json"
)
DEFAULT_HELDOUT = Path(
    "/root/projects/planets-lab/artifacts/public-capture-side/"
    "heldout-o-layer-validation.json"
)
DEFAULT_OUTPUT = Path(
    "artifacts/external-sources/postcapture-occurrence/"
    "public-o-c-topology-census.json"
)


def _load(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _matches_partition(
    payload: Mapping[str, Any],
    *,
    expected: str,
) -> bool:
    """Accept current and legacy O-layer artifacts for a known partition."""

    partition = payload.get("partition")
    if partition is not None:
        return partition == expected

    evidence_status = payload.get("evidence_status")
    if isinstance(evidence_status, str):
        upper = evidence_status.upper()
        if expected == "discovery" and upper.startswith("DISCOVERY_"):
            return True
        if expected == "heldout" and "HELDOUT" in upper:
            return True

    # Legacy v1 reports predate the explicit top-level partition field.
    # Their source path/name still records which sealed public partition
    # produced the artifact. The runner passes the expected partition
    # explicitly, so this is only a compatibility bridge, not inference.
    if payload.get("schema") == "planets-lab.combat-public-capture-o-layer-probe.v1":
        for key in (
            "source_discovery",
            "source_heldout",
            "source_capture_side_report",
        ):
            value = payload.get(key)
            if isinstance(value, str) and expected in value.lower():
                return True

    return False


def _index(order: Sequence[Any], ship_id: int) -> int | None:
    values = [int(v) for v in order if _is_int(v)]
    try:
        return values.index(ship_id)
    except ValueError:
        return None


def _classify(
    *,
    prize_position: int,
    captor_position: int,
    factual_position: int,
) -> str:
    if prize_position >= captor_position:
        return "OTHER_GEOMETRY"
    if factual_position > captor_position:
        return "O_AFTER_CAPTOR"
    if prize_position < factual_position < captor_position:
        return "C_BETWEEN_PRIZE_AND_CAPTOR"
    if factual_position <= prize_position:
        return "BEFORE_OR_AT_PRIZE"
    return "OTHER_GEOMETRY"


def _partition_rows(
    payload: Mapping[str, Any],
    *,
    partition: str,
) -> tuple[Counter[str], list[dict[str, Any]]]:
    if not _matches_partition(payload, expected=partition):
        raise ValueError(
            "O-layer artifact is not recognizable as "
            f"{partition}-only; partition={payload.get('partition')!r}, "
            f"evidence_status={payload.get('evidence_status')!r}, "
            f"schema={payload.get('schema')!r}"
        )

    rows = payload.get("observations")
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        raise ValueError(f"{partition}: observations missing or malformed")

    counts: Counter[str] = Counter()
    cases: list[dict[str, Any]] = []

    for row in rows:
        capture_vcr = row.get("capture_vcr_id")
        next_vcr = row.get("next_vcr_id")
        if not _is_int(capture_vcr) or not _is_int(next_vcr):
            counts["shape_unresolved"] += 1
            continue
        if int(next_vcr) != int(capture_vcr) + 1:
            counts["nonadjacent"] += 1
            continue
        counts["adjacent"] += 1

        capture_side = row.get("capture_side")
        if capture_side != "right":
            counts[f"capture_side:{capture_side}"] += 1
            continue
        counts["capture_side:right"] += 1

        prize_id = row.get("captured_ship_id")
        factual_id = row.get("next_opponent_ship_id")
        if not _is_int(prize_id) or not _is_int(factual_id):
            counts["right:identity_unresolved"] += 1
            continue

        anchored = row.get("identity_anchored_result")
        if not isinstance(anchored, Mapping):
            counts["right:cursor_result_missing"] += 1
            continue

        order = anchored.get("external_order")
        cursor = anchored.get("capture_cursor")
        if (
            not isinstance(order, Sequence)
            or isinstance(order, (str, bytes))
            or not isinstance(cursor, Mapping)
        ):
            counts["right:order_or_cursor_missing"] += 1
            continue

        captor_id = cursor.get("left_ship_id")
        right_ship_id = cursor.get("right_ship_id")
        if not _is_int(captor_id) or not _is_int(right_ship_id):
            counts["right:capture_cursor_identity_unresolved"] += 1
            continue
        if int(right_ship_id) != int(prize_id):
            counts["right:cursor_prize_not_right"] += 1
            cases.append(
                {
                    "partition": partition,
                    "game_id": row.get("game_id"),
                    "turn": row.get("turn"),
                    "capture_vcr_id": int(capture_vcr),
                    "next_vcr_id": int(next_vcr),
                    "captured_ship_id": int(prize_id),
                    "factual_opponent_ship_id": int(factual_id),
                    "classification": "OTHER_GEOMETRY",
                    "reason": "cursor_prize_not_right",
                    "external_order": list(order),
                    "capture_cursor": dict(cursor),
                }
            )
            continue

        prize_pos = _index(order, int(prize_id))
        captor_pos = _index(order, int(captor_id))
        factual_pos = _index(order, int(factual_id))
        if any(value is None for value in (prize_pos, captor_pos, factual_pos)):
            counts["right:order_position_missing"] += 1
            continue

        assert prize_pos is not None
        assert captor_pos is not None
        assert factual_pos is not None
        classification = _classify(
            prize_position=prize_pos,
            captor_position=captor_pos,
            factual_position=factual_pos,
        )
        counts[f"right:class:{classification}"] += 1
        counts["right:classified"] += 1

        if classification in {
            "O_AFTER_CAPTOR",
            "C_BETWEEN_PRIZE_AND_CAPTOR",
        }:
            counts["right:forward_union_covered"] += 1
        if classification == "BEFORE_OR_AT_PRIZE":
            counts["right:requires_before_prize"] += 1

        cases.append(
            {
                "partition": partition,
                "game_id": row.get("game_id"),
                "turn": row.get("turn"),
                "x": row.get("x"),
                "y": row.get("y"),
                "capture_vcr_id": int(capture_vcr),
                "next_vcr_id": int(next_vcr),
                "captured_ship_id": int(prize_id),
                "captor_ship_id": int(captor_id),
                "factual_opponent_ship_id": int(factual_id),
                "factual_prize_side": row.get("factual_prize_side"),
                "identity_anchored_o_pair_exact": anchored.get("pair_exact"),
                "classification": classification,
                "positions": {
                    "prize": prize_pos,
                    "captor": captor_pos,
                    "factual": factual_pos,
                },
                "external_order": [int(v) for v in order if _is_int(v)],
                "capture_cursor": dict(cursor),
            }
        )

    return counts, cases


def run(
    discovery: Mapping[str, Any],
    heldout: Mapping[str, Any],
) -> dict[str, Any]:
    total_counts: Counter[str] = Counter()
    all_cases: list[dict[str, Any]] = []
    per_partition: dict[str, dict[str, int]] = {}

    for name, payload in (
        ("discovery", discovery),
        ("heldout", heldout),
    ):
        counts, cases = _partition_rows(payload, partition=name)
        per_partition[name] = dict(sorted(counts.items()))
        for key, value in counts.items():
            total_counts[f"{name}:{key}"] += int(value)
            total_counts[f"all:{key}"] += int(value)
        all_cases.extend(cases)

    classified = int(total_counts["all:right:classified"])
    covered = int(total_counts["all:right:forward_union_covered"])
    before = int(total_counts["all:right:requires_before_prize"])

    return {
        "schema": "planets-lab.postcapture-o-c-topology-census.v1",
        "evidence_status": "POST_HELDOUT_STRUCTURE_CANDIDATE_CENSUS",
        "summary": {
            "counts": dict(sorted(total_counts.items())),
            "per_partition": per_partition,
            "right_forward_union_coverage": (
                {
                    "covered": covered,
                    "classified": classified,
                    "exact_fraction": (
                        covered / classified if classified else None
                    ),
                }
            ),
            "right_requires_before_prize": before,
        },
        "cases": sorted(
            all_cases,
            key=lambda row: (
                str(row.get("partition")),
                int(row.get("game_id") or 0),
                int(row.get("turn") or 0),
                int(row.get("capture_vcr_id") or 0),
            ),
        ),
        "candidate_definition": {
            "O_AFTER_CAPTOR": (
                "factual opponent lies strictly after the consumed capture "
                "target/captor cursor position"
            ),
            "C_BETWEEN_PRIZE_AND_CAPTOR": (
                "O cannot reach factual by forward continuation, but factual "
                "lies strictly after the prize's own frozen order position and "
                "before the consumed capture target"
            ),
            "BEFORE_OR_AT_PRIZE": (
                "factual target would require reaching a position at/before "
                "the prize's own frozen order position"
            ),
        },
        "evidence_boundary": (
            "Position-only census. The external order vector/cursor is the "
            "already-frozen c2ng/THost comparator and is not NuHost authority. "
            "No pair eligibility, target selection, C insertion priority or "
            "LEFT/RIGHT is predicted. Discovery and previously opened public "
            "heldout are both used, so any fit is structural/fitting evidence."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discovery", type=Path, default=DEFAULT_DISCOVERY)
    parser.add_argument("--heldout", type=Path, default=DEFAULT_HELDOUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(_load(args.discovery), _load(args.heldout))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        counts = report["summary"]["counts"]
        print("===== POST-CAPTURE O/C TOPOLOGY CENSUS =====")
        for partition in ("discovery", "heldout", "all"):
            print(partition + ":")
            print(
                "  adjacent:                    "
                f"{counts.get(partition + ':adjacent', 0)}"
            )
            print(
                "  capture RIGHT:               "
                f"{counts.get(partition + ':capture_side:right', 0)}"
            )
            print(
                "  classified RIGHT:            "
                f"{counts.get(partition + ':right:classified', 0)}"
            )
            print(
                "  O after captor:               "
                f"{counts.get(partition + ':right:class:O_AFTER_CAPTOR', 0)}"
            )
            print(
                "  C between prize/captor:       "
                f"{counts.get(partition + ':right:class:C_BETWEEN_PRIZE_AND_CAPTOR', 0)}"
            )
            print(
                "  before/at prize:              "
                f"{counts.get(partition + ':right:class:BEFORE_OR_AT_PRIZE', 0)}"
            )
            print(
                "  other geometry:               "
                f"{counts.get(partition + ':right:class:OTHER_GEOMETRY', 0)}"
            )
            print(
                "  forward union covered:        "
                f"{counts.get(partition + ':right:forward_union_covered', 0)}"
            )
            print()

        print("RIGHT-SIDE NON-O CASES:")
        for row in report["cases"]:
            if row.get("classification") in {
                "C_BETWEEN_PRIZE_AND_CAPTOR",
                "BEFORE_OR_AT_PRIZE",
                "OTHER_GEOMETRY",
            }:
                print(
                    f"  {row.get('partition')} "
                    f"{row.get('game_id')}/T{row.get('turn')} "
                    f"VCR {row.get('capture_vcr_id')}->{row.get('next_vcr_id')} "
                    f"prize={row.get('captured_ship_id')} "
                    f"captor={row.get('captor_ship_id')} "
                    f"factual={row.get('factual_opponent_ship_id')} "
                    f"class={row.get('classification')} "
                    f"positions={row.get('positions')}"
                )

        print()
        print(f"output: {args.output}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
