#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
STATIC="artifacts/combat/mass-time-indexed-static-v1/published/report.json"
RACE="artifacts/combat/mass-tminus1-race-bonus-audit-v1/published/report.json"
OUTPUT="artifacts/combat/mass-independent-late-turn-stress-v1/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$STATIC" && -f "$RACE" ]] || {
  echo "ERROR: pinned DB or published prerequisite evidence report missing" >&2
  exit 66
}
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state runtime missing: $PYTHON" >&2; exit 69; }
echo "===== INDEPENDENT EARLY/LATE COMBAT-MASS STRESS V1 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "DB: $DB_ROOT/$GENERATION"
echo "static_v1: $STATIC"
echo "race_v1: $RACE"
echo "SHA256: verified once in Python before read-only DB open"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_mass_independent_late_turn_stress_v1.py \
  --corpus-db-root "$DB_ROOT" --frozen-static "$STATIC" \
  --frozen-race "$RACE" --max-games 24 --output "$OUTPUT"
