#!/usr/bin/env bash
# Exploratory-only six-game PPQ ship-identity candidate source-field audit.
# The unchanged bounded corpus gate provides a deterministic frozen scope;
# this new entrypoint assigns an independent immutable evidence run name.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ $# -eq 0 ]] || {
  echo "Usage: bash tools/run-pq-ship-candidate-fields-with-evidence.sh" >&2
  exit 64
}
OUTPUT="artifacts/pq/surveys/control12-ppq-p1-first48-max8.json"
exec bash tools/run-with-runtime-evidence.sh \
  "pq-ship-candidate-fields-control12-p1-first48-max8" \
  --include "$OUTPUT" \
  -- bash tools/run-pq-control-multigame-gate.sh
