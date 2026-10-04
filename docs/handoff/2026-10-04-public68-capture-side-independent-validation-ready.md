# Public68 capture-side independent validation — runner ready

Date: 2026-10-04

Status:

    RUNTIME_PENDING

## Evidence boundary

The post-heldout capture-side candidate was recorded at:

    592607b07efa0f857521da05fe0651127ed8be2d

Candidate source:

    tools/diagnostics/combat_public_capture_side_postheldout_candidate.py

The independent validation wrapper requires that commit to be an ancestor of
HEAD and additionally requires the candidate source file to have no diff from
that frozen commit.

The new evidence population is the 32-game short public expansion:

    validation/corpus/manifests/public-short-expansion-selected.jsonl
    validation/corpus/index/public-short-expansion-games.jsonl

It was selected independently of the post-heldout capture-side result and has
zero game-id overlap with the original public36 population.

Canonical Corpus DB CURRENT at validation time must be exactly:

    generations/corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb

The runner checks all of these boundaries before probing mechanics.

## Runner

Use:

    bash tools/run-public-capture-side-independent-validation-with-evidence.sh

Pipeline:

1. verify short32 manifest/index = 32 games and zero overlap with public36;
2. read all short32 source members from canonical public68 Corpus DB read-only;
3. harvest all ship-to-ship post-capture observations from short32;
4. run O-layer reconstruction per game in isolated processes;
5. evaluate the frozen post-heldout candidate only on globally adjacent
   capture -> next-VCR rows;
6. merge the per-game reports;
7. emit a durable gate report and runtime evidence.

Artifacts:

    artifacts/public-capture-side/independent-short32-capture-side.json
    artifacts/public-capture-side/independent-short32-postheldout-validation.json
    artifacts/public-capture-side/independent-short32-postheldout-gate.json

## Gate semantics

Mismatch is a real independent failure.

Unresolved/missing candidate rows make the gate incomplete.

If every adjacent independent row is exact, the candidate gate passes for the
observed population. Canonical promotion nevertheless requires independent
coverage of all four frozen branches:

    reachable_sticky
    nonreachable_neutral_fresh_fc
    second_occurrence_reversal
    reachable_numeric_opponent_override

Therefore the runner distinguishes:

    FAILED_MISMATCH
    INCOMPLETE_UNRESOLVED
    PASS_PARTIAL_BRANCH_COVERAGE
    PASS_FULL_BRANCH_COVERAGE

Only PASS_FULL_BRANCH_COVERAGE sets:

    promotion_ready=true

A partial-coverage pass is useful validation evidence but is not sufficient to
promote the complete candidate as a canonical NuHost rule.

## Frozen formula preservation

The predictor file is byte-identical to its blob at the frozen candidate
commit. Independent-only input validation lives in:

    tools/diagnostics/combat_public_capture_side_postheldout_validation.py

This adapter can fail closed on missing discriminator inputs without changing
the frozen candidate formula.

No independent runtime result is claimed by this checkpoint.
