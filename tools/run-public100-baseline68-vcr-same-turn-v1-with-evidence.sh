#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# NEW read-only same-turn perspective source experiment with independently
# tracked generic sanitized publisher even on early ABSTAIN.
exec bash tools/run-with-runtime-evidence.sh \
  public100-baseline68-vcr-same-turn-v1 \
  --include artifacts/corpus/public100-baseline68-vcr-same-turn-v1/stage-status.json \
  --include artifacts/corpus/public100-baseline68-vcr-same-turn-v1/build-failure-diagnostic.json \
  --include artifacts/corpus/public100-baseline68-vcr-same-turn-v1/baseline-cohort-attestation.json \
  --include artifacts/corpus/public100-baseline68-vcr-same-turn-v1/pytest-counts.json \
  --include artifacts/corpus/public100-baseline68-vcr-same-turn-v1/pytest-failed-modules.json \
  --include artifacts/corpus/public100-baseline68-vcr-same-turn-v1/m2-deep-coverage.json \
  -- bash tools/run-public100-baseline68-vcr-same-turn-v1.sh
