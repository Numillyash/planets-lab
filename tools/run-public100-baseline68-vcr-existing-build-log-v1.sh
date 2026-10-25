#!/usr/bin/env bash
# Analyze an EXISTING local VCR build.log: NO Docker build, NO DB/Host access.
set -uo pipefail
cd "$(dirname "$0")/.."
OLD="artifacts/corpus/public100-baseline68-vcr-temporal-v1"
OUT="artifacts/corpus/public100-baseline68-vcr-build-diagnosis-v1"
mkdir -p "$OUT"
rm -f "$OUT/build-failure-diagnostic.json"
# Do not pretend we can bind the preserved log to an independently
# authenticated historical build attempt, or reconstruct a build exit code.
if [[ "$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)" != "main" ||
      -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "status=ABSTAIN_MAIN_CHECKOUT_OR_DIRTY"
  exit 125
fi
if ! python3 - "$OLD/stage-status.json" <<'PY'
import json,sys
from pathlib import Path
try:
    data=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    assert data["schema"]=="planets-lab.public100-baseline68-vcr-temporal-status.v1"
    assert data["preflight"]=="ABSTAIN_BUILD_FAILED"
    assert data["build_status"]=="FAILED_LOCAL_ONLY"
    assert data["cohort_status"]=="NOT_RUN"
    assert data["pytest_status"]=="NOT_RUN"
    assert data["economy_status"]=="NOT_RUN"
except (OSError,ValueError,KeyError,AssertionError):
    sys.exit(2)
PY
then
  echo "status=ABSTAIN_PRIOR_FAILED_BUILD_STATUS_UNAVAILABLE"
  exit 125
fi
if python3 -I -S tools/diagnostics/sanitize_docker_build_failure_v1.py \
     --input "$OLD/private-local/build.log" \
     --output "$OUT/build-failure-diagnostic.json"; then
  echo "status=PASS_SAFE_PRIOR_LOCAL_BUILD_LOG_CLASSIFICATION"
  echo "historical_attempt_log_binding_verified=false"
  echo "no_docker_build_run=true"
  echo "no_corpus_entity_read=true"
else
  echo "status=ABSTAIN_SAFE_PRIOR_LOG_CLASSIFICATION"
  exit 125
fi
