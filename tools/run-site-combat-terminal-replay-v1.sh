#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "\${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "\${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to the shared corpus DB root}"

OUTPUT="\${OUTPUT:-artifacts/combat/site-terminal-replay/game400330-t141-v592-595.json}"
RUNTIME_MODE="\${PLANETS_SITE_TERMINAL_RUNTIME_MODE:-local}"

mkdir -p "$(dirname "$OUTPUT")"

echo "===== SITE COMBAT TERMINAL REPLAY V1 ====="
echo "HEAD:      $(git rev-parse HEAD)"
echo "runtime:   $RUNTIME_MODE"
echo "output:    $OUTPUT"
echo

PLANETS_SITE_STATE_RUNTIME_MODE="$RUNTIME_MODE" \
PLANETS_SITE_STATE_TERMINAL_SOURCE=replay \
OUTPUT="$OUTPUT" \
bash tools/run-site-combat-state-v1.sh

python3 - "$OUTPUT" <<'PY'
from __future__ import annotations

import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
report = json.loads(path.read_text(encoding="utf-8"))
summary = report.get("summary") or {}
boundary = report.get("evidence_boundary") or ""

expected_modes = [
    "capture_immediate_C",
    "capture_parent_resume",
    "capture_immediate_C",
]
checks = {
    "status": report.get("status") == "SITE_STATE_EXACT",
    "terminal_source": (
        report.get("terminal_source")
        == "current_vcr_replay_carried_overlay"
    ),
    "expected_transitions": summary.get("expected_transitions") == 3,
    "evaluated_transitions": summary.get("evaluated_transitions") == 3,
    "exact_transitions": summary.get("exact_transitions") == 3,
    "current_vcr_start_exact": (
        summary.get("current_vcr_start_exact_transitions") == 3
    ),
    "next_vcr_start_exact": (
        summary.get("next_vcr_start_exact_transitions") == 3
    ),
    "all_exact": summary.get("all_exact") is True,
    "modes": summary.get("modes") == expected_modes,
    "terminal_adapter_boundary": "site_terminal_adapter" in boundary,
    "next_vcr_comparator_boundary": (
        "N+1 start vectors are opened only after selection" in boundary
    ),
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    print("SITE_TERMINAL_REPLAY_FAILED")
    print("failed_checks:", ", ".join(failed))
    print("terminal_source:", report.get("terminal_source"))
    print("summary:", summary)
    print("evidence_boundary:", boundary)
    raise SystemExit(1)

print("SITE_TERMINAL_REPLAY_EXACT")
print("expected_transitions:", summary["expected_transitions"])
print("evaluated_transitions:", summary["evaluated_transitions"])
print("exact_transitions:", summary["exact_transitions"])
print(
    "current_vcr_start_exact_transitions:",
    summary["current_vcr_start_exact_transitions"],
)
print(
    "next_vcr_start_exact_transitions:",
    summary["next_vcr_start_exact_transitions"],
)
print("modes:", summary["modes"])
print("terminal_source:", report["terminal_source"])
PY
