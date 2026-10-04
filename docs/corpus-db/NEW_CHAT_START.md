# New chat start — Corpus DB compact backend

Continue the dedicated Planets.nu corpus-database infrastructure workstream in
Numillyash/planets-lab.

GitHub is the only source of truth. Verify current refs before trusting any SHA
in this document.

## Branch

Work only on:

    feature/corpus-db-v1

Do not mix current mechanics development into this branch except when strictly
required for storage compatibility.

## Read first

1. docs/corpus-db/ARCHITECTURE.md
2. docs/corpus-db/SHARED_ACCESS.md
3. docs/corpus-db/WORKSTREAM.md
4. docs/corpus-db/COMPACT_V2.md
5. docs/corpus-db/FUTURE_OPTIMIZATIONS.md
6. docs/handoff/2026-10-02-corpus-db-compact-public36-runtime.md
7. docs/COMPILED_CORPUS.md
8. docs/ROADMAP.md

## Accepted storage backend

Canonical ACTIVE public68 compact generation:

    corpus-v2compact-public68-20261004T095236Z-09f71721b77c
    sha256 5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a

Runtime gate:

    68 archives
    169569 / 169569 exact semantic parity
    17847300096 bytes (~16.622 GiB)
    shared normal/external read PASS

Corpus fingerprint:

    09f71721b77cd1875932f75ed515636d9b79720bcc520aff72d6f9dd51f8fbf7

Physical invariants:

    no entity_rows
    no decoded_payload_zlib
    no secondary indexes
    immutable published generation
    original ZIP/TRN retained as oracle

The public68 compact generation is the accepted and ACTIVE read backend.
CURRENT was successfully switched on 2026-10-04 and both normal/external
readers passed the post-switch shared-read gate. The previous compact public36
generation is retained as the first rollback backend.

## Operational activation

Activation completed successfully. For re-verification or a future controlled
re-activation of this exact generation, use:

    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/activate-corpus-db-compact-public68.sh

The runner validates the exact SHA256, schema, corpus fingerprint, archive and
member counts, compact physical invariants, then atomically switches CURRENT.
It runs the normal + external concurrent read check after the switch and
automatically restores the previous CURRENT if that verification fails.

## Storage optimization status

Current storage optimization is CLOSED.

The compact schema is considered sufficiently general for the active corpus:
complete-corpus schema discovery, exact absent-vs-null preservation, native
typed sections, and JSON fallback for values/shapes that cannot be represented
without loss.

Do not implement further compression merely because opportunities exist.
Possible improvements and explicit reopen criteria are preserved in:

    docs/corpus-db/FUTURE_OPTIMIZATIONS.md

Highest-value deferred item is replacing repeated JSON missing-path residuals
with presence masks/schema-variant IDs. Temporal deltas, RLE and
cross-perspective/state dedup remain later options only.

## Non-negotiable requirements

- DB remains a third separate entity outside both research checkouts.
- Both normal planets-lab and external research containers read the same
  immutable CURRENT generation.
- PLANETS_CORPUS_DB_ROOT is mounted at /corpus-db.
- Original ZIP/TRN remains immutable evidence and parity oracle.
- Published generations are immutable.
- Unknown/conflicting fields remain lossless.
- Storage work must not alter mechanics conclusions or held-out boundaries.


## Current expansion gate — 2026-10-04

A second independent public acquisition has now completed:

```text
new usable games                    32
combined unique games               68
new raw ZIP bytes                   3198603411
new snapshots                       43151
runtime evidence
runtime-logs/public-short-expansion/20261003T203033Z_8e46159f20be
```

The active backend is still the accepted public36 compact generation. Do not
change `CURRENT` merely because acquisition completed.

The next storage action is only to build and validate the combined public68
generation:

```bash
export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
bash tools/run-corpus-db-public68-compact.sh
```

This runner builds from
`validation/corpus/manifests/public-short-expansion-with-public36.jsonl`,
requires 68 archives, preserves `CURRENT`, and prints the exact generation
path, SHA256, member count and corpus fingerprint required for a later guarded
activation.

Storage-model optimization remains closed; this rebuild is required solely
because the corpus itself expanded.


## Public68 compact runtime — activated

The combined public68 compact gate is now green.

Published immutable generation:

    corpus-v2compact-public68-20261004T095236Z-09f71721b77c
    sha256 5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a

Runtime gate:

    68 archives
    169569 / 169569 exact semantic parity
    17847300096 bytes (~16.622 GiB)
    shared normal/external read PASS

Corpus fingerprint:

    09f71721b77cd1875932f75ed515636d9b79720bcc520aff72d6f9dd51f8fbf7

Physical invariants remain compact1:

    no entity_rows
    no decoded_payload_zlib
    no secondary indexes

CURRENT now points to this public68 generation after a successful guarded
activation on 2026-10-04. Public36 is retained as rollback.

Re-activate or re-verify public68 only through:

    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/activate-corpus-db-compact-public68.sh

Retain public36 as rollback after activation.

Canonical runtime details:
docs/handoff/2026-10-04-corpus-db-public68-runtime.md


## Public68 CURRENT activation — closed

The guarded activation completed successfully:

    CURRENT
    generations/corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb

    source archives
    68

    source members
    169569

    normal + external shared read
    PASS

    rollback
    generations/corpus-v2compact-public36-20261002T083138Z-11cd75fa918d.duckdb

Canonical activation checkpoint:
docs/handoff/2026-10-04-corpus-db-public68-current-activation.md

The next project action is mechanics validation on the new independent
short-public population, not further storage work.
