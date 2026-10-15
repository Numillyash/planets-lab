#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
V19="artifacts/combat/c5-chunnel-chain-graph-audit-v19/published/report.json"
V20="artifacts/combat/c5-chunnel-stabilization-provenance-v20/published/report.json"
OUT="artifacts/combat/c5-stabilization-batch-v21/published"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$V19" && -f "$V20" ]] || {
 echo "ERROR: immutable public100 or pinned V19/V20 report missing" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state research Python unavailable" >&2; exit 69; }
echo "===== C5 V21 BATCH: 3 EXPERIMENTS / ONE SERVER COMMAND ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "V19 Git blob: 572d14d348235694402148273c7085d212301eac"
echo "V20 Git blob: 3d5e1d5aeb6b0138c01bab3ec81185d0685233c0"
echo "DB: $DB_ROOT/$GENERATION (pinned SHA256, read-only)"
mkdir -p "$OUT"
for phase in geometry persistence escorts; do
 echo "===== C5 V21 EXPERIMENT: $phase ====="
 PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_c5_stabilization_batch_v21.py \
  --phase "$phase" --frozen-v19 "$V19" --frozen-v20 "$V20" \
  --corpus-db-root "$DB_ROOT" --output-dir "$OUT"
done
echo "===== C5 V21 MANIFEST / COMPLETENESS GATE ====="
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 tools/diagnostics/combat_c5_stabilization_batch_v21.py \
 --phase manifest --output-dir "$OUT"
echo "===== C5 V21 ALL THREE EXPERIMENTS COMPLETED ====="
