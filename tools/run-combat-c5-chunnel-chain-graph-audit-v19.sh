#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
V17="artifacts/combat/c5-disjoint-discriminative-chunnel-gates-v17/published/report.json"
V18="artifacts/combat/c5-short-chunnel-and-visibility-audit-v18/published/report.json"
OUT="artifacts/combat/c5-chunnel-chain-graph-audit-v19/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$V17" && -f "$V18" ]] || {
 echo "ERROR: pinned public100/V17/V18 sources absent" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: research Python unavailable" >&2; exit 69; }
echo "===== C5 V19 CHUNNEL TMINUS1 CHAIN GRAPH AND 25LY CASE ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "V17 Git blob: a6256b70dc63b9b7126a211245bc65ce20ece863"
echo "V18 Git blob: 88bd596534e5e7390c21d6a0a108c732e8a07150"
echo "DB: $DB_ROOT/$GENERATION (SHA256 pinned, read-only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 tools/diagnostics/combat_c5_chunnel_chain_graph_audit_v19.py \
 --frozen-v17 "$V17" --frozen-v18 "$V18" \
 --corpus-db-root "$DB_ROOT" --output "$OUT"
