#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec bash tools/run-with-runtime-evidence.sh combat-long-mass-survey-digest-v1 --include artifacts/combat/long-mass-survey-digest-v1/published -- bash tools/run-combat-long-mass-survey-digest-v1.sh
