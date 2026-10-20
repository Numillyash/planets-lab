#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# Only the fake Node browser fixture may enter public runtime-logs.
# A real --private-bundle must NEVER be passed to this wrapper.
exec bash tools/run-with-runtime-evidence.sh \
  m2-client-sequence-audit-synthetic-v1 \
  -- python3 tools/diagnostics/m2_client_sequence_audit_v1.py --synthetic
