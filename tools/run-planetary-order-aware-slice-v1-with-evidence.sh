#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh planetary-order-aware-slice-v1 \
 --include artifacts/planetary/order-aware-slice-v1/published \
 -- bash tools/run-planetary-order-aware-slice-v1.sh
