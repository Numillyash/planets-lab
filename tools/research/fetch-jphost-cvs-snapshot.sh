#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

SNAPSHOT_URL="${JPHOST_CVS_SNAPSHOT_URL:-https://sourceforge.net/code-snapshots/cvs/j/jp/jphost.zip}"
OUT_ROOT="${JPHOST_CVS_OUT_ROOT:-artifacts/external-sources/jphost-cvs}"
ZIP_PATH="$OUT_ROOT/jphost-cvs.zip"
REPO_DIR="$OUT_ROOT/repository"
CHECKOUT_DIR="$OUT_ROOT/checkout"

mkdir -p "$OUT_ROOT"

echo "===== JPHOST CVS SNAPSHOT: DOWNLOAD ====="
echo "url:      $SNAPSHOT_URL"
echo "out_root: $OUT_ROOT"

tmp="$ZIP_PATH.part"
rm -f "$tmp"
curl --fail --location --retry 3 --retry-delay 2   --user-agent 'planets-lab-external-research/1.0'   --output "$tmp"   "$SNAPSHOT_URL"
mv "$tmp" "$ZIP_PATH"

echo
echo "===== JPHOST CVS SNAPSHOT: PROVENANCE ====="
sha256sum "$ZIP_PATH"
ls -lh "$ZIP_PATH"

echo
echo "===== JPHOST CVS SNAPSHOT: ZIP CHECK ====="
unzip -t "$ZIP_PATH" >/dev/null
unzip -l "$ZIP_PATH" | sed -n '1,80p'

rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
unzip -q "$ZIP_PATH" -d "$REPO_DIR"

echo
echo "===== JPHOST CVS SNAPSHOT: TOP LEVEL ====="
find "$REPO_DIR" -maxdepth 3 -type f -o -type d | sed -n '1,160p'

cvsroot="$(find "$REPO_DIR" -type d -name CVSROOT -print -quit || true)"
if [[ -z "$cvsroot" ]]; then
  echo "ERROR: downloaded archive does not contain a CVSROOT directory." >&2
  exit 65
fi
repo_root="$(dirname "$cvsroot")"
echo "cvs_repository_root: $repo_root"

echo
echo "===== JPHOST CVS SNAPSHOT: MODULES ====="
if [[ -f "$cvsroot/modules" ]]; then
  sed -n '1,200p' "$cvsroot/modules"
else
  echo "CVSROOT/modules not present; will try the project slug as module."
fi

if ! command -v cvs >/dev/null 2>&1; then
  echo
  echo "CVS client is not installed."
  echo "Install it with: apt-get update && apt-get install -y cvs"
  echo "The raw CVS repository is preserved at: $repo_root"
  exit 0
fi

rm -rf "$CHECKOUT_DIR"
mkdir -p "$CHECKOUT_DIR"

mapfile -t candidates < <(
  {
    if [[ -f "$cvsroot/modules" ]]; then
      awk '
        /^[[:space:]]*#/ || NF == 0 { next }
        $1 !~ /^-/ { print $1 }
      ' "$cvsroot/modules"
    fi
    printf '%s\n' jphost
  } | awk 'NF && !seen[$0]++'
)

echo
echo "===== JPHOST CVS SNAPSHOT: CHECKOUT ====="
checked=0
for module in "${candidates[@]}"; do
  echo "trying module: $module"
  if (
    cd "$CHECKOUT_DIR"
    cvs -Q -d "$repo_root" checkout -P "$module"
  ); then
    checked=1
    echo "checked_out_module: $module"
    break
  fi
done

if [[ "$checked" -ne 1 ]]; then
  echo "ERROR: could not checkout any discovered CVS module." >&2
  echo "Inspect repository manually under: $repo_root" >&2
  exit 66
fi

echo
echo "===== JPHOST CVS SNAPSHOT: SOURCE INVENTORY ====="
find "$CHECKOUT_DIR" -type f | sort | sed -n '1,240p'

echo
echo "===== JPHOST CVS SNAPSHOT: COMBAT SEARCH ====="
grep -RniE   'capture|captur|battle|combat|aggress|opponent|friendly.?code|primary.?enemy|crew|vcr'   "$CHECKOUT_DIR"   --include='*.java' --include='*.properties' --include='*.xml' --include='*.txt'   | sed -n '1,320p' || true

echo
echo "complete: $CHECKOUT_DIR"
