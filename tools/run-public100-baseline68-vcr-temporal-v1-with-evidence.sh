#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Dedicated VCR source-only corpus experiment, generic evidence publisher
# emits sanitized count-only report/status, source SHA and outer log EVEN ABSTAIN.
exec bash tools/run-with-runtime-evidence.sh \
  public100-baseline68-vcr-temporal-v1 \
  --include artifacts/corpus/public100-baseline68-vcr-temporal-v1/stage-status.json \
  --include artifacts/corpus/public100-baseline68-vcr-temporal-v1/build-failure-diagnostic.json \
  --include artifacts/corpus/public100-baseline68-vcr-temporal-v1/baseline-cohort-attestation.json \
  --include artifacts/corpus/public100-baseline68-vcr-temporal-v1/pytest-counts.json \
  --include artifacts/corpus/public100-baseline68-vcr-temporal-v1/pytest-failed-modules.json \
  --include artifacts/corpus/public100-baseline68-vcr-temporal-v1/m2-deep-coverage.json \
  -- bash tools/run-public100-baseline68-vcr-temporal-v1.sh
