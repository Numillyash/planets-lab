# Corpus DB compact public68 CURRENT activation — 2026-10-04

The accepted combined public68 compact generation is now the active shared corpus backend.

Activated generation:

```text
generations/corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb
sha256 5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a
schema planets-lab.corpus-db.v2.compact1
```

Pre-switch validation:

```text
source archives      68
source members       169569
corpus fingerprint   09f71721b77cd1875932f75ed515636d9b79720bcc520aff72d6f9dd51f8fbf7
secondary indexes    0
entity_rows          absent
decoded_payload_zlib absent
```

Previous CURRENT / rollback generation:

```text
generations/corpus-v2compact-public36-20261002T083138Z-11cd75fa918d.duckdb
```

The guarded activation runner atomically changed CURRENT and then verified both
normal planets-lab and external research readers against the public68 generation.

Runtime result:

```text
NORMAL reader
  source_members=169569
  READY / OK

EXTERNAL reader
  source_members=169569
  READY / OK

shared_generation_concurrent_read: PASS
compact_current_activation: PASS
```

No rollback was required.

## Operational state

`CURRENT` now points to the public68 compact generation.

Keep the previous compact public36 generation as the first rollback backend.
Keep the typed1 public36 generation and immutable ZIP/TRN evidence until an
explicit cleanup decision is made.

The compact1 storage model remains accepted. This activation expands the
canonical evidence population; it does not reopen storage optimization.

## Mechanics consequence

The independent short-public acquisition that motivated this expansion is now
available through the normal canonical Corpus DB read path. The post-heldout
capture-side candidate must therefore be tested on the new independent
population before any promotion decision.

Do not alter the old pre-heldout frozen candidate or relabel the 60/60
post-heldout fit as independent validation.

Canonical build/runtime details:
`docs/handoff/2026-10-04-corpus-db-public68-runtime.md`.
