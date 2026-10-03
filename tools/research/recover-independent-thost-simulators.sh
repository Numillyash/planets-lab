#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

OUT_ROOT="${INDEPENDENT_SIM_ROOT:-artifacts/external-sources/independent-sims}"
REPORT="${INDEPENDENT_SIM_REPORT:-$OUT_ROOT/recovery-audit.txt}"

for cmd in curl unzip sha256sum file strings grep find python3 stat; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command missing: $cmd" >&2
    exit 69
  fi
done

mkdir -p "$OUT_ROOT/pages" "$OUT_ROOT/downloads" "$OUT_ROOT/extracted"
exec > >(tee "$REPORT") 2>&1

# These IDs are independently indexed by Apajalista as surviving VGA Planets
# packages:
#   41859 AFSIM.ZIP  (Sean Martens)
#   61688 BSIM22.ZIP (Thomas Voigt)
#
# AFSIM is the higher-value target: historical documentation identifies it as a
# multi-ship simulator which delegates pairwise physics to Tim's VCR.
declare -a SPECS=(
  "afsim|41859|AFSIM.ZIP"
  "bsim22|61688|BSIM22.ZIP"
)

BASE="https://www.apajalista.net"

fetch_page() {
  local slug="$1"
  local id="$2"
  local page="$OUT_ROOT/pages/$slug.html"
  echo "===== INDEX PAGE: $slug ====="
  echo "url: $BASE/id?id=$id"
  curl -fL --retry 3 --retry-delay 2 --connect-timeout 20     -A 'planets-lab-external-research/1.0'     -o "$page" "$BASE/id?id=$id"
  echo -n "page_sha256: "
  sha256sum "$page" | awk '{print $1}'
  echo -n "page_size:   "
  stat -c '%s' "$page"
  echo
}

candidate_urls() {
  local page="$1"
  local filename="$2"
  python3 - "$page" "$filename" "$BASE" <<'PY'
from __future__ import annotations
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

page = Path(sys.argv[1])
filename = sys.argv[2]
base = sys.argv[3]
text = page.read_text(errors="replace")

class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k.lower() in {"href", "src", "action"} and v:
                self.hrefs.append(html.unescape(v))

p = P()
p.feed(text)

# Also recover bare absolute/relative URLs hidden in scripts/onclick values.
extra = re.findall(
    r'''(?ix)
    (?:
      https?://[^"'<>\s]+
      |
      [A-Za-z0-9_./?=&%+-]*\.(?:zip|arj|rar)(?:\?[^"'<>\s]*)?
    )
    ''',
    text,
)

urls = []
seen = set()
for raw in p.hrefs + extra:
    u = urljoin(base + "/", raw)
    if u in seen:
        continue
    seen.add(u)
    urls.append(u)

needle = filename.lower()
def score(u: str):
    l = u.lower()
    return (
        0 if needle in l else
        1 if l.endswith(".zip") or ".zip?" in l else
        2 if "download" in l or "tiedost" in l or "file" in l else
        3,
        len(u),
        u,
    )

for u in sorted(urls, key=score):
    if score(u)[0] <= 2:
        print(u)
PY
}

try_download() {
  local slug="$1"
  local filename="$2"
  local page="$OUT_ROOT/pages/$slug.html"
  local dst="$OUT_ROOT/downloads/$filename"

  echo "===== DOWNLOAD RESOLUTION: $slug ====="
  mapfile -t urls < <(candidate_urls "$page" "$filename")
  if [[ "${#urls[@]}" -eq 0 ]]; then
    echo "candidate_urls: none"
    return 1
  fi

  printf 'candidate_urls: %d\n' "${#urls[@]}"
  printf '  %s\n' "${urls[@]}"

  local n=0
  for url in "${urls[@]}"; do
    n=$((n + 1))
    tmp="$dst.part"
    rm -f "$tmp"
    echo
    echo "try[$n]: $url"
    if ! curl -fL --retry 1 --connect-timeout 20       -A 'planets-lab-external-research/1.0'       -o "$tmp" "$url"; then
      echo "status: curl-failed"
      continue
    fi
    if unzip -t "$tmp" >/dev/null 2>&1; then
      mv "$tmp" "$dst"
      echo "status: ZIP-OK"
      echo -n "sha256: "
      sha256sum "$dst" | awk '{print $1}'
      echo -n "size:   "
      stat -c '%s' "$dst"
      return 0
    fi
    echo "status: not-a-zip"
    file "$tmp" || true
    rm -f "$tmp"
  done
  return 1
}

audit_archive() {
  local slug="$1"
  local filename="$2"
  local zip="$OUT_ROOT/downloads/$filename"
  local dst="$OUT_ROOT/extracted/$slug"

  rm -rf "$dst"
  mkdir -p "$dst"
  unzip -qq -o "$zip" -d "$dst"

  echo
  echo "===== ARCHIVE INVENTORY: $slug ====="
  unzip -Z1 "$zip" | sort

  echo
  echo "===== FILE TYPES: $slug ====="
  find "$dst" -type f -print0 | sort -z | xargs -0 -r file

  echo
  echo "===== TEXT / DOCUMENT SEARCH: $slug ====="
  while IFS= read -r -d '' f; do
    desc="$(file -b "$f" 2>/dev/null || true)"
    case "${f,,}:$desc" in
      *.txt:*|*.doc:*|*.nfo:*|*.diz:*|*.hlp:*|*.ini:*|*.cfg:*|*.pas:*|*.c:*|*.h:*|*ASCII*|*text*)
        hits="$(
          grep -aniE             'battle[ _-]*(order|value)|fight[ _-]*order|multi.?ship|captur(e|ed)|surrender|aggress(or|ive)|primary[ _-]*enemy|friendly[ _-]*code|kill mission|left|right|vcr|crew|owner|passive|ship id|numeric'             "$f" 2>/dev/null | head -n 500 || true
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
  echo "===== BINARY STRINGS: $slug ====="
  while IFS= read -r -d '' f; do
    desc="$(file -b "$f" 2>/dev/null || true)"
    case "${f,,}:$desc" in
      *.exe:*|*.com:*|*.dll:*|*executable*|*MS-DOS*)
        hits="$(
          strings -a -n 4 -td "$f" 2>/dev/null             | grep -iE               'battle[ _-]*(order|value)|fight[ _-]*order|captur(e|ed)|surrender|aggress(or|ive)|primary[ _-]*enemy|friendly[ _-]*code|kill mission|left|right|vcr|crew|owner|passive|ship id|numeric'             | head -n 700 || true
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
  echo "===== SOURCE / DEBUG CANDIDATES: $slug ====="
  find "$dst" -type f     \( -iname '*.pas' -o -iname '*.c' -o -iname '*.cpp' -o -iname '*.h'        -o -iname '*.map' -o -iname '*.sym' -o -iname '*.dbg' -o -iname '*.tds'        -o -iname '*.lst' \) -print | sort
}

echo "===== INDEPENDENT THOST SIMULATOR RECOVERY ====="
echo "output: $OUT_ROOT"
echo

success=0
for spec in "${SPECS[@]}"; do
  IFS='|' read -r slug id filename <<< "$spec"
  fetch_page "$slug" "$id"
  if try_download "$slug" "$filename"; then
    audit_archive "$slug" "$filename"
    success=$((success + 1))
  else
    echo
    echo "WARNING: could not automatically resolve/download $filename."
    echo "Saved index page: $OUT_ROOT/pages/$slug.html"
    echo "The candidate URLs printed above are preserved in this log."
    echo
  fi
done

echo
echo "===== RECOVERY SUMMARY ====="
echo "archives_recovered: $success / ${#SPECS[@]}"
echo "report: $REPORT"

if [[ "$success" -eq 0 ]]; then
  echo "ERROR: no independent simulator archive recovered." >&2
  exit 66
fi
