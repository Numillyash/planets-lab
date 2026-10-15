#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
V9="artifacts/combat/c5-site-disjoint-movement-validation-v9/published/report.json"
OUT="artifacts/combat/c5-posthost-residual-coupling-v10/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$V9" ]] || {
  echo "ERROR: pinned public100 or V9 source missing" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state research Python unavailable" >&2; exit 69; }
echo "===== V9 POSTHOST RESIDUAL COUPLING V10 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "V9 Git blob: 4e7d707123586311456cc14e78ff774a851caa48"
echo "DB: $DB_ROOT/$GENERATION (SHA256-checked once, read-only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_c5_posthost_residual_coupling_v10.py \
  --frozen-v9 "$V9" --corpus-db-root "$DB_ROOT" --output "$OUT"
