#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/diagnostics/combat_long_mass_survey_digest_v1.py --survey-summary artifacts/combat/long-mass-survey-v1/published/summary.json --checkpoint-dir artifacts/combat/long-mass-survey-v1/checkpoints --output artifacts/combat/long-mass-survey-digest-v1/published/digest.json
