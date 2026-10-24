#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Generic publisher copies ONLY these fixed-shape aggregate files;
# local pytest logs/JUnit, raw archived members and raw M2 snapshots NEVER upload.
exec bash tools/run-with-runtime-evidence.sh \
  public100-baseline68-identity-v5 \
  --include artifacts/corpus/public100-baseline68-identity-v5/stage-status.json \
  --include artifacts/corpus/public100-baseline68-identity-v5/baseline-cohort-attestation.json \
  --include artifacts/corpus/public100-baseline68-identity-v5/pytest-counts.json \
  --include artifacts/corpus/public100-baseline68-identity-v5/pytest-failed-modules.json \
  --include artifacts/corpus/public100-baseline68-identity-v5/m2-deep-coverage.json \
  -- bash tools/run-public100-baseline68-identity-v5.sh
