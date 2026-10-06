#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to the shared corpus DB root}"

PUBLIC100_REL="${PUBLIC100_REL:-generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb}"
PUBLIC100_SHA="${PUBLIC100_SHA:-3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c}"
OUTPUT="${OUTPUT:-artifacts/combat/capture-resume/game400330-t141-v593-immediate-continuation.json}"

db="$PLANETS_CORPUS_DB_ROOT/$PUBLIC100_REL"
if [[ ! -f "$db" ]]; then
  echo "ERROR: public100 generation missing: $db" >&2
  exit 66
fi
actual_sha="$(sha256sum "$db" | awk '{print $1}')"
if [[ "$actual_sha" != "$PUBLIC100_SHA" ]]; then
  echo "ERROR: public100 SHA mismatch" >&2
  echo "expected: $PUBLIC100_SHA" >&2
  echo "actual:   $actual_sha" >&2
  exit 66
fi

echo "===== CAPTURE RESUME GATE ====="
echo "HEAD:       $(git rev-parse HEAD)"
echo "public100:  $PUBLIC100_REL"
echo "sha256:     $actual_sha"

docker compose -f compose.yaml -f compose.corpus-db.yaml build lab

docker compose -f compose.yaml -f compose.corpus-db.yaml run --rm -T   -e PYTHONPATH=/workspace/src:/workspace/tools/diagnostics   lab   python tools/diagnostics/combat_capture_immediate_continuation_gate.py     --corpus-db-root /corpus-db     --corpus-db-generation "$PUBLIC100_REL"     --game-id 400330     --battle-turn 141     --x 1674     --y 2363     --capture-vcr-id 593     --output "$OUTPUT"

echo "output: $OUTPUT"
