#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to immutable corpus DB root}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
DB="$PLANETS_CORPUS_DB_ROOT/$GENERATION"
OUTPUT="${OUTPUT:-artifacts/combat/multigame-conditional-ensemble/public100-pilot-v1.json}"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
MAX_GAMES="${PLANETS_COMBAT_ENSEMBLE_GAMES:-5}"
CASES_PER_GAME="${PLANETS_COMBAT_ENSEMBLE_CASES_PER_GAME:-2}"
MAX_CANDIDATE_GAMES="${PLANETS_COMBAT_ENSEMBLE_SCAN_GAMES:-24}"

[[ -f "$DB" ]] || { echo "ERROR: public100 DB missing: $DB" >&2; exit 66; }
SHA="$(sha256sum "$DB" | awk '{print $1}')"
[[ "$SHA" == "$EXPECTED_SHA" ]] || { echo "ERROR: public100 SHA mismatch: $SHA" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: cached site-state Python missing: $PYTHON" >&2; exit 69; }
echo "===== MULTIGAME CONDITIONAL CLASSIC PILOT V1 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "public100: $GENERATION"
echo "sha256: $SHA"
echo "runtime: $PYTHON"
echo "games: $MAX_GAMES"
echo "cases_per_game: $CASES_PER_GAME"
echo "candidate_game_scan_limit: $MAX_CANDIDATE_GAMES"
echo "output: $OUTPUT"
mkdir -p "$(dirname "$OUTPUT")"

PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" "$PYTHON" \
  tools/diagnostics/combat_multigame_conditional_ensemble_v1.py \
  --corpus-db-root "$PLANETS_CORPUS_DB_ROOT" \
  --corpus-db-generation "$GENERATION" \
  --max-games "$MAX_GAMES" \
  --cases-per-game "$CASES_PER_GAME" \
  --max-candidate-games "$MAX_CANDIDATE_GAMES" \
  --output "$OUTPUT"
