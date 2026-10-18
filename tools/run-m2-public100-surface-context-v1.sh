#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="${M2_CORPUS_COVERAGE_OUTPUT:-artifacts/planetary/m2-public100-surface-residual-context-v1/report.json}"
case "$OUT" in
  artifacts/planetary/m2-public100-*/report.json) ;;
  *) echo "ERROR: invalid aggregate-only report path" >&2; exit 64 ;;
esac
[[ "$OUT" != *".."* && "$OUT" != *"//"* ]] || {
  echo "ERROR: unsafe report path" >&2; exit 64;
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
  # The expensive corpus stage already succeeded. Reuse its existing
  # immutable aggregate without touching DuckDB or rehashing 26.65 GiB.
  [[ -s "$OUT" && ! -e "$SUMMARY" ]] || {
    echo "ERROR: expected existing report and missing triage; no overwrite" >&2; exit 73;
  }
elif [[ $# -eq 0 ]]; then
  [[ ! -e "$OUT" && ! -e "$SUMMARY" ]] || {
    echo "ERROR: report or derived triage already exists; refusing overwrite" >&2; exit 73;
  }
  export M2_CORPUS_COVERAGE_OUTPUT="$OUT"
  # Immutable corpus hashed/read only by existing runner, same sample.
  bash tools/run-m2-public100-economy-coverage-v1.sh
else
  echo "Usage: $0 [--complete-existing]" >&2
  exit 64
fi

# Validate aggregate-only provenance before deriving any further output.
python3 tools/diagnostics/m2_validate_corpus_aggregate_evidence_v1.py \
  --input "$OUT"
# This command is stdlib-only, including its imports; no DuckDB needed.
python3 tools/diagnostics/m2_surface_context_triage_v1.py \
  --input "$OUT" --output "$SUMMARY"
