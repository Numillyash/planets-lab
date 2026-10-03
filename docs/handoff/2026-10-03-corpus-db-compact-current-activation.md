# Corpus DB compact CURRENT activation — 2026-10-03

The accepted compact public36 generation is now the active shared corpus backend.

Activated generation:

```text
generations/corpus-v2compact-public36-20261002T083138Z-11cd75fa918d.duckdb
sha256 e1c0adc0a699d9d776f1fddb7dfc37c5a6714dfd9262f911a5939fda41cc7004
schema planets-lab.corpus-db.v2.compact1
```

Pre-switch validation:

```text
source archives      36
source members       126418
corpus fingerprint   11cd75fa918dec3d6839f6dbdcb3537bcb66d6f4c9d935f1866003998aab9e42
secondary indexes    0
```

Previous CURRENT / rollback generation:

```text
generations/corpus-v1typed-public36-20260930T211714Z-11cd75fa918d.duckdb
```

The guarded activation runner atomically changed CURRENT and then verified both
normal planets-lab and external research readers against the new generation.

Runtime result:

```text
NORMAL reader
  source_members=126418
  READY / OK

EXTERNAL reader
  source_members=126418
  READY / OK

shared_generation_concurrent_read: PASS
compact_current_activation: PASS
```

No rollback was required.

## Operational state

`CURRENT` now points to the compact generation.

Keep the typed1 public36 generation temporarily as a rollback generation. Do not
delete the immutable source ZIP/TRN evidence.

The compact backend is now the normal read path for corpus-backed research.
Storage optimization is closed for the current milestone. Reopen only under the
criteria in `docs/corpus-db/FUTURE_OPTIMIZATIONS.md`.

## Return to mechanics

With storage activated and validated, the next project work should return to
NuHost reconstruction on main. Corpus DB changes must not alter previously
established evidence/held-out boundaries.
