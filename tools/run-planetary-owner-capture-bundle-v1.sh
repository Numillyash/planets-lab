#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
OUT="artifacts/planetary/owner-capture-bundle-v1/published/report.json"
[[ -x "$PYTHON" ]] || { echo "ERROR: research Python unavailable" >&2; exit 69; }
echo "===== M2 OWNER-SCOPED PREHOST BUNDLE TEST ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "scope: synthetic per-owner signatures, no actual NuHost order capture"
rm -f "$OUT"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 tools/diagnostics/planetary_owner_bundle_v1.py --output "$OUT"
[[ -s "$OUT" ]] || { echo "ERROR: report not produced" >&2; exit 66; }
echo "===== M2 OWNER-SCOPED REPORT PUBLISHED ====="
