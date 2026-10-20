#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if ! command -v node >/dev/null 2>&1; then
    echo "ABSTAIN_NODE_RUNTIME_UNAVAILABLE"
    exit 2
fi
# Uses fake transport, fake payloads and fake clock only; never touches
# the user's browser, corpus, keys, account or Host state.
exec bash tools/run-with-runtime-evidence.sh \
  m2-save-ready-metadata-synthetic-v1 \
  -- node tests/js/test_planets_nu_save_ready_metadata_v1.cjs
