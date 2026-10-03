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

case "$PLANETS_CORPUS_DB_ROOT" in
    /*) ;;
    *)
        echo "PLANETS_CORPUS_DB_ROOT must be an absolute host path" >&2
        exit 2
        ;;
esac

repo_real="$(realpath -m "$repo_root")"
db_real="$(realpath -m "$PLANETS_CORPUS_DB_ROOT")"
archive_real="$(realpath -m "$archive")"
case "$archive_real/" in
    "$repo_real/"*) archive_container="/workspace/${archive_real#"$repo_real/"}" ;;
    *)
        echo "prototype archive must be under the planets-lab checkout so the importer container can read it: $archive_real" >&2
        exit 2
        ;;
esac
case "$db_real/" in
    "$repo_real/"*)
        echo "PLANETS_CORPUS_DB_ROOT must be outside the planets-lab checkout: $db_real" >&2
        exit 2
        ;;
esac

mkdir -p "$PLANETS_CORPUS_DB_ROOT"/{generations,manifests,staging}

compose=(docker compose -f compose.yaml -f compose.corpus-db.yaml)

printf '%s\n' '===== CORPUS DB V1: BUILD + FULL MEMBER PARITY ====='
"${compose[@]}" --profile corpus-db-writer run --rm -T corpus-db-importer \
    python -m planets_lab.corpus.corpus_db_cli build "$archive_container" --game-id 233558

printf '%s\n' '===== PUBLISHED GENERATION STATS ====='
"${compose[@]}" run --rm -T lab \
    python -m planets_lab.corpus.corpus_db_cli current

printf '%s\n' '===== INDEXED T-1/T QUERY ====='
"${compose[@]}" run --rm -T lab \
    python -m planets_lab.corpus.corpus_db_cli benchmark \
    --kind turn-pair --game-id 233558

printf '%s\n' '===== INDEXED VCR/SITE QUERY ====='
"${compose[@]}" run --rm -T lab \
    python -m planets_lab.corpus.corpus_db_cli benchmark \
    --kind vcr-site --game-id 233558

printf '%s\n' '===== SAME GENERATION: TWO CONCURRENT READ-ONLY CONTAINERS ====='
bash tools/run-corpus-db-shared-read-check.sh