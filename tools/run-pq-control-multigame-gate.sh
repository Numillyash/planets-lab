#!/usr/bin/env bash
# Exactly the existing public frozen control12 PPQ mode, perspective slot 1.
# Scoped 6-game survey, not public100 or any sealed M2 holdout.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

INDEX="validation/corpus/compiled/v1/metadata/game_features.parquet"
COHORT="validation/corpus/manifests/pq-public-control12-frozen-cohort.v1.json"
ARCHIVE_DIR="validation/corpus/cache/loadall"
OUTPUT="artifacts/pq/surveys/control12-ppq-p1-first48-max8.json"
for item in "$INDEX" "$COHORT"; do
  [[ -f "$item" ]] || { echo "ABSTAIN_PQ_SURVEY: frozen feature index/cohort missing" >&2; exit 2; }
done
mkdir -p "$(dirname "$OUTPUT")"
rm -f -- "$OUTPUT"
docker compose run --rm lab \
  python -m tools.diagnostics.pq_control_multigame_observation \
  --feature-index "$INDEX" \
  --frozen-cohort "$COHORT" \
  --archive-dir "$ARCHIVE_DIR" \
  --perspective 1 \
  --first-archive-turn 1 \
  --max-pairs-per-game 48 \
  --max-accepted-per-game 8 \
  --output "$OUTPUT"
