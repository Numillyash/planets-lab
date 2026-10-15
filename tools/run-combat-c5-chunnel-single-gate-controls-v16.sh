#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
V15="artifacts/combat/c5-chunnel-actor-outcome-audit-v15/published/report.json"
OUT="artifacts/combat/c5-chunnel-single-gate-controls-v16/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$V15" ]] || {
 echo "ERROR: pinned public100 or V15 source absent" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: research Python missing" >&2; exit 69; }
echo "===== C5 FIRECLOUD SINGLE FAILED GATE CONTROLS V16 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "V15 report Git blob: 59f39fdb73779a80c14148d07e30c84e27d699d3"
echo "DB: $DB_ROOT/$GENERATION (pinned SHA256, read-only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 tools/diagnostics/combat_c5_chunnel_single_gate_controls_v16.py \
 --frozen-v15 "$V15" --corpus-db-root "$DB_ROOT" --output "$OUT"
