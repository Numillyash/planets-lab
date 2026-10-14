#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
OUTPUT="artifacts/combat/c5-public100-site-coverage-v1/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" ]] || { echo "ERROR: immutable public100 database missing" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state Python runtime missing" >&2; exit 69; }
echo "===== C5 ORDINARY PUBLIC100 SITE-COVERAGE PREFLIGHT ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "DB: $DB_ROOT/$GENERATION"
echo "selection: metadata only; before VCR payloads"
echo "SHA256: verified once before read-only DuckDB open"
PYTHONPATH="$ROOT/src" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_c5_public100_site_coverage_v1.py \
  --corpus-db-root "$DB_ROOT" --max-games "${C5_MAX_GAMES:-48}" \
  --output "$OUTPUT"
