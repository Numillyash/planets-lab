#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to the shared corpus DB root}"

OUTPUT="${OUTPUT:-artifacts/combat/site-input-adapter/game400330-t141-v592-595.json}"
RUNTIME_MODE="${PLANETS_SITE_INPUT_ADAPTER_RUNTIME_MODE:-local}"

mkdir -p "$(dirname "$OUTPUT")"

echo "===== SITE COMBAT INPUT ADAPTER V1 REGRESSION ====="
echo "HEAD:      $(git rev-parse HEAD)"
echo "runtime:   $RUNTIME_MODE"
echo "output:    $OUTPUT"
echo

PLANETS_SITE_STATE_RUNTIME_MODE="$RUNTIME_MODE" \
OUTPUT="$OUTPUT" \
bash tools/run-site-combat-state-v1.sh

python3 - "$OUTPUT" <<'PY'
from __future__ import annotations

import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
report = json.loads(path.read_text(encoding="utf-8"))

expected_modes = [
    "capture_immediate_C",
    "capture_parent_resume",
    "capture_immediate_C",
]
summary = report.get("summary") or {}
boundary = report.get("evidence_boundary") or ""

checks = {
    "status": report.get("status") == "SITE_STATE_EXACT",
    "expected_transitions": summary.get("expected_transitions") == 3,
    "evaluated_transitions": summary.get("evaluated_transitions") == 3,
    "exact_transitions": summary.get("exact_transitions") == 3,
    "all_exact": summary.get("all_exact") is True,
    "modes": summary.get("modes") == expected_modes,
    "adapter_boundary": "site_input_adapter" in boundary,
}

failed = [name for name, ok in checks.items() if not ok]
if failed:
    print("SITE_INPUT_ADAPTER_REGRESSION_FAILED")
    print("failed_checks:", ", ".join(failed))
    print("status:", report.get("status"))
    print("summary:", summary)
    print("evidence_boundary:", boundary)
    raise SystemExit(1)

print("SITE_INPUT_ADAPTER_EXACT")
print("expected_transitions:", summary["expected_transitions"])
print("evaluated_transitions:", summary["evaluated_transitions"])
print("exact_transitions:", summary["exact_transitions"])
print("modes:", summary["modes"])
print("adapter_boundary: yes")
PY
