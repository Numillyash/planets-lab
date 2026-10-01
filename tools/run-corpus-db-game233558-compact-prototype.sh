#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to an absolute host path outside the checkout}"

archive="${1:-validation/corpus/cache/loadall/game-233558.zip}"
if [[ ! -f "$archive" ]]; then
    echo "archive not found: $archive" >&2
    exit 2
fi

repo_real="$(realpath -m "$repo_root")"
archive_real="$(realpath -m "$archive")"
case "$archive_real/" in
    "$repo_real/"*) archive_container="/workspace/${archive_real#"$repo_real/"}" ;;
    *)
        echo "compact prototype archive must be under the checkout: $archive_real" >&2
        exit 2
        ;;
esac

mkdir -p "$PLANETS_CORPUS_DB_ROOT"/{generations,manifests,staging}

min_free_gib="${CORPUS_DB_COMPACT_MIN_FREE_GIB:-4}"
if ! [[ "$min_free_gib" =~ ^[1-9][0-9]*$ ]]; then
    echo "CORPUS_DB_COMPACT_MIN_FREE_GIB must be a positive integer" >&2
    exit 2
fi
available_bytes="$(df -PB1 "$PLANETS_CORPUS_DB_ROOT" | awk 'NR==2 {print $4}')"
required_bytes="$((min_free_gib * 1024 * 1024 * 1024))"
if (( available_bytes < required_bytes )); then
    echo "insufficient free space for compact prototype" >&2
    echo "available_bytes=$available_bytes" >&2
    echo "required_bytes=$required_bytes (${min_free_gib} GiB)" >&2
    echo "free or relocate superseded derived DB generations before retrying" >&2
    exit 2
fi

before_current=""
if [[ -f "$PLANETS_CORPUS_DB_ROOT/CURRENT" ]]; then
    before_current="$(cat "$PLANETS_CORPUS_DB_ROOT/CURRENT")"
fi

compose=(docker compose -f compose.yaml -f compose.corpus-db.yaml)

printf '%s\n' '===== CORPUS DB V2 COMPACT: BUILD + FULL MEMBER PARITY ====='
"${compose[@]}" --profile corpus-db-writer run --rm -T corpus-db-importer     python -m planets_lab.corpus.corpus_db_compact_cli build     "$archive_container" --game-id 233558

after_current=""
if [[ -f "$PLANETS_CORPUS_DB_ROOT/CURRENT" ]]; then
    after_current="$(cat "$PLANETS_CORPUS_DB_ROOT/CURRENT")"
fi
if [[ "$before_current" != "$after_current" ]]; then
    echo "ERROR: compact prototype unexpectedly changed CURRENT" >&2
    echo "before: $before_current" >&2
    echo "after:  $after_current" >&2
    exit 1
fi

compact_host="$(
    find "$PLANETS_CORPUS_DB_ROOT/generations"         -maxdepth 1 -type f         -name 'corpus-v2compact-g233558-*.duckdb'         -printf '%T@ %p\n'       | sort -nr       | head -n1       | cut -d' ' -f2-
)"
if [[ -z "$compact_host" || ! -f "$compact_host" ]]; then
    echo "published compact generation not found" >&2
    exit 2
fi
compact_name="$(basename "$compact_host")"
compact_container="/corpus-db/generations/$compact_name"

printf '%s\n' '===== COMPACT GENERATION STATS ====='
"${compose[@]}" run --rm -T lab     python -m planets_lab.corpus.corpus_db_compact_cli stats     --database "$compact_container"

printf '%s\n' '===== COMPACT PHYSICAL CHECK ====='
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
    index_count = con.execute("SELECT count(*) FROM duckdb_indexes()").fetchone()[0]
    print("database:", db.name)
    print("entity_rows_present:", "entity_rows" in tables)
    print("decoded_payload_zlib_present:", "decoded_payload_zlib" in source_columns)
    print("secondary_indexes:", index_count)
    print("typed_ships.data fields:")
    for row in con.execute("""
        SELECT typeof(data.warp),
               typeof(data.damage),
               typeof(data.crew),
               typeof(data.friendlycode),
               typeof(data.iscloaked)
        FROM typed_ships
        LIMIT 1
    """).fetchall():
        print(row)
finally:
    con.close()
PY

printf '%s\n' '===== COMPACT T-1/T QUERY: NO GLOBAL ENTITY INDEX ====='
"${compose[@]}" run --rm -T lab     python -m planets_lab.corpus.corpus_db_compact_cli benchmark     --database "$compact_container"     --kind turn-pair --game-id 233558

printf '%s\n' '===== COMPACT VCR/SITE QUERY: NO GLOBAL ENTITY INDEX ====='
"${compose[@]}" run --rm -T lab     python -m planets_lab.corpus.corpus_db_compact_cli benchmark     --database "$compact_container"     --kind vcr-site --game-id 233558

printf '%s\n' '===== SAME COMPACT GENERATION: TWO CONCURRENT READ-ONLY CONTAINERS ====='
export CORPUS_DB_EXPLICIT_RELATIVE="generations/$compact_name"
bash tools/run-corpus-db-explicit-shared-read-check.sh

printf '%s\n' '===== CURRENT PRESERVED ====='
printf 'CURRENT=%s\n' "$after_current"
printf 'compact_generation=%s\n' "$compact_host"
