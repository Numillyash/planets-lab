#!/usr/bin/env bash
# Automatically publish a sanitized bounded real-public-window selection run.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
GAME_ID="${1:-620917}"
PLAYER_SLOT="${2:-1}"
FIRST_ARCHIVE_TURN="${3:-1}"
[[ $# -le 3 ]] || { echo "Usage: bash tools/run-pq-window-selection-with-evidence.sh [game [player [first_turn]]]" >&2; exit 64; }
for val in "$GAME_ID" "$PLAYER_SLOT" "$FIRST_ARCHIVE_TURN"; do
  if [[ ! "$val" =~ ^[1-9][0-9]*$ ]]; then
    echo "ABSTAIN_PQ_WINDOW_SELECTION: invalid positive integer scope" >&2
    exit 64
  fi
done
RESULT="artifacts/pq/selection/game-${GAME_ID}-p${PLAYER_SLOT}-from${FIRST_ARCHIVE_TURN}.json"
exec bash tools/run-with-runtime-evidence.sh \
  "pq-window-selection-g${GAME_ID}-p${PLAYER_SLOT}-from${FIRST_ARCHIVE_TURN}" \
  --include "$RESULT" \
  -- bash tools/run-pq-window-selection-gate.sh \
  "$GAME_ID" "$PLAYER_SLOT" "$FIRST_ARCHIVE_TURN"
