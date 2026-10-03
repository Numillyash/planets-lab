#!/usr/bin/env bash
set -euo pipefail

RESEARCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAIN_ROOT="${PLANETS_MAIN_ROOT:-/root/projects/planets-lab}"
CORPUS_DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
OUTPUT="${AFSIM_R1_OUTPUT:-$RESEARCH_ROOT/artifacts/external-sources/afsim-r1/discovery-afsim-r1.json}"

echo "===== AFSIM-R1 DISCOVERY GATE ====="
echo "research_root: $RESEARCH_ROOT"
echo "main_root:     $MAIN_ROOT"
echo "corpus_db:     $CORPUS_DB_ROOT"
echo "output:        $OUTPUT"
echo

research_branch="$(git -C "$RESEARCH_ROOT" branch --show-current)"
research_head="$(git -C "$RESEARCH_ROOT" rev-parse HEAD)"
main_branch="$(git -C "$MAIN_ROOT" branch --show-current)"
main_head="$(git -C "$MAIN_ROOT" rev-parse HEAD)"
main_origin="$(git -C "$MAIN_ROOT" rev-parse origin/main)"

if [[ "$research_branch" != "research/external-engine-analysis" ]]; then
  echo "ERROR: research checkout is on $research_branch" >&2
  exit 2
fi
if [[ "$main_branch" != "main" ]]; then
  echo "ERROR: canonical checkout is on $main_branch, expected main" >&2
  exit 2
fi
if [[ "$main_head" != "$main_origin" ]]; then
  echo "ERROR: canonical main checkout is not at origin/main" >&2
  echo "  HEAD:        $main_head" >&2
  echo "  origin/main: $main_origin" >&2
  exit 2
fi

echo "research HEAD: $research_head"
echo "main HEAD:     $main_head"
echo

echo "===== MODEL UNIT TESTS ====="
cd "$RESEARCH_ROOT"
python3 -m pytest -q tests/test_afsim_r1_model.py
echo

echo "===== DISCOVERY-ONLY CORPUS DB PROBE ====="
python3 tools/research/probe_afsim_r1_discovery_db.py   --main-root "$MAIN_ROOT"   --corpus-db-root "$CORPUS_DB_ROOT"   --output "$OUTPUT"

echo
echo "===== EVIDENCE BOUNDARY ====="
echo "AFSIM-R1 is EXTERNAL_IMPLEMENTATION evidence only."
echo "This runner accepts discovery input only; held-out remains closed."
