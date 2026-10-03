#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

OUT_ROOT="${INDEPENDENT_SIM_ROOT:-artifacts/external-sources/independent-sims}"
REPORT="${INDEPENDENT_SIM_REPORT:-$OUT_ROOT/recovery-audit.txt}"
PAGE_MAX_TIME="${INDEPENDENT_SIM_PAGE_MAX_TIME:-35}"
DOWNLOAD_MAX_TIME="${INDEPENDENT_SIM_DOWNLOAD_MAX_TIME:-120}"

for cmd in curl unzip sha256sum file strings grep find python3 stat; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command missing: $cmd" >&2
    exit 69
  fi
done

mkdir -p "$OUT_ROOT/pages" "$OUT_ROOT/downloads" "$OUT_ROOT/extracted"
exec > >(tee "$REPORT") 2>&1

# Primary independent simulator candidates:
#   41859 AFSIM.ZIP  (Sean Martens)
#   61688 BSIM22.ZIP (Thomas Voigt)
#
# Apajalista's HTML detail endpoint can be extremely slow. AFSIM currently has a
# directly downloadable archive URL, so try that first and only fall back to
# detail-page discovery when direct recovery fails.
declare -a SPECS=(
  "afsim|41859|AFSIM.ZIP|https://www.apajalista.net/tiedostot/Pelit/Purkkipelit/VGA_Planets/AFSIM.ZIP"
  "bsim22|61688|BSIM22.ZIP|"
)

# If the surviving BSim 2.2 index no longer exposes a downloadable copy, BSim
# 2.00 is a version-scoped architecture fallback only. It must not be reported
# as BSim 2.2 evidence.
FALLBACK_BSIM_SPEC="bsim2-fallback|104101|BSIM2.ZIP|"

BASE="https://www.apajalista.net"

fetch_page() {
  local slug="$1"
  local id="$2"
  local page="$OUT_ROOT/pages/$slug.html"
  local tmp="$page.part"

  echo "===== INDEX PAGE: $slug ====="
  echo "url: $BASE/id?id=$id"
  rm -f "$tmp"

  if ! curl -fL --retry 1 --retry-delay 2 --connect-timeout 15 \
      --max-time "$PAGE_MAX_TIME" \
      -A 'planets-lab-external-research/1.0' \
      -o "$tmp" "$BASE/id?id=$id"; then
    echo "status: page-fetch-failed-or-timed-out"
    rm -f "$tmp"
    echo
    return 1
  fi

  mv "$tmp" "$page"
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
    r"""(?ix)
    (?:
      https?://[^"'<>\s]+
      |
      [A-Za-z0-9_./?=&%+-]*\.(?:zip|arj|rar)(?:\?[^"'<>\s]*)?
    )
    """,
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
  local direct_url="${3:-}"
  local page="$OUT_ROOT/pages/$slug.html"
  local dst="$OUT_ROOT/downloads/$filename"

  echo "===== DOWNLOAD RESOLUTION: $slug ====="

  if [[ -f "$dst" ]]; then
    if unzip -t "$dst" >/dev/null 2>&1; then
      echo "status: EXISTING-ZIP-OK"
      echo -n "sha256: "
      sha256sum "$dst" | awk '{print $1}'
      echo -n "size:   "
      stat -c '%s' "$dst"
      return 0
    fi

    echo "status: existing-file-invalid"
    file "$dst" || true
    mv "$dst" "$dst.invalid-$(date -u +%Y%m%dT%H%M%SZ)"
  fi

  local -a urls=()
  if [[ -n "$direct_url" ]]; then
    urls+=("$direct_url")
    echo "direct_candidate: $direct_url"
  fi

  if [[ -s "$page" ]]; then
    local -a discovered=()
    mapfile -t discovered < <(candidate_urls "$page" "$filename")
    urls+=("${discovered[@]}")
  fi

  if [[ "${#urls[@]}" -eq 0 ]]; then
    echo "candidate_urls: none"
    return 1
  fi

  # Preserve ordering (direct candidate first) while suppressing duplicate URLs.
  local -A seen=()
  local -a unique_urls=()
  local url
  for url in "${urls[@]}"; do
    [[ -n "$url" ]] || continue
    if [[ -z "${seen[$url]+x}" ]]; then
      seen["$url"]=1
      unique_urls+=("$url")
    fi
  done

  printf 'candidate_urls: %d\n' "${#unique_urls[@]}"
  printf '  %s\n' "${unique_urls[@]}"

  local n=0
  for url in "${unique_urls[@]}"; do
    n=$((n + 1))
    local tmp="$dst.part"
    rm -f "$tmp"
    echo
    echo "try[$n]: $url"
    if ! curl -fL --retry 1 --retry-delay 2 --connect-timeout 15 \
        --max-time "$DOWNLOAD_MAX_TIME" \
        -A 'planets-lab-external-research/1.0' \
        -o "$tmp" "$url"; then
      echo "status: curl-failed-or-timed-out"
      rm -f "$tmp"
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
          grep -aniE \
            'battle[ _-]*(order|value)|fight[ _-]*order|multi.?ship|captur(e|ed)|surrender|aggress(or|ive)|primary[ _-]*enemy|friendly[ _-]*code|kill mission|left|right|vcr|crew|owner|passive|ship id|numeric' \
            "$f" 2>/dev/null | head -n 500 || true
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
          strings -a -n 4 -td "$f" 2>/dev/null \
            | grep -iE \
              'battle[ _-]*(order|value)|fight[ _-]*order|captur(e|ed)|surrender|aggress(or|ive)|primary[ _-]*enemy|friendly[ _-]*code|kill mission|left|right|vcr|crew|owner|passive|ship id|numeric' \
            | head -n 700 || true
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
  find "$dst" -type f \
    \( -iname '*.pas' -o -iname '*.c' -o -iname '*.cpp' -o -iname '*.h' \
       -o -iname '*.map' -o -iname '*.sym' -o -iname '*.dbg' -o -iname '*.tds' \
       -o -iname '*.lst' \) -print | sort
}

recover_spec() {
  local spec="$1"
  local fallback_label="${2:-primary}"
  local slug id filename direct_url
  IFS='|' read -r slug id filename direct_url <<< "$spec"

  echo "===== RECOVERY TARGET: $slug ====="
  echo "role: $fallback_label"
  echo "index_id: $id"
  echo "filename: $filename"
  echo

  # A known direct archive URL is preferred specifically to avoid blocking on a
  # slow detail page. If it fails, use bounded detail-page discovery.
  if [[ -n "$direct_url" ]]; then
    if try_download "$slug" "$filename" "$direct_url"; then
      audit_archive "$slug" "$filename"
      return 0
    fi
    echo
    echo "direct recovery failed; trying bounded index-page discovery"
  fi

  fetch_page "$slug" "$id" || true
  if try_download "$slug" "$filename"; then
    audit_archive "$slug" "$filename"
    return 0
  fi

  echo
  echo "WARNING: could not automatically recover $filename."
  if [[ -s "$OUT_ROOT/pages/$slug.html" ]]; then
    echo "Saved index page: $OUT_ROOT/pages/$slug.html"
  else
    echo "Index page was unavailable within PAGE_MAX_TIME=$PAGE_MAX_TIME seconds."
  fi
  echo
  return 1
}

echo "===== INDEPENDENT THOST SIMULATOR RECOVERY ====="
echo "output: $OUT_ROOT"
echo "page_max_time: $PAGE_MAX_TIME"
echo "download_max_time: $DOWNLOAD_MAX_TIME"
echo

success=0
afsim_recovered=0
bsim22_recovered=0
bsim2_fallback_recovered=0

for spec in "${SPECS[@]}"; do
  slug="${spec%%|*}"
  if recover_spec "$spec" "primary"; then
    success=$((success + 1))
    case "$slug" in
      afsim) afsim_recovered=1 ;;
      bsim22) bsim22_recovered=1 ;;
    esac
  fi
done

if [[ "$bsim22_recovered" -eq 0 ]]; then
  echo
  echo "===== BSIM 2.00 VERSION-SCOPED FALLBACK ====="
  echo "BSIM22.ZIP was not recovered. Trying the surviving BSIM2.ZIP package"
  echo "only to inspect architecture/workflow; do not treat it as BSim 2.2."
  echo
  if recover_spec "$FALLBACK_BSIM_SPEC" "version-scoped-fallback"; then
    success=$((success + 1))
    bsim2_fallback_recovered=1
  fi
fi

echo
echo "===== RECOVERY SUMMARY ====="
echo "afsim_recovered:          $afsim_recovered"
echo "bsim22_recovered:         $bsim22_recovered"
echo "bsim2_fallback_recovered: $bsim2_fallback_recovered"
echo "archives_recovered:       $success"
echo "report: $REPORT"

if [[ "$success" -eq 0 ]]; then
  echo "ERROR: no independent simulator archive recovered." >&2
  exit 66
fi
