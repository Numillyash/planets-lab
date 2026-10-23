#!/usr/bin/env bash
# One command: bounded frozen-control PPQ survey and immutable GitHub evidence.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ $# -eq 0 ]] || { echo "Usage: bash tools/run-pq-control-multigame-with-evidence.sh" >&2; exit 64; }
exec bash tools/run-with-runtime-evidence.sh \
  "pq-control12-ppq-multigame-p1-first48-max8" \
  --include "artifacts/pq/surveys/control12-ppq-p1-first48-max8.json" \
  -- bash tools/run-pq-control-multigame-gate.sh
