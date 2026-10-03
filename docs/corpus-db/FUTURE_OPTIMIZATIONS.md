# Corpus DB — deferred optimization backlog

Status: deferred. The compact public36 backend is accepted for normal research use.

This file records possible future physical improvements so storage optimization
can stop without losing the engineering trail. None of the items below are
required to activate or use the current compact generation.

## Accepted baseline

Canonical public36 compact generation:

```text
corpus-v2compact-public36-20261002T083138Z-11cd75fa918d
sha256 e1c0adc0a699d9d776f1fddb7dfc37c5a6714dfd9262f911a5939fda41cc7004
```

Measured properties:

```text
36 archives
126418 / 126418 exact semantic parity
13189001216 bytes (~12.283 GiB)
66.12% smaller than public36 typed1
90.14% smaller than decoded JSON
~1.395x source ZIP size
no entity_rows
no decoded_payload_zlib
no secondary indexes
shared normal/external read PASS
```

The current design is considered sufficiently general for the active research
corpus because it preserves provenance, field order, scalar JSON types,
array order and absent-vs-null semantics; learns one schema from the complete
selected corpus; and falls back to exact JSON representation when a typed field
would otherwise lose type/shape information.

This is not a claim that one immutable schema can accept every future Nu payload
without rebuild. New archives remain immutable evidence and must pass exact
parity after any schema refresh.

## P1 — compact presence encoding

Current union-schema absence metadata is represented by JSON missing-path arrays.

Measured public36 cost:

```text
missing residual bytes       1566825204
missing residual rows          62285221
```

The bytes are concentrated in:

```text
planets       1023708422
scores         269002122
minefields     160337422
players         97257374
torpedos        16519864
```

Possible replacement:

- assign a stable field/path ordinal within each typed section schema;
- encode absent fields as a fixed/variable bitset, Roaring bitmap, packed
  integer words, or dictionary-backed schema-variant ID;
- preserve explicit NULL independently from absence;
- reconstruct the exact original tree before parity comparison.

This is the highest-confidence future disk optimization because it attacks
repeated metadata rather than typed values.

## P2 — schema-variant dictionaries

Many games/Host eras likely use only a small number of object shapes.

Possible design:

```text
typed_planets(
    member_id,
    ordinal,
    schema_variant_id,
    data
)

planet_schema_variants(
    schema_variant_id,
    presence bitmap / field set
)
```

A variant ID may compress better than a per-row presence mask when millions of
entities repeat the same shape. Measure cardinality before implementing.

## P3 — top-level member field typing

`member_fields.value_json` currently contributes about 765.9 MB logical JSON
on public36.

Potential improvement:

- identify high-volume, stable top-level structures;
- move them to native typed tables or typed member columns;
- retain inline JSON only for truly irregular top-level fields.

Do this only after attribution by field name. Do not redesign the semantic model
blindly.

## P4 — targeted query acceleration

The accepted compact generation deliberately has zero secondary indexes.
Current measured bounded queries remain fast:

```text
game-233558 T-1/T      ~70 ms
game-233558 VCR/site   ~25 ms
```

Do not add broad ART indexes pre-emptively. If a real research query becomes a
bottleneck, prefer one of:

- physical ordering/clustering that improves zone-map pruning;
- a small section-specific lookup table;
- a narrow index only on the measured hot path;
- a materialized lookup relation generated from the canonical typed tables.

Require before/after wall time, RSS and disk attribution.

## P5 — build-time optimization

The canonical public36 compact build is correct but expensive:

```text
schema + import phase   ~5h56m38s
full parity             ~3h29m02s
import peak RSS         ~13.94 GB
```

The current per-game resume checkpoints make this operationally acceptable.

Future improvements may include:

- bounded parallel schema observation;
- avoiding repeated decode work between schema discovery/import/parity where
  this can be done without weakening source independence;
- more efficient Arrow batching;
- section-aware buffering;
- incremental parity workers;
- explicit build telemetry per game/section.

Correctness and crash recovery take priority over throughput.

## P6 — incremental corpus/schema evolution

If new games are appended regularly, avoid rebuilding all prior data merely
because one new archive introduces a field.

Potential approaches:

- versioned corpus schemas;
- append-only generation layers;
- schema migration into a new generation;
- per-section schema versions with a canonical reconstruction layer.

Any approach must retain one coherent read contract for consumers and exact
ZIP-based validation.

## P7 — temporal/state compression

Deferred intentionally:

- temporal deltas;
- state-version deduplication;
- run-length encoding across turns;
- cross-perspective deduplication;
- dictionary/state sharing between repeated observations.

These can save substantial space but introduce semantic and query complexity.
Do not reopen them unless storage volume becomes operationally material after
the simpler presence/top-level improvements.

## Reopen criteria

Resume storage optimization only if at least one becomes true:

1. corpus growth makes the accepted compact DB materially expensive to keep or
   distribute;
2. a real query workload exceeds an agreed latency/RSS budget;
3. new payload shapes cannot be represented losslessly without excessive JSON
   fallback/residual growth;
4. build time/RSS becomes a recurring operational blocker;
5. production/client integration requires a different physical access pattern.

Until then, treat compact1 as the accepted storage backend and focus research
effort on Host reconstruction rather than further compression.
