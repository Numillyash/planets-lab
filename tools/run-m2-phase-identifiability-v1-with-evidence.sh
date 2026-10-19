#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# Fixed fake fixture, no external state/order files, no credentials,
# no historic corpus. Only aggregate synthetic model outcomes enter logs.
exec bash tools/run-with-runtime-evidence.sh \
  m2-phase-identifiability-synthetic-v1 \
  -- python3 tools/diagnostics/m2_phase_identifiability_v1.py
