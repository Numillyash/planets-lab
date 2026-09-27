#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BASELINE_MANIFEST="${BASELINE_MANIFEST:-validation/corpus/manifests/accounts-recent-finished.jsonl}"
CANDIDATES_MANIFEST="${CANDIDATES_MANIFEST:-validation/corpus/manifests/public-validation-candidates.jsonl}"
SELECTED_MANIFEST="${SELECTED_MANIFEST:-validation/corpus/manifests/public-validation-selected.jsonl}"
COMBINED_MANIFEST="${COMBINED_MANIFEST:-validation/corpus/manifests/public-validation-combined.jsonl}"
REPORT="${REPORT:-artifacts/public-validation-corpus/selection-report.json}"
INDEX_OUTPUT="${INDEX_OUTPUT:-validation/corpus/index/public-validation-games.jsonl}"
STATS_OUTPUT="${STATS_OUTPUT:-validation/corpus/index/public-validation-stats.json}"
EVIDENCE_DIR="${EVIDENCE_DIR:-artifacts/public-validation-corpus/evidence}"

MIN_TURN="${MIN_TURN:-55}"
MIN_SLOTS="${MIN_SLOTS:-8}"
PROBE_LIMIT="${PROBE_LIMIT:-160}"
SELECT_COUNT="${SELECT_COUNT:-36}"
LIST_LIMIT="${LIST_LIMIT:-0}"
REQUEST_DELAY="${REQUEST_DELAY:-0.20}"
ARCHIVE_DELAY="${ARCHIVE_DELAY:-0.50}"

if [[ -n "${PLANETSNU_PROXY_URL:-}" ]]; then
  echo "network_mode: proxy"
  echo "proxy:        configured"
else
  export PLANETSNU_ALLOW_DIRECT=1
  echo "network_mode: direct"
  echo "proxy:        not configured"
fi

echo "===== PUBLIC VALIDATION CORPUS: DISCOVERY ====="
python -m planets_lab.corpus.public_finished_discover_cli \
  --baseline-manifest "$BASELINE_MANIFEST" \
  --min-turn "$MIN_TURN" \
  --min-slots "$MIN_SLOTS" \
  --probe-limit "$PROBE_LIMIT" \
  --select-count "$SELECT_COUNT" \
  --list-limit "$LIST_LIMIT" \
  --request-delay "$REQUEST_DELAY" \
  --candidates-output "$CANDIDATES_MANIFEST" \
  --selected-output "$SELECTED_MANIFEST" \
  --combined-output "$COMBINED_MANIFEST" \
  --report-output "$REPORT"

echo
echo "===== PUBLIC VALIDATION CORPUS: DOWNLOAD + INDEX ====="
python -m planets_lab.corpus.ingest_manifest_cli \
  "$SELECTED_MANIFEST" \
  --cache-dir validation/corpus/cache/loadall \
  --index-output "$INDEX_OUTPUT" \
  --stats-output "$STATS_OUTPUT" \
  --request-delay "$ARCHIVE_DELAY"

echo
echo "===== PUBLIC VALIDATION CORPUS: STAGE SAFE EVIDENCE ====="
rm -rf "$EVIDENCE_DIR"
mkdir -p "$EVIDENCE_DIR"
cp "$SELECTED_MANIFEST" "$EVIDENCE_DIR/public-validation-selected.jsonl"
cp "$COMBINED_MANIFEST" "$EVIDENCE_DIR/public-validation-combined.jsonl"
cp "$INDEX_OUTPUT" "$EVIDENCE_DIR/public-validation-games.jsonl"
cp "$STATS_OUTPUT" "$EVIDENCE_DIR/public-validation-stats.json"

echo
echo "===== PUBLIC VALIDATION CORPUS: COMPLETE ====="
echo "baseline_manifest: $BASELINE_MANIFEST"
echo "selected_manifest: $SELECTED_MANIFEST"
echo "combined_manifest: $COMBINED_MANIFEST"
echo "selection_report:  $REPORT"
echo "index_output:      $INDEX_OUTPUT"
echo "stats_output:      $STATS_OUTPUT"
echo "evidence_dir:      $EVIDENCE_DIR"
echo "archive_cache:     validation/corpus/cache/loadall"
