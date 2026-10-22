#!/usr/bin/env bash
# Execute one frozen-control PQ archive window inside the prebuilt lab image.
# No archive contents or private orders are printed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GAME_ID="${1:-620917}"
PLAYER_SLOT="${2:-1}"
ARCHIVE_TURN="${3:-1}"
for value in "$GAME_ID" "$PLAYER_SLOT" "$ARCHIVE_TURN"; do
  if [[ ! "$value" =~ ^[1-9][0-9]*$ ]]; then
    echo "ABSTAIN_PQ_PUBLIC_WINDOW: expected positive decimal game/slot/archive-turn" >&2
    exit 64
  fi
done

INDEX="validation/corpus/compiled/v1/metadata/game_features.parquet"
COHORT="validation/corpus/manifests/pq-public-control12-frozen-cohort.v1.json"
ARCHIVES="validation/corpus/cache/loadall"
RESULT="artifacts/pq/windows/game-${GAME_ID}-p${PLAYER_SLOT}-t${ARCHIVE_TURN}.json"

if [[ ! -f "$INDEX" || ! -f "$COHORT" || ! -f "$ARCHIVES/game-${GAME_ID}.zip" ]]; then
  echo "ABSTAIN_PQ_PUBLIC_WINDOW: local index/cohort/approved archive is unavailable" >&2
  exit 2
fi
mkdir -p "$(dirname "$RESULT")"
# A failed retry must not publish stale evidence from an earlier success.
rm -f -- "$RESULT"

docker compose run --rm lab \
  python -m tools.diagnostics.pq_window_field_sufficiency \
  --feature-index "$INDEX" \
  --frozen-cohort "$COHORT" \
  --archive-dir "$ARCHIVES" \
  --game-id "$GAME_ID" \
  --player-slot "$PLAYER_SLOT" \
  --turn-before "$ARCHIVE_TURN" \
  --output "$RESULT"

# The source CLI is privacy-minimal. This final line is solely metadata.
echo "pq_public_window_result: $RESULT"
