#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
V6="artifacts/combat/c5-tminus1-site-ingress-residence-v6/published/report.json"
V9="artifacts/combat/c5-site-disjoint-movement-validation-v9/published/report.json"
V13="artifacts/combat/c5-firecloud-disjoint-validation-v13/published/report.json"
V14="artifacts/combat/c5-conditional-chunnel-holdout-v14/published/report.json"
OUT="artifacts/combat/c5-chunnel-actor-outcome-audit-v15/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$V6" && -f "$V9" && -f "$V13" && -f "$V14" ]] || {
 echo "ERROR: immutable public100 or pinned V6/V9/V13/V14 source missing" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: research Python unavailable" >&2; exit 69; }
echo "===== C5 V15 ALL ACTOR EDGE AND NEGATIVE CONTROL AUDIT ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "V14 Git blob: 60aeb5ae5ccc828116911bbc61bd752374bc2df7"
echo "DB: $DB_ROOT/$GENERATION (SHA256 checked once; read-only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 tools/diagnostics/combat_c5_chunnel_actor_outcome_audit_v15.py \
 --frozen-v6 "$V6" --frozen-v9 "$V9" \
 --frozen-v13 "$V13" --frozen-v14 "$V14" \
 --corpus-db-root "$DB_ROOT" --output "$OUT"
