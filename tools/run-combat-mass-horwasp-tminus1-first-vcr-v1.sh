#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SOURCE="artifacts/combat/mass-late-residual-prestate-audit-v1/published/report.json"
OUTPUT="artifacts/combat/mass-horwasp-tminus1-first-vcr-v1/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$SOURCE" ]] || { echo "ERROR: frozen observational prestate JSON missing" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: research runtime Python missing: $PYTHON" >&2; exit 69; }
echo "===== EXPERIMENTAL HORWASP T-1 CLAN COMPONENT V1 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "frozen_source: $SOURCE"
echo "source_git_blob_sha1: f4650a6cdb612f750970385d762af0d486894c6e"
echo "DB: not opened; work strictly from immutable published T-1 evidence"
PYTHONUNBUFFERED=1 "$PYTHON" \
  tools/diagnostics/combat_mass_horwasp_tminus1_first_vcr_v1.py \
  --frozen-prestate-audit "$SOURCE" --output "$OUTPUT"
