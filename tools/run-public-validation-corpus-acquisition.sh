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
REJECTED_FILE="${REJECTED_FILE:-validation/corpus/manifests/public-validation-rejected.json}"
BACKFILL_REPORT="${BACKFILL_REPORT:-artifacts/public-validation-corpus/backfill-report.json}"
EVIDENCE_DIR="${EVIDENCE_DIR:-artifacts/public-validation-corpus/evidence}"

MIN_TURN="${MIN_TURN:-55}"
MIN_SLOTS="${MIN_SLOTS:-8}"
PROBE_LIMIT="${PROBE_LIMIT:-160}"
SELECT_COUNT="${SELECT_COUNT:-36}"
LIST_LIMIT="${LIST_LIMIT:-0}"
REQUEST_DELAY="${REQUEST_DELAY:-0.20}"
ARCHIVE_DELAY="${ARCHIVE_DELAY:-0.50}"
ARCHIVE_TIMEOUT="${ARCHIVE_TIMEOUT:-180}"
ARCHIVE_RETRIES="${ARCHIVE_RETRIES:-2}"
ARCHIVE_RETRY_DELAY="${ARCHIVE_RETRY_DELAY:-2}"
REUSE_DISCOVERY="${REUSE_DISCOVERY:-1}"
AUTO_BACKFILL="${AUTO_BACKFILL:-1}"

DOCKER_PREFLIGHT_TIMEOUT="${DOCKER_PREFLIGHT_TIMEOUT:-10}"

echo "===== PUBLIC VALIDATION CORPUS: PREFLIGHT ====="
if ! timeout "${DOCKER_PREFLIGHT_TIMEOUT}s" docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon/backend is not responding within ${DOCKER_PREFLIGHT_TIMEOUT}s." >&2
  exit 69
fi
echo "docker:       ready"

echo "===== PUBLIC VALIDATION CORPUS: BUILD LAB IMAGE ====="
docker compose build lab

lab=(
  docker compose run --rm -T
  -e PYTHONPATH=/workspace/src
)

if [[ -n "${PLANETSNU_PROXY_URL:-}" ]]; then
  lab+=(-e "PLANETSNU_PROXY_URL=${PLANETSNU_PROXY_URL}")
  echo "network_mode: proxy"
  echo "proxy:        configured"
else
  lab+=(-e PLANETSNU_ALLOW_DIRECT=1)
  echo "network_mode: direct"
  echo "proxy:        not configured"
fi

lab+=(lab)
echo "===== PUBLIC VALIDATION CORPUS: DISCOVERY ====="
if [[ "$REUSE_DISCOVERY" == "1" \
   && -s "$CANDIDATES_MANIFEST" \
   && -s "$SELECTED_MANIFEST" \
   && -s "$COMBINED_MANIFEST" \
   && -s "$REPORT" ]]; then
  echo "discovery:    reuse existing manifests/report"
else
  "${lab[@]}" python -m planets_lab.corpus.public_finished_discover_cli \
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
fi

if [[ "$AUTO_BACKFILL" == "1" \
   && -s "$CANDIDATES_MANIFEST" \
   && -s "$SELECTED_MANIFEST" \
   && -s "$STATS_OUTPUT" \
   && -s "$REPORT" ]]; then
  echo
  echo "===== PUBLIC VALIDATION CORPUS: BACKFILL PREVIOUS FAILURES ====="
  "${lab[@]}" python -m planets_lab.corpus.public_validation_backfill_cli \
    --baseline-manifest "$BASELINE_MANIFEST" \
    --candidates-manifest "$CANDIDATES_MANIFEST" \
    --selected-manifest "$SELECTED_MANIFEST" \
    --stats "$STATS_OUTPUT" \
    --selection-report "$REPORT" \
    --rejected "$REJECTED_FILE" \
    --combined-output "$COMBINED_MANIFEST" \
    --report-output "$BACKFILL_REPORT"
fi

echo
echo "===== PUBLIC VALIDATION CORPUS: DOWNLOAD + INDEX ====="
set +e
"${lab[@]}" python -m planets_lab.corpus.ingest_manifest_cli \
  "$SELECTED_MANIFEST" \
  --cache-dir validation/corpus/cache/loadall \
  --index-output "$INDEX_OUTPUT" \
  --stats-output "$STATS_OUTPUT" \
  --request-delay "$ARCHIVE_DELAY" \
  --network-timeout "$ARCHIVE_TIMEOUT" \
  --download-retries "$ARCHIVE_RETRIES" \
  --retry-delay "$ARCHIVE_RETRY_DELAY"
INGEST_RC=$?
set -e

echo
echo "===== PUBLIC VALIDATION CORPUS: STAGE SAFE EVIDENCE ====="
rm -rf "$EVIDENCE_DIR"
mkdir -p "$EVIDENCE_DIR"
cp "$SELECTED_MANIFEST" "$EVIDENCE_DIR/public-validation-selected.jsonl"
cp "$COMBINED_MANIFEST" "$EVIDENCE_DIR/public-validation-combined.jsonl"
cp "$INDEX_OUTPUT" "$EVIDENCE_DIR/public-validation-games.jsonl"
cp "$STATS_OUTPUT" "$EVIDENCE_DIR/public-validation-stats.json"
if [[ -s "$REJECTED_FILE" ]]; then
  cp "$REJECTED_FILE" "$EVIDENCE_DIR/public-validation-rejected.json"
fi
if [[ -s "$BACKFILL_REPORT" ]]; then
  cp "$BACKFILL_REPORT" "$EVIDENCE_DIR/public-validation-backfill-report.json"
fi

echo
echo "===== PUBLIC VALIDATION CORPUS: COMPLETE ====="
echo "baseline_manifest: $BASELINE_MANIFEST"
echo "selected_manifest: $SELECTED_MANIFEST"
echo "combined_manifest: $COMBINED_MANIFEST"
echo "selection_report:  $REPORT"
echo "index_output:      $INDEX_OUTPUT"
echo "stats_output:      $STATS_OUTPUT"
echo "rejected_file:     $REJECTED_FILE"
echo "backfill_report:   $BACKFILL_REPORT"
echo "evidence_dir:      $EVIDENCE_DIR"
echo "archive_cache:     validation/corpus/cache/loadall"
echo "ingest_rc:         $INGEST_RC"

exit "$INGEST_RC"
