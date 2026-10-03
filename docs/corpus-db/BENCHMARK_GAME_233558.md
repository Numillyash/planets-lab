# Corpus DB v1 — game-233558 prototype benchmark

Status: canonical game-233558 archive-host runtime green for semantic parity, bounded indexed queries and concurrent shared readers; storage attribution is the next gate before 36-game scale-out.

The first accepted runtime was produced from the immutable cached `game-233558.zip` on the archive host using the tracked runner at branch HEAD `66c8ef8e3a97bbffde4ee4bfe773aad8145407df`.

## Required runtime

```bash
cd ~/projects/planets-lab
git switch feature/corpus-db-v1
git pull --ff-only origin feature/corpus-db-v1

export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
bash tools/run-with-runtime-evidence.sh \
  corpus-db-game233558-prototype \
  -- \
  bash tools/run-corpus-db-game233558-prototype.sh
```

The corpus DB itself remains outside Git/runtime-evidence branches. The evidence wrapper captures only command output/metadata unless an explicit safe artifact path is added later.

## Acceptance measurements

Record from the canonical run:

\`\`\`text
source ZIP bytes:                  691557421
unpacked decoded JSON bytes:       9568109828
published DuckDB bytes:            11869892608
one-time import wall seconds:      506.67934049799806
one-time importer peak RSS bytes:  11229298688
TRN members parity checked:        6710
parity failures:                   0
parity wall seconds:               829.8552294809997
parity peak RSS bytes:             11811893248
T-1/T query wall seconds:          0.02508335300080944
T-1/T query peak RSS bytes:        114585600
VCR/site query wall seconds:       0.058298714000557084
VCR/site query peak RSS bytes:     217964544
normal+external concurrent read:   PASS
\`\`\`

## Green gate

The game-233558 prototype is green only if all of the following hold:

```text
parity failures == 0
parity checked == every canonical playerN-turnM.trn in the ZIP
archive integrity validation == green
CURRENT points to the newly published immutable generation
normal planets-lab reader == green
external-engine-analysis reader == green
both readers overlap while opening the same generation
```

Size/time/RSS are measurements, not pass/fail thresholds for v1. They are used to decide whether the direct mirror is already sufficient or whether a later storage format iteration is justified.

## Interpretation

The correctness and reader gate is green:

- 6710 / 6710 canonical TRN members passed full semantic parity;
- no mismatch was bypassed;
- the same immutable generation opened concurrently from both research containers;
- bounded T-1/T and VCR/site reads completed without whole-game materialization.

The direct physical schema did **not** produce a disk-space win:

\`\`\`text
decoded JSON / ZIP       13.8356x
DuckDB / ZIP             17.1640x
DuckDB / decoded JSON     1.2406x
DuckDB overhead vs JSON  +24.06%
\`\`\`

The published database is therefore excellent as a query backend but not yet
acceptable for blind 36-game scale-out. The next bounded action is storage
attribution on a disposable copy of CURRENT to separate table payload size from
ART-index overhead and repeated physical metadata. No temporal/cross-perspective
deduplication is introduced by that diagnostic.

Do not migrate mechanics diagnostics wholesale or build the full 36-game DB
until the storage attribution result is recorded and the v1 physical layout is
either accepted explicitly or tightened without changing semantic parity.

## Storage attribution follow-up

Run against the already published immutable generation:

```bash
cd ~/projects/planets-lab
git switch feature/corpus-db-v1
git pull --ff-only origin feature/corpus-db-v1

export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
bash tools/run-corpus-db-storage-attribution.sh
```

The runner creates a disposable staging DuckDB, attaches CURRENT read-only,
copies only the six v1 tables, then checkpoints after each secondary-index
stage. It deletes the scratch database after printing the result.

The active generation and `CURRENT` are never modified.


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


## Payload-vs-projection discriminator — 2026-09-30

Third disposable-layout run:

```text
entity_keys_only                  47984640
entity_query_projection_only     192163840
entity_all_context_no_payload    192163840
entity_payload_only            10535317504
entity_semantic_min            10576474112
entity_query_slim              10721177600
```

This rejects the hypothesis that typed numeric/context columns are responsible
for the multi-gigabyte expansion. All current typed query and repeated context
columns together fit in about 192 MB, while `payload_json` alone occupies
10.535 GB.

The next bounded diagnostic profiles the logical contents of `payload_json`:
per-section row counts and UTF-8 bytes, average/max object size, approximate
payload cardinality/repetition, and the key sets of the largest objects. It also
compares logical entity/member-field payload bytes against the original decoded
JSON byte total.

No source payload values are printed by default.


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


## Canonical typed1 runtime — 2026-09-30

Runtime source HEAD:

```text
8aebaa3f33a632bffbd430496a9c2b58d804d572
```

Published generation:

```text
corpus-v1typed-g233558-20260930T143229Z-8e2e7416675d
sha256 cd27dffa3871e2f70dfc0d58d9d6547a6b14b40e45fd7793dfc9548377ad7d58
```

Measurements:

```text
source ZIP bytes                   691557421
decoded semantic JSON bytes       9568109828
typed DuckDB bytes                3058970624

import wall seconds                743.576329482
import peak RSS bytes              3788349440

TRN parity checked                 6710
parity failures                    0
parity wall seconds                452.13253703700013
parity peak RSS bytes              3788349440

T-1/T wall seconds                 0.021777331000066624
T-1/T peak RSS bytes               114696192

VCR/site wall seconds              0.05098852099990836
VCR/site peak RSS bytes            215232512

normal+external concurrent read    PASS
```

Size comparison:

```text
typed DB / decoded JSON             0.3197x
typed reduction vs decoded JSON    68.03%
typed DB / first v1 DB              0.2577x
typed reduction vs first v1 DB     74.23%
typed DB / source ZIP               4.4233x
```

The size reduction comes from removing per-entity `payload_json VARCHAR`
copies and writing entity fields through native Arrow/DuckDB scalar,
STRUCT and LIST types. Full source semantics remain recoverable from one
compressed member-level fallback BLOB per TRN.

Typed-column check on the real corpus confirmed:

```text
warp          BIGINT
damage        BIGINT
crew          BIGINT
friendlycode  VARCHAR
iscloaked     BOOLEAN
```

The prototype gate is now green for storage, semantic parity, bounded indexed
queries and shared concurrent read access.

The typed import is slower than the first v1 import because it performs bounded
schema discovery plus typed conversion, but peak RSS fell from about 10.46 GiB
to about 3.53 GiB. One-time build cost is acceptable for this gate; normal
research reads remain the operational optimization target.

Next milestone: build one typed generation for the stabilized 36-game public
corpus, preserving ZIP as oracle and validating every imported member.


## Typed1 storage attribution — 2026-09-30

Attribution on the canonical 3,058,970,624-byte typed1 generation:

```text
all data, no secondary indexes          1,869,099,008
source-member indexes                         786,432
member-field index                          9,699,328
entity member/order index                 276,824,064
entity id/turn index                      524,025,856
entity site index                         330,563,584
rebuilt total with indexes              3,010,998,272
canonical source DB                     3,058,970,624
```

The three generic entity indexes alone contribute 1,131,413,504 bytes
(~1.079 GiB). All secondary indexes contribute 1,141,899,264 bytes.

The lossless full-member fallback is the second dominant cost:

```text
source_members with blob                  745,549,824
source_members without blob                 1,060,864
blob-only table                            745,025,536
logical compressed member blob bytes      744,267,100
```

The generic `entity_rows` table contributes 191,901,696 bytes.

Therefore:

```text
data without indexes                    1,869,099,008
minus full member fallback                745,025,536
                                      ----------------
                                        1,124,073,472

minus generic entity_rows                 191,901,696
                                      ----------------
                                          932,171,776
```

This is the key physical result: native typed state plus the small metadata
tables is already approximately 932 MB (0.868 GiB) before introducing any
temporal delta, RLE, state-version dedup or cross-perspective dedup.

Largest standalone typed tables:

```text
typed_messages                            308,031,488
typed_planets                             267,923,456
typed_ships                               130,297,856
typed_stock                                90,189,824
typed_notes                                44,314,624
typed_hulls                                41,431,040
typed_minefields                           26,488,832
typed_starbases                            14,168,064
typed_advantages                            7,352,320
```

The next physical layout should therefore not optimize native scalar storage.
It should:

1. remove global `entity_rows` ART indexes and add only narrowly justified
   section-specific indexes after query benchmarks;
2. eliminate the generic `entity_rows` duplication for known typed sections,
   deriving game/perspective/turn context by joining the tiny
   `source_members` table;
3. replace the complete per-TRN `decoded_payload_zlib` fallback with a sparse
   lossless residual that stores only semantic information not reconstructable
   from typed columns (unknown fields and absent-vs-null shape information);
4. retain full member parity against immutable ZIP as the publication gate.

A compact exact generation near 1 GB is therefore a realistic target on
game-233558 without temporal/cross-perspective dedup. The residual representation
must be measured before claiming a final ~900 MB target.


## Compact typed2 runtime — 2026-10-01

Canonical compact generation:

```text
corpus-v2compact-g233558-20261001T091509Z-8e2e7416675d
sha256 05d083cea27a5108af9b2428adf3af766193d77a89f3d4ee402e200067678340
```

Measurements:

```text
database bytes                       1058811904
decoded JSON bytes                   9568109828
source ZIP bytes                      691557421
import wall seconds                  1317.9859595710004
import peak RSS bytes                3068178432
parity checked                       6710
parity failed                        0
parity wall seconds                  791.5095686369968
inline JSON bytes                    34445452
missing residual rows                102971
missing residual bytes               2442748
T-1/T wall seconds                   0.0382018589953077
T-1/T peak RSS bytes                 114999296
VCR/site wall seconds                0.02191187000425998
VCR/site peak RSS bytes              112336896
shared concurrent read               PASS
CURRENT preserved                    PASS
```

Physical validation:

```text
entity_rows                          absent
decoded_payload_zlib                 absent
secondary indexes                    0
```

Comparison with typed1:

```text
typed1 bytes                         3058970624
compact bytes                        1058811904
compact / typed1                     34.61%
reduction vs typed1                  65.39%
compact / decoded JSON               11.07%
reduction vs decoded JSON            88.93%
compact / ZIP                        1.531x
```

This closes the bounded compact storage gate. The next storage task is a
crash-resumable corpus-wide compact builder and a 36-game validation run without
changing CURRENT until the result is reviewed.
