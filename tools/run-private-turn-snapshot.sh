#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "${1:-}" == "fetch" && -z "${PLANETSNU_API_KEY:-}" ]]; then
  echo "ERROR: PLANETSNU_API_KEY is not set." >&2
  echo "Load it into the environment without putting it on the command line." >&2
  exit 64
fi

if [[ -z "${PLANETSNU_PROXY_URL:-}" ]]; then
  export PLANETSNU_ALLOW_DIRECT="${PLANETSNU_ALLOW_DIRECT:-1}"
fi

compose=(docker compose -f compose.yaml)
"${compose[@]}" build lab >/dev/null

exec "${compose[@]}" run --rm -T   -e PLANETSNU_API_KEY   -e PLANETSNU_ALLOW_DIRECT   -e PLANETSNU_PROXY_URL   lab   python -m planets_lab.corpus.private_turn_snapshot_cli "$@"
