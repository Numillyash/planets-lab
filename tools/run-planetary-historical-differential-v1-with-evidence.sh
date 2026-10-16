#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
 planetary-historical-differential-v1 \
 --include artifacts/planetary/historical-differential-v1/published \
 -- bash tools/run-planetary-historical-differential-v1.sh
