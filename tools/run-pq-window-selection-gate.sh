#!/usr/bin/env bash
# Scan only a bounded approved public archive perspective; never load all ZIPs.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
GAME_ID="${1:-620917}"
PLAYER_SLOT="${2:-1}"
FIRST_ARCHIVE_TURN="${3:-1}"
for val in "$GAME_ID" "$PLAYER_SLOT" "$FIRST_ARCHIVE_TURN"; do
  if [[ ! "$val" =~ ^[1-9][0-9]*$ ]]; then
    echo "ABSTAIN_PQ_WINDOW_SELECTION: invalid positive integer scope" >&2
    exit 64
  fi
done
[[ $# -le 3 ]] || { echo "Usage: bash tools/run-pq-window-selection-gate.sh [game [player [first_turn]]]" >&2; exit 64; }
RESULT="artifacts/pq/selection/game-${GAME_ID}-p${PLAYER_SLOT}-from${FIRST_ARCHIVE_TURN}.json"
INDEX="validation/corpus/compiled/v1/metadata/game_features.parquet"
COHORT="validation/corpus/manifests/pq-public-control12-frozen-cohort.v1.json"
ARCHIVE_DIR="validation/corpus/cache/loadall"
for required in "$INDEX" "$COHORT" "$ARCHIVE_DIR/game-${GAME_ID}.zip"; do
  [[ -f "$required" ]] || { echo "ABSTAIN_PQ_WINDOW_SELECTION: required frozen corpus input missing" >&2; exit 2; }
done
mkdir -p "$(dirname "$RESULT")"
rm -f -- "$RESULT"
docker compose run --rm lab \
  python -m tools.diagnostics.pq_bounded_window_selection \
  --feature-index "$INDEX" \
  --frozen-cohort "$COHORT" \
  --archive-dir "$ARCHIVE_DIR" \
  --game-id "$GAME_ID" \
  --player-slot "$PLAYER_SLOT" \
  --first-archive-turn "$FIRST_ARCHIVE_TURN" \
  --max-pairs 48 \
  --max-accepted 5 \
  --output "$RESULT"
