#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# New local-log diagnostic, NOT a Host experiment. The existing generic
# publisher emits source SHA / sanitized evidence even on ABSTAIN.
exec bash tools/run-with-runtime-evidence.sh \
  public100-baseline68-vcr-build-diagnosis-v1 \
  --include artifacts/corpus/public100-baseline68-vcr-build-diagnosis-v1/build-failure-diagnostic.json \
  -- bash tools/run-public100-baseline68-vcr-existing-build-log-v1.sh
