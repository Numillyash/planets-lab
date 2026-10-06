# Capture parent resume V594 gate — ready

Date: 2026-10-06

## Precondition established at runtime

Runtime evidence:

    runtime-logs/capture-resume-v593/
    20261006T161754Z_2de3567c3e76

Target:

    game 400330
    turn 141
    site (1674, 2363)
    capture VCR 593

Observed held-out-safe result:

    capture prize            ship140
    captor                   ship170
    prize new owner          10
    immediate O/C selection  no_pair
    reason                   o_and_c_forward_exhausted
    unresolved               none

Status:

    NO_IMMEDIATE_CONTINUATION_PARENT_RESUME_REQUIRED

The captured ship remains physically active, but its immediate temporary
capture-order has no definitely eligible continuation.

## Parent queue hypothesis under test

After an immediate capture-order exhausts:

1. keep the prize physically alive;
2. remove only its exhausted temporary capture-order from parent STANDARD
   selection;
3. resume the parent mutable queue over the remaining active ships;
4. preserve factual pair occurrence / first-pass side history through the
   capture VCR;
5. use the production plain-STANDARD selector;
6. compare the predicted pair and sides with the held-out next VCR only after
   selection.

This is a bounded orchestration hypothesis, not yet a canonical rule.

## Held-out discipline

The parent-resume gate is:

    tools/diagnostics/combat_capture_parent_resume_v594_gate.py

The gate first reruns the V593 immediate-continuation gate and refuses parent
resume unless it returns:

    NO_IMMEDIATE_CONTINUATION_PARENT_RESUME_REQUIRED

It also refuses to proceed if any prize candidate state is unresolved.

For parent pair composition:

- only T-1 ship order/identity inputs are used for non-prize ships;
- prize140 is removed from parent selection only after its temporary capture
  cursor is proven exhausted;
- all diplomacy calibration rows from battle turn 141 are removed;
- no pair-specific knowledge of V594 is used to prepare diplomacy;
- pair occurrence and first-pass side history consume factual VCR rows only
  through V593.

Only after:

    select_next_plain_standard(...)

returns does the gate read V594 pair and sides for comparison.

## Why T-1 pair inputs are safe for the remaining parent set

The physical active set after V593 is:

    [140, 170, 184, 195, 280, 285, 330, 382, 471]

The only ship whose owner is changed by the V592/V593 capture sequence is the
temporary prize140.

After its immediate capture-order is exhausted, the parent candidate set under
test is therefore:

    [170, 184, 195, 280, 285, 330, 382, 471]

These ships retain their T-1 ownership identity through V593, so the existing
production pair-decision inputs can be reused for this bounded parent-resume
test.

## Runtime

After merge to main:

    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-capture-parent-resume-v594-gate-with-evidence.sh

Exact source DB:

    generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb

SHA256:

    3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c

Terminal results:

    PARENT_RESUME_EXACT
    PARENT_RESUME_MISMATCH
    PARENT_RESUME_UNRESOLVED
    PARENT_RESUME_NO_PAIR_MISMATCH
    PARENT_RESUME_PRECONDITION_NOT_MET
    PARENT_RESUME_UNRESOLVED_PRIZE_DEPENDENCY

Only PARENT_RESUME_EXACT is a pass.

## Research consequence

If V594 is predicted exactly, the site chain obtains a compositional transition:

    V592 capture -> immediate C continuation V593
    V593 capture -> no immediate continuation
    parent queue resume -> V594

The already independently tested next capture continuation is then:

    V594 capture -> immediate C continuation V595

That would establish the first concrete alternating capture/parent/capture
mutable-queue chain in Nu evidence.

If V594 mismatches, the residual is specifically parent-resume cursor/state,
not capture side or immediate C-forward selection.
