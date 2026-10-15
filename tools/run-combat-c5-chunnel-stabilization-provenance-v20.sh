#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
V17="artifacts/combat/c5-disjoint-discriminative-chunnel-gates-v17/published/report.json"
V19="artifacts/combat/c5-chunnel-chain-graph-audit-v19/published/report.json"
OUT="artifacts/combat/c5-chunnel-stabilization-provenance-v20/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$V17" && -f "$V19" ]] || {
 echo "ERROR: immutable public100 or pinned V17/V19 report missing" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state research Python missing" >&2; exit 69; }
echo "===== C5 V20 CHUNNEL STABILIZATION FIELD TMINUS1 SOURCE AUDIT ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "V17 Git blob: a6256b70dc63b9b7126a211245bc65ce20ece863"
echo "V19 Git blob: 572d14d348235694402148273c7085d212301eac"
echo "DB: $DB_ROOT/$GENERATION (pinned SHA256 once; read-only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 tools/diagnostics/combat_c5_chunnel_stabilization_provenance_v20.py \
 --frozen-v17 "$V17" --frozen-v19 "$V19" \
 --corpus-db-root "$DB_ROOT" --output "$OUT"
