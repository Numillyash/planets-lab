#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Prospective validation population for the post-independent capture-side
# candidate. Every public68 game is excluded by using the combined 68-game
# manifest as the immutable baseline.
export BASELINE_MANIFEST="${BASELINE_MANIFEST:-validation/corpus/manifests/public-short-expansion-with-public36.jsonl}"
export CANDIDATES_MANIFEST="${CANDIDATES_MANIFEST:-validation/corpus/manifests/public-postindependent-validation-candidates.jsonl}"
export SELECTED_MANIFEST="${SELECTED_MANIFEST:-validation/corpus/manifests/public-postindependent-validation-selected.jsonl}"
export COMBINED_MANIFEST="${COMBINED_MANIFEST:-validation/corpus/manifests/public-postindependent-validation-with-public68.jsonl}"
export REPORT="${REPORT:-artifacts/public-postindependent-validation/selection-report.json}"
export INDEX_OUTPUT="${INDEX_OUTPUT:-validation/corpus/index/public-postindependent-validation-games.jsonl}"
export STATS_OUTPUT="${STATS_OUTPUT:-validation/corpus/index/public-postindependent-validation-stats.json}"
export REJECTED_FILE="${REJECTED_FILE:-validation/corpus/manifests/public-postindependent-validation-rejected.json}"
export BACKFILL_REPORT="${BACKFILL_REPORT:-artifacts/public-postindependent-validation/backfill-report.json}"
export EVIDENCE_DIR="${EVIDENCE_DIR:-artifacts/public-postindependent-validation/evidence}"

# Predeclared acquisition profile. The range is shifted later than the first
# short32 corpus to increase combat density while retaining a bounded archive
# size. Selection still uses only public game metadata/loadinfo, never capture
# outcomes.
export MIN_TURN="${MIN_TURN:-80}"
export MAX_TURN="${MAX_TURN:-180}"
export MIN_SLOTS="${MIN_SLOTS:-8}"
export MAX_SLOTS="${MAX_SLOTS:-16}"
export PROBE_LIMIT="${PROBE_LIMIT:-320}"
export SELECT_COUNT="${SELECT_COUNT:-32}"
export LIST_LIMIT="${LIST_LIMIT:-0}"
export REQUEST_DELAY="${REQUEST_DELAY:-0.20}"
export ARCHIVE_DELAY="${ARCHIVE_DELAY:-0.50}"
export ARCHIVE_TIMEOUT="${ARCHIVE_TIMEOUT:-180}"
export ARCHIVE_RETRIES="${ARCHIVE_RETRIES:-2}"
export ARCHIVE_RETRY_DELAY="${ARCHIVE_RETRY_DELAY:-2}"
export REUSE_DISCOVERY="${REUSE_DISCOVERY:-1}"
export AUTO_BACKFILL="${AUTO_BACKFILL:-1}"
export MAX_BACKFILL_ROUNDS="${MAX_BACKFILL_ROUNDS:-24}"

FROZEN_CANDIDATE_COMMIT="${FROZEN_CANDIDATE_COMMIT:-46bcb08c2f0d3f0449b97921edb03ab6647f7d3b}"

if [[ ! -s "$BASELINE_MANIFEST" ]]; then
  echo "ERROR: public68 baseline manifest missing or empty: $BASELINE_MANIFEST" >&2
  exit 66
fi

baseline_count="$(awk 'NF {count++} END {print count+0}' "$BASELINE_MANIFEST")"
if [[ "$baseline_count" != "68" ]]; then
  echo "ERROR: prospective validation baseline must contain exactly 68 public games." >&2
  echo "baseline=$BASELINE_MANIFEST" >&2
  echo "count=$baseline_count" >&2
  exit 66
fi

printf '%s\n' '===== POST-INDEPENDENT PUBLIC VALIDATION ACQUISITION PROFILE ====='
printf 'frozen_candidate_commit: %s\n' "$FROZEN_CANDIDATE_COMMIT"
printf 'baseline_games:          %s\n' "$baseline_count"
printf 'turns:                   %s..%s\n' "$MIN_TURN" "$MAX_TURN"
printf 'slots:                   %s..%s\n' "$MIN_SLOTS" "$MAX_SLOTS"
printf 'probe_limit:             %s\n' "$PROBE_LIMIT"
printf 'select_count:            %s\n' "$SELECT_COUNT"
printf 'baseline:                %s\n' "$BASELINE_MANIFEST"
printf 'selected:                %s\n' "$SELECTED_MANIFEST"
printf 'index:                   %s\n' "$INDEX_OUTPUT"

exec bash tools/run-public-validation-corpus-acquisition.sh
