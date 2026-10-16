#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
DB="$DB_ROOT/generations/corpus-v2compact-c5-v25-public8-20261016.duckdb"
V25="artifacts/combat/c5-new-game-corpus-batch-v25/published"
V26="artifacts/combat/c5-new-corpus-exception-batch-v26/published"
OUT="artifacts/combat/c5-moving-target-visibility-foreign-v27/published"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
for file in "$DB" "$V25/manifest.json" "$V25/actors.json" "$V25/fields.json" "$V25/passengers.json" "$V26/manifest.json" "$V26/exception_routes.json" "$V26/archive_visibility.json" "$V26/passenger_episodes.json"; do
 [[ -f "$file" ]] || { echo "ERROR: required pinned V25/V26 source missing: $file" >&2; exit 66; }
done
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state Python environment missing" >&2; exit 69; }
echo "===== C5 V27: TARGET COLOCATION / FUTURE IDENTITY / FOREIGN ROUTES ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "new corpus SHA256: af4c1579b97736c158cf50a7f709e39b749860661ed65c028fb8085e756c573a"
echo "V26 manifest blob: 1b44aa0d1f885a3adbf58bdf7fffd065d18e42f8"
echo "V25 manifest blob: 2c89d5320b31b2f12d9235192a8ac31240549052"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 tools/diagnostics/combat_c5_moving_target_visibility_foreign_v27.py \
 --database "$DB" \
 --v25-manifest "$V25/manifest.json" --v25-actors "$V25/actors.json" \
 --v25-fields "$V25/fields.json" --v25-passengers "$V25/passengers.json" \
 --v26-manifest "$V26/manifest.json" --v26-exception-routes "$V26/exception_routes.json" \
 --v26-archive-visibility "$V26/archive_visibility.json" \
 --v26-passenger-episodes "$V26/passenger_episodes.json" \
 --output-dir "$OUT"
echo "===== C5 V27 THREE REPORTS COMPLETE ====="
