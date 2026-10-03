#!/usr/bin/env bash
set -euo pipefail

RESEARCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAIN_ROOT="${PLANETS_MAIN_ROOT:-/root/projects/planets-lab}"
CORPUS_DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
OUTPUT_REL="${AFSIM_R1_OUTPUT_REL:-artifacts/external-sources/afsim-r1/discovery-afsim-r1.json}"
OUTPUT_HOST="$RESEARCH_ROOT/$OUTPUT_REL"
OUTPUT_CONTAINER="/research/$OUTPUT_REL"
DOCKER_PREFLIGHT_TIMEOUT="${DOCKER_PREFLIGHT_TIMEOUT:-10}"

echo "===== AFSIM-R1 DISCOVERY GATE ====="
echo "research_root: /root/projects/planets-lab-external"
echo "main_root:     $MAIN_ROOT"
echo "corpus_db:     $CORPUS_DB_ROOT"
echo "output:        $OUTPUT_HOST"
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
if [[ ! -s "$CORPUS_DB_ROOT/CURRENT" ]]; then
  echo "ERROR: Corpus DB CURRENT missing: $CORPUS_DB_ROOT/CURRENT" >&2
  exit 66
fi
if ! timeout "${DOCKER_PREFLIGHT_TIMEOUT}s" docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon/backend is not responding within ${DOCKER_PREFLIGHT_TIMEOUT}s." >&2
  exit 69
fi

echo "research HEAD: $research_head"
echo "main HEAD:     $main_head"
echo "corpus CURRENT: $(cat "$CORPUS_DB_ROOT/CURRENT")"
echo

echo "===== BUILD CANONICAL MAIN LAB IMAGE ====="
compose=(
  docker compose
  -f "$MAIN_ROOT/compose.yaml"
  -f "$MAIN_ROOT/compose.corpus-db.yaml"
)
(
  cd "$MAIN_ROOT"
  "${compose[@]}" build lab
)
echo

# The main checkout remains /workspace so all canonical diagnostics/imports come
# from main.  The research checkout is mounted separately and supplies only the
# frozen AFSim model/probe/tests.
lab=(
  "${compose[@]}" run --rm -T
  -v "$RESEARCH_ROOT:/research"
  -e PYTHONPATH=/workspace/src:/workspace/tools/diagnostics:/research/tools/research
  lab
)

echo "===== MODEL UNIT TESTS (CANONICAL LAB PYTHON) ====="
(
  cd "$MAIN_ROOT"
  "${lab[@]}" python -m pytest -q /research/tests/test_afsim_r1_model.py
)
echo

echo "===== DISCOVERY-ONLY CORPUS DB PROBE ====="
mkdir -p "$(dirname "$OUTPUT_HOST")"
(
  cd "$MAIN_ROOT"
  "${lab[@]}" python /research/tools/research/probe_afsim_r1_discovery_db.py     --main-root /workspace     --corpus-db-root /corpus-db     --discovery /workspace/artifacts/public-capture-side/discovery-capture-side.json     --output "$OUTPUT_CONTAINER"
)

echo
echo "===== AFSIM-R1 DISCOVERY GATE COMPLETE ====="
echo "research HEAD: $research_head"
echo "main HEAD:     $main_head"
echo "corpus_db:     $(cat "$CORPUS_DB_ROOT/CURRENT")"
echo "output:        $OUTPUT_HOST"
echo
echo "===== EVIDENCE BOUNDARY ====="
echo "AFSIM-R1 is EXTERNAL_IMPLEMENTATION evidence only."
echo "Canonical site/history reconstruction came from the separate main checkout."
echo "Corpus DB was mounted read-only."
echo "This runner accepts discovery input only; held-out remains closed."
