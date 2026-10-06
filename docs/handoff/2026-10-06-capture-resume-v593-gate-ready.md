# Capture resume V593 gate — ready

Date: 2026-10-06

## Scope

Canonical workstream:

    main

Target:

    game 400330
    turn 141
    site (1674, 2363)
    capture VCR 593

The question is deliberately narrower than a full next-pair prediction:

    after V593 capture, does the captured prize have a definitely available
    immediate O/C continuation?

If the answer is no, parent/global queue resume becomes the next bounded step.

## Held-out boundary

The gate does not use V594 pair identity as an input.

It reconstructs:

- public100 VCR593 replay terminals;
- captured prize and captor from terminal/capture state;
- capture ownership/race transfer;
- active membership after replaying factual history through V593;
- elapsed pair occurrence counts through V593;
- foreign post-capture candidate requests and strict diplomacy;
- pair eligibility under preserved/fresh captured-prize FC bounds;
- frozen site order anchored by the independently validated mainline fixture.

The historical active-membership helper requires a comparator-shaped
`current_opponent_ship_id` field. The gate supplies a sentinel ID that cannot
match a real ship and never uses the returned factual-opponent fields.

No VCR N+1 ship id, pair, side or terminal state is consumed by selection.

## Terminal statuses

    IMMEDIATE_CONTINUATION_RESOLVED

The frozen O/C cursor found a definitely eligible immediate opponent.

    NO_IMMEDIATE_CONTINUATION_PARENT_RESUME_REQUIRED

Both O and C scans exhausted under definitely skippable candidates. The next
research step is parent/global queue resume.

    IMMEDIATE_CONTINUATION_UNRESOLVED

The gate encountered an unresolved candidate dependency before it could decide.

## Runtime

Use:

    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-capture-resume-v593-gate-with-evidence.sh

Expected runtime evidence:

    runtime-logs/capture-resume-v593/<run-id>

The runtime uses the exact public100 generation:

    generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb

SHA256:

    3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c

## Repository boundary

This gate is fully mainline-native.

Do not run it from or depend on:

    research/external-engine-analysis

The external workstream may continue independently in its own chat, but it is
not a runtime dependency for this gate.
