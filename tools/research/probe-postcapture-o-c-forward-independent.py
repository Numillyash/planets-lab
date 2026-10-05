#!/usr/bin/env python3
"""Prospective independent validation wrapper for the frozen O->C selector."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping


BASE_PATH = Path(__file__).resolve().parent / "probe-postcapture-o-c-forward-open.py"


def _load_base():
    spec = importlib.util.spec_from_file_location(
        "postcapture_o_c_forward_frozen_base",
        BASE_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import frozen selector probe: {BASE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _gate_status(report: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    counts = report.get("summary", {}).get("counts", {})
    if not isinstance(counts, Mapping):
        raise ValueError("selector report counts missing")

    total = int(report.get("frozen_qualified_rows", 0))
    resolved = int(counts.get("primary:status:resolved", 0))
    exact = int(counts.get("primary:exact", 0))
    mismatch = int(counts.get("primary:mismatch", 0))
    unresolved = int(counts.get("primary:status:unresolved", 0))
    no_pair = int(counts.get("primary:status:no_pair", 0))
    active_unresolved = int(counts.get("primary:active_replay_unresolved", 0))
    order_unresolved = int(counts.get("primary:order_unresolved", 0))
    o_branch = int(counts.get("primary:branch:O", 0))
    c_branch = int(counts.get("primary:branch:C", 0))

    infrastructure_unresolved = active_unresolved + order_unresolved
    all_exact = (
        total > 0
        and resolved == total
        and exact == total
        and mismatch == 0
        and unresolved == 0
        and no_pair == 0
        and infrastructure_unresolved == 0
    )
    full_branch = o_branch > 0 and c_branch > 0

    if mismatch > 0:
        status = "FAILED_MISMATCH"
    elif total == 0:
        status = "INSUFFICIENT_NO_COMPARABLE_ROWS"
    elif (
        unresolved > 0
        or no_pair > 0
        or infrastructure_unresolved > 0
        or resolved != total
        or exact != total
    ):
        status = "INCOMPLETE_UNRESOLVED"
    elif all_exact and full_branch:
        status = "PASS_FULL_BRANCH_COVERAGE"
    elif all_exact:
        status = "PASS_PARTIAL_BRANCH_COVERAGE"
    else:
        status = "INCOMPLETE_UNRESOLVED"

    summary = {
        "qualified_rows": total,
        "resolved": resolved,
        "exact": exact,
        "mismatch": mismatch,
        "unresolved": unresolved,
        "no_pair": no_pair,
        "active_replay_unresolved": active_unresolved,
        "order_unresolved": order_unresolved,
        "o_branch": o_branch,
        "c_branch": c_branch,
        "all_exact": all_exact,
        "full_branch_coverage": full_branch,
    }
    return status, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-root", type=Path, required=True)
    parser.add_argument("--corpus-db-root", type=Path, required=True)
    parser.add_argument("--capture-report", type=Path, required=True)
    parser.add_argument("--o-layer-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        base = _load_base()
        base_args = argparse.Namespace(
            main_root=args.main_root,
            corpus_db_root=args.corpus_db_root,
            capture_report=args.capture_report,
            capture_partition="all",
            o_layer_report=args.o_layer_report,
            o_layer_partition="independent",
            label="fresh32-independent",
            output=args.output,
        )
        report = base.run(base_args)
        status, gate = _gate_status(report)

        report = dict(report)
        report["schema"] = (
            "planets-lab.postcapture-o-c-forward-independent-validation.v1"
        )
        report["label"] = "fresh32-independent"
        report["evidence_status"] = "INDEPENDENT_VALIDATION"
        report["validation_status"] = status
        report["validation_gate"] = gate
        report["frozen_selector_implementation_commit"] = (
            "d6f80a12c9d6fbf3eaa1d7dfeb1cc39839d147ad"
        )
        report["frozen_validation_protocol_commit"] = (
            "16b5a10e6bda7ebd8e98e1cee3a8ca16508727de"
        )
        report["evidence_boundary"] = (
            "Prospective independent validation on the fresh post-public68 "
            "32-game population selected before the O/C-forward exact selector "
            "was formulated. The population has zero game-id overlap with "
            "public68. Factual N+1 opponent identity is comparator-only; "
            "LEFT/RIGHT is not used by this gate. Public100 is opened through "
            "a temporary read-only validation view while canonical CURRENT "
            "remains public68."
        )

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        print("===== FRESH32 INDEPENDENT O/C-FORWARD VALIDATION =====")
        print(f"status:                    {status}")
        print(f"qualified rows:            {gate['qualified_rows']}")
        print(f"resolved:                  {gate['resolved']}")
        print(f"exact:                     {gate['exact']}")
        print(f"mismatch:                  {gate['mismatch']}")
        print(f"unresolved:                {gate['unresolved']}")
        print(f"no_pair:                   {gate['no_pair']}")
        print(
            "active/order unresolved:   "
            f"{gate['active_replay_unresolved']} / "
            f"{gate['order_unresolved']}"
        )
        print(f"O / C branches:            {gate['o_branch']} / {gate['c_branch']}")
        print(
            "full branch coverage:      "
            f"{str(gate['full_branch_coverage']).lower()}"
        )
        print(f"output:                    {args.output}")

        if status == "FAILED_MISMATCH":
            return 3
        if status in {
            "INCOMPLETE_UNRESOLVED",
            "INSUFFICIENT_NO_COMPARABLE_ROWS",
        }:
            return 4
        return 0
    except (OSError, ValueError, json.JSONDecodeError, ImportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
