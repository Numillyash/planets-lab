#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to the shared host corpus DB directory}"

baseline_manifest="${CORPUS_DB_PUBLIC100_BASELINE_MANIFEST:-validation/corpus/manifests/public-short-expansion-with-public36.jsonl}"
selected_manifest="${CORPUS_DB_PUBLIC100_SELECTED_MANIFEST:-validation/corpus/manifests/public-postindependent-validation-selected.jsonl}"
manifest="${CORPUS_DB_PUBLIC100_MANIFEST:-validation/corpus/manifests/public-postindependent-validation-with-public68.jsonl}"
cache_dir="${CORPUS_DB_PUBLIC100_CACHE_DIR:-validation/corpus/cache/loadall}"
expected_baseline_count="${CORPUS_DB_PUBLIC100_BASELINE_COUNT:-68}"
expected_selected_count="${CORPUS_DB_PUBLIC100_SELECTED_COUNT:-32}"
expected_count="${CORPUS_DB_PUBLIC100_EXPECTED_COUNT:-100}"
state_name="${CORPUS_DB_PUBLIC100_STATE_NAME:-compact-public100-resume}"
min_free_gib="${CORPUS_DB_PUBLIC100_MIN_FREE_GIB:-55}"

for required in "$baseline_manifest" "$selected_manifest" "$manifest"; do
    if [[ ! -f "$required" ]]; then
        echo "manifest not found: $required" >&2
        exit 2
    fi
done
if [[ ! -d "$cache_dir" ]]; then
    echo "cache directory not found: $cache_dir" >&2
    exit 2
fi
for value_name in expected_baseline_count expected_selected_count expected_count min_free_gib; do
    value="${!value_name}"
    if ! [[ "$value" =~ ^[1-9][0-9]*$ ]]; then
        echo "$value_name must be a positive integer" >&2
        exit 2
    fi
done
if (( expected_baseline_count + expected_selected_count != expected_count )); then
    echo "configured corpus counts do not add up" >&2
    exit 2
fi

python3 - "$baseline_manifest" "$selected_manifest" "$manifest"     "$expected_baseline_count" "$expected_selected_count" "$expected_count" <<'PY'
import json
import sys
from pathlib import Path

baseline_path = Path(sys.argv[1])
selected_path = Path(sys.argv[2])
combined_path = Path(sys.argv[3])
expected_baseline = int(sys.argv[4])
expected_selected = int(sys.argv[5])
expected_combined = int(sys.argv[6])

def ids(path: Path) -> set[int]:
    result: set[int] = set()
    rows = 0
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        rows += 1
        payload = json.loads(raw)
        game_id = payload.get("game_id")
        if isinstance(game_id, bool) or not isinstance(game_id, int) or game_id <= 0:
            raise SystemExit(f"{path}:{line_number}: invalid game_id")
        if game_id in result:
            raise SystemExit(f"{path}:{line_number}: duplicate game_id={game_id}")
        result.add(game_id)
    if rows != len(result):
        raise SystemExit(f"{path}: row/id count mismatch")
    return result

baseline = ids(baseline_path)
selected = ids(selected_path)
combined = ids(combined_path)
overlap = baseline & selected

print("===== PUBLIC100 MANIFEST BOUNDARY =====")
print(f"baseline_games={len(baseline)}")
print(f"selected_games={len(selected)}")
print(f"combined_games={len(combined)}")
print(f"baseline_selected_overlap={len(overlap)}")

if len(baseline) != expected_baseline:
    raise SystemExit(f"baseline count mismatch: expected={expected_baseline} actual={len(baseline)}")
if len(selected) != expected_selected:
    raise SystemExit(f"selected count mismatch: expected={expected_selected} actual={len(selected)}")
if len(combined) != expected_combined:
    raise SystemExit(f"combined count mismatch: expected={expected_combined} actual={len(combined)}")
if overlap:
    raise SystemExit(f"fresh selected games overlap public68: {sorted(overlap)}")
if combined != baseline | selected:
    missing = sorted((baseline | selected) - combined)
    extra = sorted(combined - (baseline | selected))
    raise SystemExit(f"combined manifest mismatch: missing={missing} extra={extra}")
print("public100_manifest_boundary: PASS")
PY

mkdir -p "$PLANETS_CORPUS_DB_ROOT"/{generations,manifests,staging}

available_bytes="$(df -PB1 "$PLANETS_CORPUS_DB_ROOT" | awk 'NR==2 {print $4}')"
required_bytes="$((min_free_gib * 1024 * 1024 * 1024))"
if (( available_bytes < required_bytes )); then
    echo "insufficient free space for public100 compact build" >&2
    echo "available_bytes=$available_bytes" >&2
    echo "required_bytes=$required_bytes (${min_free_gib} GiB)" >&2
    exit 2
fi

before_current=""
if [[ -f "$PLANETS_CORPUS_DB_ROOT/CURRENT" ]]; then
    before_current="$(tr -d '\r\n' < "$PLANETS_CORPUS_DB_ROOT/CURRENT")"
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

compose=(docker compose -f compose.yaml -f compose.corpus-db.yaml)

printf '%s\n' '===== CORPUS DB V2 COMPACT: PUBLIC100 COMBINED CORPUS ====='
printf 'manifest=%s\n' "$manifest"
printf 'cache_dir=%s\n' "$cache_dir"
printf 'expected_count=%s\n' "$expected_count"
printf 'resume_db=%s\n' "$PLANETS_CORPUS_DB_ROOT/staging/${state_name}.duckdb"
printf 'schema_checkpoints=%s\n' "$PLANETS_CORPUS_DB_ROOT/staging/${state_name}-schema"
printf 'current_before=%s\n' "$before_current"
printf 'free_bytes=%s\n' "$available_bytes"

"${compose[@]}" --profile corpus-db-writer run --rm -T corpus-db-importer   python -m planets_lab.corpus.corpus_db_compact_multi_cli build     --manifest "$manifest_container"     --cache-dir "$cache_container"     --expected-count "$expected_count"     --state-name "$state_name"

after_current=""
if [[ -f "$PLANETS_CORPUS_DB_ROOT/CURRENT" ]]; then
    after_current="$(tr -d '\r\n' < "$PLANETS_CORPUS_DB_ROOT/CURRENT")"
fi
if [[ "$before_current" != "$after_current" ]]; then
    echo "ERROR: public100 compact gate unexpectedly changed canonical CURRENT" >&2
    echo "before: $before_current" >&2
    echo "after:  $after_current" >&2
    exit 1
fi

compact_host="$(
    find "$PLANETS_CORPUS_DB_ROOT/generations"       -maxdepth 1 -type f       -name 'corpus-v2compact-public100-*.duckdb'       -printf '%T@ %p\n'     | sort -nr     | head -n1     | cut -d' ' -f2-
)"
if [[ -z "$compact_host" || ! -f "$compact_host" ]]; then
    echo "published public100 compact generation not found" >&2
    exit 2
fi
compact_name="$(basename "$compact_host")"
compact_rel="generations/$compact_name"
compact_container="/corpus-db/$compact_rel"
compact_sha="$(sha256sum "$compact_host" | awk '{print $1}')"

printf '%s\n' '===== PUBLIC100 COMPACT GENERATION STATS ====='
"${compose[@]}" run --rm -T lab   python -m planets_lab.corpus.corpus_db_compact_multi_cli stats   --database "$compact_container"

printf '%s\n' '===== PUBLIC100 COMPACT PHYSICAL FACTS ====='
"${compose[@]}" run --rm -T lab python -   "$compact_container" "$expected_count" "$compact_rel" "$compact_sha" <<'PY'
from pathlib import Path
import sys
import duckdb

database = Path(sys.argv[1])
expected_archives = int(sys.argv[2])
generation_rel = sys.argv[3]
sha256 = sys.argv[4]

connection = duckdb.connect(str(database), read_only=True)
try:
    schema_row = connection.execute("SELECT schema_version FROM corpus_metadata").fetchone()
    if schema_row is None:
        raise SystemExit("corpus_metadata schema_version is absent")
    schema = str(schema_row[0])
    if schema != "planets-lab.corpus-db.v2.compact1":
        raise SystemExit(f"unexpected schema: {schema!r}")

    archives = int(connection.execute("SELECT count(*) FROM source_archives").fetchone()[0])
    members = int(connection.execute("SELECT count(*) FROM source_members").fetchone()[0])
    state = connection.execute(
        "SELECT corpus_fingerprint, expected_archive_count FROM compact_build_state"
    ).fetchone()
    if state is None:
        raise SystemExit("compact_build_state is absent")
    fingerprint = str(state[0])
    state_archives = int(state[1])

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
    index_count = int(connection.execute("SELECT count(*) FROM duckdb_indexes()").fetchone()[0])

    if archives != expected_archives:
        raise SystemExit(f"archive count mismatch: expected={expected_archives} actual={archives}")
    if state_archives != expected_archives:
        raise SystemExit(
            "compact_build_state archive count mismatch: "
            f"expected={expected_archives} actual={state_archives}"
        )
    if "entity_rows" in tables:
        raise SystemExit("compact invariant failed: entity_rows exists")
    if "decoded_payload_zlib" in source_columns:
        raise SystemExit("compact invariant failed: decoded_payload_zlib exists")
    if index_count != 0:
        raise SystemExit(f"compact invariant failed: secondary index count={index_count}")

    print(f"generation_rel={generation_rel}")
    print(f"sha256={sha256}")
    print(f"schema={schema}")
    print(f"source_archives={archives}")
    print(f"source_members={members}")
    print(f"corpus_fingerprint={fingerprint}")
    print(f"secondary_indexes={index_count}")
    print("entity_rows_present=false")
    print("decoded_payload_zlib_present=false")
finally:
    connection.close()
PY

printf '%s\n' '===== PUBLIC100 T-1/T QUERY: GAME 233558 ====='
"${compose[@]}" run --rm -T lab   python -m planets_lab.corpus.corpus_db_compact_cli benchmark   --database "$compact_container"   --kind turn-pair   --game-id 233558

printf '%s\n' '===== PUBLIC100 VCR/SITE QUERY: GAME 233558 ====='
"${compose[@]}" run --rm -T lab   python -m planets_lab.corpus.corpus_db_compact_cli benchmark   --database "$compact_container"   --kind vcr-site   --game-id 233558

printf '%s\n' '===== SAME PUBLIC100 GENERATION: TWO CONCURRENT READ-ONLY CONTAINERS ====='
export CORPUS_DB_EXPLICIT_RELATIVE="$compact_rel"
bash tools/run-corpus-db-explicit-shared-read-check.sh

printf '%s\n' '===== PUBLIC100 GATE COMPLETE; CURRENT PRESERVED ====='
printf 'CURRENT=%s\n' "$after_current"
printf 'public100_generation=%s\n' "$compact_host"
printf 'public100_generation_rel=%s\n' "$compact_rel"
printf 'public100_sha256=%s\n' "$compact_sha"
printf '%s\n' 'Do not activate this generation before prospective capture-side validation is reviewed.'
printf '%s\n' 'If interrupted before publication, rerun this same script; resumable staging and schema checkpoints are reused.'
