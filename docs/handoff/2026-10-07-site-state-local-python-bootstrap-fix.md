# Site-state local Python bootstrap fix

Date: 2026-10-07

## Triggering runtime evidence

Source commit:

    9f639f07b32993970a4042830281cdd85b9b78ca

Runtime evidence:

    runtime-logs/site-combat-input-adapter-v1/
    20261006T235752Z_9f639f07b329

Observed exit:

    exit_code 70

The run did not reach the combat differential. It failed during local runtime
preparation because the host has no Python >=3.11.

Observed host behavior:

    no compatible host Python found
    cached Python 3.10 venv removed
    empty python_bin then reached "-m venv"
    : command not found
    runtime venv missing

This is infrastructure-only. No mechanics comparator was opened.

## Root cause

The runner used:

    python_bin="$(select_local_python)"

inside a shell with set -e, but the failing command substitution did not stop the
function in this context. The runner then continued with an empty python_bin.

A second shell edge was also fixed: failure status from a negated bootstrap
command must not be returned through "$?" after "!".

## Fix

tools/run-site-combat-state-v1.sh now:

1. still prefers an already-installed Python 3.12, then 3.11, then compatible
   python3;
2. still rejects an explicitly configured incompatible
   PLANETS_SITE_STATE_RUNTIME_PYTHON;
3. if automatic selection finds no Python >=3.11, bootstraps an isolated
   managed Python 3.12;
4. uses the existing host python3 only to create a small uv bootstrap venv;
5. installs uv into:

       ~/.cache/planets-lab/site-state-bootstrap-uv

6. asks uv to install managed Python 3.12 under:

       ~/.cache/planets-lab/python

7. uses that Python directly if duckdb/pyarrow are already available, otherwise
   creates/rebuilds the normal project runtime venv:

       ~/.cache/planets-lab/site-state-v1

No system Python, apt packages, /usr/bin links, or combat mechanics are changed.

## Overrides

Optional paths remain configurable:

    PLANETS_SITE_STATE_RUNTIME_PYTHON
    PLANETS_SITE_STATE_RUNTIME_VENV
    PLANETS_SITE_STATE_BOOTSTRAP_VENV
    PLANETS_SITE_STATE_MANAGED_PYTHON_DIR

Explicit PLANETS_SITE_STATE_RUNTIME_PYTHON remains fail-closed: if the user
points it at Python 3.10, the runner does not silently replace that explicit
choice with a managed runtime.

## Tests

tests/test_site_combat_state_runtime_fallback.py now covers:

- shell syntax;
- Docker -> local fallback;
- explicit local mode avoiding Docker;
- explicit Python 3.10 rejection;
- incompatible cached runtime-venv rebuild;
- no-host-Python>=3.11 path bootstrapping managed Python 3.12 through a fully
  isolated fake uv fixture;
- regression against the prior ": command not found" / missing-venv failure.

## Next runtime action

After this fix reaches main:

    cd ~/projects/planets-lab
    git switch main
    git pull --ff-only origin main

    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db

    bash tools/run-site-combat-input-adapter-v1-with-evidence.sh

Expected successful mechanics result remains:

    SITE_STATE_EXACT
    3/3

followed by:

    SITE_INPUT_ADAPTER_EXACT

The runtime wrapper will publish the new evidence under:

    runtime-logs/site-combat-input-adapter-v1/
