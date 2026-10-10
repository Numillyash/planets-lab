#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
SOURCE="artifacts/combat/mass-time-indexed-static-v1/published/report.json"
OUTPUT="artifacts/combat/mass-tminus1-race-bonus-audit-v1/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$SOURCE" ]] || { echo "ERROR: pinned DB or successful source V1 report missing" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: runtime Python missing: $PYTHON" >&2; exit 69; }
echo "===== PRE-VCR TMINUS1 RACE BONUS AUDIT ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "source: $SOURCE"
echo "DB: $DB_ROOT/$GENERATION"
echo "SHA256: checked once before read-only DuckDB open in Python"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_mass_tminus1_race_bonus_audit_v1.py \
  --corpus-db-root "$DB_ROOT" --source-static-v1 "$SOURCE" \
  --output "$OUTPUT"
