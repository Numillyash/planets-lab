# Post-independent capture-side prospective validation acquisition

Date: 2026-10-05

Status:

    ACQUISITION_READY

## Frozen candidate

The current research candidate is frozen at:

    46bcb08c2f0d3f0449b97921edb03ab6647f7d3b

Candidate source:

    tools/diagnostics/combat_public_capture_side_postindependent_candidate.py

Status remains:

    POST_INDEPENDENT_CANDIDATE_NOT_CANONICAL

The acquisition wrapper refuses to run if this candidate source differs from
the frozen commit.

## Population boundary

The new population excludes every game already present in canonical public68.

Baseline manifest:

    validation/corpus/manifests/public-short-expansion-with-public36.jsonl

Required baseline count:

    68

New acquisition outputs:

    validation/corpus/manifests/public-postindependent-validation-candidates.jsonl
    validation/corpus/manifests/public-postindependent-validation-selected.jsonl
    validation/corpus/manifests/public-postindependent-validation-with-public68.jsonl
    validation/corpus/index/public-postindependent-validation-games.jsonl
    validation/corpus/index/public-postindependent-validation-stats.json
    artifacts/public-postindependent-validation/

## Predeclared acquisition profile

    finished public games only
    final turn             80..180
    slots                   8..16
    loadinfo probes          320
    target games              32

The later turn range is deliberate: the required capture-side discriminator is
rare, so this population trades some size for higher expected combat density.
Selection still uses only public listing metadata and loadinfo/settings. It does
not inspect VCR/capture outcomes before selection.

The acquisition uses the existing bounded backfill mechanism for incompatible
legacy/binary archives. Backfill restores selected-count failures only; it does
not adapt the candidate to observed mechanics outcomes.

## Runner

Run only from main:

    bash tools/run-public-postindependent-validation-acquisition-with-evidence.sh

The wrapper checks:

- current branch is main;
- the frozen candidate commit is an ancestor of HEAD;
- the frozen candidate source has no diff from that commit;
- the public68 baseline manifest exists and contains exactly 68 games.

Runtime evidence namespace:

    runtime-logs/public-postindependent-validation-acquisition/

## Prospective validation criteria

Acquisition itself does not validate the candidate.

After acquisition, build a separate compact exact-parity generation containing
only the new selected games. Do not switch canonical CURRENT away from public68.

The future candidate gate must require:

    all comparable adjacent rows exact
    zero factual mismatches
    zero unresolved candidate rows

In addition, the changed Kill-sensitive branch is not considered independently
validated unless the fresh population contains both of these discriminators:

1. captured prize LEFT + identity-anchored reachable opponent + numeric group 0
   + Kill mission;
2. captured prize LEFT + identity-anchored reachable opponent + numeric group 0
   + non-Kill combat request.

If either discriminator is absent, the correct result is:

    INSUFFICIENT_DISCRIMINATOR_COVERAGE

not a promotion pass.

The unchanged reachable-sticky, nonreachable/fresh-FC, and repeated-pair
branches already have independent short32 evidence collected before the
Kill-sensitive replacement candidate was formulated. The fresh population is
primarily required to validate the branch that changed after the short32
counterexample.

## Evidence discipline

Do not alter the candidate after seeing this population and then reuse the same
population as validation.

Do not add these new games to canonical public68 CURRENT before the prospective
gate is evaluated. The validation DB is a separate immutable compact generation.

Current mechanics checkpoint:

    docs/handoff/2026-10-05-public68-capture-side-independent-result.md
