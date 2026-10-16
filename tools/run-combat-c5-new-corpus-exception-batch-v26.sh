#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
DB="$DB_ROOT/generations/corpus-v2compact-c5-v25-public8-20261016.duckdb"
V25="artifacts/combat/c5-new-game-corpus-batch-v25/published"
OUT="artifacts/combat/c5-new-corpus-exception-batch-v26/published"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB" && -f "$V25/manifest.json" && -f "$V25/actors.json" && -f "$V25/fields.json" && -f "$V25/passengers.json" ]] || {
 echo "ERROR: pinned public8 generation or complete V25 published evidence unavailable" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state research Python unavailable" >&2; exit 69; }
echo "===== C5 V26: LONG EXCEPTION, ARCHIVE VISIBILITY, PASSENGER CLUSTERS ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "V25 manifest Git blob: 2c89d5320b31b2f12d9235192a8ac31240549052"
echo "V25 actors Git blob: 423e6123496068b8d2987bd27fe0b455fee4c1df"
echo "V25 passengers Git blob: ebe8e812d91a80e4fd3c9ccdbc99df0edcc98145"
echo "V25 fields Git blob: b559901540ee1a906811ed4e510629be70aae365"
echo "DB: $DB (SHA256 af4c1579b97736c158cf50a7f709e39b749860661ed65c028fb8085e756c573a)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 tools/diagnostics/combat_c5_new_corpus_exception_batch_v26.py \
 --database "$DB" --v25-manifest "$V25/manifest.json" \
 --v25-actors "$V25/actors.json" --v25-fields "$V25/fields.json" \
 --v25-passengers "$V25/passengers.json" --output-dir "$OUT"
