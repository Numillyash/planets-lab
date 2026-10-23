#!/usr/bin/env bash
# Frozen-control12 six PPQ games, player slot 1, 48 candidate / 8 admitted
# pairs per game. Compares already-present owned ships with prior base
# templates as a non-independent descriptive baseline, not Host proof.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ $# -eq 0 ]] || {
  echo "Usage: bash tools/run-pq-existing-ship-reference-with-evidence.sh" >&2
  exit 64
}
exec bash tools/run-with-runtime-evidence.sh \
  "pq-existing-ship-template-reference-control12-p1-first48-max8" \
  --include "artifacts/pq/surveys/control12-ppq-p1-first48-max8.json" \
  -- bash tools/run-pq-control-multigame-gate.sh
