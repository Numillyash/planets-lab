#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to the shared host corpus DB directory}"

manifest="${PUBLIC_SHORT_COMPACT_MANIFEST:-validation/corpus/manifests/public-short-expansion-selected.jsonl}"
cache_dir="${PUBLIC_SHORT_COMPACT_CACHE_DIR:-validation/corpus/cache/loadall}"
expected_count="${PUBLIC_SHORT_COMPACT_EXPECTED_COUNT:-32}"
state_name="${PUBLIC_SHORT_COMPACT_STATE_NAME:-compact-public-short32-resume}"
min_free_gib="${PUBLIC_SHORT_COMPACT_MIN_FREE_GIB:-12}"

if [[ ! -f "$manifest" ]]; then
    echo "manifest not found: $manifest" >&2
    exit 2
fi
if [[ ! -d "$cache_dir" ]]; then
    echo "cache directory not found: $cache_dir" >&2
    exit 2
fi
if ! [[ "$expected_count" =~ ^[1-9][0-9]*$ ]]; then
    echo "PUBLIC_SHORT_COMPACT_EXPECTED_COUNT must be positive" >&2
    exit 2
fi
if ! [[ "$min_free_gib" =~ ^[1-9][0-9]*$ ]]; then
    echo "PUBLIC_SHORT_COMPACT_MIN_FREE_GIB must be positive" >&2
    exit 2
fi

mkdir -p "$PLANETS_CORPUS_DB_ROOT"/{generations,manifests,staging}

available_bytes="$(df -PB1 "$PLANETS_CORPUS_DB_ROOT" | awk 'NR==2 {print $4}')"
required_bytes="$((min_free_gib * 1024 * 1024 * 1024))"
if (( available_bytes < required_bytes )); then
    echo "insufficient free space for public short compact build" >&2
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
    *) echo "manifest must be under checkout: $manifest_real" >&2; exit 2 ;;
esac
case "$cache_real/" in
    "$repo_real/"*) cache_container="/workspace/${cache_real#"$repo_real/"}" ;;
    *) echo "cache dir must be under checkout: $cache_real" >&2; exit 2 ;;
esac

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
build_id="corpus-v2compact-short${expected_count}-${stamp}"
compose=(docker compose -f compose.yaml -f compose.corpus-db.yaml)

printf '%s\n' '===== CORPUS DB V2 COMPACT: PUBLIC SHORT EXPANSION ====='
printf 'manifest=%s\n' "$manifest"
printf 'expected_count=%s\n' "$expected_count"
printf 'resume_db=%s\n' "$PLANETS_CORPUS_DB_ROOT/staging/${state_name}.duckdb"
printf 'build_id=%s\n' "$build_id"

"${compose[@]}" --profile corpus-db-writer run --rm -T corpus-db-importer \
  python -m planets_lab.corpus.corpus_db_compact_multi_cli build \
    --manifest "$manifest_container" \
    --cache-dir "$cache_container" \
    --expected-count "$expected_count" \
    --state-name "$state_name" \
    --build-id "$build_id"

after_current=""
if [[ -f "$PLANETS_CORPUS_DB_ROOT/CURRENT" ]]; then
    after_current="$(cat "$PLANETS_CORPUS_DB_ROOT/CURRENT")"
fi
if [[ "$before_current" != "$after_current" ]]; then
    echo "ERROR: short expansion build unexpectedly changed canonical CURRENT" >&2
    echo "before: $before_current" >&2
    echo "after:  $after_current" >&2
    exit 1
fi

compact_host="$PLANETS_CORPUS_DB_ROOT/generations/${build_id}.duckdb"
if [[ ! -f "$compact_host" ]]; then
    echo "published compact generation not found: $compact_host" >&2
    exit 2
fi
compact_container="/corpus-db/generations/${build_id}.duckdb"

printf '%s\n' '===== PUBLIC SHORT COMPACT GENERATION STATS ====='
"${compose[@]}" run --rm -T lab \
  python -m planets_lab.corpus.corpus_db_compact_multi_cli stats \
  --database "$compact_container"

printf '%s\n' '===== SAME GENERATION: TWO CONCURRENT READ-ONLY CONTAINERS ====='
export CORPUS_DB_EXPLICIT_RELATIVE="generations/${build_id}.duckdb"
bash tools/run-corpus-db-explicit-shared-read-check.sh

printf '%s\n' '===== CANONICAL CURRENT PRESERVED ====='
printf 'CURRENT=%s\n' "$after_current"
printf 'short_generation=%s\n' "$compact_host"
printf '%s\n' 'If interrupted before publication, rerun this same script; resumable staging is reused.'
