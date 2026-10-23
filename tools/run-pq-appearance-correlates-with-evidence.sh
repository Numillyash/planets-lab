#!/usr/bin/env bash
# Same immutable six-game frozen public PPQ scope; new observational hypotheses.
# Publish only summary JSON and gate logs to runtime-logs via existing worktree wrapper.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ $# -eq 0 ]] || { echo "Usage: bash tools/run-pq-appearance-correlates-with-evidence.sh" >&2; exit 64; }
exec bash tools/run-with-runtime-evidence.sh \
  "pq-appearance-correlates-control12-p1-first48-max8" \
  --include "artifacts/pq/surveys/control12-ppq-p1-first48-max8.json" \
  -- bash tools/run-pq-control-multigame-gate.sh
