#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
: "${PLANETS_CORPUS_DB_ROOT:?Set shared corpus DB root}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
DB="$PLANETS_CORPUS_DB_ROOT/$GENERATION"
EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
OUTPUT="${OUTPUT:-artifacts/combat/site-seed-continuity/game400330-t141.json}"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB" ]] || { echo "ERROR: DB missing: $DB" >&2; exit 66; }
ACTUAL_SHA="$(sha256sum "$DB" | awk '{print $1}')"
[[ "$ACTUAL_SHA" == "$EXPECTED_SHA" ]] || { echo "ERROR: DB SHA mismatch: $ACTUAL_SHA" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: cached Python missing: $PYTHON" >&2; exit 69; }
echo "===== CLASSIC SEED CONTINUITY AUDIT V1 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "public100: $GENERATION"
echo "sha256: $ACTUAL_SHA"
echo "runtime: $PYTHON"
echo "output: $OUTPUT"
mkdir -p "$(dirname "$OUTPUT")"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" "$PYTHON" \
  tools/diagnostics/combat_site_seed_continuity_v1.py \
  --corpus-db-root "$PLANETS_CORPUS_DB_ROOT" \
  --corpus-db-generation "$GENERATION" \
  --game-id 400330 \
  --battle-turn 141 \
  --output "$OUTPUT"
