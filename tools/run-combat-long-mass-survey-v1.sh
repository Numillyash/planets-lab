#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to immutable public100 root}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
EXPECTED_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
DB="$PLANETS_CORPUS_DB_ROOT/$GENERATION"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
HEAD="$(git rev-parse HEAD)"
GAMES="${PLANETS_LONG_MASS_GAMES:-80}"
TURNS="${PLANETS_LONG_MASS_TURNS_PER_GAME:-4}"
VCR_LIMIT="${PLANETS_LONG_MASS_MAX_VCRS_PER_TURN:-150}"
EXAMPLES="${PLANETS_LONG_MASS_EXAMPLES_PER_TURN:-20}"
CHECKPOINT_DIR="${PLANETS_LONG_MASS_CHECKPOINT_DIR:-artifacts/combat/long-mass-survey-v1/checkpoints}"
PUBLISHED_SUMMARY="${PLANETS_LONG_MASS_PUBLISHED_SUMMARY:-artifacts/combat/long-mass-survey-v1/published/summary.json}"
[[ -f "$DB" ]] || { echo "ERROR: public100 DB missing: $DB" >&2; exit 66; }
SHA="$(sha256sum "$DB" | awk '{print $1}')"
[[ "$SHA" == "$EXPECTED_SHA" ]] || { echo "ERROR: public100 SHA mismatch: $SHA" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state Python not available: $PYTHON" >&2; exit 69; }
echo "===== LONG PUBLIC100 COMBAT MASS SURVEY ====="
echo "HEAD: $HEAD"
echo "public100: $GENERATION"
echo "sha256: $SHA"
echo "max_games: $GAMES"
echo "turns_per_game: $TURNS"
echo "max_vcrs_per_turn: $VCR_LIMIT"
echo "local_resume: $CHECKPOINT_DIR"
echo "published_summary: $PUBLISHED_SUMMARY"
PYTHONUNBUFFERED=1 PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" "$PYTHON" \
  tools/diagnostics/combat_long_mass_survey_v1.py \
  --corpus-db-root "$PLANETS_CORPUS_DB_ROOT" \
  --corpus-db-generation "$GENERATION" \
  --source-sha "$HEAD" \
  --max-games "$GAMES" \
  --turns-per-game "$TURNS" \
  --max-vcrs-per-turn "$VCR_LIMIT" \
  --max-examples-per-turn "$EXAMPLES" \
  --checkpoint-dir "$CHECKPOINT_DIR" \
  --published-summary "$PUBLISHED_SUMMARY"
