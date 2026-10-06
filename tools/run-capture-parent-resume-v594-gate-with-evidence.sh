#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

exec bash tools/run-with-runtime-evidence.sh   capture-parent-resume-v594   --include artifacts/combat/capture-resume   --   bash tools/run-capture-parent-resume-v594-gate.sh
