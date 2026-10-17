#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OUT="${M2_CORPUS_COVERAGE_OUTPUT:-artifacts/planetary/m2-public100-economy-coverage-v1/report.json}"
export M2_CORPUS_COVERAGE_OUTPUT="$OUT"

# The evidence wrapper copies --include files into runtime-logs, which
# can be a public branch. Only let it include aggregate M2 reports.
case "$OUT" in
  artifacts/planetary/m2-public100-*/report.json) ;;
  *)
    echo "ERROR: only artifacts/planetary/m2-public100-*/report.json may be published" >&2
    exit 64
    ;;
esac
if [[ "$OUT" == *".."* || "$OUT" == *"//"* ]]; then
  echo "ERROR: unsafe aggregate output path" >&2
  exit 64
fi

if [[ "${1:-}" == "--publish-existing" && $# -eq 1 ]]; then
  [[ -s "$OUT" ]] || {
    echo "ERROR: no existing aggregate report to publish: $OUT" >&2
    exit 66
  }
  # The first gate is before the evidence publisher: failed validation
  # never includes a potentially sensitive/malformed JSON report.
  # This does NOT rehash or reopen the 26.65-GiB corpus.
  python3 tools/diagnostics/m2_validate_corpus_aggregate_evidence_v1.py \
    --input "$OUT" >/dev/null || {
      echo "ERROR: aggregate-only report validation failed; no publication" >&2
      exit 65
    }
  exec bash tools/run-with-runtime-evidence.sh \
    m2-public100-coverage-existing-v1 \
    --include "$OUT" \
    -- python3 tools/diagnostics/m2_validate_corpus_aggregate_evidence_v1.py \
      --input "$OUT"
fi
if [[ $# -ne 0 ]]; then
  echo "Usage: $0 [--publish-existing]" >&2
  exit 64
fi
[[ ! -e "$OUT" ]] || {
  echo "ERROR: report already exists: $OUT; use --publish-existing instead" >&2
  exit 73
}
# Existing explicit-generation runner does SHA256, read-only metadata
# census and baseline68 entity sampling. Its aggregate JSON + complete
# combined stdout/stderr are published after the command completes.
exec bash tools/run-with-runtime-evidence.sh \
  m2-public100-economy-coverage-v1 \
  --include "$OUT" \
  -- bash tools/run-m2-public100-economy-coverage-v1.sh
