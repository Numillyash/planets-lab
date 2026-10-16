#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
OUT="artifacts/planetary/multiturn-baseline-v1/published/report.json"
[[ -x "$PYTHON" ]] || { echo "ERROR: research Python environment unavailable" >&2; exit 69; }
echo "===== M2 START: PLANETARY MULTITURN BASELINE ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "scope: internal 3-turn deterministic phase composition, NOT NuHost parity"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 "$ROOT/tools/diagnostics/planetary_multiturn_baseline_v1.py" --output "$OUT"
echo "===== M2 BASELINE V1 PUBLISHED ====="
