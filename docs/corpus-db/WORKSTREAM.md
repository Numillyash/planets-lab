# Corpus DB v1 workstream

Branch:

    feature/corpus-db-v1

Created from main:

    2cc98e3cab3cc0ce0dbdb48f032e9650029f8273

This branch owns storage infrastructure only. Do not promote NuHost mechanics
from it.

## First milestone

Prototype only on game-233558.

Deliver:

1. shared PLANETS_CORPUS_DB_ROOT contract and mounts for both research
   containers;
2. direct ZIP-to-DuckDB importer without full extraction to disk;
3. v1 direct-mirror schema preserving player/perspective/turn/source provenance;
4. lossless handling of unknown/untyped fields;
5. semantic round-trip validator for every TRN member in game-233558;
6. indexes/query helpers for game/player/turn/entity and VCR/site access;
7. disk/time/RSS benchmark report;
8. concurrent read-only test from normal and external containers.

Do not add deltas/dedup in this milestone.

## Acceptance gate

- original ZIP remains untouched;
- every member in game-233558 passes semantic parity;
- same published DB opens read-only from both containers simultaneously;
- active generation requires no writer for normal queries;
- narrow queries avoid whole-game JSON/Python materialization;
- DB footprint, runtime and peak RSS are recorded;
- storage backend alone does not alter mechanics results.

Only then scale to the 36-game public corpus.

Keep ZIP backend available as an oracle during migration.


## Implementation checkpoint

The first v1 prototype implementation is now tracked in:

- `src/planets_lab/corpus/corpus_db.py`;
- `src/planets_lab/corpus/corpus_db_cli.py`;
- `compose.corpus-db.yaml`;
- `tools/run-corpus-db-game233558-prototype.sh`;
- `tools/run-corpus-db-shared-read-check.sh`;
- `tests/test_corpus_db.py`;
- `docs/corpus-db/IMPLEMENTATION_V1.md`;
- `docs/corpus-db/BENCHMARK_GAME_233558.md`.

The canonical archive-host game-233558 run is now complete: 6710 / 6710 TRN
members passed full semantic parity, both containers concurrently opened the
same immutable generation read-only, and bounded indexed queries completed in
25 ms / ~109 MiB RSS and 58 ms / ~208 MiB RSS.

The correctness/query gate is green, but the first physical layout produced an
11.87 GB DuckDB from 9.57 GB decoded JSON (+24.06%). Blind 36-game scale-out is
therefore held for one bounded storage-attribution pass. See
`docs/handoff/2026-09-30-corpus-db-game233558-runtime.md`.


## Storage attribution result — 2026-09-30

Canonical disposable-copy run:

```text
source database bytes      11869892608
data-only bytes            10714361856
all secondary indexes       1157627904
final attributed bytes     11871989760
diagnostic peak RSS          4535009280
```

The data-only copy is already 11.98% larger than the decoded semantic JSON
stream, so indexes are not the primary explanation for the storage expansion.

Index contribution:

```text
source-member indexes        786432
member-field index          9699328
entity member/order index  277610496
entity id/turn index       533200896
entity site index          336330752
total                    1157627904
```

Of total secondary-index bytes, the three entity indexes account for about
99.1%. The entity-id index alone contributes about 46.1%, site about 29.1%,
and member/order about 24.0%.

This narrows the next question to the base table representation itself,
especially `entity_rows`: distinguish semantic payload bytes from repeated
per-row game/perspective/turn metadata and typed query projections before
changing the schema.


## Deep entity-layout attribution result — 2026-09-30

Second disposable-copy run:

```text
data-only total                 10722488320
entity_rows incremental         10713563136
entity_semantic_min             10573328384
entity_query_slim               10716983296
```

Interpretation:

- `entity_rows` accounts for 99.92% of the data-only database;
- even the semantic-minimum entity layout is 10.57 GB;
- adding the typed query projection to semantic-minimum costs only about
  143.65 MB (+1.36%);
- omitting repeated `game_id/perspective/archive_turn/embedded_turn` columns
  does not yield a material size reduction relative to the current table.
  The few-megabyte inversion between standalone/cumulative measurements is
  below the precision of comparing different physical scratch layouts.

Therefore the dominant cost is the per-entity lossless `payload_json`
representation itself, not provenance/context columns and not secondary
indexes.

The next attribution pass separates:

- structural entity keys with no payload;
- typed query projection with no payload;
- all current typed/context columns with no payload;
- `payload_json` alone.

That measurement is the final physical-layout discriminator before deciding
whether v1 should replace per-entity JSON fallback with a member-level
compressed lossless fallback plus typed query tables.


## Typed-layout correction

The first direct-mirror prototype exposed a physical-model error: each entity was
stored almost entirely as a complete `payload_json VARCHAR`, with only a small
set of typed locator/query columns beside it. Real game-233558 samples confirm
that numeric/boolean ship, planet, VCR, minefield and ion-storm fields therefore
remained characters inside JSON rather than native database values.

The correction is implemented as a separate `typed1` prototype path before
replacing the published v1 layout:

```text
src/planets_lab/corpus/corpus_db_typed.py
src/planets_lab/corpus/corpus_db_typed_cli.py
tools/run-corpus-db-game233558-typed-prototype.sh
```

Physical rule:

- `entity_rows` keeps only member/perspective/turn identity and generic query
  locators; it has no per-entity JSON payload;
- known entity sections are written to `typed_<section>` tables using native
  Arrow/DuckDB STRUCT/LIST/scalar types;
- nested structures such as VCR `left`/`right` are typed recursively;
- the full semantic source member is retained exactly once per TRN as a
  compressed `decoded_payload_zlib BLOB`;
- full semantic reconstruction/parity uses that member-level lossless fallback,
  so unknown/late fields are not discarded even if they are not in the learned
  typed projection.

The typed schema is learned from a bounded early source sample and the full
archive import then fails closed on incompatible values for projected fields.
Fields not present in the learned projection remain preserved by the compressed
member-level fallback.

This is still a game-233558 prototype. Do not scale to the 36-game corpus until
the typed generation passes full parity and its size/query/RSS measurements are
recorded.
