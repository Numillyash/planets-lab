#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

exec bash tools/run-with-runtime-evidence.sh   mutable-capture-site-loop-v1   --include artifacts/combat/mutable-site-loop   --   bash tools/run-mutable-capture-site-loop-v1.sh
