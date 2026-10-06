# New chat handoff — mutable site executor / input adapter

Date: 2026-10-06

## Scope

Continue mainline NuHost combat reconstruction in:

    Numillyash/planets-lab

Use the normal checkout:

    /root/projects/planets-lab
    ~/projects/planets-lab

Do NOT switch to research/external-engine-analysis in this chat. External-engine
research continues separately in another chat.

GitHub is the source of truth. Verify actual origin/main before doing work.

## Current mainline architecture

Reusable carried site state:

    src/planets_lab/rules/combat/site_state.py

Reusable capture queue core:

    src/planets_lab/rules/combat/capture_queue.py

Reusable queue orchestration:

    src/planets_lab/rules/combat/site_executor.py

Important state distinction:

    physically active
    != parent STANDARD queue membership
    != temporary post-capture order membership

SiteCombatState carries:

    active_ships
    StandardQueueState
      pair_occurrences
      first_pass_sides
    parent_queue_excluded_ship_ids
    temporary_capture_order

A captured prize can remain physically active while being excluded from the
parent queue. Exhausting its temporary capture order clears only that temporary
order and does not reinsert the prize into the parent queue.

## Closed runtime evidence

### History-anchored compositional site loop

Runtime:

    runtime-logs/mutable-capture-site-loop-v1/
    20261006T182353Z_af60578ecaed

Result:

    SITE_LOOP_EXACT

Summary:

    expected_transitions 3
    evaluated_transitions 3
    exact_transitions 3

Sequence:

    V592 -> V593  capture_immediate_C   exact pair + sides
    V593 -> V594  capture_parent_resume exact pair + sides
    V594 -> V595  capture_immediate_C   exact pair + sides

### Carried SiteCombatState differential

Runtime:

    runtime-logs/site-combat-state-v1/
    20261006T184725Z_7456617fb460

Result:

    SITE_STATE_EXACT

Summary:

    expected_transitions 3
    evaluated_transitions 3
    exact_transitions 3
    all_exact true

Exact transitions:

    V592 -> V593
      mode       capture_immediate_C
      predicted  [140, 170]
      factual    [140, 170]
      pair exact true
      side exact true

    V593 -> V594
      mode       capture_parent_resume
      predicted  [170, 184]
      factual    [170, 184]
      pair exact true
      side exact true

    V594 -> V595
      mode       capture_immediate_C
      predicted  [170, 382]
      factual    [170, 382]
      pair exact true
      side exact true

This is the last successful mechanics checkpoint.

## Reusable executor evidence boundary

capture_queue.py contains the pure O -> C-forward selector geometry.

Independent fresh32 support:

    C-forward: 6/6 exact

Fresh32 did not provide a qualified independent O case.

Therefore:

- reusable core can represent O;
- site_executor rejects O by default;
- O remains fail-closed with:

      o_branch_not_independently_covered

Do not silently promote O to canonical behavior.

Immediate-C LEFT/RIGHT projection remains research-candidate scope and is still
kept out of reusable canonical executor logic.

## Exact corpus backend

Shared Corpus DB root:

    /root/projects/planets-corpus-db

Inside containers:

    /corpus-db

Explicit public100 generation:

    generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb

SHA256:

    3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c

Schema:

    planets-lab.corpus-db.v2.compact1

public100 counts:

    archives       100
    source_members 224014

Do not change CURRENT merely to run diagnostics. Use explicit-generation
support.

## Infrastructure-only runtime failure after executor refactor

A later regression attempt did NOT reach mechanics execution.

Runtime:

    runtime-logs/site-combat-state-v1/
    20261006T192642Z_745b6eb4a409

Observed checkout:

    HEAD   745b6eb4a409ded32a657284311c706587786df4
    REMOTE 745b6eb4a409ded32a657284311c706587786df4

The runner selected local fallback because Docker/containerd was unhealthy.

Host default python was:

    Python 3.10.12

But pyproject requires:

    Python >=3.11

The old fallback:

1. created cached venv with Python 3.10;
2. pip install -e failed because requires-python >=3.11;
3. runner continued;
4. diagnostic then failed importing duckdb.

Observed terminal tail:

    ERROR: Package 'planets-lab' requires a different Python:
           3.10.12 not in '>=3.11'

    ModuleNotFoundError: No module named 'duckdb'

This is infrastructure/runtime selection failure only:

    differential executed: NO
    comparator opened:     NO
    mechanics mismatch:    NO

Do not count it against SITE_STATE_EXACT.

## Host runtime fallback fix

PR #129 fixed this on 2026-10-06.

Exact tested fix SHA:

    72f694bfb1e041316b761896d2c40cd8600a5306

Behavior now:

- configured host Python must exist and be >=3.11;
- automatic host selection tries:
      python3.12
      python3.11
      python3
  and accepts only >=3.11;
- an old cached site-state venv on Python 3.10 is deleted/rebuilt;
- duckdb and pyarrow are rechecked after installation;
- if no Python >=3.11 exists, runner fails clearly instead of continuing into a
  half-installed environment.

Relevant files:

    tools/run-site-combat-state-v1.sh
    tests/test_site_combat_state_runtime_fallback.py

PR CI for #129:

    PASS

## Current runner

Normal command:

    cd ~/projects/planets-lab
    git switch main
    git pull --ff-only origin main

    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db

    bash tools/run-site-combat-state-v1-with-evidence.sh

Runtime mode:

    PLANETS_SITE_STATE_RUNTIME_MODE=auto

Optional explicit host mode:

    export PLANETS_SITE_STATE_RUNTIME_MODE=local

If local fallback has no Python >=3.11 installed, either install/use Python
3.11+ or restore Docker/containerd. Do not weaken pyproject requires-python.

## Next immediate action

First verify current origin/main and runner fix.

Then rerun:

    bash tools/run-site-combat-state-v1-with-evidence.sh

Expected mechanics result:

    SITE_STATE_EXACT

with the same 3/3 transitions.

If the machine still lacks both working Docker and Python >=3.11, treat that as
infrastructure work only. Fix runtime first; do not modify combat mechanics to
make the gate pass.

## Next research implementation after regression pass

Do NOT add another one-off VCR gate.

The next code step is a reusable evidence-scoped input adapter that moves
candidate/pair recomposition out of diagnostics.

Target pipeline:

    corpus / factual pre-state
      -> combat input adapter
      -> SiteCombatState
      -> site_executor
      -> predicted engagement
      -> factual comparator

Move out of:

    tools/diagnostics/combat_site_state_differential_v1.py

at least:

- post-capture candidate-state recomposition;
- pair input recomposition for parent STANDARD resume;
- temporal diplomacy cutoff plumbing;
- current-owner / T-1 order-state assembly.

Preserve strict evidence boundaries:

- no VCR N+1 pair/side/terminal state may enter prediction of N+1;
- same-turn diplomacy calibration must be truncated through current VCR N;
- unresolved dependencies fail closed;
- O branch remains unpromoted until independently covered;
- immediate-C side projection remains research candidate unless independently
  promoted.

After adapter extraction, the diagnostic should mostly be:

    corpus reader
      -> input adapter
      -> SiteCombatState/site_executor
      -> comparator/report

## Remaining major injected dependency

After the input adapter refactor, the main remaining factual injection is:

    terminal combat outcome itself

That is the next major bridge toward a genuinely generative mutable NuHost site
executor.

## Related handoffs

Read if needed:

    docs/handoff/2026-10-06-site-combat-state-v1-ready.md
    docs/handoff/2026-10-06-site-queue-executor-v1-ready.md
    docs/handoff/2026-10-06-capture-parent-resume-v594-result.md
    docs/handoff/2026-10-06-mutable-capture-site-loop-v1-ready.md
    docs/handoff/2026-10-06-capture-queue-mainline-handoff.md

## Working style

Use GitHub-first workflow:

1. inspect actual main;
2. branch from exact main SHA;
3. change code/tests/docs;
4. PR;
5. require green CI;
6. fast-forward exact tested SHA to main;
7. verify push CI;
8. close PR if fast-forwarded manually.

Do not ask the user to paste huge logs if runtime evidence is already published
under runtime-logs.

Do not invent script names; inspect the repository first.

Do not merge research/external-engine-analysis wholesale into main.
