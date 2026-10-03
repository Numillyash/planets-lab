#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

OUT_ROOT="${PCC1_AUDIT_ROOT:-artifacts/external-sources/pcc1}"
BASE_URL="${PCC1_BASE_URL:-https://phost.de/~stefan/planets}"
REPORT="${PCC1_AUDIT_REPORT:-$OUT_ROOT/pcc1-ccbsim-package-audit.txt}"

# Keep the default pass small. Override with e.g.
#   PCC1_PACKAGES="cc1122.zip cc1122db.zip ccbsim1122.zip ccbsim1191.zip"
read -r -a PACKAGES <<< "${PCC1_PACKAGES:-cc1122.zip cc1122db.zip ccbsim1122.zip}"

for cmd in curl unzip sha256sum strings file grep find awk sed sort; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command is missing: $cmd" >&2
    exit 69
  fi
done

mkdir -p "$OUT_ROOT/downloads" "$OUT_ROOT/extracted"
exec > >(tee "$REPORT") 2>&1

echo "===== PCC1 / CCBSIM PACKAGE AUDIT ====="
echo "base_url: $BASE_URL"
printf 'packages:'
printf ' %s' "${PACKAGES[@]}"
echo
echo

download_one() {
  local name="$1"
  local url="$BASE_URL/$name"
  local dst="$OUT_ROOT/downloads/$name"
  echo "===== DOWNLOAD: $name ====="
  echo "url: $url"
  if [[ ! -s "$dst" ]]; then
    curl -fL --retry 3 --retry-delay 2 --connect-timeout 20       -o "$dst.part" "$url"
    mv "$dst.part" "$dst"
  else
    echo "status: cached"
  fi
  echo -n "size:   "
  stat -c '%s' "$dst"
  echo -n "sha256: "
  sha256sum "$dst" | awk '{print $1}'
  if unzip -t "$dst" >/dev/null 2>&1; then
    echo "zipcheck: ok"
  else
    echo "ERROR: invalid ZIP: $dst" >&2
    return 1
  fi
  echo
}

extract_one() {
  local name="$1"
  local stem="${name%.zip}"
  local src="$OUT_ROOT/downloads/$name"
  local dst="$OUT_ROOT/extracted/$stem"
  rm -rf "$dst"
  mkdir -p "$dst"
  unzip -qq -o "$src" -d "$dst"

  echo "===== ARCHIVE INVENTORY: $name ====="
  unzip -Z1 "$src" | sort
  echo

  echo "===== FILE TYPES: $name ====="
  find "$dst" -type f -print0     | sort -z     | xargs -0 -r file
  echo

  echo "===== DEBUG / MAP / SYMBOL CANDIDATES: $name ====="
  find "$dst" -type f     \( -iname '*.map' -o -iname '*.sym' -o -iname '*.dbg' -o -iname '*.tds'        -o -iname '*.lst' -o -iname '*.cod' -o -iname '*.log' -o -iname '*core*'        -o -iname '*debug*' -o -iname '*sym*' \)     -print | sort
  echo

  echo "===== SOURCE-LIKE FILES: $name ====="
  find "$dst" -type f     \( -iname '*.pas' -o -iname '*.pp' -o -iname '*.inc' -o -iname '*.c'        -o -iname '*.cc' -o -iname '*.cpp' -o -iname '*.h' -o -iname '*.hpp'        -o -iname '*.asm' \)     -print | sort
  echo
}

scan_text_like() {
  local name="$1"
  local stem="${name%.zip}"
  local dst="$OUT_ROOT/extracted/$stem"

  echo "===== TEXT/DEBUG QUEUE-TERM SEARCH: $name ====="
  while IFS= read -r -d '' f; do
    case "${f,,}" in
      *.txt|*.doc|*.hlp|*.map|*.sym|*.dbg|*.lst|*.cod|*.log|*.pas|*.pp|*.inc|*.c|*.cc|*.cpp|*.h|*.hpp|*.asm|*.ini|*.cfg)
        hits="$(
          grep -aniE             'battle[ _-]*(order|value)|combat[ _-]*(order|queue)|captur(e|ed)|surrender|aggress(or|ive)|opponent|primary[ _-]*enemy|friendly[ _-]*code|fight|vcr|crew|setowner|owner|passive|left|right|queue|sort'             "$f" 2>/dev/null | head -n 240 || true
        )"
        if [[ -n "$hits" ]]; then
          echo
          echo "--- $f ---"
          printf '%s\n' "$hits"
        fi
        ;;
    esac
  done < <(find "$dst" -type f -print0 | sort -z)
  echo
}

scan_binary_strings() {
  local name="$1"
  local stem="${name%.zip}"
  local dst="$OUT_ROOT/extracted/$stem"

  echo "===== EXECUTABLE/BINARY QUEUE-TERM STRINGS: $name ====="
  while IFS= read -r -d '' f; do
    # DOS executables do not always have a useful filename extension. Scan files
    # that file(1) identifies as executable plus conventional binary extensions.
    desc="$(file -b "$f" 2>/dev/null || true)"
    case "${f,,}:$desc" in
      *.exe:*|*.com:*|*.ovr:*|*.dll:*|*executable*|*MS-DOS*)
        hits="$(
          strings -a -n 4 -td "$f" 2>/dev/null             | grep -iE               'battle[ _-]*(order|value)|combat[ _-]*(order|queue)|captur(e|ed)|surrender|aggress(or|ive)|opponent|primary[ _-]*enemy|friendly[ _-]*code|fight|vcr|crew|passive|left|right|queue|sort'             | head -n 400 || true
        )"
        if [[ -n "$hits" ]]; then
          echo
          echo "--- $f ---"
          echo "file: $desc"
          printf '%s\n' "$hits"
        fi
        ;;
    esac
  done < <(find "$dst" -type f -print0 | sort -z)
  echo
}

for pkg in "${PACKAGES[@]}"; do
  download_one "$pkg"
done

for pkg in "${PACKAGES[@]}"; do
  extract_one "$pkg"
  scan_text_like "$pkg"
  scan_binary_strings "$pkg"
done

echo "===== CROSS-PACKAGE FILENAME HINTS ====="
find "$OUT_ROOT/extracted" -type f   | grep -iE 'battle|combat|sim|vcr|core|debug|map|sym'   | sort || true

echo
echo "===== AUDIT COMPLETE ====="
echo "report:    $REPORT"
echo "downloads: $OUT_ROOT/downloads"
echo "extracted: $OUT_ROOT/extracted"
