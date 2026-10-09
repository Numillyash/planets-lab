#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
CAPTURE="artifacts/combat/mass-capture-phase-controls-v1/published/report.json"
RESIDUALS="artifacts/combat/mass-residual-complete-v1/published/residuals.json"
OUTPUT="artifacts/combat/mass-temporal-reconciliation-v1/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$CAPTURE" ]] || { echo "ERROR: capture/static controls missing: $CAPTURE" >&2; exit 66; }
[[ -f "$RESIDUALS" ]] || { echo "ERROR: complete 67-residual source missing: $RESIDUALS" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: cached site-state Python missing: $PYTHON" >&2; exit 69; }
echo "===== MASS TEMPORAL RECONCILIATION V1 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "capture_controls: $CAPTURE"
echo "residuals: $RESIDUALS"
echo "output: $OUTPUT"
"$PYTHON" tools/diagnostics/combat_mass_temporal_reconciliation_v1.py \
 --capture-controls "$CAPTURE" \
 --complete-residuals "$RESIDUALS" \
 --output "$OUTPUT"
