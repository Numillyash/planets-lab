#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to the explicit public DB root}"

PUBLIC100_REL="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
PUBLIC100_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
DB="$PLANETS_CORPUS_DB_ROOT/$PUBLIC100_REL"
OUTPUT="${OUTPUT:-artifacts/combat/site-payload-provenance/game400330-t141-v592-595.json}"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"

if [[ ! -f "$DB" ]]; then
  echo "ERROR: public100 DB not found: $DB" >&2
  exit 66
fi
actual_sha="$(sha256sum "$DB" | awk '{print $1}')"
if [[ "$actual_sha" != "$PUBLIC100_SHA" ]]; then
  echo "ERROR: public100 SHA mismatch: $actual_sha" >&2
  exit 66
fi
if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: cached site-state Python missing: $PYTHON" >&2
  echo "Run the validated terminal-replay gate to prepare its runtime first." >&2
  exit 69
fi

echo "===== SITE COMBAT PAYLOAD PROVENANCE V1 ====="
echo "HEAD:      $(git rev-parse HEAD)"
echo "public100: $PUBLIC100_REL"
echo "sha256:    $actual_sha"
echo "runtime:   $PYTHON"
echo "output:    $OUTPUT"

mkdir -p "$(dirname "$OUTPUT")"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" "$PYTHON" \
  tools/diagnostics/combat_site_payload_provenance_v1.py \
  --corpus-db-root "$PLANETS_CORPUS_DB_ROOT" \
  --corpus-db-generation "$PUBLIC100_REL" \
  --game-id 400330 \
  --battle-turn 141 \
  --x 1674 --y 2363 \
  --start-vcr-id 592 --end-vcr-id 595 \
  --output "$OUTPUT"
