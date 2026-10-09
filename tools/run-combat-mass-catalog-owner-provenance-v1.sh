#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
: "${PLANETS_CORPUS_DB_ROOT:?Set immutable public100 corpus DB root}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
DB="$PLANETS_CORPUS_DB_ROOT/$GENERATION"
SOURCE="artifacts/combat/mass-rulebook-reconciliation-v2/published/report.json"
OUTPUT="artifacts/combat/mass-catalog-owner-provenance-v1/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB" ]] || { echo "ERROR: public100 DB missing: $DB" >&2; exit 66; }
SHA="$(sha256sum "$DB" | awk '{print $1}')"
[[ "$SHA" == "$EXPECTED_SHA" ]] || { echo "ERROR: public100 SHA mismatch: $SHA" >&2; exit 66; }
[[ -f "$SOURCE" ]] || { echo "ERROR: rulebook v2 report missing: $SOURCE" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: cached site-state Python missing: $PYTHON" >&2; exit 69; }
echo "===== MASS CATALOG AND OWNER PROVENANCE V1 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "public100: $GENERATION"
echo "sha256: $SHA"
echo "source: $SOURCE"
echo "output: $OUTPUT"
PYTHONUNBUFFERED=1 PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" "$PYTHON" \
  tools/diagnostics/combat_mass_catalog_owner_provenance_v1.py \
  --corpus-db-root "$PLANETS_CORPUS_DB_ROOT" \
  --corpus-db-generation "$GENERATION" \
  --rulebook-input "$SOURCE" \
  --output "$OUTPUT"
