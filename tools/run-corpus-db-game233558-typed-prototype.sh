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
        echo "prototype archive must be under the checkout: $archive_real" >&2
        exit 2
        ;;
esac

mkdir -p "$PLANETS_CORPUS_DB_ROOT"/{generations,manifests,staging}
compose=(docker compose -f compose.yaml -f compose.corpus-db.yaml)

printf '%s\n' '===== CORPUS DB V1 TYPED: BUILD + FULL MEMBER PARITY ====='
"${compose[@]}" --profile corpus-db-writer run --rm -T corpus-db-importer \
    python -m planets_lab.corpus.corpus_db_typed_cli build \
    "$archive_container" --game-id 233558

printf '%s\n' '===== TYPED GENERATION STATS ====='
"${compose[@]}" run --rm -T lab \
    python -m planets_lab.corpus.corpus_db_cli current

printf '%s\n' '===== TYPED SHIP COLUMN CHECK ====='
"${compose[@]}" run --rm -T lab python - <<'PY'
from pathlib import Path
import os
import duckdb

root = Path(os.environ["PLANETS_CORPUS_DB_ROOT"])
db = (root / (root / "CURRENT").read_text().strip()).resolve()
con = duckdb.connect(str(db), read_only=True)
try:
    print("database:", db.name)
    print("entity_rows:")
    for row in con.execute("DESCRIBE entity_rows").fetchall():
        print(row)
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

printf '%s\n' '===== INDEXED T-1/T QUERY ====='
"${compose[@]}" run --rm -T lab \
    python -m planets_lab.corpus.corpus_db_typed_cli benchmark \
    --kind turn-pair --game-id 233558

printf '%s\n' '===== INDEXED VCR/SITE QUERY ====='
"${compose[@]}" run --rm -T lab \
    python -m planets_lab.corpus.corpus_db_typed_cli benchmark \
    --kind vcr-site --game-id 233558

printf '%s\n' '===== SAME TYPED GENERATION: TWO CONCURRENT READ-ONLY CONTAINERS ====='
bash tools/run-corpus-db-shared-read-check.sh
