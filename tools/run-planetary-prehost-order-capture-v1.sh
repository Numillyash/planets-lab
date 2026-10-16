#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
OUT="artifacts/planetary/prehost-order-capture-v1/published/report.json"
[[ -x "$PYTHON" ]] || { echo "ERROR: research Python unavailable" >&2; exit 69; }
echo "===== M2 PREHOST ORDER CAPTURE ADMISSION CONTROLS ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "scope: synthetic signing, identity, HMAC, time, coverage and fail-closed; NO real NuHost submitted orders"
rm -f "$OUT"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 tools/diagnostics/planetary_order_capture_v1.py --output "$OUT"
[[ -s "$OUT" ]] || { echo "ERROR: published report absent" >&2; exit 66; }
echo "===== M2 PREHOST ORDER ADMISSION REPORT PUBLISHED ====="
