from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "planets-lab.combat-capture-reintegration-check.v1"
PROFILE = "combat-planar-no-horwasp"
EXPECTED_CAPTURE_CONTINUATIONS = 23
EXPECTED_SHIP_CONTINUATIONS = 8
EXPECTED_PLANET_CONTINUATIONS = 15


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _summary(report: Mapping[str, Any]) -> Mapping[str, Any]:
    value = report.get("summary")
    return value if isinstance(value, Mapping) else {}


def _scope(summary: Mapping[str, Any]) -> Mapping[str, Any]:
    value = summary.get("feature_scope")
    return value if isinstance(value, Mapping) else {}


def _acceptance(summary: Mapping[str, Any]) -> Mapping[str, Any]:
    value = summary.get("acceptance")
    return value if isinstance(value, Mapping) else {}


def _counts(summary: Mapping[str, Any]) -> Mapping[str, Any]:
    value = summary.get("counts")
    return value if isinstance(value, Mapping) else {}


def run(
    predictive_path: Path,
    capture_path: Path,
    initiator_path: Path,
) -> dict[str, Any]:
    predictive = _load(predictive_path)
    capture = _summary(_load(capture_path))
    initiator = _summary(_load(initiator_path))

    capture_counts = _counts(capture)
    initiator_counts = _counts(initiator)
    capture_acceptance = _acceptance(capture)
    initiator_acceptance = _acceptance(initiator)

    capture_population = int(capture_counts.get("capture_reappearance_transitions", 0) or 0)
    initiator_population = int(initiator_counts.get("capture_continuations", 0) or 0)
    ship_continuations = int(initiator_counts.get("opponent_type:ship", 0) or 0)
    planet_continuations = int(initiator_counts.get("opponent_type:planet", 0) or 0)
    independent = int(initiator_counts.get("independent_opponent_attack_candidate", 0) or 0)

    checks = {
        "predictive_queue_checkpoint_exact": predictive.get("exact") is True,
        "predictive_queue_checkpoint_no_failures": predictive.get("failures") == [],
        "capture_scope_profile_exact": _scope(capture).get("profile") == PROFILE,
        "initiator_scope_profile_exact": _scope(initiator).get("profile") == PROFILE,
        "capture_transition_gate_passed": capture_acceptance.get("capture_transition_gate_passed") is True,
        "post_capture_initiator_gate_passed": initiator_acceptance.get("post_capture_initiator_gate_passed") is True,
        "capture_population_preserved": capture_population == EXPECTED_CAPTURE_CONTINUATIONS,
        "initiator_population_preserved": initiator_population == EXPECTED_CAPTURE_CONTINUATIONS,
        "ship_continuation_population_preserved": ship_continuations == EXPECTED_SHIP_CONTINUATIONS,
        "planet_continuation_population_preserved": planet_continuations == EXPECTED_PLANET_CONTINUATIONS,
        "all_continuations_have_independent_opponent_attack": independent == EXPECTED_CAPTURE_CONTINUATIONS,
        "capture_required_unresolved_zero": int(initiator.get("required_unresolved_total", -1)) == 0,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "counts": {
            "capture_continuations": capture_population,
            "initiator_continuations": initiator_population,
            "ship_continuations": ship_continuations,
            "planet_continuations": planet_continuations,
            "independent_opponent_attack": independent,
        },
        "checks": checks,
        "exact": not failures,
        "failures": failures,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gate capture-state and opponent-initiator continuity after C5 reintegration."
    )
    parser.add_argument("predictive_integration", type=Path)
    parser.add_argument("capture_report", type=Path)
    parser.add_argument("initiator_report", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(
        args.predictive_integration,
        args.capture_report,
        args.initiator_report,
    )
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
