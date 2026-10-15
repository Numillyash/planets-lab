#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
V11="artifacts/combat/c5-chunnel-endpoint-screen-v11/published/report.json"
OUT="artifacts/combat/c5-phase-aware-firecloud-v12/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$V11" ]] || {
 echo "ERROR: pinned public100 or V11 source not found" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: research Python unavailable" >&2; exit 69; }
echo "===== C5 PREMOVE ENDPOINT FIRECLOUD CHUNNEL SCREEN V12 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "V11 Git blob: 98e31ff87b615af1e60d9e120317cbbe8c756d4e"
echo "DB: $DB_ROOT/$GENERATION (pinned SHA256 once, read-only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 tools/diagnostics/combat_c5_phase_aware_firecloud_v12.py \
 --frozen-v11 "$V11" --corpus-db-root "$DB_ROOT" --output "$OUT"
