#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# New real corpus observation stage: dedicated exact wrapper, all safe files
# published through unchanged generic publisher even on ABSTAIN.
exec bash tools/run-with-runtime-evidence.sh \
  public100-baseline68-starbase-link-v1 \
  --include artifacts/corpus/public100-baseline68-starbase-link-v1/stage-status.json \
  --include artifacts/corpus/public100-baseline68-starbase-link-v1/baseline-cohort-attestation.json \
  --include artifacts/corpus/public100-baseline68-starbase-link-v1/pytest-counts.json \
  --include artifacts/corpus/public100-baseline68-starbase-link-v1/pytest-failed-modules.json \
  --include artifacts/corpus/public100-baseline68-starbase-link-v1/m2-deep-coverage.json \
  -- bash tools/run-public100-baseline68-starbase-link-v1.sh
