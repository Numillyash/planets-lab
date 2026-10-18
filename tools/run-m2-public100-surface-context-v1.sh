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
[[ ! -e "$OUT" && ! -e "$SUMMARY" ]] || {
  echo "ERROR: report or derived triage already exists; refusing overwrite" >&2; exit 73;
}
export M2_CORPUS_COVERAGE_OUTPUT="$OUT"

# Immutable corpus hashed/read only by the EXISTING runner, same
# frozen baseline68 pair sample. One pass, not two separate DB runs.
bash tools/run-m2-public100-economy-coverage-v1.sh

# The source report is finished. Validate known aggregate-only schema
# and provenance BEFORE generating any derivative/publication.
python3 tools/diagnostics/m2_validate_corpus_aggregate_evidence_v1.py \
  --input "$OUT"
python3 tools/diagnostics/m2_surface_context_triage_v1.py \
  --input "$OUT" --output "$SUMMARY"
