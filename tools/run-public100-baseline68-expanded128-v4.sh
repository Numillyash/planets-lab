#!/usr/bin/env bash
# Explicit public100 metadata, baseline68-only deep M2 reconstruction, all pytest.
set -uo pipefail
cd "$(dirname "$0")/.."
OUT="artifacts/corpus/public100-baseline68-expanded128-v4"
mkdir -p "$OUT/private-local"
REPORT="$OUT/m2-deep-coverage.json"
COUNTS="$OUT/pytest-counts.json"
MODULES="$OUT/pytest-failed-modules.json"
STATUS="$OUT/stage-status.json"
COHORT="$OUT/baseline-cohort-attestation.json"
LOCAL="$OUT/private-local"
BASELINE="validation/corpus/manifests/public-short-expansion-with-public36.jsonl"
export PLANETS_CORPUS_DB_ROOT="${PLANETS_CORPUS_DB_ROOT:-/root/projects/planets-corpus-db}"
GEN="corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
CURRENT="generations/corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb"
rm -f "$REPORT" "$COUNTS" "$MODULES" "$STATUS" "$COHORT" "$LOCAL/pytest.xml"
preflight="ABSTAIN_PRECONDITIONS"
build="NOT_RUN"
pytest_status="NOT_RUN"
economy="NOT_RUN"
cohort="NOT_RUN"
pytest_rc=125
economy_rc=125
finish() {
  local original=$?
  PREFLIGHT="$preflight" BUILD="$build" PYTEST_STATUS="$pytest_status" ECONOMY="$economy" \
  COHORT="$cohort" PYTEST_RC="$pytest_rc" ECONOMY_RC="$economy_rc" \
  python3 - "$STATUS" <<'PY'
import json,os,sys,pathlib
data={
 "schema":"planets-lab.public100-baseline68-expanded128-status.v4",
 "preflight":os.environ["PREFLIGHT"],"build_status":os.environ["BUILD"],
 "cohort_status":os.environ["COHORT"],
 "pytest_status":os.environ["PYTEST_STATUS"],"pytest_exit":int(os.environ["PYTEST_RC"]),
 "economy_status":os.environ["ECONOMY"],"economy_exit":int(os.environ["ECONOMY_RC"]),
 "full_metadata_games_expected":100,"full_metadata_members_expected":224014,
 "baseline_entity_game_cap":68,"heldout32_entities_read":False,
 "current_changed_by_runner":False,"host_orders_verified":False,"host_diff_verified":False
}
pathlib.Path(sys.argv[1]).write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")
PY
  echo "batch_stage_status=$preflight/$build/$cohort/$pytest_status/$economy"
  echo "aggregate_status_path=$STATUS"
  return "$original"
}
trap finish EXIT
abstain() { preflight="$1"; echo "batch_status=$preflight"; exit 125; }
[[ "$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)" == main ]] || abstain "ABSTAIN_NOT_MAIN"
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || abstain "ABSTAIN_DIRTY_CHECKOUT"
git fetch --quiet origin main 2>/dev/null || abstain "ABSTAIN_REMOTE_FETCH"
[[ "$(git rev-parse HEAD)" == "$(git rev-parse FETCH_HEAD)" ]] || abstain "ABSTAIN_STALE_HEAD"
[[ -f "$PLANETS_CORPUS_DB_ROOT/CURRENT" ]] || abstain "ABSTAIN_CURRENT_MISSING"
[[ "$(cat "$PLANETS_CORPUS_DB_ROOT/CURRENT")" == "$CURRENT" ]] || abstain "ABSTAIN_UNEXPECTED_CURRENT"
[[ -f "$PLANETS_CORPUS_DB_ROOT/generations/$GEN" ]] || abstain "ABSTAIN_PUBLIC100_MISSING"
[[ -f "$BASELINE" ]] || abstain "ABSTAIN_BASELINE_MANIFEST_MISSING"
command -v docker >/dev/null 2>&1 || abstain "ABSTAIN_DOCKER_MISSING"
docker compose version >/dev/null 2>&1 || abstain "ABSTAIN_COMPOSE_MISSING"
preflight="PASS_PINNED_PUBLIC100_BASELINE68"
echo "===== FULL PUBLIC100 METADATA + BASELINE68 DEEP READ-ONLY SURVEY ====="
echo "source_commit=$(git rev-parse HEAD)"
echo "metadata_games=100"
echo "source_members_expected=224014"
echo "selected_baseline_games_max=68"
echo "selected_adjacent_pairs_per_game_max=128"
echo "selected_adjacent_pairs_budget_max=8704"
echo "nonplanet_observability=minefields_ships_starbases_vcrs_ionstorms"
echo "sealed_heldout32_entity_access=false"
echo "generation=EXPLICIT_PUBLIC100"
echo "database_mount=READ_ONLY"
echo "current_changed=false"
echo "new_real_host_diff_verified=false"

docker compose -f compose.yaml -f compose.corpus-db.yaml build lab > "$LOCAL/build.log" 2>&1
build_rc=$?
if (( build_rc != 0 )); then
  build="FAILED_LOCAL_ONLY"
  abstain "ABSTAIN_BUILD_FAILED"
fi
build="PASS"
# Fail promptly if the container lacks tools required by test harnesses.
# This guards the exact on-host issue evidenced in v2 and v4.
if docker compose -f compose.yaml -f compose.corpus-db.yaml run --rm -T lab \
    sh -ec 'command -v git >/dev/null && git --version >/dev/null && command -v bash >/dev/null' \
    > "$LOCAL/lab-tool-preflight.log" 2>&1; then
  echo "stage=container_tool_preflight status=PASS_GIT_AND_BASH"
else
  abstain "ABSTAIN_LAB_GIT_OR_BASH_MISSING"
fi
echo "stage=baseline68_cohort_metadata_identity begin"
# Server-local manifest was never committed to Git; verify exact GAME-ID SET
# against SHA-pinned public68 and public100 metadata before any entity read.
docker compose -f compose.yaml -f compose.corpus-db.yaml run --rm -T lab \
  python tools/diagnostics/public100_baseline68_cohort_guard_v3.py \
  --db-root /corpus-db --manifest "$BASELINE" --output "$COHORT" \
  > "$LOCAL/cohort-guard.log" 2>&1
cohort_rc=$?
if (( cohort_rc != 0 )) || [[ ! -s "$COHORT" ]]; then
  cohort="ABSTAIN_UNVERIFIED_BASELINE_GAME_SET"
  rm -f "$COHORT"
  abstain "ABSTAIN_BASELINE_COHORT_GUARD"
fi
cohort="PASS_EXACT_68_IDS_SHA_PINNED_PUBLIC68"
attested_sha="$(python3 - "$COHORT" <<'PY'
import json,sys
data=json.load(open(sys.argv[1],encoding="utf-8"))
assert data["status"]=="PASS_EXACT_MANIFEST_GAME_IDS_MATCH_SHA_PINNED_PUBLIC68"
assert data["baseline_game_count"]==68 and data["all_metadata_game_count"]==100
assert data["heldout_entity_sampling"] is False
print(data["manifest_sha256"])
PY
)"
if [[ ! "$attested_sha" =~ ^[0-9a-f]{64}$ ]]; then
  cohort="ABSTAIN_ATTESTED_HASH_INVALID"
  rm -f "$COHORT"
  abstain "ABSTAIN_COHORT_REPORT_INVALID"
fi
echo "stage=baseline68_cohort_metadata_identity result=PASS_EXACT_SET_MATCH"
echo "stage=full_pytest started"
docker compose -f compose.yaml -f compose.corpus-db.yaml run --rm -T lab \
  python -m pytest -q --tb=short --junitxml="$LOCAL/pytest.xml" \
  > "$LOCAL/pytest.log" 2>&1
pytest_rc=$?
if python3 tools/diagnostics/public100_pytest_safe_counts_v2.py \
    --xml "$LOCAL/pytest.xml" --exit-code "$pytest_rc" \
    --output "$COUNTS" > "$LOCAL/sanitize.log" 2>&1; then
  pytest_status="$(python3 - "$COUNTS" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))["status"])
PY
)"
else
  pytest_status="SANITIZER_FAILED"
  rm -f "$COUNTS"
fi
echo "stage=full_pytest result=$pytest_status"
# Classify only exact Git-tracked TEST FILE names (not parametrized test
# names, failure messages, raw JUnit or private paths).
if python3 tools/diagnostics/public100_pytest_failed_modules_v4.py \
    --xml "$LOCAL/pytest.xml" --repository . --output "$MODULES" \
    > "$LOCAL/failure-module-sanitizer.log" 2>&1; then
  echo "stage=pytest_module_failure_classifier result=PASS_SAFE_COUNTS"
else
  rm -f "$MODULES"
  echo "stage=pytest_module_failure_classifier result=ABSTAIN"
fi
if [[ -s "$COUNTS" ]]; then
  python3 - "$COUNTS" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
print("test_cases="+str(r["tests"]))
print("test_failures="+str(r["failures"]))
print("test_errors="+str(r["errors"]))
PY
fi

echo "stage=deep_m2_100_metadata_68_baseline begin"
docker compose -f compose.yaml -f compose.corpus-db.yaml run --rm -T lab \
  python tools/diagnostics/m2_public_corpus_economy_coverage_v1.py \
  --db-root /corpus-db --baseline-manifest "$BASELINE" \
  --expected-baseline-games 68 --max-games 68 --pairs-per-game 128 \
  --expected-baseline-manifest-sha256 "$attested_sha" \
  --output "$REPORT" > "$LOCAL/deep-m2.log" 2>&1
economy_rc=$?
if (( economy_rc == 0 )) && [[ -s "$REPORT" ]] && \
  python3 tools/diagnostics/m2_validate_corpus_aggregate_evidence_v1.py \
  --input "$REPORT" > "$LOCAL/report-validator.log" 2>&1 && \
  python3 - "$REPORT" "$attested_sha" > "$LOCAL/manifest-match.log" 2>&1 <<'PY'
import json,sys
payload=json.load(open(sys.argv[1],encoding="utf-8"))
assert payload["baseline_sample_allowlist"]["manifest_sha256"]==sys.argv[2]
assert payload["baseline_sample_allowlist"]["allowed_game_count"]==68
assert payload["baseline_sample_allowlist"]["heldout_entity_sampling"] is False
PY
then
  economy="PASS_VALIDATED_AGGREGATE"
  python3 - "$REPORT" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]));m=p["metadata"]
print("observed_metadata_games="+str(m["all_games_in_source_metadata"]))
print("observed_metadata_members="+str(m["all_source_perspective_members"]))
print("sampled_baseline_games="+str(m["metadata_selected_game_count"]))
print("sampled_adjacent_pairs="+str(m["metadata_frozen_sample_pairs"]))
print("sampled_nonplanet_sections=minefields_ships_starbases_vcrs_ionstorms")
print("heldout_entities_read=false")
PY
else
  economy="FAILED_OR_UNVALIDATED"
  rm -f "$REPORT"
fi
[[ "$(cat "$PLANETS_CORPUS_DB_ROOT/CURRENT" 2>/dev/null)" == "$CURRENT" ]] || abstain "ABSTAIN_CURRENT_CHANGED_DURING_RUN"
echo "stage=deep_m2 result=$economy"
echo "aggregate_report=$REPORT"
if (( pytest_rc != 0 )); then exit "$pytest_rc"; fi
if [[ "$pytest_status" != PASS || "$economy" != PASS_VALIDATED_AGGREGATE ]]; then exit 2; fi
echo "batch_status=PASS_NONCAUSAL_READONLY"
exit 0
