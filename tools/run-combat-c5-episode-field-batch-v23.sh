#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-$HOME/projects/planets-corpus-db}"
GENERATION="generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
V22="artifacts/combat/c5-ruleaware-disjoint-batch-v22/published"
OUT="artifacts/combat/c5-episode-field-batch-v23/published"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$DB_ROOT/$GENERATION" && -f "$V22/manifest.json" && -f "$V22/actors.json" && -f "$V22/escorts.json" && -f "$V22/stabilizers.json" ]] || {
 echo "ERROR: pinned immutable public100 or complete V22 manifest/reports missing" >&2; exit 66;
}
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state research Python unavailable" >&2; exit 69; }
echo "===== C5 V23 THREE STUDIES / ONE SERVER COMMAND ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "V22 manifest Git blob: ef6ad48b2f8f8e0c054525c2bdc19780f465d92a"
echo "V22 actors Git blob: 77b76ac6726e8ad08ab505b7ac112c513aeb89e5"
echo "V22 escorts Git blob: 2174e1e7675296b229674e56b5f68d1f087908f1"
echo "V22 stabilizers Git blob: 37a2924a705017fbca7b6cbf9177321beb6623a3"
echo "DB: $DB_ROOT/$GENERATION (pinned SHA256, read-only)"
PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" PYTHONUNBUFFERED=1 "$PYTHON" \
 tools/diagnostics/combat_c5_episode_and_field_batch_v23.py \
 --frozen-v22-manifest "$V22/manifest.json" \
 --frozen-v22-actors "$V22/actors.json" \
 --frozen-v22-escorts "$V22/escorts.json" \
 --frozen-v22-stabilizers "$V22/stabilizers.json" \
 --corpus-db-root "$DB_ROOT" --output-dir "$OUT"
