# New chat start — Corpus DB v1

Continue the dedicated Planets.nu corpus-database infrastructure workstream in
Numillyash/planets-lab.

GitHub is the only source of truth. Verify current refs before trusting any SHA
in this document.

## Branch

Work only on:

    feature/corpus-db-v1

It was originally cut from:

    main
    2cc98e3cab3cc0ce0dbdb48f032e9650029f8273

Do not mix current C5/O-layer mechanics development into this branch except when
strictly required for storage compatibility.

## Read first

1. docs/corpus-db/ARCHITECTURE.md
2. docs/corpus-db/SHARED_ACCESS.md
3. docs/corpus-db/WORKSTREAM.md
4. docs/COMPILED_CORPUS.md
5. docs/ARCHITECTURE.md
6. docs/WORKFLOW.md

Then inspect the live archive/normalizer/prepared-cache code before implementing.

## Non-negotiable requirements

- DB is a third separate entity, not owned by either research container.
- Both normal planets-lab and research/external-engine-analysis containers read
  the same published DB concurrently.
- One host PLANETS_CORPUS_DB_ROOT is mounted as /corpus-db in both.
- Published generations are immutable; writer builds only new staging
  generations.
- Original ZIP/TRN files remain immutable evidence.
- v1 preserves players, perspective, archive/embedded turn, all source fields,
  scalar types, null-vs-absent and array order.
- Unknown fields are preserved losslessly.
- No temporal deltas, state dedup, RLE spans or redesigned game model in v1.
- Existing held-out mechanics boundaries remain sealed.

## First target

Prototype only:

    game-233558

## First deliverable

Implement and benchmark:

    original game-233558.zip
      -> one-time DuckDB import
      -> semantic parity validator
      -> indexed read-only queries
      -> concurrent access from both containers

Record ZIP/raw-JSON/DB sizes, import time and peak RSS, parity counts, targeted
T-1/T query time/RSS, capture/VCR query time/RSS, and a two-container concurrent
read test.

Do not scale to all 36 games until the game-233558 parity/benchmark gate is
green.

Commit completed work to feature/corpus-db-v1 with tests and documentation.
If a design decision could alter source semantics, validate it against raw TRN
before proceeding.
