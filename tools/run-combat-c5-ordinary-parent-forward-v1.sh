#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
SOURCE="artifacts/combat/c5-public100-site-coverage-v1/published/report.json"
OUTPUT="artifacts/combat/c5-ordinary-parent-forward-v1/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$SOURCE" ]] || {
  echo "ERROR: immutable public100 DB or frozen C5 report missing" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: research Python runtime not installed" >&2; exit 69; }
echo "===== C5 ORDINARY PARENT STANDARD NEXT-VCR FORWARD V1 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "frozen_c5_census_sha1: fda92475988d2f7dfbc7b93606de4f8cec909806"
echo "frozen_c5_census: $SOURCE"
echo "DB: $DB_ROOT/$GENERATION (pinned SHA256 once, read-only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_c5_ordinary_parent_forward_v1.py \
  --frozen-c5-census "$SOURCE" --corpus-db-root "$DB_ROOT" \
  --output "$OUTPUT"
