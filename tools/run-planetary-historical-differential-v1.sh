#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
DB="$DB_ROOT/generations/corpus-v2compact-c5-v25-public8-20261016.duckdb"
SOURCE="artifacts/combat/c5-new-game-corpus-batch-v25/published/manifest.json"
OUT="artifacts/planetary/historical-differential-v1/published"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB" && -f "$SOURCE" ]] || {
 echo "ERROR: pinned new public8 compact archive or V25 source manifest missing" >&2
 exit 66
}
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state Python missing" >&2; exit 69; }
echo "===== M2 ARCHIVE DIFF V1: 4 PLANET FAMILIES / ONE RUN ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "generation: $DB (SHA256 pinned read-only)"
echo "V25 manifest Git blob: 2c89d5320b31b2f12d9235192a8ac31240549052"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 "$ROOT/tools/diagnostics/planetary_historical_differential_v1.py" \
 --database "$DB" --v25-manifest "$SOURCE" --output-dir "$OUT"
