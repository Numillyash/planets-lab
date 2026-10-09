#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SOURCE="artifacts/combat/mass-residual-complete-v1/published/residuals.json"
OUTPUT="artifacts/combat/mass-rulebook-reconciliation-v2/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$SOURCE" ]] || { echo "ERROR: published 67-residual input missing: $SOURCE" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: cached site-state Python missing: $PYTHON" >&2; exit 69; }
echo "===== COMBAT MASS RULEBOOK RECONCILIATION V2 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "source: $SOURCE"
echo "output: $OUTPUT"
"$PYTHON" tools/diagnostics/combat_mass_rulebook_reconciliation_v2.py \
  --source "$SOURCE" \
  --output "$OUTPUT"
