#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to external corpus DB root}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
DB="$PLANETS_CORPUS_DB_ROOT/$GENERATION"
OUTPUT="${OUTPUT:-artifacts/combat/mass-crossgame-controls-v1/public100-mass-controls.json}"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
EXTRA_GAMES="${PLANETS_MASS_CROSSGAME_EXTRA_GAMES:-20}"
MAX_VCRS="${PLANETS_MASS_CROSSGAME_MAX_VCRS_PER_TURN:-120}"

[[ -f "$DB" ]] || { echo "ERROR: missing public100 DB: $DB" >&2; exit 66; }
SHA="$(sha256sum "$DB" | awk '{print $1}')"
[[ "$SHA" == "$EXPECTED_SHA" ]] || { echo "ERROR: public100 SHA mismatch: $SHA" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: cached site-state Python missing: $PYTHON" >&2; exit 69; }
echo "===== CROSS-GAME COMBAT MASS CONTROLS V1 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "public100: $GENERATION"
echo "sha256: $SHA"
echo "extra_games: $EXTRA_GAMES"
echo "max_vcrs_per_turn: $MAX_VCRS"
echo "output: $OUTPUT"
mkdir -p "$(dirname "$OUTPUT")"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" "$PYTHON" \
  tools/diagnostics/combat_mass_crossgame_controls_v1.py \
  --corpus-db-root "$PLANETS_CORPUS_DB_ROOT" \
  --corpus-db-generation "$GENERATION" \
  --extra-games "$EXTRA_GAMES" \
  --max-vcrs-per-turn "$MAX_VCRS" \
  --output "$OUTPUT"
