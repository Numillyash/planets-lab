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

Canonical public36 compact generation:

    corpus-v2compact-public36-20261002T083138Z-11cd75fa918d
    sha256 e1c0adc0a699d9d776f1fddb7dfc37c5a6714dfd9262f911a5939fda41cc7004

Runtime gate:

    36 archives
    126418 / 126418 exact semantic parity
    13189001216 bytes (~12.283 GiB)
    shared normal/external read PASS

Physical invariants:

    no entity_rows
    no decoded_payload_zlib
    no secondary indexes
    immutable published generation
    original ZIP/TRN retained as oracle

The compact generation is the accepted read backend. The previous public36
typed1 generation should be retained temporarily as rollback after activation.

## Operational activation

Use the guarded activation runner:

    export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
    bash tools/activate-corpus-db-compact-public36.sh

The runner validates the canonical SHA256, schema, corpus fingerprint, archive
and member counts, compact physical invariants, then atomically switches CURRENT.
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
