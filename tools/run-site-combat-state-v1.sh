#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to the shared corpus DB root}"

PUBLIC100_REL="${PUBLIC100_REL:-generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb}"
PUBLIC100_SHA="${PUBLIC100_SHA:-3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c}"
OUTPUT="${OUTPUT:-artifacts/combat/site-state/game400330-t141-v592-595.json}"
RUNTIME_MODE="${PLANETS_SITE_STATE_RUNTIME_MODE:-auto}"
RUNTIME_VENV="${PLANETS_SITE_STATE_RUNTIME_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/planets-lab/site-state-v1}"

db="$PLANETS_CORPUS_DB_ROOT/$PUBLIC100_REL"
if [[ ! -f "$db" ]]; then
  echo "ERROR: public100 generation missing: $db" >&2
  exit 66
fi
actual_sha="$(sha256sum "$db" | awk '{print $1}')"
if [[ "$actual_sha" != "$PUBLIC100_SHA" ]]; then
  echo "ERROR: public100 SHA mismatch" >&2
  echo "expected: $PUBLIC100_SHA" >&2
  echo "actual:   $actual_sha" >&2
  exit 66
fi

echo "===== SITE COMBAT STATE DIFFERENTIAL V1 ====="
echo "HEAD:      $(git rev-parse HEAD)"
echo "public100: $PUBLIC100_REL"
echo "sha256:    $actual_sha"
echo "runtime:   $RUNTIME_MODE"

run_docker_gate() {
  docker compose -f compose.yaml -f compose.corpus-db.yaml run --rm -T \
    -e PYTHONPATH=/workspace/src:/workspace/tools/diagnostics \
    lab \
    python tools/diagnostics/combat_site_state_differential_v1.py \
      --corpus-db-root /corpus-db \
      --corpus-db-generation "$PUBLIC100_REL" \
      --game-id 400330 \
      --battle-turn 141 \
      --x 1674 \
      --y 2363 \
      --start-vcr-id 592 \
      --end-vcr-id 595 \
      --output "$OUTPUT"
}

python_is_compatible() {
  local python_bin="$1"
  "$python_bin" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1
}

select_local_python() {
  local configured="${PLANETS_SITE_STATE_RUNTIME_PYTHON:-}"

  if [[ -n "$configured" ]]; then
    if ! command -v "$configured" >/dev/null 2>&1; then
      echo "ERROR: configured host Python not found: $configured" >&2
      return 69
    fi
    if ! python_is_compatible "$configured"; then
      echo "ERROR: configured host Python is too old; planets-lab requires Python >=3.11: $configured" >&2
      return 69
    fi
    printf '%s\n' "$configured"
    return 0
  fi

  local candidate
  for candidate in python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && python_is_compatible "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  echo "ERROR: no compatible host Python found; planets-lab requires Python >=3.11." >&2
  echo "Install python3.11+ or restore Docker/containerd, then rerun." >&2
  return 69
}

prepare_local_python() {
  local python_bin
  python_bin="$(select_local_python)"

  if "$python_bin" - <<'PY' >/dev/null 2>&1
import duckdb, pyarrow
PY
  then
    printf '%s\n' "$python_bin"
    return 0
  fi

  echo "host python is missing runtime dependencies; preparing cached venv: $RUNTIME_VENV" >&2

  if [[ -x "$RUNTIME_VENV/bin/python" ]] && ! python_is_compatible "$RUNTIME_VENV/bin/python"; then
    echo "cached venv uses incompatible Python; rebuilding: $RUNTIME_VENV" >&2
    rm -rf "$RUNTIME_VENV"
  fi

  if [[ ! -x "$RUNTIME_VENV/bin/python" ]]; then
    mkdir -p "$(dirname "$RUNTIME_VENV")"
    "$python_bin" -m venv "$RUNTIME_VENV"
  fi

  if ! "$RUNTIME_VENV/bin/python" - <<'PY' >/dev/null 2>&1
import duckdb, pyarrow
PY
  then
    "$RUNTIME_VENV/bin/python" -m pip install --disable-pip-version-check -e "$ROOT" 1>&2
  fi

  if ! "$RUNTIME_VENV/bin/python" - <<'PY' >/dev/null 2>&1
import duckdb, pyarrow
PY
  then
    echo "ERROR: cached host runtime still lacks duckdb/pyarrow after installation: $RUNTIME_VENV" >&2
    return 70
  fi

  printf '%s\n' "$RUNTIME_VENV/bin/python"
}

run_local_gate() {
  local python_bin
  python_bin="$(prepare_local_python)"
  echo "runtime_selected: host-python"
  echo "runtime_python:   $python_bin"
  PYTHONPATH="$ROOT/src:$ROOT/tools/diagnostics" \
    "$python_bin" tools/diagnostics/combat_site_state_differential_v1.py \
      --corpus-db-root "$PLANETS_CORPUS_DB_ROOT" \
      --corpus-db-generation "$PUBLIC100_REL" \
      --game-id 400330 \
      --battle-turn 141 \
      --x 1674 \
      --y 2363 \
      --start-vcr-id 592 \
      --end-vcr-id 595 \
      --output "$OUTPUT"
}

case "$RUNTIME_MODE" in
  docker)
    echo "runtime_selected: docker"
    docker info >/dev/null
    docker compose -f compose.yaml -f compose.corpus-db.yaml build lab
    run_docker_gate
    ;;
  local)
    run_local_gate
    ;;
  auto)
    if timeout 20s docker info >/dev/null 2>&1 \
      && docker compose -f compose.yaml -f compose.corpus-db.yaml build lab
    then
      echo "runtime_selected: docker"
      run_docker_gate
    else
      echo "WARNING: Docker/containerd preflight or build failed; falling back to host Python." >&2
      run_local_gate
    fi
    ;;
  *)
    echo "ERROR: unsupported PLANETS_SITE_STATE_RUNTIME_MODE=$RUNTIME_MODE (expected auto|docker|local)" >&2
    exit 64
    ;;
esac

echo "output: $OUTPUT"
