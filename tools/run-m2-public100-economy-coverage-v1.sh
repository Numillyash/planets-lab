#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
BASELINE="${M2_CORPUS_BASELINE_MANIFEST:-validation/corpus/manifests/public-short-expansion-with-public36.jsonl}"
OUT="${M2_CORPUS_COVERAGE_OUTPUT:-artifacts/planetary/m2-public100-economy-coverage-v1/report.json}"
MAX_GAMES="${M2_CORPUS_MAX_GAMES:-100}"
PAIRS_PER_GAME="${M2_CORPUS_PAIRS_PER_GAME:-2}"
GEN="corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
DB="$DB_ROOT/generations/$GEN"

[[ -f "$DB" ]] || { echo "ERROR: explicit public100 DB is unavailable: $DB" >&2; exit 66; }
[[ -f "$BASELINE" ]] || { echo "ERROR: public68 baseline manifest unavailable: $BASELINE" >&2; exit 66; }
[[ ! -e "$OUT" ]] || { echo "ERROR: report already exists; refusing overwrite: $OUT" >&2; exit 73; }

CURRENT_BEFORE=""
if [[ -f "$DB_ROOT/CURRENT" ]]; then
    CURRENT_BEFORE="$(cat "$DB_ROOT/CURRENT")"
fi

# The existing lab service mounts published corpus at /corpus-db READ-ONLY.
# No writer container, changes to published generations, or CURRENT switch.
echo "===== M2 CORPUS METADATA CENSUS / BASELINE-ONLY ECONOMY COVERAGE ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "explicit_generation: $GEN"
echo "game_metadata_scope: ALL public100 games"
echo "entity_reconstruction_scope: public68 baseline only"
echo "max_games: $MAX_GAMES"
echo "pairs_per_game: $PAIRS_PER_GAME"
echo "CURRENT_before: $CURRENT_BEFORE"

docker compose -f compose.yaml -f compose.corpus-db.yaml run --rm -T lab \
    python tools/diagnostics/m2_public_corpus_economy_coverage_v1.py \
    --db-root /corpus-db \
    --baseline-manifest "$BASELINE" \
    --expected-baseline-games 68 \
    --max-games "$MAX_GAMES" \
    --pairs-per-game "$PAIRS_PER_GAME" \
    --output "$OUT"

CURRENT_AFTER=""
if [[ -f "$DB_ROOT/CURRENT" ]]; then
    CURRENT_AFTER="$(cat "$DB_ROOT/CURRENT")"
fi
if [[ "$CURRENT_BEFORE" != "$CURRENT_AFTER" ]]; then
    echo "ERROR: CURRENT changed during read-only run!" >&2
    exit 1
fi
[[ -s "$OUT" ]] || { echo "ERROR: aggregate report not published" >&2; exit 66; }
echo "CURRENT_unchanged: true"
echo "aggregate_report: $OUT"
echo "No NuHost causal attribution is claimed."
