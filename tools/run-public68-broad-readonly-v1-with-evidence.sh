#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# Reuse the exact generic publisher, including failed/ABSTAIN status. Never
# upload raw DuckDB/source members/local Docker logs or private orders.
exec bash tools/run-with-runtime-evidence.sh \
  public68-broad-readonly-census-v1 \
  --include artifacts/corpus/public68-broad-readonly-v1/report.json \
  --include artifacts/corpus/public68-broad-readonly-v1/suite-status.json \
  -- bash tools/run-public68-broad-readonly-v1.sh
