#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec bash tools/run-with-runtime-evidence.sh planetary-owner-capture-bundle-v1 \
 --include artifacts/planetary/owner-capture-bundle-v1/published \
 -- bash tools/run-planetary-owner-capture-bundle-v1.sh
