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

The corrected typed1 archive-host game-233558 run is complete:
6710 / 6710 TRN members passed full semantic parity; the entity layer uses
native DuckDB/Arrow scalar, STRUCT and LIST types; the same immutable generation
opened concurrently from both containers; and bounded indexed queries completed
in 21.8 ms / ~109 MiB RSS and 51.0 ms / ~205 MiB RSS.

The typed generation is 3.06 GB versus 9.57 GB decoded JSON and 11.87 GB for the
rejected first layout. The game-233558 acceptance gate is closed. Proceed to a
single typed 36-game public-corpus generation with the ZIP cache retained as
oracle. See
`docs/handoff/2026-09-30-corpus-db-typed-game233558-runtime.md`.


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


## Public 36-game typed generation

After the typed game-233558 gate closed, the branch added a corpus-wide builder:

```text
src/planets_lab/corpus/corpus_db_typed_multi.py
src/planets_lab/corpus/corpus_db_typed_multi_cli.py
tools/run-corpus-db-public36-typed.sh
```

The builder consumes the already stabilized
`validation/corpus/manifests/public-validation-selected.jsonl` and immutable
`validation/corpus/cache/loadall/game-<id>.zip` cache.

It creates one DuckDB generation for the whole selected population:

- one `source_archives` row per game;
- globally unique `member_id` values;
- archive-local ZIP-member ordinals retained through `archive_id`;
- one corpus-wide native typed schema rather than 36 incompatible per-game
  schemas;
- the schema union is formed from raw type observations sampled from every
  archive and normalized only after the union, so null-only observations from
  one game do not force numeric/bool fields from another game into JSON
  fallback;
- full ZIP provenance and semantic member parity are checked independently for
  every source archive before publication;
- publication remains staging -> immutable generation -> atomic CURRENT.

The tracked runner defaults to exactly 36 selected games and fails before build
if a selected cached archive is missing.

No network acquisition is performed by this runner. It uses the existing
stabilized public corpus only.


## Compact typed2 prototype

The typed1 36-game baseline is closed. The next bounded storage iteration is
defined in `docs/corpus-db/COMPACT_V2.md`.

compact1 removes the three dominant typed1 overheads measured on game-233558:

- full `decoded_payload_zlib` member copies;
- generic `entity_rows` duplication;
- global entity ART indexes.

Exact reconstruction is instead based on native typed section tables plus
top-level inline values and sparse missing-field presence residuals. Full archive
schema discovery prevents late fields from being silently omitted, and
type-conflicting fields fall back locally to JSON rather than being coerced.

The first runtime remains game-233558 only. It publishes an immutable compact
generation without switching `CURRENT`, so the canonical public36 typed1
generation remains active until compact1 passes its own runtime gate.


The bounded compact gate is now closed on game-233558:

```text
compact DB bytes         1058811904
typed1 DB bytes          3058970624
reduction vs typed1      65.39%
full parity              6710 / 6710
entity_rows              absent
member fallback blob     absent
secondary indexes        0
shared read              PASS
CURRENT preserved        PASS
```

The next implementation milestone is a corpus-wide compact builder. It must be
resumable at completed-game boundaries, preserve the exact compact semantic
model, bound memory, and validate all 36 public archives before any activation
decision.


The public36 compact gate is closed:

```text
archives                 36
full parity              126418 / 126418
compact DB               13189001216 bytes (~12.283 GiB)
typed1 DB                38931017728 bytes
reduction vs typed1      66.12%
reduction vs decoded     90.14%
import peak RSS          13938348032 bytes
entity_rows              absent
member fallback blob     absent
secondary indexes        0
shared read              PASS
CURRENT preserved        PASS
```

The compact public36 backend is accepted as the end of the current storage
optimization milestone. It is sufficiently compact and general for the active
research corpus, and further compression is deferred rather than blocking Host
reconstruction work.

The largest known remaining physical optimization is the 1.567 GB global-schema
missing residual, concentrated in planets, scores, minefields, players and
torpedos. A compact presence/schema-variant encoding is recorded as future work,
together with top-level typing, targeted query acceleration, incremental schema
evolution, build-time optimization and later temporal/state compression.

See `docs/corpus-db/FUTURE_OPTIMIZATIONS.md`.

Operational next step: deliberately activate the canonical compact public36
generation through the guarded activation runner, retain typed1 as rollback, and
then leave storage optimization closed unless a documented reopen criterion is
met.


## Compact CURRENT activated — 2026-10-03

The guarded activation completed successfully.

```text
CURRENT
generations/corpus-v2compact-public36-20261002T083138Z-11cd75fa918d.duckdb

schema
planets-lab.corpus-db.v2.compact1

source archives
36

source members
126418

shared normal/external read
PASS
```

Rollback generation retained:

```text
generations/corpus-v1typed-public36-20260930T211714Z-11cd75fa918d.duckdb
```

The storage workstream is operationally complete. The compact generation is now
the normal shared read backend. Further compression remains deferred in
`docs/corpus-db/FUTURE_OPTIMIZATIONS.md`.

Activation checkpoint:
`docs/handoff/2026-10-03-corpus-db-compact-current-activation.md`.


## Public68 expansion gate — 2026-10-04

The independent short public-corpus expansion completed successfully against
source commit `8e46159f20be54a724c7ff960fab8450ed3a6e93`.

Canonical runtime evidence:

```text
runtime-logs/public-short-expansion/20261003T203033Z_8e46159f20be
```

Acquisition result:

```text
new selected games                  32 / 32
new raw ZIP bytes                   3198603411
new snapshots                       43151
new transitions                     42815
new canonical_ok                    41957
new canonical_failed                1194
backfill rounds                     23
rejected candidates                 46
combined manifest games             68 unique
```

The final short-expansion bucket mix is availability-limited:

```text
campaign                            18
championship                         4
finite_fuel                          9
sphere                               1
```

The requested sphere target was 3, so the combined corpus must not be described
as sphere-balanced. The acquisition nevertheless reached the independent
32-game usable target after exhausting/rejecting many candidates.

This corpus expansion reopens generation construction, not storage-model
optimization. compact1 remains the accepted physical model.

The next gate is a new immutable compact generation over:

```text
validation/corpus/manifests/public-short-expansion-with-public36.jsonl
```

using:

```text
tools/run-corpus-db-public68-compact.sh
```

The runner requires 68 manifest entries, uses a stable resumable
`compact-public68-resume` staging identity, requires 40 GiB free-space
headroom by default, performs exact full-corpus parity and shared-reader gates,
and does not switch `CURRENT`.

The active public36 compact generation remains canonical until the public68
runtime output is reviewed and a separate guarded activation decision is made.


## Public68 compact runtime gate — 2026-10-04

The 68-game combined generation has passed the complete compact1 gate.

    generation
    corpus-v2compact-public68-20261004T095236Z-09f71721b77c

    sha256
    5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a

    corpus fingerprint
    09f71721b77cd1875932f75ed515636d9b79720bcc520aff72d6f9dd51f8fbf7

    archives                         68
    source members                   169569
    full parity                      169569 / 169569
    database bytes                   17847300096
    source ZIP bytes                 12655376984
    decoded JSON bytes               179227392513
    import peak RSS                  18496663552
    shared read                      PASS

The physical model remains accepted compact1; this is a corpus-size expansion,
not a new compression milestone.

CURRENT was preserved on public36 by the build gate. The next operational step
is guarded activation through:

    tools/activate-corpus-db-compact-public68.sh

The activation script fails closed on SHA/schema/archive/member/fingerprint or
physical-invariant mismatch, runs the shared-read gate after the atomic switch,
and automatically restores the previous CURRENT if post-switch verification
fails.

Runtime handoff:
docs/handoff/2026-10-04-corpus-db-public68-runtime.md
