#!/usr/bin/env bash
set -uo pipefail

MANIFEST="${1:-validation/corpus/manifests/accounts-recent-finished.jsonl}"
JOBS="${JOBS:-2}"
SAMPLES="${SAMPLES:-1000}"
TOP="${TOP:-150}"
STAMP="${RUN_STAMP:-$(date +%Y%m%d-%H%M%S)}"
OUT="${OUT_DIR:-runs/overnight-corpus-${STAMP}}"
LOG_DIR="${OUT}/logs"
STATUS="${OUT}/status.tsv"

mkdir -p "$LOG_DIR"
printf 'stage\texit_code\tstarted_at\tfinished_at\n' > "$STATUS"
printf '%s\n' "$OUT" > runs/overnight-latest.txt

if [[ ! -f "$MANIFEST" ]]; then
    echo "manifest not found: $MANIFEST" >&2
    exit 2
fi

run_stage() {
    local name="$1"
    shift
    local log="${LOG_DIR}/${name}.log"
    local started finished rc
    started="$(date -Iseconds)"

    echo
    echo "================================================================"
    echo "STAGE: $name"
    echo "START: $started"
    echo "CMD:   $*"
    echo "LOG:   $log"
    echo "================================================================"

    set +e
    "$@" 2>&1 | tee "$log"
    rc=${PIPESTATUS[0]}
    set -e

    finished="$(date -Iseconds)"
    printf '%s\t%s\t%s\t%s\n' "$name" "$rc" "$started" "$finished" >> "$STATUS"
    echo "STAGE DONE: $name rc=$rc finished=$finished"

    # Deliberately continue after a failed diagnostic. The overnight runner is
    # designed to maximize evidence collected before the external time limit.
    return 0
}

cat > "${OUT}/run-config.txt" <<EOF
manifest=$MANIFEST
jobs=$JOBS
samples=$SAMPLES
top=$TOP
started_at=$(date -Iseconds)
python=$(python --version 2>&1)
EOF

if command -v git >/dev/null 2>&1; then
    {
        echo "git_head=$(git rev-parse HEAD 2>/dev/null || true)"
        echo "git_branch=$(git branch --show-current 2>/dev/null || true)"
        echo "git_status_begin"
        git status --short 2>/dev/null || true
        echo "git_status_end"
    } >> "${OUT}/run-config.txt"
fi

run_stage 01-movement-pipeline-rebuild \
    python -u -m planets_lab.corpus.movement_pipeline_corpus_cli \
    "$MANIFEST" \
    --jobs "$JOBS" \
    --rebuild-prepared-cache \
    --output "${OUT}/movement-pipeline.json"

run_stage 02-compiled-movement-rebuild \
    python -u -m planets_lab.corpus.compiled_movement_corpus_cli \
    "$MANIFEST" \
    --jobs "$JOBS" \
    --rebuild \
    --output-dir validation/corpus/compiled/v1

run_stage 03-compiled-context-labels-rebuild \
    python -u -m planets_lab.corpus.compiled_movement_labels_corpus_cli \
    "$MANIFEST" \
    --jobs "$JOBS" \
    --rebuild \
    --compiled-dir validation/corpus/compiled/v1

run_stage 04-compiled-residual-cross-game-summary \
    python -u tools/diagnostics/compiled_residual_cross_game_summary.py \
    --database validation/corpus/compiled/v1/corpus.duckdb \
    --output-dir "${OUT}/compiled-residual" \
    --top "$TOP"

run_stage 05-residual-profile \
    python -u -m planets_lab.corpus.movement_residual_profile_cli \
    "$MANIFEST" \
    --top "$TOP" \
    --games-output "${OUT}/residual-profile-games.jsonl" \
    --stats-output "${OUT}/residual-profile-stats.json"

run_stage 06-horwasp-trajectory-deep \
    python -u -m planets_lab.corpus.movement_horwasp_trajectory_cli \
    "$MANIFEST" \
    --samples "$SAMPLES" \
    --output "${OUT}/horwasp-trajectory.json"

run_stage 07-horwasp-state-linkage-deep \
    python -u -m planets_lab.corpus.movement_horwasp_state_linkage_cli \
    "$MANIFEST" \
    --samples "$SAMPLES" \
    --output "${OUT}/horwasp-state-linkage.json"

run_stage 08-sphere-period-empirical \
    python -u tools/diagnostics/sphere_period_empirical_audit.py

run_stage 09-full-test-suite \
    pytest -q

{
    echo "finished_at=$(date -Iseconds)"
    echo "status_file=$STATUS"
    echo "output_dir=$OUT"
} > "${OUT}/DONE.txt"

printf '\n===== OVERNIGHT DISCOVERY COMPLETE =====\n'
cat "$STATUS"
printf '\noutput_dir=%s\n' "$OUT"
printf 'latest_pointer=runs/overnight-latest.txt\n'
