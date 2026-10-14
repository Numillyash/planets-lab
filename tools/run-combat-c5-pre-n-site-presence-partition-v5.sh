#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
V4="artifacts/combat/c5-parent-queue-arrival-uncertainty-v4/published/report.json"
CENSUS="artifacts/combat/c5-public100-site-coverage-v1/published/report.json"
OUTPUT="artifacts/combat/c5-pre-n-site-presence-partition-v5/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$V4" && -f "$CENSUS" ]] || {
    echo "ERROR: pinned public100 DB or V4/census sources missing" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || {
    echo "ERROR: site-state research Python unavailable" >&2; exit 69;
}
echo "===== ORDINARY C5 PRE-N SITE HISTORY PARTITION V5 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "v4_report_git_blob: 847d0a951c1a3bdddc55f1b1b9a82f9d50c0c610"
echo "census_git_blob: fda92475988d2f7dfbc7b93606de4f8cec909806"
echo "DB: $DB_ROOT/$GENERATION (pinned SHA256 once, read-only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_c5_pre_n_site_presence_partition_v5.py \
  --frozen-v4 "$V4" --frozen-census "$CENSUS" \
  --corpus-db-root "$DB_ROOT" --output "$OUTPUT"
