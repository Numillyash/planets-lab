#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to the shared host corpus DB directory}"

database_args=()
if [[ -n "${CORPUS_DB_ATTRIBUTION_DATABASE:-}" ]]; then
    database_args=(--database "${CORPUS_DB_ATTRIBUTION_DATABASE}")
fi

memory_limit="${CORPUS_DB_ATTRIBUTION_MEMORY_LIMIT:-4GB}"
threads="${CORPUS_DB_ATTRIBUTION_THREADS:-2}"

compose=(docker compose -f compose.yaml -f compose.corpus-db.yaml)

printf '%s\n' '===== CORPUS DB TYPED: STORAGE ATTRIBUTION ====='
printf 'memory_limit=%s threads=%s\n' "$memory_limit" "$threads"

"${compose[@]}" --profile corpus-db-writer run --rm -T corpus-db-importer \
    python -m planets_lab.corpus.corpus_db_typed_cli storage-attribution \
    "${database_args[@]}" \
    --memory-limit "$memory_limit" \
    --threads "$threads"
