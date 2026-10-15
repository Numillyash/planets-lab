#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
V10="artifacts/combat/c5-posthost-residual-coupling-v10/published/report.json"
OUTPUT="artifacts/combat/c5-chunnel-endpoint-screen-v11/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$V10" ]] || {
  echo "ERROR: frozen public100 DB or published V10 report missing" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || {
  echo "ERROR: research Python unavailable" >&2; exit 69;
}
echo "===== C5 V10 RESIDUAL CHUNNEL T-1 ENDPOINT SCREEN V11 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "V10 Git blob: 9f2fc93e189b264ebdd1d78b0cd0c39517bb2386"
echo "DB: $DB_ROOT/$GENERATION (pinned SHA256 once; immutable read-only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_c5_chunnel_endpoint_screen_v11.py \
  --frozen-v10 "$V10" --corpus-db-root "$DB_ROOT" --output "$OUTPUT"
