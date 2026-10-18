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
[[ ! -e "$OUT" && ! -e "$SUMMARY" ]] || {
  echo "ERROR: existing artifact detected; refusing overwrite" >&2; exit 73;
}
export M2_CORPUS_COVERAGE_OUTPUT="$OUT"
# Existing evidence wrapper automatically publishes complete gate.log,
# source commit and TWO safe aggregate-only JSON artifacts, not raw TRNs.
exec bash tools/run-with-runtime-evidence.sh \
  m2-public100-surface-context-v1 \
  --include "$OUT" \
  --include "$SUMMARY" \
  -- bash tools/run-m2-public100-surface-context-v1.sh
