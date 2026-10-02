#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to the shared host corpus DB directory}"

generation_rel="${1:-generations/corpus-v2compact-public36-20261002T083138Z-11cd75fa918d.duckdb}"
expected_sha="${2:-e1c0adc0a699d9d776f1fddb7dfc37c5a6714dfd9262f911a5939fda41cc7004}"
expected_schema="${CORPUS_DB_ACTIVATE_SCHEMA:-planets-lab.corpus-db.v2.compact1}"
expected_archives="${CORPUS_DB_ACTIVATE_ARCHIVES:-36}"
expected_members="${CORPUS_DB_ACTIVATE_MEMBERS:-126418}"
expected_fingerprint="${CORPUS_DB_ACTIVATE_FINGERPRINT:-11cd75fa918dec3d6839f6dbdcb3537bcb66d6f4c9d935f1866003998aab9e42}"

case "$generation_rel" in
    generations/*.duckdb) ;;
    *)
        echo "generation must be generations/<name>.duckdb" >&2
        exit 2
        ;;
esac
case "$generation_rel" in
    *"/../"*|../*|*/..)
        echo "generation path must not contain '..'" >&2
        exit 2
        ;;
esac
if ! [[ "$expected_sha" =~ ^[0-9a-fA-F]{64}$ ]]; then
    echo "expected SHA256 must be exactly 64 hexadecimal characters" >&2
    exit 2
fi
if ! [[ "$expected_archives" =~ ^[1-9][0-9]*$ ]]; then
    echo "CORPUS_DB_ACTIVATE_ARCHIVES must be a positive integer" >&2
    exit 2
fi
if ! [[ "$expected_members" =~ ^[1-9][0-9]*$ ]]; then
    echo "CORPUS_DB_ACTIVATE_MEMBERS must be a positive integer" >&2
    exit 2
fi
if ! [[ "$expected_fingerprint" =~ ^[0-9a-fA-F]{64}$ ]]; then
    echo "CORPUS_DB_ACTIVATE_FINGERPRINT must be exactly 64 hexadecimal characters" >&2
    exit 2
fi

root_real="$(realpath -m "$PLANETS_CORPUS_DB_ROOT")"
target_host="$(realpath -m "$PLANETS_CORPUS_DB_ROOT/$generation_rel")"
case "$target_host/" in
    "$root_real/generations/"*) ;;
    *)
        echo "target generation resolves outside <root>/generations" >&2
        exit 2
        ;;
esac
if [[ ! -f "$target_host" ]]; then
    echo "target generation not found: $target_host" >&2
    exit 2
fi

current_file="$PLANETS_CORPUS_DB_ROOT/CURRENT"
if [[ ! -f "$current_file" ]]; then
    echo "CURRENT not found: $current_file" >&2
    exit 2
fi
before_current="$(tr -d '\r\n' < "$current_file")"
if [[ -z "$before_current" ]]; then
    echo "CURRENT is empty" >&2
    exit 2
fi
before_host="$(realpath -m "$PLANETS_CORPUS_DB_ROOT/$before_current")"
if [[ ! -f "$before_host" ]]; then
    echo "CURRENT target does not exist: $before_host" >&2
    exit 2
fi

printf '%s\n' '===== COMPACT CURRENT ACTIVATION: PRECHECK ====='
printf 'old_current=%s\n' "$before_current"
printf 'new_current=%s\n' "$generation_rel"
printf 'target=%s\n' "$target_host"

actual_sha="$(sha256sum "$target_host" | awk '{print $1}')"
printf 'target_sha256=%s\n' "$actual_sha"
if [[ "${actual_sha,,}" != "${expected_sha,,}" ]]; then
    echo "target SHA256 mismatch" >&2
    echo "expected=$expected_sha" >&2
    echo "actual=$actual_sha" >&2
    exit 1
fi

compose=(docker compose -f compose.yaml -f compose.corpus-db.yaml)
target_container="/corpus-db/$generation_rel"

"${compose[@]}" run --rm -T lab python -     "$target_container"     "$expected_schema"     "$expected_archives"     "$expected_members"     "$expected_fingerprint" <<'PY'
from pathlib import Path
import sys
import duckdb

database = Path(sys.argv[1])
expected_schema = sys.argv[2]
expected_archives = int(sys.argv[3])
expected_members = int(sys.argv[4])
expected_fingerprint = sys.argv[5]

connection = duckdb.connect(str(database), read_only=True)
try:
    schema_row = connection.execute(
        "SELECT schema_version FROM corpus_metadata"
    ).fetchone()
    if schema_row is None or schema_row[0] != expected_schema:
        raise SystemExit(
            f"schema mismatch: expected={expected_schema!r} actual={schema_row!r}"
        )

    archives = int(
        connection.execute("SELECT count(*) FROM source_archives").fetchone()[0]
    )
    members = int(
        connection.execute("SELECT count(*) FROM source_members").fetchone()[0]
    )
    if archives != expected_archives:
        raise SystemExit(
            f"archive count mismatch: expected={expected_archives} actual={archives}"
        )
    if members != expected_members:
        raise SystemExit(
            f"member count mismatch: expected={expected_members} actual={members}"
        )

    state = connection.execute(
        "SELECT corpus_fingerprint, expected_archive_count "
        "FROM compact_build_state"
    ).fetchone()
    if state is None:
        raise SystemExit("compact_build_state is absent")
    if str(state[0]) != expected_fingerprint:
        raise SystemExit(
            "corpus fingerprint mismatch: "
            f"expected={expected_fingerprint} actual={state[0]}"
        )
    if int(state[1]) != expected_archives:
        raise SystemExit(
            "compact build archive count mismatch: "
            f"expected={expected_archives} actual={state[1]}"
        )

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='main' AND table_type='BASE TABLE'"
        ).fetchall()
    }
    source_columns = {
        row[0]
        for row in connection.execute("DESCRIBE source_members").fetchall()
    }
    index_count = int(
        connection.execute("SELECT count(*) FROM duckdb_indexes()").fetchone()[0]
    )
    if "entity_rows" in tables:
        raise SystemExit("compact invariant failed: entity_rows exists")
    if "decoded_payload_zlib" in source_columns:
        raise SystemExit(
            "compact invariant failed: decoded_payload_zlib exists"
        )
    if index_count != 0:
        raise SystemExit(
            f"compact invariant failed: secondary index count={index_count}"
        )

    print(
        "PRECHECK PASS "
        f"schema={expected_schema} archives={archives} members={members} "
        f"fingerprint={state[0]} indexes={index_count}",
        flush=True,
    )
finally:
    connection.close()
PY

atomic_set_current() {
    local value="$1"
    local tmp="$PLANETS_CORPUS_DB_ROOT/.CURRENT.activate.$$"
    printf '%s\n' "$value" > "$tmp"
    mv -f "$tmp" "$current_file"
}

if [[ "$before_current" == "$generation_rel" ]]; then
    echo "CURRENT already points to requested compact generation"
    bash tools/run-corpus-db-shared-read-check.sh
    echo "compact_current_activation: ALREADY_ACTIVE_AND_VERIFIED"
    exit 0
fi

printf '%s\n' '===== COMPACT CURRENT ACTIVATION: SWITCH ====='
atomic_set_current "$generation_rel"
printf 'CURRENT=%s\n' "$(cat "$current_file")"

printf '%s\n' '===== COMPACT CURRENT ACTIVATION: SHARED READ VERIFY ====='
if bash tools/run-corpus-db-shared-read-check.sh; then
    echo "compact_current_activation: PASS"
    echo "rollback_generation=$before_current"
    exit 0
fi

echo "compact shared-read verification failed; rolling CURRENT back" >&2
atomic_set_current "$before_current"
printf 'ROLLED_BACK_CURRENT=%s\n' "$(cat "$current_file")" >&2

printf '%s\n' '===== COMPACT CURRENT ACTIVATION: ROLLBACK VERIFY =====' >&2
if bash tools/run-corpus-db-shared-read-check.sh; then
    echo "compact_current_activation: FAILED_AND_ROLLED_BACK" >&2
    exit 1
fi

echo "CRITICAL: compact activation failed and rollback shared-read verification also failed" >&2
echo "CURRENT=$before_current" >&2
exit 3
