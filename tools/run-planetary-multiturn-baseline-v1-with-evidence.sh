#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh \
 planetary-multiturn-baseline-v1 \
 --include artifacts/planetary/multiturn-baseline-v1/published \
 -- bash tools/run-planetary-multiturn-baseline-v1.sh
