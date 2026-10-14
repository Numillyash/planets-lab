#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
CENSUS="artifacts/combat/c5-public100-site-coverage-v1/published/report.json"
V2="artifacts/combat/c5-current-n-roster-bridge-v2/published/report.json"
OUTPUT="artifacts/combat/c5-parent-queue-arrival-uncertainty-v4/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$CENSUS" && -f "$V2" ]] || { echo "ERROR: pinned public100 DB or published reports missing" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state research Python unavailable" >&2; exit 69; }
echo "===== C5 PARENT QUEUE UNCERTAIN T-1 ARRIVALS SAFETY GATE V4 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "census_git_blob: fda92475988d2f7dfbc7b93606de4f8cec909806"
echo "conditional_v2_git_blob: dd641864dc3bd541098ea2c21cf21fb8ff03d5ce"
echo "DB: $DB_ROOT/$GENERATION (pinned SHA256 once, read-only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_c5_parent_queue_arrival_uncertainty_v4.py \
  --frozen-census "$CENSUS" --frozen-conditional-v2 "$V2" \
  --corpus-db-root "$DB_ROOT" --output "$OUTPUT"
