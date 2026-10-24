#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Exactly the generic publisher, sanitized count-only artifacts, even on ABSTAIN.
exec bash tools/run-with-runtime-evidence.sh \
  public100-baseline68-mine-joint-v6 \
  --include artifacts/corpus/public100-baseline68-mine-joint-v6/stage-status.json \
  --include artifacts/corpus/public100-baseline68-mine-joint-v6/baseline-cohort-attestation.json \
  --include artifacts/corpus/public100-baseline68-mine-joint-v6/pytest-counts.json \
  --include artifacts/corpus/public100-baseline68-mine-joint-v6/pytest-failed-modules.json \
  --include artifacts/corpus/public100-baseline68-mine-joint-v6/m2-deep-coverage.json \
  -- bash tools/run-public100-baseline68-mine-joint-v6.sh
