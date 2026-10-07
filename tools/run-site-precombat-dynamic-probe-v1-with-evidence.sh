#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

exec bash tools/run-with-runtime-evidence.sh   site-precombat-dynamic-probe-v1   --include artifacts/combat/site-precombat-dynamic-probe   --   bash tools/run-site-precombat-dynamic-probe-v1.sh
