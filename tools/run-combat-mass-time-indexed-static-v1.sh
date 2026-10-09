#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
DB_ROOT="$HOME/projects/planets-corpus-db"
if [[ -n "${PLANETS_CORPUS_DB_ROOT:-}" ]]; then DB_ROOT="$PLANETS_CORPUS_DB_ROOT"; fi
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
DB="$DB_ROOT/$GENERATION"
CAPTURE="artifacts/combat/mass-capture-phase-controls-v1/published/report.json"
RECON="artifacts/combat/mass-temporal-reconciliation-v1/published/report.json"
OUTPUT="artifacts/combat/mass-time-indexed-static-v1/published/report.json"
PYTHON="$HOME/.cache/planets-lab/site-state-v1/bin/python"
[[ -f "$DB" && -f "$CAPTURE" && -f "$RECON" ]] || {
  echo "ERROR: immutable DB or V1 prerequisite report missing" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: runtime Python missing: $PYTHON" >&2; exit 69; }
ACTUAL_SHA="$(sha256sum "$DB" | cut -d ' ' -f 1)"
[[ "$ACTUAL_SHA" == "$EXPECTED_SHA" ]] || {
  echo "ERROR: pinned public100 SHA256 mismatch" >&2; exit 66;
}
echo "===== EXPERIMENTAL PRE-VCR T-1 STATIC FORECAST ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "DB: $DB"
echo "sha256: $ACTUAL_SHA"
PYTHONPATH="$ROOT/src" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_mass_time_indexed_static_v1.py \
  --corpus-db-root "$DB_ROOT" --capture-controls "$CAPTURE" \
  --reconciliation "$RECON" --output "$OUTPUT"
