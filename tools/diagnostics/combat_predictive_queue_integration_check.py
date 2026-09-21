from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "planets-lab.combat-predictive-queue-integration-check.v1"
PROFILE = "combat-planar-no-horwasp"
HISTORICAL_MIN_TRANSITIONS = 22


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def run(feature_scope_path: Path, queue_path: Path) -> dict[str, Any]:
    feature = _load(feature_scope_path)
    queue = _load(queue_path)
    feature_checks = feature.get("checks")
    feature_checks = feature_checks if isinstance(feature_checks, Mapping) else {}
    queue_summary = queue.get("summary")
    queue_summary = queue_summary if isinstance(queue_summary, Mapping) else {}
    scope = queue_summary.get("feature_scope")
    scope = scope if isinstance(scope, Mapping) else {}
    acceptance = queue_summary.get("acceptance")
    acceptance = acceptance if isinstance(acceptance, Mapping) else {}
    counts = queue_summary.get("counts")
    counts = counts if isinstance(counts, Mapping) else {}

    checks: dict[str, bool] = {
        "feature_scope_exact": feature.get("exact") is True,
        "feature_scope_no_failures": feature.get("failures") == [],
        "selector_partition_shared": feature_checks.get("selector_partition_shared") is True,
        "selector_partition_disjoint": feature_checks.get("selector_partition_disjoint") is True,
        "planet_c4_checkpoint_preserved": feature_checks.get("planet_c4_checkpoint_preserved") is True,
        "ship_c3_checkpoint_preserved": feature_checks.get("ship_c3_checkpoint_preserved") is True,
        "cluster_partition_preserved": feature_checks.get("cluster_partition_preserved") is True,
        "queue_scope_profile_exact": scope.get("profile") == PROFILE,
        "queue_all_profiles_pass": acceptance.get("all_profiles_pass") is True,
    }

    profile_counts: dict[str, dict[str, int]] = {}
    for profile in ("strict", "conditional"):
        compared = int(counts.get(f"{profile}:transitions_compared", 0) or 0)
        exact = int(counts.get(f"{profile}:next_vcr_exact", 0) or 0)
        mismatch = int(counts.get(f"{profile}:next_vcr_mismatch", 0) or 0)
        profile_counts[profile] = {
            "transitions_compared": compared,
            "next_vcr_exact": exact,
            "next_vcr_mismatch": mismatch,
        }
        checks[f"{profile}_historical_population_preserved"] = (
            compared >= HISTORICAL_MIN_TRANSITIONS
        )
        checks[f"{profile}_held_out_next_vcr_exact"] = (
            compared > 0 and exact == compared and mismatch == 0
        )

    failures = [name for name, passed in checks.items() if not passed]
    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "checks": checks,
        "profile_counts": profile_counts,
        "exact": not failures,
        "failures": failures,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gate shared FeatureScope continuity plus held-out predictive combat queue."
    )
    parser.add_argument("feature_scope_integration", type=Path)
    parser.add_argument("queue_report", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args.feature_scope_integration, args.queue_report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0 if report["exact"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
