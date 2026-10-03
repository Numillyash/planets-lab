#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Independent post-public36 corpus. Keep every path separate from the canonical
# public36 manifests/index so the old evidence population remains immutable.
export BASELINE_MANIFEST="${BASELINE_MANIFEST:-validation/corpus/manifests/public-validation-selected.jsonl}"
export CANDIDATES_MANIFEST="${CANDIDATES_MANIFEST:-validation/corpus/manifests/public-short-expansion-candidates.jsonl}"
export SELECTED_MANIFEST="${SELECTED_MANIFEST:-validation/corpus/manifests/public-short-expansion-selected.jsonl}"
export COMBINED_MANIFEST="${COMBINED_MANIFEST:-validation/corpus/manifests/public-short-expansion-with-public36.jsonl}"
export REPORT="${REPORT:-artifacts/public-short-expansion/selection-report.json}"
export INDEX_OUTPUT="${INDEX_OUTPUT:-validation/corpus/index/public-short-expansion-games.jsonl}"
export STATS_OUTPUT="${STATS_OUTPUT:-validation/corpus/index/public-short-expansion-stats.json}"
export REJECTED_FILE="${REJECTED_FILE:-validation/corpus/manifests/public-short-expansion-rejected.json}"
export BACKFILL_REPORT="${BACKFILL_REPORT:-artifacts/public-short-expansion/backfill-report.json}"
export EVIDENCE_DIR="${EVIDENCE_DIR:-artifacts/public-short-expansion/evidence}"

# Deliberately bounded size profile. The old public36 contained very long games;
# this population is intended to provide new independent evidence without
# another 300+ turn outlier.
export MIN_TURN="${MIN_TURN:-55}"
export MAX_TURN="${MAX_TURN:-140}"
export MIN_SLOTS="${MIN_SLOTS:-8}"
export MAX_SLOTS="${MAX_SLOTS:-16}"
export PROBE_LIMIT="${PROBE_LIMIT:-240}"
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

printf '%s\n' '===== PUBLIC SHORT EXPANSION PROFILE ====='
printf 'turns:        %s..%s\n' "$MIN_TURN" "$MAX_TURN"
printf 'slots:        %s..%s\n' "$MIN_SLOTS" "$MAX_SLOTS"
printf 'probe_limit:  %s\n' "$PROBE_LIMIT"
printf 'select_count: %s\n' "$SELECT_COUNT"
printf 'baseline:     %s\n' "$BASELINE_MANIFEST"
printf 'selected:     %s\n' "$SELECTED_MANIFEST"
printf 'index:        %s\n' "$INDEX_OUTPUT"

exec bash tools/run-public-validation-corpus-acquisition.sh
