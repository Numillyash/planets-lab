#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to the shared host corpus DB directory}"

memory_limit="${CORPUS_DB_ATTRIBUTION_MEMORY_LIMIT:-4GB}"
threads="${CORPUS_DB_ATTRIBUTION_THREADS:-2}"

compose=(docker compose -f compose.yaml -f compose.corpus-db.yaml)

printf '%s\n' '===== CORPUS DB V1: STORAGE ATTRIBUTION ON DISPOSABLE COPY ====='
printf 'memory_limit=%s threads=%s\n' "$memory_limit" "$threads"

"${compose[@]}" --profile corpus-db-writer run --rm -T corpus-db-importer \
    python -m planets_lab.corpus.corpus_db_cli storage-attribution \
    --memory-limit "$memory_limit" \
    --threads "$threads"
