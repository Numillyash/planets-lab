#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
: "${PLANETS_CORPUS_DB_ROOT:?Set external immutable public100 root}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
DB="$PLANETS_CORPUS_DB_ROOT/$GENERATION"
V2="artifacts/combat/mass-temporal-static-identity-v2/published/report.json"
DIGEST="artifacts/combat/long-mass-survey-digest-v1/published/digest.json"
OUTPUT="artifacts/combat/mass-capture-phase-controls-v1/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB" ]] || { echo "ERROR: public100 missing: $DB" >&2; exit 66; }
HASH="$(sha256sum "$DB" | awk '{print $1}')"
[[ "$HASH" == "$EXPECTED_SHA" ]] || { echo "ERROR: immutable corpus SHA mismatch: $HASH" >&2; exit 66; }
[[ -f "$V2" && -f "$DIGEST" ]] || { echo "ERROR: temporal V2 report / original digest missing" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state Python unavailable: $PYTHON" >&2; exit 69; }
echo "===== COMBAT MASS CAPTURE / TEMPORAL STATIC CONTROLS ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "public100: $GENERATION"
echo "sha256: $HASH"
echo "source_v2: $V2"
echo "original_digest: $DIGEST"
echo "output: $OUTPUT"
PYTHONUNBUFFERED=1 PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" "$PYTHON" \
  tools/diagnostics/combat_mass_capture_phase_controls_v1.py \
  --corpus-db-root "$PLANETS_CORPUS_DB_ROOT" \
  --corpus-db-generation "$GENERATION" \
  --v2-source "$V2" \
  --digest "$DIGEST" \
  --output "$OUTPUT"
