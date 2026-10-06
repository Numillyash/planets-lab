# Site queue executor v1 — reusable orchestration checkpoint

Date: 2026-10-06

## Closed prerequisite

Runtime evidence:

    runtime-logs/site-combat-state-v1/
    20261006T184725Z_7456617fb460

Result:

    SITE_STATE_EXACT

Transitions:

    V592 -> V593  capture_immediate_C   exact pair + sides
    V593 -> V594  capture_parent_resume exact pair + sides
    V594 -> V595  capture_immediate_C   exact pair + sides

The target chain is therefore exact while carrying SiteCombatState across the
window instead of rebuilding state after every VCR.

## Reusable capture queue core

Module:

    src/planets_lab/rules/combat/capture_queue.py

This is the pure O -> C-forward selector geometry previously exercised only in
diagnostics.

Evidence scope is explicit:

- fresh32 independently covered C-forward: 6/6 exact;
- fresh32 did not contain a qualified O case;
- complete O -> C is therefore not promoted as fully independently validated.

The core can return O, but the reusable site executor rejects O by default.

## Reusable site queue executor

Module:

    src/planets_lab/rules/combat/site_executor.py

Operations:

    select_temporary_capture_continuation(...)
    select_parent_resume(...)

Temporary continuation behavior:

- resolved C:
    keep TemporaryCaptureOrder open;
    return prize/opponent pair;
- no_pair:
    clear only TemporaryCaptureOrder;
    keep captured prize physically active;
    keep captured prize excluded from parent queue;
    return parent_resume_required;
- unresolved:
    preserve state and fail closed;
- O result:
    fail closed by default with o_branch_not_independently_covered.

Parent resume behavior:

- derive parent active membership from SiteCombatState;
- reuse carried StandardQueueState;
- delegate ordinary STANDARD selection to select_next_plain_standard;
- return pair/sides/occurrence without mutating pair history.

The executor does not reconstruct:

- diplomacy;
- pair eligibility;
- post-capture candidate dispositions;
- terminal combat outcomes;
- immediate-C LEFT/RIGHT side projection.

Those remain evidence-scoped caller inputs.

## Mainline source of truth

The independently validated fixture test now imports the selector from:

    planets_lab.rules.combat.capture_queue

rather than the old tools/diagnostics selector file.

The diagnostic copy may remain as historical provenance, but it is no longer
the mainline source of truth.

## Differential refactor

The carried-state differential:

    tools/diagnostics/combat_site_state_differential_v1.py

now delegates:

    temporary capture lifecycle -> site_executor
    parent STANDARD selection    -> site_executor

Candidate-state reconstruction remains diagnostic-specific.

Immediate C side projection remains diagnostic-specific because the side-flip
candidate is not independently promoted.

## Acceptance after merge

Rerun:

    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-site-combat-state-v1-with-evidence.sh

Pass remains:

    SITE_STATE_EXACT

with 3/3 exact transitions.

If unchanged, the next implementation step is to move pair/candidate
recomposition behind a reusable evidence-scoped input adapter so that the
diagnostic becomes only:

    corpus -> input adapter -> SiteCombatState/site_executor -> comparator

After that, factual terminal outcomes are the principal remaining injected
dependency before a genuinely generative site executor.


## Runtime infrastructure failures after merge

Two post-merge regression attempts failed before the differential executed.

First attempt:

    runtime-logs/site-combat-state-v1/
    20261006T190923Z_07e19bd01d03

Docker completed package installation but containerd died while exporting the
image:

    dial unix /run/containerd/containerd.sock: connect: connection refused
    failed to solve: Unavailable: error reading from server: EOF

Second attempt:

    runtime-logs/site-combat-state-v1/
    20261006T191604Z_07e19bd01d03

The Docker compose build process itself terminated with segmentation fault
before the diagnostic started.

These are infrastructure-only failures:

    differential executed: NO
    mechanics comparator opened: NO
    SITE_STATE result: NONE

They must not be counted as queue/executor mismatches.

## Docker-independent runtime fallback

The site-state runner now supports:

    PLANETS_SITE_STATE_RUNTIME_MODE=auto
    PLANETS_SITE_STATE_RUNTIME_MODE=docker
    PLANETS_SITE_STATE_RUNTIME_MODE=local

Default:

    auto

In auto mode:

1. Docker daemon preflight is bounded;
2. Docker image build is attempted;
3. only if preflight/build fails, execution falls back to host Python;
4. if Docker build succeeds, any nonzero exit from the actual differential is
   propagated and is not hidden by a local fallback.

Host mode reads the exact same immutable public100 generation directly from:

    PLANETS_CORPUS_DB_ROOT

and verifies the same SHA before execution.

If the host Python lacks project runtime dependencies, a cached venv is created
under:

    ~/.cache/planets-lab/site-state-v1

The repository itself remains clean.

For a currently unhealthy Docker/containerd installation, prefer the explicit
one-shot regression:

    export PLANETS_SITE_STATE_RUNTIME_MODE=local
    bash tools/run-site-combat-state-v1-with-evidence.sh

This bypasses Docker entirely while preserving the same diagnostic code,
database generation, held-out comparator, and runtime-evidence wrapper.
