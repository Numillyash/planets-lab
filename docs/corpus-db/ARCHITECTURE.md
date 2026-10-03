# Corpus DB v1 architecture

Status: design checkpoint for branch feature/corpus-db-v1.

Base at creation:

    main
    2cc98e3cab3cc0ce0dbdb48f032e9650029f8273

## Goal

Replace repeated ZIP/TRN decoding as the normal analytical storage path with a
typed indexed DuckDB mirror, while keeping original Planets.nu archives as
immutable evidence.

This is a storage migration, not a new game model. Player, perspective, turn,
entity and source semantics must remain intact.

## Why

Current diagnostics can turn a sub-gigabyte ZIP into many gigabytes of decoded
JSON and tens of gigabytes of Python objects. game-233558 has already exposed a
~30 GiB single-game peak in whole-game diagnostics.

The DB should make runtime cost depend on the requested rows rather than on the
size of the entire game archive.

## Evidence boundary

Raw archives remain immutable and are never rewritten or deleted by this
workstream.

Every imported member must retain provenance sufficient to trace any DB row
back to:

- game id and source archive SHA-256;
- source member name, CRC/size where available, payload SHA-256;
- perspective player id;
- archive turn and embedded turn.

The DB must preserve semantic distinctions including absent field vs explicit
JSON null, scalar types/values, array ordering, and distinct observations from
different player perspectives.

Byte-identical JSON whitespace/object-key ordering is not required. Semantic
parity with the current JSON decoder is required.

## v1 intentionally has no deltas

v1 is a direct database mirror.

Do not add temporal deltas, state-version dedup, RLE spans, cross-perspective
dedup or a redesigned domain model yet.

Expected wins should come from normal DB representation itself:

- field names live in schema rather than every JSON object;
- typed numeric/bool columns;
- columnar compression and repeated-string compression;
- indexes/predicate pushdown;
- no repeated ZIP decompression during normal research;
- no full-game Python object graph for narrow queries.

A 5-10x reduction versus unpacked JSON is a hypothesis to measure, not a
guaranteed result. ZIP is already compressed and is the harder disk baseline.

## Separate shared DB entity

The DB must live outside both repository checkouts.

Host variable:

    PLANETS_CORPUS_DB_ROOT

Container path:

    /corpus-db

Recommended structure:

    <PLANETS_CORPUS_DB_ROOT>/
      CURRENT
      generations/
        corpus-v1-<build-id>.duckdb
      manifests/
      staging/

Published generations are immutable.

One writer builds a new file in staging, closes it, runs integrity/semantic
parity checks, publishes the generation, then atomically updates CURRENT.
Consumers open the published generation read-only.

The same host path must be mounted into both the normal planets-lab container
and the research/external-engine-analysis container.

Consumer mount contract:

    ${PLANETS_CORPUS_DB_ROOT}:/corpus-db:ro

Importer mount contract:

    ${PLANETS_CORPUS_DB_ROOT}:/corpus-db:rw

The DB must not be a project-scoped Docker volume whose lifecycle follows either
compose project.

## Logical schema direction

Keep existing TRN concepts: players, ships, planets, starbases, minefields,
ionstorms, relations, VCRs, settings/game state and other source sections.

Each entity row must retain snapshot/member provenance and perspective.

Unknown or nested fields must not be discarded. v1 may keep a generic lossless
fallback representation for fields not promoted to typed columns, but it must
preserve absent/null/type/array-order semantics.

Dominant query keys to benchmark/index include:

    (game_id, perspective_player_id, archive_turn)
    (game_id, archive_turn, entity_id)
    (game_id, archive_turn, vcr_id)
    (game_id, archive_turn, x, y)

## Semantic parity gate

For every source member in the prototype:

    A = current decoder semantic value tree from original TRN
    B = semantic value tree reconstructed from DB

Require A == B semantically.

The validator must report exact member/path mismatches and catch missing/extra
fields, absent-vs-null collapse, scalar type/value changes, array reordering and
wrong perspective/turn association.

## Prototype

Start only with game-233558.

Measure:

1. ZIP bytes;
2. unpacked semantic JSON bytes;
3. DB bytes;
4. one-time import wall time and peak RSS;
5. member parity checked/failed;
6. targeted T-1/T query wall time and peak RSS;
7. capture/VCR query wall time and peak RSS;
8. two simultaneous read-only consumers from separate containers.

Only after this gate passes should the workstream scale to the stabilized
36-game corpus.

## Later, not v1

Possible later layers include exact-state dedup, temporal spans/deltas, Parquet
exports and cold-storage relocation. None belong in the initial direct mirror.


## Accepted compact physical implementation

The original v1 direct-mirror layout and typed1 layout are historical design
steps. The accepted public36 physical backend is now:

```text
schema: planets-lab.corpus-db.v2.compact1
generation:
  corpus-v2compact-public36-20261002T083138Z-11cd75fa918d
```

It keeps the architectural evidence/provenance contract above but changes the
physical representation:

- one `source_members` row per TRN with provenance and hashes, not a complete
  decoded member blob;
- native `typed_<section>` Arrow/DuckDB scalar, STRUCT and LIST data;
- top-level irregular fields in exact inline JSON fallback;
- sparse missing-field metadata to preserve absent vs explicit NULL;
- no generic `entity_rows` duplication;
- no broad secondary ART indexes in the accepted baseline.

The schema is learned from the complete selected corpus and fails back to exact
JSON representation where a native typed projection would lose scalar type or
shape semantics.

Canonical public36 validation:

```text
36 source archives
126418 / 126418 exact semantic parity
13189001216 bytes (~12.283 GiB)
normal + external concurrent read PASS
```

The immutable ZIP/TRN corpus remains the semantic oracle. Expanding the selected
corpus with previously unseen payload shapes requires a new generation and full
parity validation; consumers must never assume that CURRENT is writable or
schema-evolves in place.

Further compression is not part of the active milestone. Deferred physical
ideas and explicit reopen conditions live in
`docs/corpus-db/FUTURE_OPTIMIZATIONS.md`.
