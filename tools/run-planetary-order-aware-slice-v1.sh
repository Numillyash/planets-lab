#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
OUT="artifacts/planetary/order-aware-slice-v1/published/report.json"
[[ -x "$PYTHON" ]] || { echo "ERROR: research Python unavailable" >&2; exit 69; }

echo "===== M2 ORDER-AWARE RESEARCH INTEGRATION ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "scope: 3-turn synthetic integration and eight ABSTAIN controls; NOT NuHost historical validation"
echo "runtime: dependency-free scenario acceptance; pytest belongs to GitHub CI"
# Fail closed if a prior successful report is present and this invocation fails.
rm -f "$OUT"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/planetary_order_aware_slice_v1.py --output "$OUT"
[[ -s "$OUT" ]] || { echo "ERROR: runtime report is absent or empty" >&2; exit 66; }
echo "===== M2 ORDER-AWARE REPORT PUBLISHED ====="
