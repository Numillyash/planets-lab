#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

exec bash tools/run-with-runtime-evidence.sh   postcapture-o-c-forward-independent   --include artifacts/external-sources/postcapture-occurrence/fresh32-independent   --   bash tools/research/run-postcapture-o-c-forward-independent.sh
