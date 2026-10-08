#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "${PLANETS_CORPUS_DB_ROOT:?Set corpus database root}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
DB="$PLANETS_CORPUS_DB_ROOT/$GENERATION"
INPUT="${PLANETS_MASS_SIGNATURE_INPUT:-artifacts/combat/mass-crossgame-controls-v1/public100-mass-controls.json}"
OUTPUT="${OUTPUT:-artifacts/combat/mass-composition-signatures-v2/public100-signatures-v2.json}"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB" ]] || { echo "ERROR: public100 DB missing: $DB" >&2; exit 66; }
SHA="$(sha256sum "$DB" | awk '{print $1}')"
[[ "$SHA" == "$EXPECTED_SHA" ]] || { echo "ERROR: public100 SHA mismatch: $SHA" >&2; exit 66; }
[[ -f "$INPUT" ]] || { echo "ERROR: previous v1 mass-control artifact missing: $INPUT" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: cached site-state Python missing: $PYTHON" >&2; exit 69; }
echo "===== COMBAT MASS COMPOSITION SIGNATURES V2 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "source: $INPUT"
echo "public100: $GENERATION"
echo "sha256: $SHA"
echo "output: $OUTPUT"
mkdir -p "$(dirname "$OUTPUT")"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" "$PYTHON" \
  tools/diagnostics/combat_mass_composition_signatures_v2.py \
  --input "$INPUT" \
  --output "$OUTPUT"
