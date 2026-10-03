#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

BASE_URL="${PCC1_BASE_URL:-https://phost.de/~stefan/planets}"
OUT_ROOT="${PCC1_LINEAGE_ROOT:-artifacts/external-sources/pcc1-lineage}"
REPORT="${PCC1_LINEAGE_REPORT:-$OUT_ROOT/pcc1-simulator-lineage.txt}"

# 1.1.20 = 2020-04-18
# 1.1.21 = 2021-05-31 (five days before c2ng's captured-LEFT fix)
# 1.1.22 = 2024-04-28
read -r -a VERSIONS <<< "${PCC1_LINEAGE_VERSIONS:-1120 1121 1122}"

for cmd in curl unzip sha256sum strings file grep find awk sed sort diff python3 stat; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command is missing: $cmd" >&2
    exit 69
  fi
done

mkdir -p "$OUT_ROOT/downloads" "$OUT_ROOT/extracted" "$OUT_ROOT/derived"
exec > >(tee "$REPORT") 2>&1

echo "===== PCC1 SIMULATOR LINEAGE AUDIT ====="
echo "base_url: $BASE_URL"
printf 'versions:'
printf ' %s' "${VERSIONS[@]}"
echo
echo

release_date() {
  case "$1" in
    1120) echo "2020-04-18" ;;
    1121) echo "2021-05-31" ;;
    1122) echo "2024-04-28" ;;
    *)    echo "unknown" ;;
  esac
}

download_pkg() {
  local name="$1"
  local dst="$OUT_ROOT/downloads/$name"
  local url="$BASE_URL/$name"

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
  unzip -t "$dst" >/dev/null
  echo "zipcheck: ok"
  echo
}

extract_pkg() {
  local name="$1"
  local stem="${name%.zip}"
  local src="$OUT_ROOT/downloads/$name"
  local dst="$OUT_ROOT/extracted/$stem"
  rm -rf "$dst"
  mkdir -p "$dst"
  unzip -qq -o "$src" -d "$dst"
}

find_one() {
  local root="$1"
  shift
  find "$root" -type f "$@" -print | head -n 1
}

analyze_map() {
  local ver="$1"
  local map="$2"
  local symout="$OUT_ROOT/derived/cc$ver-simulator-symbols.txt"
  local gapout="$OUT_ROOT/derived/cc$ver-target-gaps.txt"

  echo "===== MAP TARGETS: PCC $ver ====="
  echo "map: $map"
  grep -aniE     'CalcBattleOrder|MakeVCR|MakePlanetVCR|KeepVCR|FreeVCRList|SortFCBO|FillInPlanetAggressiveness|SetShipOwner|Attacking|IsAttacking|Capture|Captured|Aggressor|Opponent'     "$map" || true
  echo

  python3 - "$map" "$symout" "$gapout" <<'PY'
import re
import sys
from pathlib import Path

map_path = Path(sys.argv[1])
sym_path = Path(sys.argv[2])
gap_path = Path(sys.argv[3])

rx = re.compile(r"^\s*([0-9A-Fa-f]+):([0-9A-Fa-f]+)\s+(\S+)")
rows = []
for raw in map_path.read_text(errors="replace").splitlines():
    m = rx.match(raw)
    if m:
        rows.append((m.group(1).upper(), int(m.group(2), 16), m.group(3), raw))

segments = [seg for seg, off, name, raw in rows if name.lower() == "calcbattleorder".lower()]
if not segments:
    print("ERROR: CalcBattleOrder not found in MAP", file=sys.stderr)
    raise SystemExit(2)
seg = segments[0]

dedup = {}
for s, off, name, raw in rows:
    if s == seg:
        dedup[(off, name)] = raw
ordered = sorted((off, name, raw) for (off, name), raw in dedup.items())

with sym_path.open("w", encoding="utf-8") as f:
    f.write(f"segment={seg}\n")
    for off, name, raw in ordered:
        f.write(f"{seg}:{off:04X} {name}\n")

targets = [
    "SetShipOwner",
    "SortFCBO",
    "CalcBattleOrder",
    "FreeVCRList",
    "KeepVCR",
    "MakeVCR",
    "MakePlanetVCR",
    "NoFightWarning",
    "FillInPlanetAggressiveness",
    "SortResult",
]
with gap_path.open("w", encoding="utf-8") as f:
    f.write(f"segment={seg}\n")
    for target in targets:
        idxs = [i for i, (_, name, _) in enumerate(ordered) if name.lower() == target.lower()]
        if not idxs:
            f.write(f"{target}: absent\n")
            continue
        i = idxs[0]
        off, name, _ = ordered[i]
        if i + 1 < len(ordered):
            noff, nname, _ = ordered[i + 1]
            f.write(f"{target}: {seg}:{off:04X} next={nname}@{seg}:{noff:04X} delta=0x{noff-off:X}\n")
        else:
            f.write(f"{target}: {seg}:{off:04X} next=<none>\n")

print(f"simulator_segment: {seg}")
print(f"simulator_symbols: {len(ordered)}")
print(f"symbols_file: {sym_path}")
print(f"gaps_file: {gap_path}")
PY

  echo "--- complete simulator segment symbols ---"
  cat "$symout"
  echo
  echo "--- target spacing ---"
  cat "$gapout"
  echo

  echo "===== MAP SEGMENT TABLE CONTEXT: PCC $ver ====="
  # The first MAP section describes code/data segments. Show the beginning and
  # any entry whose start/name references the simulator segment.
  sed -n '1,120p' "$map"
  echo
  grep -aniE '(^|[[:space:]])2A92|sim|battle|vcr' "$map" | head -n 260 || true
  echo
}

analyze_debug_metadata() {
  local ver="$1"
  local dm="$2"

  echo "===== CC.DM TARGETS: PCC $ver ====="
  echo "dm: $dm"
  grep -aniE     'ccsim|CalcBattleOrder|MakeVCR|MakePlanetVCR|KeepVCR|SortFCBO|battle|combat|captur|aggress|opponent|passive|left|right'     "$dm" | head -n 500 || true
  echo
  echo "--- CC.DM head ---"
  sed -n '1,160p' "$dm" || true
  echo
}

analyze_doc() {
  local ver="$1"
  local doc="$2"

  echo "===== CCBSIM.DOC RELEVANT RULES: $ver ====="
  echo "doc: $doc"
  sed -n '145,195p' "$doc" || true
  echo
  echo "===== CCBSIM.DOC CHANGELOG HITS: $ver ====="
  grep -aniE -B4 -A8     '1\.1\.(20|21|22)|battle order|active/passive|aggress(or|ive)|opponent|captur|fight several times|friendly code'     "$doc" | head -n 700 || true
  echo
}

analyze_binary() {
  local label="$1"
  local f="$2"

  echo "===== BINARY FINGERPRINT: $label ====="
  echo "file: $f"
  file "$f" || true
  echo -n "size:   "
  stat -c '%s' "$f"
  echo -n "sha256: "
  sha256sum "$f" | awk '{print $1}'
  echo "--- targeted strings ---"
  strings -a -n 4 -td "$f" 2>/dev/null     | grep -iE       'battle order|captured back|captured by|was captured|we captured|they captured|passive|aggressive|aggressor|opponent|random left/right|left/right balance|primary enemy|change ship id|fight several times|no fights'     | head -n 500 || true
  echo
}

for ver in "${VERSIONS[@]}"; do
  echo "################################################################"
  echo "### PCC 1.1.${ver#11} family"
  echo "### release_date: $(release_date "$ver")"
  echo "################################################################"
  echo

  for pkg in "cc$ver.zip" "cc${ver}db.zip" "ccbsim$ver.zip"; do
    download_pkg "$pkg"
    extract_pkg "$pkg"
  done

  main_dir="$OUT_ROOT/extracted/cc$ver"
  db_dir="$OUT_ROOT/extracted/cc${ver}db"
  sim_dir="$OUT_ROOT/extracted/ccbsim$ver"

  map="$(find "$db_dir" -maxdepth 2 -type f -iname '*.MAP' -print | head -n 1 || true)"
  dm="$(find "$db_dir" -maxdepth 2 -type f -iname 'CC.DM' -print | head -n 1 || true)"
  doc="$(find "$sim_dir" -maxdepth 2 -type f -iname 'CCBSIM.DOC' -print | head -n 1 || true)"
  ovr="$(find "$main_dir" -maxdepth 2 -type f -iname 'CC.OVR' -print | head -n 1 || true)"
  ccexe="$(find "$main_dir" -maxdepth 2 -type f -iname 'CC.EXE' -print | head -n 1 || true)"
  simexe="$(find "$sim_dir" -maxdepth 2 -type f -iname 'CCBSIM.EXE' -print | head -n 1 || true)"

  [[ -n "$map" ]] && analyze_map "$ver" "$map" || echo "WARN: MAP missing for $ver"
  [[ -n "$dm" ]] && analyze_debug_metadata "$ver" "$dm" || echo "WARN: CC.DM missing for $ver"
  [[ -n "$doc" ]] && analyze_doc "$ver" "$doc" || echo "WARN: CCBSIM.DOC missing for $ver"
  [[ -n "$ovr" ]] && analyze_binary "PCC $ver CC.OVR" "$ovr"
  [[ -n "$ccexe" ]] && analyze_binary "PCC $ver CC.EXE" "$ccexe"
  [[ -n "$simexe" ]] && analyze_binary "CCBSim $ver CCBSIM.EXE" "$simexe"
done

echo "===== CROSS-VERSION SIMULATOR SYMBOL DIFFS ====="
for ((i=0; i+1<${#VERSIONS[@]}; ++i)); do
  a="${VERSIONS[$i]}"
  b="${VERSIONS[$((i+1))]}"
  fa="$OUT_ROOT/derived/cc$a-simulator-symbols.txt"
  fb="$OUT_ROOT/derived/cc$b-simulator-symbols.txt"
  echo
  echo "--- $a -> $b ---"
  if [[ -f "$fa" && -f "$fb" ]]; then
    diff -u "$fa" "$fb" || true
  fi
done

echo
echo "===== CROSS-VERSION TARGET-SPACING DIFFS ====="
for ((i=0; i+1<${#VERSIONS[@]}; ++i)); do
  a="${VERSIONS[$i]}"
  b="${VERSIONS[$((i+1))]}"
  fa="$OUT_ROOT/derived/cc$a-target-gaps.txt"
  fb="$OUT_ROOT/derived/cc$b-target-gaps.txt"
  echo
  echo "--- $a -> $b ---"
  if [[ -f "$fa" && -f "$fb" ]]; then
    diff -u "$fa" "$fb" || true
  fi
done

echo
echo "===== LINEAGE AUDIT COMPLETE ====="
echo "report:  $REPORT"
echo "derived: $OUT_ROOT/derived"
