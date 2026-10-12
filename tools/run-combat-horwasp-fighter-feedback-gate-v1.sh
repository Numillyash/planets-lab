#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
POST="artifacts/combat/horwasp-postcombat-clan-projection-v1/published/report.json"
TERMINAL="artifacts/combat/horwasp-terminal-continuity-v1/published/report.json"
HORWASP="artifacts/combat/mass-horwasp-tminus1-first-vcr-v1/published/report.json"
OUTPUT="artifacts/combat/horwasp-fighter-feedback-gate-v1/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$POST" && -f "$TERMINAL" && -f "$HORWASP" ]] || {
  echo "ERROR: immutable corpus or required published evidence missing" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state research Python missing" >&2; exit 69; }
echo "===== HORWASP 2021 FIGHTER FEEDBACK RULE GATE / COUNTERFACTUAL V1 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "postcombat_sha1: d58fc71d414a08f2a60618981ee3c550b7d7bf2a"
echo "terminal_sha1: 04144af2d862a5040d822648f93bfeca8d22c1eb"
echo "horwasp_sha1: 358c354d424907488dffd3665e6d6d07c8d04f64"
echo "DB: $DB_ROOT/$GENERATION (sha256 verified once before read-only open)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_horwasp_fighter_feedback_gate_v1.py \
  --frozen-postcombat "$POST" --frozen-terminal "$TERMINAL" \
  --frozen-horwasp "$HORWASP" --corpus-db-root "$DB_ROOT" \
  --output "$OUTPUT"
