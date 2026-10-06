#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

exec bash tools/run-with-runtime-evidence.sh   postcapture-site-transition-chain   --include artifacts/external-sources/postcapture-site-transition   --   bash tools/research/run-postcapture-site-transition-chain.sh
