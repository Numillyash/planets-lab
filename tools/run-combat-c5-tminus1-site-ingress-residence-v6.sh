#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
V4="artifacts/combat/c5-parent-queue-arrival-uncertainty-v4/published/report.json"
V5="artifacts/combat/c5-pre-n-site-presence-partition-v5/published/report.json"
OUT="artifacts/combat/c5-tminus1-site-ingress-residence-v6/published/report.json"
PYTHON="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}/bin/python"
[[ -f "$V4" && -f "$V5" ]] || { echo "ERROR: frozen V4 or V5 published JSON absent" >&2; exit 66; }
[[ -x "$PYTHON" ]] || { echo "ERROR: site-state research Python unavailable" >&2; exit 69; }
echo "===== C5 TMINUS1 SITE INGRESS VS RESIDENCE V6 ====="
echo "HEAD: $(git rev-parse HEAD)"
echo "V4 git blob: 847d0a951c1a3bdddc55f1b1b9a82f9d50c0c610"
echo "V5 git blob: bd293c573c85bd849c9e6add06af661bfe519ee9"
echo "Source: published pinned JSON only; no DB or CURRENT access"
PYTHONUNBUFFERED=1 "$PYTHON" tools/diagnostics/combat_c5_tminus1_site_ingress_residence_v6.py \
  --frozen-v4 "$V4" --frozen-v5 "$V5" --output "$OUT"
