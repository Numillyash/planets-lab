#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
external_checkout="${PLANETS_EXTERNAL_CHECKOUT:-$HOME/projects/planets-lab-external}"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to the shared host corpus DB directory}"

if [[ ! -f "$external_checkout/compose.yaml" ]]; then
    echo "external checkout compose.yaml not found: $external_checkout/compose.yaml" >&2
    exit 2
fi

reader_code=$(cat <<'PY'
from pathlib import Path
import os
import time
import duckdb

root = Path(os.environ["PLANETS_CORPUS_DB_ROOT"])
value = (root / "CURRENT").read_text(encoding="utf-8").strip()
database = (root / value).resolve()
connection = duckdb.connect(str(database), read_only=True)
try:
    first = connection.execute("SELECT count(*) FROM source_members").fetchone()[0]
    print(f"READY database={database.name} source_members={first}", flush=True)
    time.sleep(3)
    second = connection.execute("SELECT count(*) FROM source_members").fetchone()[0]
    if second != first:
        raise SystemExit(f"source_members changed while generation should be immutable: {first} -> {second}")
    print(f"OK database={database.name} source_members={second}", flush=True)
finally:
    connection.close()
PY
)

normal_log="$(mktemp)"
external_log="$(mktemp)"
cleanup() {
    rm -f "$normal_log" "$external_log"
}
trap cleanup EXIT

(
    cd "$repo_root"
    docker compose \
        -f compose.yaml \
        -f compose.corpus-db.yaml \
        run --rm -T lab python -c "$reader_code"
) >"$normal_log" 2>&1 &
normal_pid=$!

(
    cd "$external_checkout"
    docker compose \
        -f compose.yaml \
        -f "$repo_root/compose.corpus-db.yaml" \
        run --rm -T lab python -c "$reader_code"
) >"$external_log" 2>&1 &
external_pid=$!

status=0
wait "$normal_pid" || status=1
wait "$external_pid" || status=1

printf '%s\n' '===== NORMAL planets-lab READER ====='
cat "$normal_log"
printf '%s\n' '===== EXTERNAL research READER ====='
cat "$external_log"

if [[ "$status" -ne 0 ]]; then
    echo "concurrent shared read check failed" >&2
    exit 1
fi

echo "shared_generation_concurrent_read: PASS"