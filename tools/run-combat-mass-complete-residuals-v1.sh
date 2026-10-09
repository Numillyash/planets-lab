#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to immutable public100 root}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
DB="$PLANETS_CORPUS_DB_ROOT/$GENERATION"
SURVEY="artifacts/combat/long-mass-survey-v1/published/summary.json"
DIGEST="artifacts/combat/long-mass-survey-digest-v1/published/digest.json"
CHECKPOINTS="artifacts/combat/long-mass-survey-v1/checkpoints"
OUTPUT="artifacts/combat/mass-residual-complete-v1/published/residuals.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB" ]] || { echo "ERROR: public100 DB missing: $DB" >&2; exit 66; }
SHA="$(sha256sum "$DB" | awk '{print $1}')"
[[ "$SHA" == "$EXPECTED_SHA" ]] || { echo "ERROR: public100 SHA mismatch: $SHA" >&2; exit 66; }
[[ -f "$SURVEY" && -f "$DIGEST" && -d "$CHECKPOINTS" ]] || { echo "ERROR: frozen survey / digest / checkpoints missing" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: cached site-state runtime Python missing: $PYTHON" >&2; exit 69; }
echo "===== COMPLETE MASS RESIDUAL VCR AUDIT ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "public100: $GENERATION"
echo "sha256: $SHA"
echo "output: $OUTPUT"
mkdir -p "$(dirname "$OUTPUT")"
PYTHONUNBUFFERED=1 PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" "$PYTHON" \
 tools/diagnostics/combat_mass_complete_residuals_v1.py \
 --corpus-db-root "$PLANETS_CORPUS_DB_ROOT" \
 --corpus-db-generation "$GENERATION" \
 --survey-summary "$SURVEY" \
 --digest "$DIGEST" \
 --checkpoint-dir "$CHECKPOINTS" \
 --output "$OUTPUT"
