#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

OUT_ROOT="${JPHOST_CVS_OUT_ROOT:-artifacts/external-sources/jphost-cvs}"
CHECKOUT="${JPHOST_CHECKOUT:-$OUT_ROOT/checkout/jhost}"
REPO="${JPHOST_CVS_REPO:-$OUT_ROOT/repository/jphost}"
REPORT="${JPHOST_AUDIT_REPORT:-$OUT_ROOT/jphost-source-audit.txt}"
JAR_OUT="${JPHOST_HISTORICAL_JAR:-$OUT_ROOT/Jhost-historical.jar}"

if [[ ! -d "$CHECKOUT/src" ]]; then
  echo "ERROR: JPHost checkout missing: $CHECKOUT" >&2
  echo "Run tools/research/fetch-jphost-cvs-snapshot.sh first." >&2
  exit 66
fi
if [[ ! -d "$REPO/CVSROOT" ]]; then
  echo "ERROR: JPHost CVS repository missing: $REPO" >&2
  exit 66
fi

REPO_ABS="$(readlink -f "$REPO")"
CVSROOT_LOCAL=":local:$REPO_ABS"
mkdir -p "$(dirname "$REPORT")"

exec > >(tee "$REPORT") 2>&1

echo "===== JPHOST SOURCE AUDIT ====="
echo "checkout:      $(readlink -f "$CHECKOUT")"
echo "repository:    $REPO_ABS"
echo "cvsroot:       $CVSROOT_LOCAL"
if [[ -s "$OUT_ROOT/jphost-cvs.zip" ]]; then
  echo -n "snapshot_sha:  "
  sha256sum "$OUT_ROOT/jphost-cvs.zip" | awk '{print $1}'
fi
echo

echo "===== SOURCE COUNTS ====="
printf 'java_files:      '
find "$CHECKOUT/src" -type f -name '*.java' | wc -l
printf 'test_java_files: '
find "$CHECKOUT/test" -type f -name '*.java' 2>/dev/null | wc -l || true
printf 'source_bytes:    '
find "$CHECKOUT/src" -type f -name '*.java' -printf '%s\n' | awk '{s+=$1} END{print s+0}'
echo

echo "===== COMPLETE SERVER-SIDE JAVA INVENTORY ====="
find "$CHECKOUT/src" -type f -name '*.java' \
  ! -path '*/jhostclient/*' \
  | sort

echo
echo "===== PACKAGE / CLASS INVENTORY ====="
grep -RHE '^[[:space:]]*(public[[:space:]]+)?(abstract[[:space:]]+)?(class|interface)[[:space:]]+[A-Za-z0-9_]+' \
  "$CHECKOUT/src" "$CHECKOUT/test" \
  --include='*.java' 2>/dev/null | sort || true

echo
echo "===== COMBAT / CAPTURE FILENAMES ====="
find "$CHECKOUT/src" "$CHECKOUT/test" -type f \
  \( -iname '*combat*' -o -iname '*battle*' -o -iname '*vcr*' \
     -o -iname '*capture*' -o -iname '*aggress*' -o -iname '*enemy*' \) \
  | sort || true

echo
echo "===== COMBAT / CAPTURE SYMBOL SEARCH ====="
grep -RniE \
  'combat|battle|capture|captured|vcr|aggress(or|ive|ion)?|opponent|primary.?enemy|friendly.?code|kill.?mission|mission.?4|crew.?10|setCrew|setOwner|battle.?order|fight' \
  "$CHECKOUT/src" "$CHECKOUT/test" "$CHECKOUT/config" "$CHECKOUT/game" "$CHECKOUT/global" \
  --include='*.java' --include='*.xml' --include='*.properties' --include='*.txt' \
  2>/dev/null | sort || true

echo
echo "===== HOST PIPELINE SYMBOL SEARCH ====="
grep -RniE \
  'ProcessTurn|processTurn|stage|phase|command|bean|JHost|BoardingParties|Combat|TransferOwner|CreateResults' \
  "$CHECKOUT/src/jhost" "$CHECKOUT/src/jhostcore" "$CHECKOUT/config" \
  --include='*.java' --include='*.xml' --include='*.properties' \
  2>/dev/null | sort || true

dump_file() {
  local label="$1"
  local file="$2"
  echo
  echo "===== FILE: $label ====="
  if [[ -f "$file" ]]; then
    nl -ba "$file"
  else
    echo "MISSING: $file"
  fi
}

dump_file "src/jhost/JHost.java" "$CHECKOUT/src/jhost/JHost.java"
dump_file "src/jhost/commands/ProcessTurn.java" "$CHECKOUT/src/jhost/commands/ProcessTurn.java"
dump_file "src/jhost/commands/CreateResults.java" "$CHECKOUT/src/jhost/commands/CreateResults.java"
dump_file "config/jhostcore.xml" "$CHECKOUT/config/jhostcore.xml"
dump_file "config/game.xml" "$CHECKOUT/config/game.xml"
dump_file "README.txt" "$CHECKOUT/README.txt"
dump_file "Changes.txt" "$CHECKOUT/Changes.txt"
dump_file "notas.txt" "$CHECKOUT/notas.txt"

echo
echo "===== CVS LOG: PIPELINE FILES ====="
for rel in   jhost/src/jhost/JHost.java   jhost/src/jhost/commands/ProcessTurn.java   jhost/src/jhost/commands/CreateResults.java   jhost/Changes.txt   jhost/README.txt
do
  echo
  echo "--- $rel ---"
  cvs -Q -d "$CVSROOT_LOCAL" log "$rel" 2>&1 || true
done

echo
echo "===== CVS HISTORY: COMBAT/CAPTURE TERMS ====="
if [[ -f "$REPO_ABS/CVSROOT/history" ]]; then
  grep -niE 'combat|battle|capture|captur|vcr|phost|host' \
    "$REPO_ABS/CVSROOT/history" | tail -n 300 || true
fi

echo
echo "===== ATTIC JHOST.JAR CVS LOG ====="
JAR_RCS="$REPO_ABS/jhost/Attic/Jhost.jar,v"
if [[ -f "$JAR_RCS" ]]; then
  cvs -Q -d "$CVSROOT_LOCAL" log jhost/Attic/Jhost.jar 2>&1 || true

  revision="$(
    cvs -Q -d "$CVSROOT_LOCAL" log jhost/Attic/Jhost.jar 2>/dev/null \
      | awk '/^revision [0-9.]+/{print $2; exit}'
  )"
  if [[ -n "$revision" ]]; then
    echo "historical_jar_revision: $revision"
    rm -f "$JAR_OUT"
    if cvs -Q -d "$CVSROOT_LOCAL" checkout -p -r "$revision" \
      jhost/Attic/Jhost.jar > "$JAR_OUT"; then
      echo -n "historical_jar_sha256:  "
      sha256sum "$JAR_OUT" | awk '{print $1}'
      echo -n "historical_jar_size:    "
      stat -c '%s' "$JAR_OUT"
      echo
      echo "===== HISTORICAL JAR CLASS INVENTORY ====="
      if unzip -t "$JAR_OUT" >/dev/null 2>&1; then
        unzip -Z1 "$JAR_OUT" \
          | grep -Ei '(^|/)(jhost|phost)|combat|battle|capture|vcr|ship|turn' \
          | sort || true
        echo
        echo "===== JAR CLASSES ABSENT FROM CHECKED-OUT SOURCE ====="
        tmp_classes="$(mktemp)"
        tmp_sources="$(mktemp)"
        trap 'rm -f "$tmp_classes" "$tmp_sources"' EXIT
        unzip -Z1 "$JAR_OUT" \
          | awk '/\.class$/ {sub(/\.class$/, ""); gsub("/", "."); print}' \
          | sort -u > "$tmp_classes"
        find "$CHECKOUT/src" -type f -name '*.java' -print \
          | sed "s#^$CHECKOUT/src/##; s#\.java$##; s#/#.#g" \
          | sort -u > "$tmp_sources"
        comm -23 "$tmp_classes" "$tmp_sources" || true
      else
        echo "WARNING: recovered historical Jhost.jar did not validate as ZIP/JAR"
      fi
    else
      echo "WARNING: could not recover historical Jhost.jar revision $revision"
      rm -f "$JAR_OUT"
    fi
  fi
else
  echo "No Attic/Jhost.jar,v found."
fi

echo
echo "===== AUDIT COMPLETE ====="
echo "report: $REPORT"
