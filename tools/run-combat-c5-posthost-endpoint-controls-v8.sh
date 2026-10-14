#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
V6="artifacts/combat/c5-tminus1-site-ingress-residence-v6/published/report.json"
V7="artifacts/combat/c5-pre-mine-route-counterfactual-v7/published/report.json"
OUTPUT="artifacts/combat/c5-posthost-endpoint-controls-v8/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$V6" && -f "$V7" ]] || {
    echo "ERROR: immutable public100 DB or pinned V6/V7 missing" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: research Python missing" >&2; exit 69; }
echo "===== C5 T-1 VERSUS POST-HOST T ENDPOINT DIFFERENTIAL V8 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "V6 Git blob: 51d21132e4db89511be59805ebe2be14014b3e7a"
echo "V7 Git blob: f551fc83b1725f7170aae210238ebae68c0e6eee"
echo "DB: $DB_ROOT/$GENERATION (SHA256 checked once, read only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_c5_posthost_endpoint_controls_v8.py \
  --frozen-v6 "$V6" --frozen-v7 "$V7" \
  --corpus-db-root "$DB_ROOT" --output "$OUTPUT"
