from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EVIDENCE_KEYS = (
    "summary",
    "settings_sources_per_turn_member",
    "unsupported_reasons",
    "battle_shapes",
    "games",
    "malformed_member_samples",
    "details",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: report must be a JSON object")
    return value


def compare_reports(
    baseline: dict[str, Any],
    selected: dict[str, Any],
) -> dict[str, Any]:
    mismatches = [
        key for key in EVIDENCE_KEYS if baseline.get(key) != selected.get(key)
    ]
    return {
        "schema": "planets-lab.feature-index-integration-check.v1",
        "evidence_keys": list(EVIDENCE_KEYS),
        "mismatches": mismatches,
        "exact": not mismatches,
        "selected_feature_selection": selected.get("feature_selection"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that all-indexed feature selection leaves combat parity "
            "evidence-bearing output unchanged."
        )
    )
    parser.add_argument("baseline", type=Path)
    parser.add_argument("selected", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    try:
        report = compare_reports(_load(args.baseline), _load(args.selected))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2

    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["exact"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
