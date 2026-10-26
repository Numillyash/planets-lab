#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# NEW distinct, read-only VCR missingness joint study with unchanged generic
# evidence publisher; count-only JSON/status/log/exit/SHA even on ABSTAIN.
exec bash tools/run-with-runtime-evidence.sh \
  public100-baseline68-vcr-missingness-joint-v2 \
  --include artifacts/corpus/public100-baseline68-vcr-missingness-joint-v2/stage-status.json \
  --include artifacts/corpus/public100-baseline68-vcr-missingness-joint-v2/build-failure-diagnostic.json \
  --include artifacts/corpus/public100-baseline68-vcr-missingness-joint-v2/baseline-cohort-attestation.json \
  --include artifacts/corpus/public100-baseline68-vcr-missingness-joint-v2/pytest-counts.json \
  --include artifacts/corpus/public100-baseline68-vcr-missingness-joint-v2/pytest-failed-modules.json \
  --include artifacts/corpus/public100-baseline68-vcr-missingness-joint-v2/m2-deep-coverage.json \
  -- bash tools/run-public100-baseline68-vcr-missingness-joint-v2.sh
