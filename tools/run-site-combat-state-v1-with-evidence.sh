#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

exec bash tools/run-with-runtime-evidence.sh   site-combat-state-v1   --include artifacts/combat/site-state   --   bash tools/run-site-combat-state-v1.sh
