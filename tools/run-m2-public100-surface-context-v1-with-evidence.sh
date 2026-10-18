#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="${M2_CORPUS_COVERAGE_OUTPUT:-artifacts/planetary/m2-public100-surface-residual-context-v1/report.json}"
case "$OUT" in
  artifacts/planetary/m2-public100-*/report.json) ;;
  *) echo "ERROR: only aggregate surface-context reports may publish" >&2; exit 64 ;;
esac
[[ "$OUT" != *".."* && "$OUT" != *"//"* ]] || {
  echo "ERROR: unsafe aggregate output path" >&2; exit 64;
}
SUMMARY="${OUT%/report.json}/triage.json"
MODE="${1:-}"
# A prior run may have completed the expensive corpus phase but failed
# before writing triage.json. An omitted --complete-existing must NEVER
# lead to a redundant 26.65 GiB run or a confusing overwrite error.
# Auto-recover only when the source report exists and triage does not.
if [[ ( "$MODE" == "--complete-existing" && $# -eq 1 ) || \
      ( $# -eq 0 && -s "$OUT" && ! -e "$SUMMARY" ) ]]; then
  if [[ $# -eq 0 ]]; then
    echo "M2 recovery auto-detected: existing report present, triage absent"
  fi
  [[ -s "$OUT" && ! -e "$SUMMARY" ]] || {
    echo "ERROR: existing report required, triage must not exist" >&2; exit 73;
  }
  # CRITICAL: runtime-evidence publishes even FAILED gate artifacts.
  # Validate BEFORE passing the report as --include, so secrets/raw
  # state can never be included if report provenance is invalid.
  python3 tools/diagnostics/m2_validate_corpus_aggregate_evidence_v1.py \
    --input "$OUT" >/dev/null || {
      echo "ERROR: aggregate provenance invalid; nothing published" >&2
      exit 65
    }
  RUN_NAME="m2-public100-surface-context-recovered-v1"
  INNER_ARGS=(--complete-existing)
elif [[ $# -eq 0 ]]; then
  [[ ! -e "$OUT" && ! -e "$SUMMARY" ]] || {
    echo "ERROR: existing artifact detected; refusing overwrite" >&2; exit 73;
  }
  RUN_NAME="m2-public100-surface-context-v1"
  INNER_ARGS=()
else
  echo "Usage: $0 [--complete-existing]" >&2
  exit 64
fi
export M2_CORPUS_COVERAGE_OUTPUT="$OUT"
# Publish gate log, source commit and TWO aggregate-only artifacts.
# Recovery reuses the existing report and runs ONLY pure stdlib triage.
exec bash tools/run-with-runtime-evidence.sh \
  "$RUN_NAME" \
  --include "$OUT" \
  --include "$SUMMARY" \
  -- bash tools/run-m2-public100-surface-context-v1.sh "${INNER_ARGS[@]}"
