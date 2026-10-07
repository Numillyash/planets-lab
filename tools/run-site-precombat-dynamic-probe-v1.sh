#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to the shared corpus DB root}"

PUBLIC100_REL="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
PUBLIC100_SHA="3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
DB="$PLANETS_CORPUS_DB_ROOT/$PUBLIC100_REL"
OUTPUT="${OUTPUT:-artifacts/combat/site-precombat-dynamic-probe/game400330-t141-v592.json}"
RUNTIME_MODE="${PLANETS_SITE_PRECOMBAT_PROBE_RUNTIME_MODE:-local}"

if [[ ! -f "$DB" ]]; then
  echo "ERROR: public100 DB missing: $DB" >&2
  exit 66
fi
actual_sha="$(sha256sum "$DB" | awk '{print $1}')"
if [[ "$actual_sha" != "$PUBLIC100_SHA" ]]; then
  echo "ERROR: public100 SHA mismatch: $actual_sha" >&2
  exit 66
fi

mkdir -p "$(dirname "$OUTPUT")"

echo "===== SITE PRECOMBAT DYNAMIC PROBE V1 ====="
echo "HEAD:      $(git rev-parse HEAD)"
echo "public100: $PUBLIC100_REL"
echo "sha256:    $actual_sha"
echo "runtime:   $RUNTIME_MODE"
echo "output:    $OUTPUT"
echo

# Reuse the already-hardened local Python bootstrap/venv by asking the canonical
# site-state runner to expose its cached runtime only when needed. The cached
# venv is the normal path after the first successful bootstrap.
RUNTIME_VENV="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}"
PYTHON="$RUNTIME_VENV/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: site-state runtime venv missing: $PYTHON" >&2
  echo "Run tools/run-site-combat-terminal-replay-v1-with-evidence.sh once to bootstrap it." >&2
  exit 69
fi

"$PYTHON" tools/diagnostics/combat_site_precombat_dynamic_probe.py \
  --corpus-db-root "$PLANETS_CORPUS_DB_ROOT" \
  --corpus-db-generation "$PUBLIC100_REL" \
  --game-id 400330 \
  --battle-turn 141 \
  --x 1674 \
  --y 2363 \
  --vcr-id 592 \
  --output "$OUTPUT"
