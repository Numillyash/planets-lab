#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SOURCE="artifacts/planetary/historical-differential-v1/published"
OUT="artifacts/planetary/evidence-triangulation-v1/published"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state research Python missing" >&2; exit 69; }
for file in manifest supplies taxes minerals populations; do
 [[ -f "$SOURCE/$file.json" ]] || { echo "ERROR: missing original published M2 source: $file" >&2; exit 66; }
done
echo "===== M2 ECONOMY FOUR-FAMILY CROSS-EVIDENCE GATE ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "source manifest Git blob: c2d95b1c50d89895a30497f0008c0e0f486d12ef"
echo "scope: pinned 650 previously observed planets; no corpus rescans"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 "$ROOT/tools/diagnostics/planetary_evidence_triangulation_v1.py" \
 --source-dir "$SOURCE" --output-dir "$OUT"
echo "===== M2 CROSS-FAMILY REPORTS COMPLETE ====="
