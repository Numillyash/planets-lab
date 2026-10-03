#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to an absolute host path outside the checkout}"

manifest="${PUBLIC_CORPUS_MANIFEST:-validation/corpus/manifests/public-validation-selected.jsonl}"
cache_dir="${PUBLIC_CORPUS_CACHE_DIR:-validation/corpus/cache/loadall}"
expected_count="${PUBLIC_CORPUS_EXPECTED_COUNT:-36}"

if [[ ! -f "$manifest" ]]; then
    echo "manifest not found: $manifest" >&2
    exit 2
fi
if [[ ! -d "$cache_dir" ]]; then
    echo "cache directory not found: $cache_dir" >&2
    exit 2
fi
if ! [[ "$expected_count" =~ ^[1-9][0-9]*$ ]]; then
    echo "PUBLIC_CORPUS_EXPECTED_COUNT must be a positive integer" >&2
    exit 2
fi

repo_real="$(realpath -m "$repo_root")"
manifest_real="$(realpath -m "$manifest")"
cache_real="$(realpath -m "$cache_dir")"

case "$manifest_real/" in
    "$repo_real/"*) manifest_container="/workspace/${manifest_real#"$repo_real/"}" ;;
    *)
        echo "manifest must be under the planets-lab checkout: $manifest_real" >&2
        exit 2
        ;;
esac
case "$cache_real/" in
    "$repo_real/"*) cache_container="/workspace/${cache_real#"$repo_real/"}" ;;
    *)
        echo "cache directory must be under the planets-lab checkout: $cache_real" >&2
        exit 2
        ;;
esac

mkdir -p "$PLANETS_CORPUS_DB_ROOT"/{generations,manifests,staging}
compose=(docker compose -f compose.yaml -f compose.corpus-db.yaml)

printf '%s\n' '===== CORPUS DB V1 TYPED: PUBLIC CORPUS BUILD + FULL PARITY ====='
printf 'manifest=%s\ncache_dir=%s\nexpected_count=%s\n'     "$manifest" "$cache_dir" "$expected_count"

"${compose[@]}" --profile corpus-db-writer run --rm -T corpus-db-importer     python -m planets_lab.corpus.corpus_db_typed_multi_cli     --manifest "$manifest_container"     --cache-dir "$cache_container"     --expected-count "$expected_count"

printf '%s\n' '===== PUBLISHED PUBLIC TYPED GENERATION STATS ====='
"${compose[@]}" run --rm -T lab     python -m planets_lab.corpus.corpus_db_cli current

printf '%s\n' '===== SAME PUBLIC GENERATION: TWO CONCURRENT READ-ONLY CONTAINERS ====='
bash tools/run-corpus-db-shared-read-check.sh
