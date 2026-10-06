#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

exec bash tools/run-with-runtime-evidence.sh   capture-resume-v593   --include artifacts/combat/capture-resume   --   bash tools/run-capture-resume-v593-gate.sh
