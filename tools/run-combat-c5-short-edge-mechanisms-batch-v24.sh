#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
V23="artifacts/combat/c5-episode-field-batch-v23/published"
OUT="artifacts/combat/c5-short-edge-mechanisms-batch-v24/published"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$V23/field_scan.json" && -f "$V23/manifest.json" ]] || {
 echo "ERROR: pinned immutable public100 / V23 field+manifest absent" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state research Python unavailable" >&2; exit 69; }
echo "===== C5 V24: SHORT-EDGE MECHANISMS (3 REPORTS, ONE RUN) ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "V23 field Git blob: 9d5dab0cdd8969313c795a56efea939de83242b4"
echo "V23 manifest Git blob: 12c0648b5b123caa50ef8d974ed7dc3d2bab4c9b"
echo "DB: $DB_ROOT/$GENERATION (pinned SHA256 once, immutable/read-only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 tools/diagnostics/combat_c5_short_edge_mechanisms_batch_v24.py \
 --frozen-v23-field "$V23/field_scan.json" --frozen-v23-manifest "$V23/manifest.json" \
 --corpus-db-root "$DB_ROOT" --output-dir "$OUT"
