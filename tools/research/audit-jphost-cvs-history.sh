#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

OUT_ROOT="${JPHOST_CVS_OUT_ROOT:-artifacts/external-sources/jphost-cvs}"
CHECKOUT="${JPHOST_CHECKOUT:-$OUT_ROOT/checkout/jhost}"
REPO="${JPHOST_CVS_REPO:-$OUT_ROOT/repository/jphost}"
REPORT="${JPHOST_HISTORY_REPORT:-$OUT_ROOT/jphost-history-attic-audit.txt}"
JAR_OUT="${JPHOST_HISTORICAL_JAR:-$OUT_ROOT/Jhost-historical.jar}"
ATTIC_SRC_OUT="${JPHOST_ATTIC_SOURCE_OUT:-$OUT_ROOT/attic-source}"

if [[ ! -d "$CHECKOUT/CVS" || ! -d "$CHECKOUT/src" ]]; then
  echo "ERROR: checked-out JPHost working tree missing: $CHECKOUT" >&2
  exit 66
fi
if [[ ! -d "$REPO/CVSROOT" ]]; then
  echo "ERROR: raw JPHost CVS repository missing: $REPO" >&2
  exit 66
fi
if ! command -v cvs >/dev/null 2>&1; then
  echo "ERROR: cvs client is required." >&2
  exit 69
fi

REPO_ABS="$(readlink -f "$REPO")"
CHECKOUT_ABS="$(readlink -f "$CHECKOUT")"
CVSROOT_LOCAL=":local:$REPO_ABS"

mkdir -p "$(dirname "$REPORT")" "$ATTIC_SRC_OUT"
exec > >(tee "$REPORT") 2>&1

echo "===== JPHOST CVS HISTORY / ATTIC AUDIT ====="
echo "checkout:      $CHECKOUT_ABS"
echo "repository:    $REPO_ABS"
echo "cvsroot:       $CVSROOT_LOCAL"
if [[ -s "$OUT_ROOT/jphost-cvs.zip" ]]; then
  echo -n "snapshot_sha:  "
  sha256sum "$OUT_ROOT/jphost-cvs.zip" | awk '{print $1}'
fi

echo
echo "===== RAW ATTIC INVENTORY ====="
find "$REPO_ABS/jhost" -type f -path '*/Attic/*,v' | sort

echo
echo "===== RAW ATTIC JAVA INVENTORY ====="
mapfile -t attic_java_rcs < <(
  find "$REPO_ABS/jhost" -type f -path '*/Attic/*.java,v' | sort
)
if [[ "${#attic_java_rcs[@]}" -eq 0 ]]; then
  echo "attic_java_files: 0"
else
  printf 'attic_java_files: %d\n' "${#attic_java_rcs[@]}"
  printf '%s\n' "${attic_java_rcs[@]}"
fi

echo
echo "===== RAW RCS COMBAT/CAPTURE SEARCH ====="
# RCS files contain complete text for at least one revision plus reverse deltas.
# This search is not a source reconstruction; it is a high-recall historical
# inventory to detect mechanics symbols that no longer exist in HEAD.
grep -RaniE   'combat|battle|capture|captured|vcr|aggress(or|ive|ion)?|opponent|primary.?enemy|battle.?order|friendly.?code|crew.?10|setCrew|setOwner|fight'   "$REPO_ABS/jhost/src" "$REPO_ABS/jhost/test"   --include='*,v' 2>/dev/null | head -n 1200 || true

echo
echo "===== RLOG: ACTIVE PIPELINE FILES ====="
for rel in   jhost/src/jhost/JHost.java   jhost/src/jhost/commands/ProcessTurn.java   jhost/src/jhost/commands/CreateResults.java   jhost/src/jhost/ship/Ship.java   jhost/Changes.txt   jhost/notas.txt   jhost/README.txt
do
  echo
  echo "--- $rel ---"
  cvs -Q -d "$CVSROOT_LOCAL" rlog "$rel" 2>&1 || true
done

echo
echo "===== WORKING-COPY LOG CROSSCHECK ====="
(
  cd "$CHECKOUT_ABS"
  for rel in     src/jhost/JHost.java     src/jhost/commands/ProcessTurn.java     src/jhost/commands/CreateResults.java     src/jhost/ship/Ship.java     Changes.txt     notas.txt     README.txt
  do
    echo
    echo "--- $rel ---"
    cvs -Q log "$rel" 2>&1 || true
  done
)

echo
echo "===== RECOVER DELETED ATTIC JAVA ====="
rm -rf "$ATTIC_SRC_OUT"
mkdir -p "$ATTIC_SRC_OUT"

recover_attic_java() {
  local rcs="$1"
  local physical="${rcs#"$REPO_ABS/"}"
  local logical="${physical/\/Attic\//\/}"
  logical="${logical%,v}"
  local log tmp revision state

  echo
  echo "--- $logical ---"
  log="$(cvs -Q -d "$CVSROOT_LOCAL" rlog "$logical" 2>&1 || true)"
  printf '%s\n' "$log" | sed -n '1,180p'

  # Choose the newest non-dead revision from rlog. CVS rlog prints:
  #   revision X
  #   date: ...; author: ...; state: Exp;
  revision="$(
    printf '%s\n' "$log" | awk '
      /^revision [0-9.]+/ { rev=$2; next }
      rev != "" && /state: [^;]+;/ {
        if ($0 !~ /state: dead;/) { print rev; exit }
        rev=""
      }
    '
  )"

  if [[ -z "$revision" ]]; then
    echo "recover_status: no-live-revision"
    return
  fi

  echo "recover_revision: $revision"
  tmp="$ATTIC_SRC_OUT/${logical#jhost/}"
  mkdir -p "$(dirname "$tmp")"
  if cvs -Q -d "$CVSROOT_LOCAL" checkout -p -r "$revision" "$logical" > "$tmp"; then
    echo "recover_status: ok"
    echo -n "sha256: "
    sha256sum "$tmp" | awk '{print $1}'
    echo "combat_hits:"
    grep -niE       'combat|battle|capture|captured|vcr|aggress(or|ive|ion)?|opponent|primary.?enemy|battle.?order|crew.?10|fight'       "$tmp" || true
  else
    echo "recover_status: failed"
    rm -f "$tmp"
  fi
}

for rcs in "${attic_java_rcs[@]}"; do
  recover_attic_java "$rcs"
done

echo
echo "===== HISTORICAL JHOST.JAR RLOG ====="
JAR_RCS="$REPO_ABS/jhost/Attic/Jhost.jar,v"
if [[ ! -f "$JAR_RCS" ]]; then
  echo "historical_jar_rcs: absent"
else
  jar_log="$(cvs -Q -d "$CVSROOT_LOCAL" rlog jhost/Jhost.jar 2>&1 || true)"
  printf '%s\n' "$jar_log"

  revision="$(
    printf '%s\n' "$jar_log" | awk '
      /^revision [0-9.]+/ { rev=$2; next }
      rev != "" && /state: [^;]+;/ {
        if ($0 !~ /state: dead;/) { print rev; exit }
        rev=""
      }
    '
  )"

  if [[ -z "$revision" ]]; then
    # Defensive fallback for unusual binary RCS logs: use physical RCS head,
    # then let checkout report whether that revision is dead.
    revision="$(sed -n 's/^head[[:space:]]\+\([0-9.][0-9.]*\);/\1/p' "$JAR_RCS" | head -n 1)"
    echo "historical_jar_revision_source: raw-head-fallback"
  else
    echo "historical_jar_revision_source: rlog-live"
  fi

  echo "historical_jar_revision: ${revision:-NONE}"
  rm -f "$JAR_OUT"

  if [[ -n "$revision" ]] &&      cvs -Q -d "$CVSROOT_LOCAL" checkout -p -r "$revision"        jhost/Jhost.jar > "$JAR_OUT"; then
    echo "historical_jar_recover: ok"
    echo -n "historical_jar_sha256: "
    sha256sum "$JAR_OUT" | awk '{print $1}'
    echo -n "historical_jar_size:   "
    stat -c '%s' "$JAR_OUT"

    if unzip -t "$JAR_OUT" >/dev/null 2>&1; then
      echo "historical_jar_zipcheck: ok"

      echo
      echo "===== HISTORICAL JAR: ALL CLASS NAMES ====="
      unzip -Z1 "$JAR_OUT" | awk '/\.class$/' | sort

      echo
      echo "===== HISTORICAL JAR: COMBAT/CAPTURE CLASS NAMES ====="
      unzip -Z1 "$JAR_OUT"         | grep -Ei 'combat|battle|capture|captur|vcr|aggress|opponent|enemy|fight'         | sort || true

      echo
      echo "===== HISTORICAL JAR: CLASSES ABSENT FROM CURRENT SOURCE ====="
      tmp_classes="$(mktemp)"
      tmp_sources="$(mktemp)"
      trap 'rm -f "$tmp_classes" "$tmp_sources"' EXIT

      unzip -Z1 "$JAR_OUT"         | awk '/\.class$/ {
            sub(/\.class$/, "");
            gsub("/", ".");
            sub(/\$.*$/, "");
            print
          }'         | sort -u > "$tmp_classes"

      find "$CHECKOUT_ABS/src" -type f -name '*.java' -print         | sed "s#^$CHECKOUT_ABS/src/##; s#\.java$##; s#/#.#g"         | sort -u > "$tmp_sources"

      comm -23 "$tmp_classes" "$tmp_sources" || true

      if command -v javap >/dev/null 2>&1; then
        echo
        echo "===== HISTORICAL JAR: TARGETED JAVAP ====="
        mapfile -t target_classes < <(
          unzip -Z1 "$JAR_OUT"             | awk '/\.class$/ {
                sub(/\.class$/, "");
                gsub("/", ".");
                if (tolower($0) ~ /(combat|battle|capture|vcr|fight)/ ||
                    $0 ~ /^jhost\.JHost$/ ||
                    $0 ~ /^jhost\.ship\.Ship$/) print
              }'             | sort -u
        )
        if [[ "${#target_classes[@]}" -eq 0 ]]; then
          echo "target_classes: none"
        else
          for cls in "${target_classes[@]}"; do
            echo
            echo "--- javap $cls ---"
            javap -classpath "$JAR_OUT" -c -p "$cls" 2>&1 | sed -n '1,500p' || true
          done
        fi
      else
        echo "javap: unavailable; class-name audit still complete"
      fi
    else
      echo "historical_jar_zipcheck: FAILED"
    fi
  else
    echo "historical_jar_recover: failed"
    rm -f "$JAR_OUT"
  fi
fi

echo
echo "===== HISTORY / ATTIC AUDIT COMPLETE ====="
echo "report:       $REPORT"
echo "attic_source: $ATTIC_SRC_OUT"
echo "jar:          $JAR_OUT"
