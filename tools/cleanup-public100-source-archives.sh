#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to the shared host corpus DB directory}"

apply=0
case "${1:-}" in
  "") ;;
  --apply) apply=1 ;;
  *) echo "usage: $0 [--apply]" >&2; exit 64 ;;
esac

manifest="${PUBLIC100_MANIFEST:-validation/corpus/manifests/public-postindependent-validation-with-public68.jsonl}"
cache_dir="${PUBLIC100_CACHE_DIR:-validation/corpus/cache/loadall}"
public100_rel="${PUBLIC100_REL:-generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb}"
public100_sha="${PUBLIC100_SHA:-3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c}"

if [[ ! -s "$manifest" ]]; then
  echo "ERROR: public100 manifest missing or empty: $manifest" >&2
  exit 65
fi
if [[ ! -d "$cache_dir" ]]; then
  echo "ERROR: source cache directory missing: $cache_dir" >&2
  exit 65
fi

db="$PLANETS_CORPUS_DB_ROOT/$public100_rel"
if [[ ! -f "$db" ]]; then
  echo "ERROR: validated public100 generation missing: $db" >&2
  exit 66
fi
actual_sha="$(sha256sum "$db" | awk '{print $1}')"
if [[ "$actual_sha" != "$public100_sha" ]]; then
  echo "ERROR: public100 SHA256 mismatch; refusing source deletion." >&2
  echo "expected: $public100_sha" >&2
  echo "actual:   $actual_sha" >&2
  exit 66
fi

mapfile -t GAME_IDS < <(
  python3 - "$manifest" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
ids = []
seen = set()
for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
    if not raw.strip():
        continue
    payload = json.loads(raw)
    game_id = payload.get("game_id")
    if isinstance(game_id, bool) or not isinstance(game_id, int) or game_id <= 0:
        raise SystemExit(f"{path}:{line_number}: invalid game_id")
    if game_id in seen:
        raise SystemExit(f"{path}:{line_number}: duplicate game_id={game_id}")
    seen.add(game_id)
    ids.append(game_id)
if len(ids) != 100:
    raise SystemExit(f"expected exactly 100 public100 game IDs, got {len(ids)}")
for game_id in sorted(ids):
    print(game_id)
PY
)

candidate_count=0
candidate_bytes=0
missing_count=0

echo "===== PUBLIC100 SOURCE ARCHIVE CLEANUP ====="
echo "validated_generation=$public100_rel"
echo "validated_sha256=$actual_sha"
echo "manifest=$manifest"
echo "cache_dir=$cache_dir"

for game_id in "${GAME_IDS[@]}"; do
  path="$cache_dir/game-${game_id}.zip"
  if [[ -f "$path" ]]; then
    bytes="$(stat -c '%s' "$path")"
    candidate_count=$((candidate_count + 1))
    candidate_bytes=$((candidate_bytes + bytes))
  else
    missing_count=$((missing_count + 1))
  fi
done

echo "manifest_games=${#GAME_IDS[@]}"
echo "cached_archives_present=$candidate_count"
echo "cached_archives_missing=$missing_count"
echo "candidate_bytes=$candidate_bytes"
python3 - "$candidate_bytes" <<'PY'
import sys
value = int(sys.argv[1])
print(f"candidate_gib={value / 1024**3:.3f}")
PY

if [[ "$apply" -ne 1 ]]; then
  echo "DRY RUN ONLY."
  echo "Re-run with --apply to remove these 100-game source ZIPs."
  exit 0
fi

echo "===== APPLY PUBLIC100 SOURCE CLEANUP ====="
removed=0
removed_bytes=0
for game_id in "${GAME_IDS[@]}"; do
  path="$cache_dir/game-${game_id}.zip"
  if [[ -f "$path" ]]; then
    bytes="$(stat -c '%s' "$path")"
    rm -f -- "$path"
    removed=$((removed + 1))
    removed_bytes=$((removed_bytes + bytes))
  fi
done

# The validated DB must remain byte-identical after source deletion.
after_sha="$(sha256sum "$db" | awk '{print $1}')"
if [[ "$after_sha" != "$public100_sha" ]]; then
  echo "ERROR: public100 generation SHA changed during source cleanup." >&2
  exit 70
fi

echo "source_cleanup: PASS"
echo "removed_archives=$removed"
echo "removed_bytes=$removed_bytes"
python3 - "$removed_bytes" <<'PY'
import sys
value = int(sys.argv[1])
print(f"removed_gib={value / 1024**3:.3f}")
PY
echo "validated_generation_preserved=$public100_rel"
