#!/usr/bin/env bash
# One host-side command called inside the established runtime-evidence wrapper.
# All database state is read-only; output is allowlisted aggregates only.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
RUN_DIR="artifacts/corpus/public68-broad-readonly-v1"
REPORT="$RUN_DIR/report.json"
SUITE_REPORT="$RUN_DIR/suite-status.json"
mkdir -p "$RUN_DIR"
rm -f "$REPORT" "$SUITE_REPORT"
record() {
  local test_status="$1" census_status="$2" count="$3"
  printf '{"schema":"planets-lab.public68-broad-suite-status.v1","synthetic_tests_exit_code":%s,"test_summary":"%s","corpus_exit_code":%s,"causal_host_verification":false,"all_private_data_excluded":true}\n' \
    "$test_status" "$count" "$census_status" > "$SUITE_REPORT"
}
die() {
  echo "batch_status=ABSTAIN"
  echo "reason_code=$1"
  record 125 125 "NOT_STARTED"
  exit 125
}
[[ "$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)" == "main" ]] || die "MAIN_BRANCH_REQUIRED"
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || die "DIRTY_TRACKED_CHECKOUT"
git fetch --quiet origin main 2>/dev/null || die "GIT_MAIN_FETCH_UNAVAILABLE"
[[ "$(git rev-parse HEAD)" == "$(git rev-parse FETCH_HEAD)" ]] || die "STALE_HEAD_PULL_MAIN_FIRST"
export PLANETS_CORPUS_DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
expected="generations/corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb"
[[ -f "$PLANETS_CORPUS_DB_ROOT/CURRENT" ]] || die "CURRENT_MISSING"
[[ "$(cat "$PLANETS_CORPUS_DB_ROOT/CURRENT")" == "$expected" ]] || die "NOT_PINNED_PUBLIC68"
[[ -f "$PLANETS_CORPUS_DB_ROOT/$expected" ]] || die "PINNED_PUBLIC68_FILE_MISSING"
command -v docker >/dev/null 2>&1 || die "DOCKER_UNAVAILABLE"
docker compose version >/dev/null 2>&1 || die "COMPOSE_UNAVAILABLE"
echo "===== PINNED PUBLIC68 MAXIMAL READ-ONLY SUITE ====="
echo "source_commit=$(git rev-parse HEAD)"
echo "source_branch=main"
echo "database_scope=PINNED_PUBLIC68_CURRENT_ONLY"
echo "expected_games=68"
echo "expected_source_members=169569"
echo "database_mount=READ_ONLY"
echo "public100_read=false"
echo "M2_sealed_holdout_entities_read=false"
echo "real_host_phase_executed=false"
echo "private_raw_orders_or_member_data_logged=false"
# Raw Docker/pytest diagnostics stay LOCAL and are never included in evidence.
docker compose -f compose.yaml -f compose.corpus-db.yaml build lab \
  > "$RUN_DIR/local-build.log" 2>&1 || die "LAB_IMAGE_BUILD_FAILED"
echo "stage=synthetic_regression_tests status=RUNNING"
docker compose -f compose.yaml -f compose.corpus-db.yaml run --rm -T lab \
  python -m pytest -q --tb=no > "$RUN_DIR/local-pytest.log" 2>&1
test_rc=$?
tests_summary="$(grep -oE '[0-9]+ passed' "$RUN_DIR/local-pytest.log" | tail -1 || true)"
if [[ -z "$tests_summary" ]]; then tests_summary="COUNT_NOT_AVAILABLE"; fi
tests_summary="${tests_summary// /_}"
echo "stage=synthetic_regression_tests exit_code=$test_rc count=$tests_summary"
echo "stage=full_public68_readonly_census status=RUNNING"
docker compose -f compose.yaml -f compose.corpus-db.yaml run --rm -T lab \
  python tools/diagnostics/public68_broad_readonly_census_v1.py \
  --db-root /corpus-db --report "$REPORT" > "$RUN_DIR/local-census.log" 2>&1
corpus_rc=$?
if [[ -f "$REPORT" ]]; then
  python3 - "$REPORT" <<'PY'
import json
import sys
try:
    with open(sys.argv[1],encoding="utf-8") as stream:
        o=json.load(stream)
    print("stage=full_public68_readonly_census status="+str(o.get("status","MISSING")))
    if isinstance(o.get("metadata_census"),dict):
        m=o["metadata_census"]
        print("metadata_games="+str(m.get("distinct_games",0)))
        print("metadata_source_members="+str(m.get("source_members",0)))
    if isinstance(o.get("temporal_census"),dict):
        t=o["temporal_census"]
        print("consecutive_archival_observation_pairs="+str(t.get("consecutive_archival_observation_pairs",0)))
    print("typed_sections_checked="+str(o.get("source_sections_checked",0)))
    print("host_diff_verified=false")
except (OSError, ValueError, KeyError, TypeError):
    print("stage=full_public68_readonly_census status=INVALID_AGGREGATE_REPORT")
PY
else
  echo "stage=full_public68_readonly_census status=NO_AGGREGATE_REPORT"
fi
record "$test_rc" "$corpus_rc" "$tests_summary"
echo "synthetic_test_exit=$test_rc"
echo "corpus_census_exit=$corpus_rc"
echo "report=$REPORT"
echo "suite_status=$SUITE_REPORT"
echo "status=ALL_COMPLETE_ONLY_IF_BOTH_ZERO"
if (( test_rc != 0 )); then exit "$test_rc"; fi
if (( corpus_rc != 0 )); then exit "$corpus_rc"; fi
exit 0
