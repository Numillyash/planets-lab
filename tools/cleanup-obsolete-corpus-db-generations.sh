#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "${PLANETS_CORPUS_DB_ROOT:?Set PLANETS_CORPUS_DB_ROOT to the shared host corpus DB directory}"

apply=0
case "${1:-}" in
  "") ;;
  --apply) apply=1 ;;
  *)
    echo "usage: $0 [--apply]" >&2
    exit 64
    ;;
esac

db_root="$(realpath -m "$PLANETS_CORPUS_DB_ROOT")"
current_file="$db_root/CURRENT"

expected_current="generations/corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb"
rollback_rel="generations/corpus-v2compact-public36-20261002T083138Z-11cd75fa918d.duckdb"

active_sha="5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a"
rollback_sha="e1c0adc0a699d9d776f1fddb7dfc37c5a6714dfd9262f911a5939fda41cc7004"

obsolete_rel=(
  "generations/corpus-v1-g233558-20260930T041155Z-8e2e7416675d.duckdb"
  "generations/corpus-v1typed-g233558-20260930T143229Z-8e2e7416675d.duckdb"
  "generations/corpus-v1typed-public36-20260930T211714Z-11cd75fa918d.duckdb"
)

obsolete_manifest_rel=(
  "manifests/corpus-v1-g233558-20260930T041155Z-8e2e7416675d.json"
  "manifests/corpus-v1typed-g233558-20260930T143229Z-8e2e7416675d.json"
  "manifests/corpus-v1typed-public36-20260930T211714Z-11cd75fa918d.json"
)

obsolete_checkpoint_rel=(
  "staging/compact-public36-resume-schema"
  "staging/compact-public36-resume-parity.json"
  "staging/compact-public68-resume-schema"
  "staging/compact-public68-resume-parity.json"
)

if [[ ! -f "$current_file" ]]; then
  echo "ERROR: CURRENT missing: $current_file" >&2
  exit 65
fi

actual_current="$(tr -d '\r\n' < "$current_file")"
if [[ "$actual_current" != "$expected_current" ]]; then
  echo "ERROR: refusing cleanup because CURRENT is not the accepted public68 generation." >&2
  echo "expected: $expected_current" >&2
  echo "actual:   $actual_current" >&2
  exit 65
fi

active="$db_root/$expected_current"
rollback="$db_root/$rollback_rel"

for required in "$active" "$rollback"; do
  if [[ ! -f "$required" ]]; then
    echo "ERROR: required retained generation missing: $required" >&2
    exit 66
  fi
done

echo "===== CORPUS DB OBSOLETE GENERATION CLEANUP: RETAINED BACKENDS ====="
echo "CURRENT=$actual_current"
echo "active=$active"
echo "rollback=$rollback"

echo "verifying active public68 SHA256..."
actual_active_sha="$(sha256sum "$active" | awk '{print $1}')"
if [[ "$actual_active_sha" != "$active_sha" ]]; then
  echo "ERROR: active public68 SHA mismatch." >&2
  echo "expected: $active_sha" >&2
  echo "actual:   $actual_active_sha" >&2
  exit 66
fi

echo "verifying compact public36 rollback SHA256..."
actual_rollback_sha="$(sha256sum "$rollback" | awk '{print $1}')"
if [[ "$actual_rollback_sha" != "$rollback_sha" ]]; then
  echo "ERROR: compact public36 rollback SHA mismatch." >&2
  echo "expected: $rollback_sha" >&2
  echo "actual:   $actual_rollback_sha" >&2
  exit 66
fi

before_free="$(df -PB1 "$db_root" | awk 'NR==2 {print $4}')"
candidate_bytes=0
candidate_count=0

echo
echo "===== OBSOLETE IMMUTABLE GENERATIONS ====="
for rel in "${obsolete_rel[@]}"; do
  path="$db_root/$rel"
  if [[ -f "$path" ]]; then
    bytes="$(stat -c '%s' "$path")"
    candidate_bytes=$((candidate_bytes + bytes))
    candidate_count=$((candidate_count + 1))
    printf 'DELETE %s bytes=%s\n' "$rel" "$bytes"
  else
    printf 'ABSENT %s\n' "$rel"
  fi
done

echo
echo "===== OBSOLETE TYPED STAGING ====="
while IFS= read -r -d '' path; do
  bytes="$(du -sb "$path" | awk '{print $1}')"
  candidate_bytes=$((candidate_bytes + bytes))
  candidate_count=$((candidate_count + 1))
  printf 'DELETE %s bytes=%s\n' "${path#"$db_root/"}" "$bytes"
done < <(
  find "$db_root/staging" -maxdepth 1 \(     -type f -o -type d   \) \(     -name 'typed-corpus-*.duckdb' -o     -name 'typed-corpus-*.duckdb.wal'   \) -print0 2>/dev/null || true
)

for rel in "${obsolete_checkpoint_rel[@]}"; do
  path="$db_root/$rel"
  if [[ -e "$path" ]]; then
    bytes="$(du -sb "$path" | awk '{print $1}')"
    candidate_bytes=$((candidate_bytes + bytes))
    candidate_count=$((candidate_count + 1))
    printf 'DELETE %s bytes=%s\n' "$rel" "$bytes"
  fi
done

echo
echo "candidate_count=$candidate_count"
echo "candidate_bytes=$candidate_bytes"
python3 - "$candidate_bytes" <<'PY'
import sys
value = int(sys.argv[1])
print(f"candidate_gib={value / 1024**3:.3f}")
PY

if [[ "$apply" -ne 1 ]]; then
  echo
  echo "DRY RUN ONLY."
  echo "Re-run with --apply to delete the exact obsolete generations above."
  exit 0
fi

echo
echo "===== APPLY CLEANUP ====="
for rel in "${obsolete_rel[@]}"; do
  path="$db_root/$rel"
  if [[ -f "$path" ]]; then
    rm -f -- "$path"
    rm -f -- "$path.wal"
    echo "removed $rel"
  fi
done

for rel in "${obsolete_manifest_rel[@]}"; do
  path="$db_root/$rel"
  if [[ -f "$path" ]]; then
    rm -f -- "$path"
    echo "removed $rel"
  fi
done

while IFS= read -r -d '' path; do
  rm -rf -- "$path"
  echo "removed ${path#"$db_root/"}"
done < <(
  find "$db_root/staging" -maxdepth 1 \(     -type f -o -type d   \) \(     -name 'typed-corpus-*.duckdb' -o     -name 'typed-corpus-*.duckdb.wal'   \) -print0 2>/dev/null || true
)

for rel in "${obsolete_checkpoint_rel[@]}"; do
  path="$db_root/$rel"
  if [[ -e "$path" ]]; then
    rm -rf -- "$path"
    echo "removed $rel"
  fi
done

# Re-verify the retained backends and CURRENT after destructive work.
after_current="$(tr -d '\r\n' < "$current_file")"
if [[ "$after_current" != "$expected_current" ]]; then
  echo "ERROR: CURRENT changed during cleanup." >&2
  exit 70
fi
if [[ ! -f "$active" || ! -f "$rollback" ]]; then
  echo "ERROR: retained compact generation disappeared during cleanup." >&2
  exit 70
fi

after_free="$(df -PB1 "$db_root" | awk 'NR==2 {print $4}')"
freed=$((after_free - before_free))

echo
echo "===== CLEANUP COMPLETE ====="
echo "CURRENT=$after_current"
echo "retained_active=$expected_current"
echo "retained_rollback=$rollback_rel"
echo "free_bytes_before=$before_free"
echo "free_bytes_after=$after_free"
echo "freed_bytes=$freed"
python3 - "$before_free" "$after_free" "$freed" <<'PY'
import sys
before, after, freed = map(int, sys.argv[1:])
print(f"free_gib_before={before / 1024**3:.3f}")
print(f"free_gib_after={after / 1024**3:.3f}")
print(f"freed_gib={freed / 1024**3:.3f}")
PY
