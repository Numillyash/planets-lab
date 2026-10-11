#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
HORWASP="artifacts/combat/mass-horwasp-tminus1-first-vcr-v1/published/report.json"
TERMINAL="artifacts/combat/horwasp-terminal-continuity-v1/published/report.json"
OUTPUT="artifacts/combat/horwasp-postcombat-clan-projection-v1/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$HORWASP" && -f "$TERMINAL" ]] || {
  echo "ERROR: frozen source artifacts or immutable public100 DB missing" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: research runtime Python missing" >&2; exit 69; }
echo "===== HORWASP DOCUMENTED POSTCOMBAT CLAN LOSS CONDITIONAL V1 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "frozen_horwasp: $HORWASP"
echo "source_horwasp_sha1: 358c354d424907488dffd3665e6d6d07c8d04f64"
echo "frozen_terminal: $TERMINAL"
echo "source_terminal_sha1: 04144af2d862a5040d822648f93bfeca8d22c1eb"
echo "DB: $DB_ROOT/$GENERATION (SHA256 verified once, read-only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_horwasp_postcombat_clan_projection_v1.py \
  --frozen-horwasp-v1 "$HORWASP" --frozen-terminal-v1 "$TERMINAL" \
  --corpus-db-root "$DB_ROOT" --output "$OUTPUT"
