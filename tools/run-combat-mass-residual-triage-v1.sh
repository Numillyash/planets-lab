#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to explicit DB root}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
SHA_EXPECTED="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
DB="$PLANETS_CORPUS_DB_ROOT/$GENERATION"
OUTPUT="${OUTPUT:-artifacts/combat/mass-residual-triage-v1/public100-two-residuals.json}"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB" ]] || { echo "ERROR: public100 DB not found: $DB" >&2; exit 66; }
SHA="$(sha256sum "$DB" | awk '{print $1}')"
[[ "$SHA" == "$SHA_EXPECTED" ]] || { echo "ERROR: explicit generation SHA mismatch: $SHA" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state Python missing: $PYTHON" >&2; exit 69; }
echo "===== COMBAT MASS RESIDUAL TRIAGE V1 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "public100: $GENERATION"
echo "sha256: $SHA"
echo "output: $OUTPUT"
mkdir -p "$(dirname "$OUTPUT")"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" "$PYTHON" \
  tools/diagnostics/combat_mass_residual_triage_v1.py \
  --corpus-db-root "$PLANETS_CORPUS_DB_ROOT" \
  --corpus-db-generation "$GENERATION" \
  --output "$OUTPUT"
