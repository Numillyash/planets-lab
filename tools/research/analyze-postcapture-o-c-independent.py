#!/usr/bin/env python3
"""Independent short32 O/C topology gate.

Consumes the already-produced independent O-layer artifact and applies the
position classes frozen before reading short32 O/C topology. No pair selector
or LEFT/RIGHT rule is fitted here.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "analyze-postcapture-o-c-topology.py"
DEFAULT_INPUT = Path(
    "/root/projects/planets-lab/artifacts/public-capture-side/"
    "independent-short32-postheldout-validation.json"
)
DEFAULT_OUTPUT = Path(
    "artifacts/external-sources/postcapture-occurrence/"
    "independent-short32-o-c-topology-gate.json"
)


def _load_base():
    spec = importlib.util.spec_from_file_location(
        "postcapture_o_c_topology_base",
        BASE_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import topology analyzer: {BASE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def run(payload: Mapping[str, Any]) -> dict[str, Any]:
    base = _load_base()
    counts, cases = base._partition_rows(payload, partition="independent")

    right = int(counts.get("capture_side:right", 0))
    classified = int(counts.get("right:classified", 0))
    qualified = int(counts.get("right:dependency:qualified", 0))
    q_o = int(
        counts.get(
            "right:dependency:qualified:class:O_AFTER_CAPTOR",
            0,
        )
    )
    q_c = int(
        counts.get(
            "right:dependency:qualified:class:C_BETWEEN_PRIZE_AND_CAPTOR",
            0,
        )
    )
    q_before = int(
        counts.get(
            "right:dependency:qualified:class:BEFORE_OR_AT_PRIZE",
            0,
        )
    )
    q_other = int(
        counts.get(
            "right:dependency:qualified:class:OTHER_GEOMETRY",
            0,
        )
    )
    q_covered = int(
        counts.get(
            "right:dependency:qualified:forward_union_covered",
            0,
        )
    )

    if classified != right:
        status = "INCOMPLETE_POSITION_CLASSIFICATION"
    elif qualified <= 0:
        status = "INCOMPLETE_NO_QUALIFIED_ROWS"
    elif q_before > 0 or q_other > 0 or q_covered != qualified:
        status = "FAILED_COUNTEREXAMPLE"
    elif q_o > 0 and q_c > 0:
        status = "PASS_FULL_BRANCH_COVERAGE"
    else:
        status = "PASS_PARTIAL_BRANCH_COVERAGE"

    counterexamples = [
        row
        for row in cases
        if isinstance(row, Mapping)
        and isinstance(row.get("dependency"), Mapping)
        and row["dependency"].get("qualified") is True
        and row.get("classification")
        in {"BEFORE_OR_AT_PRIZE", "OTHER_GEOMETRY"}
    ]

    return {
        "schema": "planets-lab.postcapture-o-c-independent-topology-gate.v1",
        "partition": "independent",
        "evidence_status": "INDEPENDENT_O_C_TOPOLOGY_VALIDATION",
        "frozen_candidate_commit": (
            "7e590cd73690ebf544ff8b7d671747cb6e0ca047"
        ),
        "frozen_gate_protocol_commit": (
            "a5002f7df49c7db76b0d38cd86fb916ae29f3dcc"
        ),
        "status": status,
        "summary": {
            "counts": dict(sorted(counts.items())),
            "right_rows": right,
            "classified_right_rows": classified,
            "qualified_right_rows": qualified,
            "qualified_o_after_captor": q_o,
            "qualified_c_between_prize_and_captor": q_c,
            "qualified_before_or_at_prize": q_before,
            "qualified_other_geometry": q_other,
            "qualified_forward_union_covered": q_covered,
            "qualified_forward_union_exact": (
                q_covered == qualified if qualified > 0 else None
            ),
            "full_branch_coverage": q_o > 0 and q_c > 0,
        },
        "qualified_counterexamples": counterexamples,
        "cases": cases,
        "evidence_boundary": (
            "Independent short32 topology validation of position classes frozen "
            "before short32 O/C topology was read. short32 has zero game-id "
            "overlap with public36 and was independently selected, but it was "
            "previously opened for capture-side LEFT/RIGHT validation. The "
            "external order vector remains c2ng/THost implementation evidence, "
            "not NuHost authority. Only dependency-qualified RIGHT captures "
            "decide the topology gate."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(_load(args.input))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        s = report["summary"]
        print("===== INDEPENDENT SHORT32 O/C TOPOLOGY GATE =====")
        print(f"status:                        {report['status']}")
        print(f"RIGHT rows:                    {s['right_rows']}")
        print(f"classified RIGHT:              {s['classified_right_rows']}")
        print(f"dependency qualified:          {s['qualified_right_rows']}")
        print(f"  qualified O after captor:    {s['qualified_o_after_captor']}")
        print(
            "  qualified C between:         "
            f"{s['qualified_c_between_prize_and_captor']}"
        )
        print(
            "  qualified before/at prize:   "
            f"{s['qualified_before_or_at_prize']}"
        )
        print(
            "  qualified other geometry:    "
            f"{s['qualified_other_geometry']}"
        )
        print(
            "  qualified forward covered:   "
            f"{s['qualified_forward_union_covered']}"
        )
        print(
            "  full branch coverage:         "
            f"{str(s['full_branch_coverage']).lower()}"
        )

        if report["qualified_counterexamples"]:
            print()
            print("QUALIFIED COUNTEREXAMPLES:")
            for row in report["qualified_counterexamples"]:
                print(
                    f"  {row.get('game_id')}/T{row.get('turn')} "
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
    except (OSError, ValueError, json.JSONDecodeError, ImportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
