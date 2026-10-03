# Independent short public corpus expansion

Date: 2026-10-03

Purpose: acquire a new public evidence population after the original public36
has been fully opened by capture-side discovery/held-out work.

The new population must not overlap public36 and must not be used to retroactively
claim that the old held-out gate passed.

Default bounds:

    finished public games only
    turn >= 55
    turn <= 140
    slots >= 8
    slots <= 16
    loadinfo probe limit 240
    selected compatible games 32

The public36 selected manifest is the baseline. Therefore its game IDs are
excluded and its ruleset tokens count as already-seen when novelty is scored.

Acquisition outputs use independent namespaces:

    validation/corpus/manifests/public-short-expansion-*.jsonl
    validation/corpus/index/public-short-expansion-*.json
    artifacts/public-short-expansion/

Raw ZIPs continue to use the shared immutable loadall cache because game IDs are
globally unique.

Run acquisition:

    bash tools/run-public-short-expansion-with-evidence.sh

After acquisition, inspect:

    validation/corpus/index/public-short-expansion-stats.json

especially:

    games_indexed
    totals.archive_bytes
    totals.snapshots

The compact DB build is deliberately separate so the selected count can be
adjusted after actual archive sizes are known if the resulting corpus is clearly
too large/small.

Default compact build:

    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/run-corpus-db-public-short-expansion-compact.sh

The new compact generation is published beside public36 under generations/ but
does NOT change canonical CURRENT. Both normal and external research containers
can read it explicitly because the complete shared root is mounted at
/corpus-db.

The intended physical target is approximately five GiB, not a hard acceptance
threshold. Actual compact size is authoritative and is reported after build.

This new corpus is independent validation material for the current
POST_HELDOUT_CANDIDATE_NOT_CANONICAL capture-side hypothesis. Do not inspect
capture outcomes before the candidate/validation gate for that generation is
frozen.
