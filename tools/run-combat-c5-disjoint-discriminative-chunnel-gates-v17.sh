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
V16="artifacts/combat/c5-chunnel-single-gate-controls-v16/published/report.json"
OUT="artifacts/combat/c5-disjoint-discriminative-chunnel-gates-v17/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$V6" && -f "$V9" && -f "$V13" && -f "$V14" && -f "$V16" ]] || {
 echo "ERROR: immutable public100 or source V6/V9/V13/V14/V16 missing" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || {
 echo "ERROR: site-state research Python missing" >&2; exit 69;
}
echo "===== C5 V17 GAME-DISJOINT DISCRIMINATIVE CHUNNEL GATES ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "V6 Git blob: 51d21132e4db89511be59805ebe2be14014b3e7a"
echo "V9 Git blob: 4e7d707123586311456cc14e78ff774a851caa48"
echo "V13 Git blob: 29309650f770b60dab2ec9aaedba3bcbbb652982"
echo "V14 Git blob: 60aeb5ae5ccc828116911bbc61bd752374bc2df7"
echo "V16 Git blob: 9b12fde64ca175d3ac29b7135606cf2c73c24119"
echo "DB: $DB_ROOT/$GENERATION (SHA256 pinned, read-only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 tools/diagnostics/combat_c5_disjoint_discriminative_chunnel_gates_v17.py \
 --frozen-v6 "$V6" --frozen-v9 "$V9" \
 --frozen-v13 "$V13" --frozen-v14 "$V14" --frozen-v16 "$V16" \
 --corpus-db-root "$DB_ROOT" --output "$OUT"
