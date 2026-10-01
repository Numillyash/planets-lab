#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to an absolute host path outside the checkout}"

manifest="${CORPUS_DB_COMPACT_MANIFEST:-validation/corpus/manifests/public-validation-selected.jsonl}"
cache_dir="${CORPUS_DB_COMPACT_CACHE_DIR:-validation/corpus/cache/loadall}"

if [[ ! -f "$manifest" ]]; then
    echo "manifest not found: $manifest" >&2
    exit 2
fi
if [[ ! -d "$cache_dir" ]]; then
    echo "cache directory not found: $cache_dir" >&2
    exit 2
fi

mkdir -p "$PLANETS_CORPUS_DB_ROOT"/{generations,manifests,staging}

min_free_gib="${CORPUS_DB_COMPACT_PUBLIC_MIN_FREE_GIB:-30}"
if ! [[ "$min_free_gib" =~ ^[1-9][0-9]*$ ]]; then
    echo "CORPUS_DB_COMPACT_PUBLIC_MIN_FREE_GIB must be a positive integer" >&2
    exit 2
fi
available_bytes="$(df -PB1 "$PLANETS_CORPUS_DB_ROOT" | awk 'NR==2 {print $4}')"
required_bytes="$((min_free_gib * 1024 * 1024 * 1024))"
if (( available_bytes < required_bytes )); then
    echo "insufficient free space for public36 compact build" >&2
    echo "available_bytes=$available_bytes" >&2
    echo "required_bytes=$required_bytes (${min_free_gib} GiB)" >&2
    exit 2
fi

before_current=""
if [[ -f "$PLANETS_CORPUS_DB_ROOT/CURRENT" ]]; then
    before_current="$(cat "$PLANETS_CORPUS_DB_ROOT/CURRENT")"
fi

repo_real="$(realpath -m "$repo_root")"
manifest_real="$(realpath -m "$manifest")"
cache_real="$(realpath -m "$cache_dir")"
case "$manifest_real/" in
    "$repo_real/"*) manifest_container="/workspace/${manifest_real#"$repo_real/"}" ;;
    *)
        echo "manifest must be under checkout: $manifest_real" >&2
        exit 2
        ;;
esac
case "$cache_real/" in
    "$repo_real/"*) cache_container="/workspace/${cache_real#"$repo_real/"}" ;;
    *)
        echo "cache dir must be under checkout: $cache_real" >&2
        exit 2
        ;;
esac

compose=(docker compose -f compose.yaml -f compose.corpus-db.yaml)

printf '%s\n' '===== CORPUS DB V2 COMPACT: PUBLIC36 RESUMABLE BUILD + FULL PARITY ====='
printf 'manifest=%s\n' "$manifest"
printf 'cache_dir=%s\n' "$cache_dir"
printf 'resume_db=%s\n' "$PLANETS_CORPUS_DB_ROOT/staging/compact-public36-resume.duckdb"
printf 'schema_checkpoints=%s\n' "$PLANETS_CORPUS_DB_ROOT/staging/compact-public36-resume-schema"

"${compose[@]}" --profile corpus-db-writer run --rm -T corpus-db-importer     python -m planets_lab.corpus.corpus_db_compact_multi_cli build     --manifest "$manifest_container"     --cache-dir "$cache_container"     --expected-count 36     --state-name compact-public36-resume

after_current=""
if [[ -f "$PLANETS_CORPUS_DB_ROOT/CURRENT" ]]; then
    after_current="$(cat "$PLANETS_CORPUS_DB_ROOT/CURRENT")"
fi
if [[ "$before_current" != "$after_current" ]]; then
    echo "ERROR: compact public36 gate unexpectedly changed CURRENT" >&2
    echo "before: $before_current" >&2
    echo "after:  $after_current" >&2
    exit 1
fi

compact_host="$(
    find "$PLANETS_CORPUS_DB_ROOT/generations"         -maxdepth 1 -type f         -name 'corpus-v2compact-public36-*.duckdb'         -printf '%T@ %p\n'       | sort -nr       | head -n1       | cut -d' ' -f2-
)"
if [[ -z "$compact_host" || ! -f "$compact_host" ]]; then
    echo "published public36 compact generation not found" >&2
    exit 2
fi
compact_name="$(basename "$compact_host")"
compact_container="/corpus-db/generations/$compact_name"

printf '%s\n' '===== PUBLIC36 COMPACT GENERATION STATS ====='
"${compose[@]}" run --rm -T lab     python -m planets_lab.corpus.corpus_db_compact_multi_cli stats     --database "$compact_container"

printf '%s\n' '===== PUBLIC36 COMPACT PHYSICAL CHECK ====='
"${compose[@]}" run --rm -T lab python - "$compact_container" <<'PY'
from pathlib import Path
import sys
import duckdb

db = Path(sys.argv[1])
con = duckdb.connect(str(db), read_only=True)
try:
    tables = {
        row[0]
        for row in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='main' AND table_type='BASE TABLE'"
        ).fetchall()
    }
    source_columns = {
        row[0]
        for row in con.execute("DESCRIBE source_members").fetchall()
    }
    print("database:", db.name)
    print("source_archives:", con.execute("SELECT count(*) FROM source_archives").fetchone()[0])
    print("source_members:", con.execute("SELECT count(*) FROM source_members").fetchone()[0])
    print("entity_rows_present:", "entity_rows" in tables)
    print("decoded_payload_zlib_present:", "decoded_payload_zlib" in source_columns)
    print("secondary_indexes:", con.execute("SELECT count(*) FROM duckdb_indexes()").fetchone()[0])
finally:
    con.close()
PY

printf '%s\n' '===== PUBLIC36 COMPACT T-1/T QUERY: GAME 233558 ====='
"${compose[@]}" run --rm -T lab     python -m planets_lab.corpus.corpus_db_compact_cli benchmark     --database "$compact_container"     --kind turn-pair --game-id 233558

printf '%s\n' '===== PUBLIC36 COMPACT VCR/SITE QUERY: GAME 233558 ====='
"${compose[@]}" run --rm -T lab     python -m planets_lab.corpus.corpus_db_compact_cli benchmark     --database "$compact_container"     --kind vcr-site --game-id 233558

printf '%s\n' '===== SAME PUBLIC36 COMPACT GENERATION: TWO CONCURRENT READ-ONLY CONTAINERS ====='
export CORPUS_DB_EXPLICIT_RELATIVE="generations/$compact_name"
bash tools/run-corpus-db-explicit-shared-read-check.sh

printf '%s\n' '===== CURRENT PRESERVED ====='
printf 'CURRENT=%s\n' "$after_current"
printf 'compact_generation=%s\n' "$compact_host"
printf '%s\n' 'If interrupted, rerun this same script. Schema, import and parity checkpoints are reused.'
