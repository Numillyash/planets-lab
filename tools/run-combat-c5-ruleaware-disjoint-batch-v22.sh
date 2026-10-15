#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
V17="artifacts/combat/c5-disjoint-discriminative-chunnel-gates-v17/published/report.json"
V20="artifacts/combat/c5-chunnel-stabilization-provenance-v20/published/report.json"
OUT="artifacts/combat/c5-ruleaware-disjoint-batch-v22/published"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$V17" && -f "$V20" ]] || {
 echo "ERROR: pinned immutable public100/V17/V20 missing" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state research Python unavailable" >&2; exit 69; }
echo "===== C5 V22: THREE REPORTS / ONE IMMUTABLE DB PASS ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "V17 Git blob: a6256b70dc63b9b7126a211245bc65ce20ece863"
echo "V20 Git blob: 3d5e1d5aeb6b0138c01bab3ec81185d0685233c0"
echo "DB: $DB_ROOT/$GENERATION (one pinned SHA256 check, read-only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 tools/diagnostics/combat_c5_ruleaware_disjoint_batch_v22.py \
 --frozen-v17 "$V17" --frozen-v20 "$V20" \
 --corpus-db-root "$DB_ROOT" --output-dir "$OUT"
