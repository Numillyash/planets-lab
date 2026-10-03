#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

BASE="${INDEPENDENT_SIM_ROOT:-artifacts/external-sources/independent-sims}"
ZIP="${AFSIM_ZIP:-$BASE/downloads/AFSIM.ZIP}"
EXTRACT="${AFSIM_EXTRACT:-$BASE/extracted/afsim}"
OUT="${AFSIM_QUEUE_AUDIT_ROOT:-$BASE/afsim-queue-audit}"
REPORT="$OUT/audit.txt"

for cmd in python3 unzip sha256sum file strings stat; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command missing: $cmd" >&2
    exit 69
  fi
done

if [[ ! -f "$ZIP" ]]; then
  echo "ERROR: missing AFSim archive: $ZIP" >&2
  exit 66
fi

if ! unzip -t "$ZIP" >/dev/null 2>&1; then
  echo "ERROR: AFSim archive is not a valid ZIP: $ZIP" >&2
  exit 65
fi

mkdir -p "$EXTRACT" "$OUT"
unzip -qq -o "$ZIP" -d "$EXTRACT"

DOC="$EXTRACT/AFSIM.DOC"
EXE="$EXTRACT/AFSIM.EXE"
CFG="$EXTRACT/AFSIM.CFG"
DIZ="$EXTRACT/FILE_ID.DIZ"

for f in "$DOC" "$EXE" "$CFG" "$DIZ"; do
  if [[ ! -f "$f" ]]; then
    echo "ERROR: expected AFSim member missing after extraction: $f" >&2
    exit 66
  fi
done

exec > >(tee "$REPORT") 2>&1

echo "===== AFSIM QUEUE / CAPTURE SEMANTICS AUDIT ====="
echo "archive: $ZIP"
echo "extract: $EXTRACT"
echo "output:  $OUT"
echo

echo "===== PINNED ARTIFACT METADATA ====="
for f in "$ZIP" "$DOC" "$EXE" "$CFG" "$DIZ"; do
  printf '%s\n' "$f"
  printf '  type:   '
  file -b "$f"
  printf '  size:   '
  stat -c '%s' "$f"
  printf '  sha256: '
  sha256sum "$f" | awk '{print $1}'
done
echo

python3 - "$DOC" "$OUT/AFSIM.DOC.utf8.txt" <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
raw = src.read_bytes()

# Historical DOS documentation commonly mixes CP437 box drawing with ordinary
# ASCII. CP437 preserves those characters and is deterministic.
text = raw.decode("cp437", errors="replace")
text = text.replace("\r\n", "\n").replace("\r", "\n")
dst.write_text(text, encoding="utf-8")
print(f"normalized_doc: {dst}")
print(f"normalized_lines: {len(text.splitlines())}")
PY

DOC_UTF8="$OUT/AFSIM.DOC.utf8.txt"

echo
echo "===== MANUAL HEADER / VERSION / PROVENANCE ====="
python3 - "$DOC_UTF8" <<'PY'
from pathlib import Path
import re
import sys

lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
rx = re.compile(
    r"(?i)afsim|version|copyright|author|written|martens|shareware|register|"
    r"release|date|email|internet"
)
shown = 0
for n, line in enumerate(lines[:140], 1):
    if rx.search(line):
        print(f"{n:04d}: {line}")
        shown += 1
if not shown:
    print("(no provenance/version lines found in first 140 lines)")
PY

echo
echo "===== MANUAL FIXED HIGH-VALUE RANGES ====="
python3 - "$DOC_UTF8" <<'PY'
from pathlib import Path
import sys

lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
ranges = [
    (1, 80, "overview"),
    (180, 225, "ship input and OOB fields"),
    (240, 365, "OOB display and simulation loop"),
    (450, 535, "battle-order rules"),
]
for start, end, label in ranges:
    print()
    print(f"--- {label}: lines {start}-{end} ---")
    for n in range(start, min(end, len(lines)) + 1):
        print(f"{n:04d}: {lines[n-1]}")
PY

echo
echo "===== MANUAL KEYWORD WINDOWS ====="
python3 - "$DOC_UTF8" <<'PY'
from pathlib import Path
import re
import sys

lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
rx = re.compile(
    r"(?i)"
    r"order of battle|\bOOB\b|battle[- ]?order|attack value|"
    r"captur(?:e|ed|ing)|surrender|destroyed|surviv|"
    r"fight(?:s|ing)?|battle|primary enemy|friendly code|"
    r"kill mission|mission|owner|crew|race|"
    r"again|repeat|twice|next ship|next battle|"
    r"left|right|passive"
)
hits = [i for i, line in enumerate(lines) if rx.search(line)]
windows = []
for i in hits:
    lo = max(0, i - 6)
    hi = min(len(lines), i + 7)
    if windows and lo <= windows[-1][1]:
        windows[-1] = (windows[-1][0], max(windows[-1][1], hi))
    else:
        windows.append((lo, hi))

for lo, hi in windows:
    print()
    print(f"--- lines {lo+1}-{hi} ---")
    for i in range(lo, hi):
        print(f"{i+1:04d}: {lines[i]}")
PY

strings -a -n 4 -td "$EXE" > "$OUT/AFSIM.EXE.strings.txt"

echo
echo "===== EXECUTABLE STRING WINDOWS ====="
python3 - "$OUT/AFSIM.EXE.strings.txt" <<'PY'
from pathlib import Path
import re
import sys

lines = Path(sys.argv[1]).read_text(errors="replace").splitlines()
rx = re.compile(
    r"(?i)"
    r"captur|surrender|destroy|surviv|battle|fight|"
    r"primary enemy|friendly code|kill|mission|"
    r"owner|crew|race|order|OOB|attack value|"
    r"left|right|passive|vcr|afsvcr|log|tmp"
)
hits = [i for i, line in enumerate(lines) if rx.search(line)]
windows = []
for i in hits:
    lo = max(0, i - 8)
    hi = min(len(lines), i + 9)
    if windows and lo <= windows[-1][1]:
        windows[-1] = (windows[-1][0], max(windows[-1][1], hi))
    else:
        windows.append((lo, hi))

for lo, hi in windows:
    print()
    print(f"--- string rows {lo+1}-{hi} ---")
    for i in range(lo, hi):
        print(lines[i])
PY

echo
echo "===== CONFIGURATION ====="
python3 - "$CFG" <<'PY'
from pathlib import Path
import sys

raw = Path(sys.argv[1]).read_bytes()
print(raw.decode("cp437", errors="replace").replace("\r\n", "\n").replace("\r", "\n"))
PY

echo
echo "===== FILE_ID.DIZ ====="
python3 - "$DIZ" <<'PY'
from pathlib import Path
import sys

raw = Path(sys.argv[1]).read_bytes()
print(raw.decode("cp437", errors="replace").replace("\r\n", "\n").replace("\r", "\n"))
PY

echo
echo "===== AUDIT SUMMARY ====="
echo "normalized_manual: $DOC_UTF8"
echo "exe_strings:       $OUT/AFSIM.EXE.strings.txt"
echo "report:            $REPORT"
echo
echo "Interpretation gate:"
echo "  - establish exact automatic OOB/pair traversal from the manual first;"
echo "  - isolate explicit post-capture mutation/re-entry semantics if documented;"
echo "  - only if docs are insufficient, reverse the smallest EXE region reachable"
echo "    from capture/result-handling strings and VCR result ingestion;"
echo "  - do not promote any AFSim behavior to NuHost mechanics without a frozen"
echo "    candidate and discovery-corpus discriminator."
