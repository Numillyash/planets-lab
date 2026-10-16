#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
OUT="artifacts/planetary/order-aware-slice-v1/published/report.json"
[[ -x "$PYTHON" ]] || { echo "ERROR: research Python unavailable" >&2; exit 69; }
echo "===== M2 ORDER-AWARE RESEARCH INTEGRATION ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "scope: 3-turn internal simulation; NOT NuHost historical validation"
PYTHONPATH="$ROOT/src:$ROOT/tests" "$PYTHON" -m pytest -q tests/test_planetary_order_aware_slice.py
PYTHONPATH="$ROOT/src:$ROOT/tests" "$PYTHON" tools/diagnostics/planetary_order_aware_slice_v1.py --output "$OUT"
echo "===== M2 ORDER-AWARE REPORT PUBLISHED ====="
