#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
SOURCE="artifacts/combat/mass-independent-late-turn-stress-v1/published/report.json"
OUTPUT="artifacts/combat/mass-late-residual-prestate-audit-v1/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$SOURCE" ]] || { echo "ERROR: frozen public100 or stress report missing" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state Python missing: $PYTHON" >&2; exit 69; }
echo "===== LATE VCR RESIDUAL PHASE / HISTORICAL PRESTATE AUDIT ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "DB: $DB_ROOT/$GENERATION"
echo "frozen stress source: $SOURCE"
echo "SHA256: verified once in Python before read-only open"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_mass_late_residual_prestate_audit_v1.py \
  --corpus-db-root "$DB_ROOT" --frozen-stress "$SOURCE" \
  --output "$OUTPUT"
