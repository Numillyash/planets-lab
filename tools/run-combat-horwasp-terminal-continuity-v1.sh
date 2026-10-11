#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SOURCE="artifacts/combat/mass-horwasp-tminus1-first-vcr-v1/published/report.json"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
OUTPUT="artifacts/combat/horwasp-terminal-continuity-v1/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$SOURCE" && -f "$DB_ROOT/$GENERATION" ]] || {
  echo "ERROR: pinned frozen Horwasp evidence or immutable DB missing" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state research Python missing" >&2; exit 69; }
echo "===== HORWASP SAME-TURN CLASSIC TERMINAL CONTINUITY V1 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "frozen_source: $SOURCE"
echo "source_git_blob_sha1: 358c354d424907488dffd3665e6d6d07c8d04f64"
echo "DB: $DB_ROOT/$GENERATION (SHA256 verified before read-only open)"
PYTHONPATH="$ROOT/src" PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_horwasp_terminal_continuity_v1.py \
  --frozen-horwasp "$SOURCE" --corpus-db-root "$DB_ROOT" \
  --output "$OUTPUT"
