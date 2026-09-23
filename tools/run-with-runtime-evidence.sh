#!/usr/bin/env bash
set -uo pipefail

usage() {
  cat <<'EOF'
Usage:
  tools/run-with-runtime-evidence.sh RUN_NAME [--include artifacts/path ...] -- COMMAND [ARG ...]

Runs COMMAND, captures stdout/stderr, records minimal metadata, copies explicit
artifact paths, and publishes the evidence to the orphan runtime-logs branch.

Only paths under artifacts/ may be included. The wrapper never records the
process environment or full command arguments.

Environment:
  RUNTIME_EVIDENCE_REMOTE          Git remote to push (default: origin)
  RUNTIME_EVIDENCE_BRANCH          Evidence branch (default: runtime-logs)
  RUNTIME_EVIDENCE_MAX_FILE_BYTES  Max included artifact file size (default: 10485760)
  RUNTIME_EVIDENCE_PUSH_ATTEMPTS   Publish retries for concurrent writers (default: 3)
EOF
}

if [[ $# -lt 3 ]]; then
  usage >&2
  exit 64
fi

RUN_NAME="$1"
shift

if [[ ! "$RUN_NAME" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "ERROR: RUN_NAME must match [A-Za-z0-9._-]+" >&2
  exit 64
fi

INCLUDES=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --include)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --include requires a path" >&2
        exit 64
      fi
      INCLUDES+=("$2")
      shift 2
      ;;
    --)
      shift
      break
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: expected --include or -- before command, got: $1" >&2
      exit 64
      ;;
  esac
done

if [[ $# -eq 0 ]]; then
  echo "ERROR: command is required after --" >&2
  exit 64
fi
COMMAND=("$@")

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "ERROR: must be run inside a Git repository" >&2
  exit 64
}
cd "$ROOT"

REMOTE="${RUNTIME_EVIDENCE_REMOTE:-origin}"
EVIDENCE_BRANCH="${RUNTIME_EVIDENCE_BRANCH:-runtime-logs}"
MAX_FILE_BYTES="${RUNTIME_EVIDENCE_MAX_FILE_BYTES:-10485760}"
PUSH_ATTEMPTS="${RUNTIME_EVIDENCE_PUSH_ATTEMPTS:-3}"

if [[ ! "$MAX_FILE_BYTES" =~ ^[0-9]+$ ]] || (( MAX_FILE_BYTES <= 0 )); then
  echo "ERROR: RUNTIME_EVIDENCE_MAX_FILE_BYTES must be a positive integer" >&2
  exit 64
fi
if [[ ! "$PUSH_ATTEMPTS" =~ ^[0-9]+$ ]] || (( PUSH_ATTEMPTS <= 0 )); then
  echo "ERROR: RUNTIME_EVIDENCE_PUSH_ATTEMPTS must be a positive integer" >&2
  exit 64
fi

for include in "${INCLUDES[@]}"; do
  case "$include" in
    artifacts|artifacts/*) ;;
    *)
      echo "ERROR: evidence include must be under artifacts/: $include" >&2
      exit 64
      ;;
  esac
  if [[ "$include" == /* || "$include" == *".."* ]]; then
    echo "ERROR: unsafe evidence include path: $include" >&2
    exit 64
  fi
done

SOURCE_COMMIT="$(git rev-parse HEAD)"
SOURCE_SHORT="$(git rev-parse --short=12 HEAD)"
SOURCE_BRANCH="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || printf 'DETACHED')"
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  SOURCE_DIRTY=true
else
  SOURCE_DIRTY=false
fi

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_ID="${RUN_STAMP}_${SOURCE_SHORT}"

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/planets-lab-runtime-evidence.XXXXXX")"
EVIDENCE_ROOT="$TMP_ROOT/evidence"
mkdir -p "$EVIDENCE_ROOT"

cleanup_tmp=true
cleanup() {
  if [[ "$cleanup_tmp" == true ]]; then
    rm -rf "$TMP_ROOT"
  fi
}
trap cleanup EXIT

INTERRUPTED_SIGNAL=""
on_interrupt() {
  local signal_name="$1"
  if [[ -z "$INTERRUPTED_SIGNAL" ]]; then
    INTERRUPTED_SIGNAL="$signal_name"
    echo >&2
    echo "WARNING: received $signal_name; waiting for the interrupted runner to stop, then publishing partial evidence" >&2
  fi
}
trap 'on_interrupt INT' INT
trap 'on_interrupt TERM' TERM

LOG_PATH="$EVIDENCE_ROOT/gate.log"

echo "===== RUNTIME EVIDENCE ====="
echo "run_name:       $RUN_NAME"
echo "source_commit:  $SOURCE_COMMIT"
echo "source_branch:  $SOURCE_BRANCH"
echo "evidence_branch:$EVIDENCE_BRANCH"
echo

set +e
"${COMMAND[@]}" 2>&1 | tee "$LOG_PATH"
RUN_EXIT=${PIPESTATUS[0]}
set -e

if [[ "$INTERRUPTED_SIGNAL" == "INT" ]]; then
  RUN_EXIT=130
elif [[ "$INTERRUPTED_SIGNAL" == "TERM" ]]; then
  RUN_EXIT=143
fi

# The foreground runner has stopped. Further Ctrl+C/TERM should not silently
# discard evidence while publication is in progress.
trap '' INT TERM

FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

LOG_FILE="gate.log"
if [[ -f "$LOG_PATH" ]]; then
  LOG_BYTES="$(stat -c '%s' "$LOG_PATH" 2>/dev/null || printf '0')"
  if [[ "$LOG_BYTES" =~ ^[0-9]+$ ]] && (( LOG_BYTES > MAX_FILE_BYTES )); then
    if command -v gzip >/dev/null 2>&1; then
      gzip -9 "$LOG_PATH"
      LOG_FILE="gate.log.gz"
    else
      echo "WARNING: log exceeds size threshold and gzip is unavailable" >&2
    fi
  fi
fi

MISSING_INCLUDES=()
SKIPPED_OVERSIZED=()
for include in "${INCLUDES[@]}"; do
  src="$ROOT/$include"
  if [[ ! -e "$src" ]]; then
    MISSING_INCLUDES+=("$include")
    continue
  fi

  oversized=""
  if [[ -f "$src" ]]; then
    bytes="$(stat -c '%s' "$src" 2>/dev/null || printf '0')"
    if [[ "$bytes" =~ ^[0-9]+$ ]] && (( bytes > MAX_FILE_BYTES )); then
      oversized="$src"
    fi
  else
    oversized="$(find "$src" -type f -size +"${MAX_FILE_BYTES}c" -print -quit 2>/dev/null || true)"
  fi

  if [[ -n "$oversized" ]]; then
    SKIPPED_OVERSIZED+=("$include")
    continue
  fi

  mkdir -p "$EVIDENCE_ROOT/$(dirname "$include")"
  cp -a "$src" "$EVIDENCE_ROOT/$include"
done

REQUESTED_INCLUDE_TEXT="$(printf '%s\n' "${INCLUDES[@]-}")"
MISSING_INCLUDE_TEXT="$(printf '%s\n' "${MISSING_INCLUDES[@]-}")"
SKIPPED_OVERSIZED_TEXT="$(printf '%s\n' "${SKIPPED_OVERSIZED[@]-}")"

RUN_NAME_ENV="$RUN_NAME" \
RUN_ID_ENV="$RUN_ID" \
SOURCE_COMMIT_ENV="$SOURCE_COMMIT" \
SOURCE_BRANCH_ENV="$SOURCE_BRANCH" \
SOURCE_DIRTY_ENV="$SOURCE_DIRTY" \
STARTED_AT_ENV="$STARTED_AT" \
FINISHED_AT_ENV="$FINISHED_AT" \
RUN_EXIT_ENV="$RUN_EXIT" \
INTERRUPTED_SIGNAL_ENV="$INTERRUPTED_SIGNAL" \
RUNNER_ENV="${COMMAND[0]}" \
REMOTE_ENV="$REMOTE" \
EVIDENCE_BRANCH_ENV="$EVIDENCE_BRANCH" \
LOG_FILE_ENV="$LOG_FILE" \
REQUESTED_INCLUDE_TEXT_ENV="$REQUESTED_INCLUDE_TEXT" \
MISSING_INCLUDE_TEXT_ENV="$MISSING_INCLUDE_TEXT" \
SKIPPED_OVERSIZED_TEXT_ENV="$SKIPPED_OVERSIZED_TEXT" \
python3 - "$EVIDENCE_ROOT/metadata.json" <<'PY'
import json
import os
import pathlib
import socket
import sys

def lines(name: str) -> list[str]:
    raw = os.environ.get(name, "")
    return [line for line in raw.splitlines() if line]

metadata = {
    "schema": "planets-lab.runtime-evidence.v1",
    "run_name": os.environ["RUN_NAME_ENV"],
    "run_id": os.environ["RUN_ID_ENV"],
    "source_commit": os.environ["SOURCE_COMMIT_ENV"],
    "source_branch": os.environ["SOURCE_BRANCH_ENV"],
    "source_dirty": os.environ["SOURCE_DIRTY_ENV"].lower() == "true",
    "started_at_utc": os.environ["STARTED_AT_ENV"],
    "finished_at_utc": os.environ["FINISHED_AT_ENV"],
    "exit_code": int(os.environ["RUN_EXIT_ENV"]),
    "interrupted_signal": os.environ.get("INTERRUPTED_SIGNAL_ENV") or None,
    "runner": os.environ["RUNNER_ENV"],
    "hostname": socket.gethostname(),
    "remote": os.environ["REMOTE_ENV"],
    "evidence_branch": os.environ["EVIDENCE_BRANCH_ENV"],
    "log_file": os.environ["LOG_FILE_ENV"],
    "requested_artifact_paths": lines("REQUESTED_INCLUDE_TEXT_ENV"),
    "missing_artifact_paths": lines("MISSING_INCLUDE_TEXT_ENV"),
    "skipped_oversized_artifact_paths": lines("SKIPPED_OVERSIZED_TEXT_ENV"),
}
path = pathlib.Path(sys.argv[1])
path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

cat > "$EVIDENCE_ROOT/README.txt" <<EOF
Runtime evidence generated by tools/run-with-runtime-evidence.sh

run_name: $RUN_NAME
run_id: $RUN_ID
source_commit: $SOURCE_COMMIT
exit_code: $RUN_EXIT
interrupted_signal: ${INTERRUPTED_SIGNAL:-none}

See metadata.json for machine-readable metadata.
EOF

publish_attempt() {
  local attempt="$1"
  local wt_parent="$TMP_ROOT/worktree-$attempt"
  local wt="$wt_parent/wt"
  local init_branch=""
  mkdir -p "$wt_parent"

  git fetch --quiet "$REMOTE" "+refs/heads/$EVIDENCE_BRANCH:refs/remotes/$REMOTE/$EVIDENCE_BRANCH" >/dev/null 2>&1 || true

  if git show-ref --verify --quiet "refs/remotes/$REMOTE/$EVIDENCE_BRANCH"; then
    if ! git worktree add --quiet --detach "$wt" "refs/remotes/$REMOTE/$EVIDENCE_BRANCH"; then
      return 1
    fi
  else
    if ! git worktree add --quiet --detach "$wt" "$SOURCE_COMMIT"; then
      return 1
    fi
    init_branch="runtime-evidence-init-${RUN_ID//[^A-Za-z0-9._-]/-}-$attempt"
    if ! git -C "$wt" switch --quiet --orphan "$init_branch"; then
      git worktree remove --force "$wt" >/dev/null 2>&1 || true
      return 1
    fi
    git -C "$wt" rm -rf . >/dev/null 2>&1 || true
    cat > "$wt/README.md" <<'EOF'
# Runtime evidence

Machine-generated archive-host evidence for planets-lab.

This orphan branch intentionally contains runtime logs and generated diagnostic
artifacts only. Source code and durable conclusions remain on main.
EOF
  fi

  local dest="$wt/runtime-logs/$RUN_NAME/$RUN_ID"
  mkdir -p "$dest"
  cp -a "$EVIDENCE_ROOT/." "$dest/"

  git -C "$wt" add "runtime-logs/$RUN_NAME/$RUN_ID"
  if [[ -n "$init_branch" ]]; then
    git -C "$wt" add README.md
  fi

  if ! git -C "$wt" \
      -c user.name="planets-lab runtime evidence" \
      -c user.email="runtime-evidence@planets-lab.local" \
      commit --quiet -m "runtime: $RUN_NAME $RUN_ID exit=$RUN_EXIT"; then
    git worktree remove --force "$wt" >/dev/null 2>&1 || true
    [[ -n "$init_branch" ]] && git branch -D "$init_branch" >/dev/null 2>&1 || true
    return 1
  fi

  if git -C "$wt" push --quiet "$REMOTE" "HEAD:refs/heads/$EVIDENCE_BRANCH"; then
    git worktree remove --force "$wt" >/dev/null 2>&1 || true
    [[ -n "$init_branch" ]] && git branch -D "$init_branch" >/dev/null 2>&1 || true
    return 0
  fi

  git worktree remove --force "$wt" >/dev/null 2>&1 || true
  [[ -n "$init_branch" ]] && git branch -D "$init_branch" >/dev/null 2>&1 || true
  return 1
}

PUBLISHED=false
for ((attempt=1; attempt<=PUSH_ATTEMPTS; attempt++)); do
  if publish_attempt "$attempt"; then
    PUBLISHED=true
    break
  fi
  echo "WARNING: runtime evidence push attempt $attempt/$PUSH_ATTEMPTS failed" >&2
  sleep 1
done

echo
if [[ "$PUBLISHED" == true ]]; then
  echo "runtime_evidence: published"
  echo "branch:           $EVIDENCE_BRANCH"
  echo "path:             runtime-logs/$RUN_NAME/$RUN_ID"
else
  cleanup_tmp=false
  echo "ERROR: runtime evidence could not be pushed" >&2
  echo "local_evidence: $EVIDENCE_ROOT" >&2
fi

if (( RUN_EXIT != 0 )); then
  exit "$RUN_EXIT"
fi
if [[ "$PUBLISHED" != true ]]; then
  exit 70
fi
exit 0
