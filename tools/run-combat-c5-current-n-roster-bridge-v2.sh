#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
CENSUS="artifacts/combat/c5-public100-site-coverage-v1/published/report.json"
STRICT="artifacts/combat/c5-ordinary-parent-forward-v1/published/report.json"
OUTPUT="artifacts/combat/c5-current-n-roster-bridge-v2/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$CENSUS" && -f "$STRICT" ]] || {
  echo "ERROR: pinned corpus, published site census or strict V1 missing" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: research Python unavailable" >&2; exit 69; }
echo "===== C5 CONDITIONAL CURRENT-VCR-N ROSTER BRIDGE V2 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "source_census_git_blob: fda92475988d2f7dfbc7b93606de4f8cec909806"
echo "source_strict_v1_git_blob: 1ed69919f38fbc7d09b2e890162c1a25a3f677bd"
echo "DB: $DB_ROOT/$GENERATION (SHA256 once, read-only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_c5_current_n_roster_bridge_v2.py \
  --frozen-census "$CENSUS" --frozen-strict-v1 "$STRICT" \
  --corpus-db-root "$DB_ROOT" --output "$OUTPUT"
