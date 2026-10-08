#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to external public100 DB root}"

GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
DB="$PLANETS_CORPUS_DB_ROOT/$GENERATION"
OUTPUT="${OUTPUT:-artifacts/combat/multigame-conditional-coverage-v2/public100-coverage-v2.json}"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"

MAX_GAMES="${PLANETS_COMBAT_COVERAGE_V2_GAMES:-10}"
CASES_PER_GAME="${PLANETS_COMBAT_COVERAGE_V2_CASES_PER_GAME:-2}"
MAX_CANDIDATE_GAMES="${PLANETS_COMBAT_COVERAGE_V2_SCAN_GAMES:-35}"
TURNS_PER_GAME="${PLANETS_COMBAT_COVERAGE_V2_TURNS_PER_GAME:-4}"

[[ -f "$DB" ]] || { echo "ERROR: explicit public100 DB not found: $DB" >&2; exit 66; }
SHA="$(sha256sum "$DB" | awk '{print $1}')"
[[ "$SHA" == "$EXPECTED_SHA" ]] || { echo "ERROR: public100 SHA mismatch: $SHA" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: cached site-state Python missing: $PYTHON" >&2; exit 69; }

echo "===== MULTIGAME CONDITIONAL COMBAT COVERAGE V2 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "public100: $GENERATION"
echo "sha256: $SHA"
echo "runtime: $PYTHON"
echo "games: $MAX_GAMES"
echo "cases_per_game: $CASES_PER_GAME"
echo "max_candidate_games: $MAX_CANDIDATE_GAMES"
echo "turns_per_game: $TURNS_PER_GAME"
echo "output: $OUTPUT"
mkdir -p "$(dirname "$OUTPUT")"

PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" "$PYTHON" \
  tools/diagnostics/combat_multigame_conditional_coverage_v2.py \
  --corpus-db-root "$PLANETS_CORPUS_DB_ROOT" \
  --corpus-db-generation "$GENERATION" \
  --max-games "$MAX_GAMES" \
  --cases-per-game "$CASES_PER_GAME" \
  --max-candidate-games "$MAX_CANDIDATE_GAMES" \
  --turns-per-game "$TURNS_PER_GAME" \
  --output "$OUTPUT"
