#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# Synthetic source only, no cargo archives, passwords, order envelopes or
# private game data. Runtime evidence is an aggregate log with source SHA.
exec bash tools/run-with-runtime-evidence.sh \
  m2-starbase-tech-synthetic-v1 \
  -- python3 tools/diagnostics/m2_starbase_tech_synthetic_gate_v1.py
