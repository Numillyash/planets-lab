#!/usr/bin/env bash
# Strictly frozen six public PPQ games / player1 / 48 candidate pairs and
# at most 8 verified consecutive turns per game. Same-window ship pairing
# is non-independent and cannot establish a Host build.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ $# -eq 0 ]] || { echo "Usage: bash tools/run-pq-paired-specificity-with-evidence.sh" >&2; exit 64; }
exec bash tools/run-with-runtime-evidence.sh \
  "pq-paired-template-specificity-control12-p1-first48-max8" \
  --include "artifacts/pq/surveys/control12-ppq-p1-first48-max8.json" \
  -- bash tools/run-pq-control-multigame-gate.sh
