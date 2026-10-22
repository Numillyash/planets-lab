#!/usr/bin/env bash
# One-command corpus run + immutable sanitized push to runtime-logs.
# Requires existing git push permissions; never commits evidence to main.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GAME_ID="${1:-620917}"
PLAYER_SLOT="${2:-1}"
ARCHIVE_TURN="${3:-1}"
for value in "$GAME_ID" "$PLAYER_SLOT" "$ARCHIVE_TURN"; do
  if [[ ! "$value" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: expected positive decimal game/slot/archive-turn" >&2
    exit 64
  fi
done
if [[ $# -gt 3 ]]; then
  echo "Usage: bash tools/run-pq-public-window-with-evidence.sh [game_id [player_slot [archive_turn]]]" >&2
  exit 64
fi
RESULT="artifacts/pq/windows/game-${GAME_ID}-p${PLAYER_SLOT}-t${ARCHIVE_TURN}.json"
# Log+JSON publication is handled by the existing tested wrapper. It
# publishes even on a failed gate and returns its exit code to the operator.
exec bash tools/run-with-runtime-evidence.sh \
  "pq-public-window-g${GAME_ID}-p${PLAYER_SLOT}-t${ARCHIVE_TURN}" \
  --include "$RESULT" \
  -- bash tools/run-pq-public-window-gate.sh \
  "$GAME_ID" "$PLAYER_SLOT" "$ARCHIVE_TURN"
