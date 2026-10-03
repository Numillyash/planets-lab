# Corpus DB v2 compact prototype

Status: game-233558 runtime green; exact compact storage gate closed.

Branch: `feature/corpus-db-v1`

## Purpose

typed1 proved native typed storage and full semantic parity, but storage
attribution on game-233558 showed three avoidable physical costs:

```text
secondary indexes                 ~1.142 GB
full decoded_payload_zlib         ~0.745 GB
generic entity_rows               ~0.192 GB
```

Native typed state plus small metadata was already approximately 932 MB before
adding an exact-semantic residual.

compact1 tests whether exact lossless reconstruction can stay near that floor
without temporal deltas, state-version dedup, RLE or cross-perspective dedup.

## Physical model

Schema id:

```text
planets-lab.corpus-db.v2.compact1
```

Core tables:

```text
corpus_metadata
source_archives
zip_members
source_members
member_fields
typed_entity_schema
typed_<section>
```

Deliberately absent:

```text
entity_rows
source_members.decoded_payload_zlib
global entity ART indexes
```

`source_members` retains source/member provenance, hashes, perspective and turn
identity, but not a second compressed copy of the decoded TRN.

Non-entity top-level fields are stored independently in `member_fields.value_json`.
Entity arrays are represented by native Arrow/DuckDB scalar, STRUCT and LIST
columns in `typed_<section>.data`.

## Exact semantic residual

Typed STRUCT nullability alone cannot distinguish:

```text
{"x": null}
{}
```

compact1 therefore stores a sparse `missing_json` only on entity rows where a
schema field is absent. Rows with the normal complete shape store NULL.

The residual contains only missing paths. It does not duplicate ordinary typed
values.

Schema discovery scans the complete source archive before import. This prevents
late fields from being silently omitted.

Type conflicts that would destroy JSON scalar identity, including int-vs-float,
fall back locally to canonical JSON VARCHAR rather than coercing to DOUBLE.

Thus exact reconstruction is:

```text
member_fields inline values
+ typed_<section>.data
+ sparse missing paths
= semantic member tree
```

The complete decoded source member is not stored in the DB.

## Publication gate

For every canonical TRN:

```text
A = existing decoder tree from immutable ZIP
B = tree reconstructed from compact DB

type(A) == type(B)
key presence == exact
array order == exact
scalar values/types == exact
```

ZIP/member hashes, CRCs, sizes, game/player/turn provenance remain independently
checked.

A compact generation is not published if parity has any failure.

## Prototype safety

The game-233558 compact runner publishes an immutable generation but does not
change `CURRENT` by default. The canonical public36 typed1 generation therefore
remains the active shared DB while compact1 is evaluated.

The runner also verifies:

- no `entity_rows` table;
- no `decoded_payload_zlib` column;
- zero secondary indexes;
- bounded T-1/T and VCR/site query behavior without global entity indexes;
- concurrent read-only open from normal and external research containers.

## Acceptance measurements

Record:

- DB bytes;
- import wall/RSS;
- full parity wall/RSS;
- inline top-level JSON logical bytes;
- sparse missing-residual row count and bytes;
- per-section typed row counts;
- T-1/T wall/RSS;
- VCR/site wall/RSS;
- concurrent two-container read.

Target is not a hard byte threshold. The working hypothesis from typed1
attribution is approximately 1.0-1.2 GB for game-233558 while retaining exact
semantic parity.


## Canonical game-233558 runtime

Runtime source HEAD:

```text
0936a95dae97a5a81bfbfb80b3c3d43c7f5b81bd
```

Published immutable generation:

```text
corpus-v2compact-g233558-20261001T091509Z-8e2e7416675d
sha256 05d083cea27a5108af9b2428adf3af766193d77a89f3d4ee402e200067678340
```

Measurements:

```text
source ZIP bytes                    691557421
decoded semantic JSON bytes        9568109828
compact DuckDB bytes               1058811904

import wall seconds                 1317.9859595710004
import peak RSS bytes               3068178432

TRN parity checked                  6710
parity failures                     0
parity wall seconds                 791.5095686369968
parity peak RSS bytes               3068178432

inline top-level JSON bytes         34445452
missing residual rows               102971
missing residual bytes              2442748

T-1/T wall seconds                  0.0382018589953077
T-1/T peak RSS bytes                114999296

VCR/site wall seconds               0.02191187000425998
VCR/site peak RSS bytes             112336896

normal+external concurrent read     PASS
CURRENT preserved                   PASS
```

Physical checks:

```text
entity_rows table                   absent
decoded_payload_zlib column         absent
secondary indexes                   0
typed ship warp/damage/crew         BIGINT
typed ship friendlycode             VARCHAR
typed ship iscloaked                BOOLEAN
```

Size comparison:

```text
compact / typed1                     0.3461x
reduction vs typed1                 65.39%

compact / decoded JSON              0.1107x
reduction vs decoded JSON           88.93%

compact / source ZIP                1.5311x
compact size                        0.986 GiB
```

The sparse exact-semantic overhead is small:

```text
inline top-level JSON / DB           3.25%
missing residual / DB                0.23%
rows with missing residual /
  all entity rows                    0.36%
```

The measured result validates the physical-layout hypothesis: the dominant
typed1 overhead came from broad entity ART indexes, the complete member fallback
and generic entity-row duplication rather than native typed state.

The compact build is slower than typed1 because it performs complete-archive
schema discovery and exact reconstruction without the member-blob shortcut.
Peak importer RSS nevertheless fell by about 19% relative to typed1.

No temporal delta encoding, state-version dedup, RLE or cross-perspective dedup
was used.

## Next gate

Do not replace the active public36 typed1 generation yet.

The next step is a corpus-wide compact builder with:

- one full corpus schema union rather than incompatible per-game schemas;
- the same exact missing/null and type-preserving semantics;
- resumable per-game checkpoints so a crash does not discard hours of work;
- bounded-memory schema discovery/import;
- full 36-game ZIP parity before publication;
- publication without switching CURRENT until size/query/shared-read results
  are reviewed.

The game-233558 result makes a substantially smaller public36 generation
plausible, but the single-game size ratio must not be extrapolated as a
guarantee.


## Public36 resumable builder

The next gate is implemented in:

```text
src/planets_lab/corpus/corpus_db_compact_multi.py
src/planets_lab/corpus/corpus_db_compact_multi_cli.py
tools/run-corpus-db-public36-compact.sh
tests/test_corpus_db_compact_multi.py
```

The corpus-wide builder uses one global compact schema learned from every
selected archive. Per-game schema observations are checkpointed under the
external corpus DB staging root and reused after restart.

The import staging database also has a stable resume identity. A completed game
is marked by its committed `source_archives` row. On restart:

- completed archives are provenance-checked and reused;
- any touched archive lacking a completed `source_archives` row is considered
  partial;
- typed rows, member fields, source members and ZIP provenance for that partial
  archive are deleted;
- import resumes from the next game with globally unique member IDs.

Full semantic parity is checkpointed at completed-game boundaries as well. The
parity checkpoint is accepted only for the same corpus fingerprint, staging DB
size and source-member count.

The public36 runner requires free-space headroom, publishes the compact
generation without switching CURRENT, benchmarks game-233558 against the
corpus-wide generation and performs the two-container read-only check.

Synthetic CI covers:

- global type union across games;
- int/float exact fallback;
- top-level shape conflicts;
- empty typed arrays;
- late fields and missing/null semantics;
- partial-archive cleanup;
- completed-game import resume;
- completed-game parity resume;
- no generic `entity_rows`;
- no member fallback blob;
- zero secondary indexes.


## Canonical public36 compact runtime

Runtime source HEAD:

```text
3739274b797ed6b2e346436e837c4c27849632de
```

Published immutable generation:

```text
corpus-v2compact-public36-20261002T083138Z-11cd75fa918d
sha256 e1c0adc0a699d9d776f1fddb7dfc37c5a6714dfd9262f911a5939fda41cc7004
```

Corpus:

```text
archives                            36
source ZIP bytes                    9456773573
turn members                        126418
entity rows                         314311240
decoded JSON bytes                  133808928311
corpus fingerprint                  11cd75fa918dec3d6839f6dbdcb3537bcb66d6f4c9d935f1866003998aab9e42
```

Build and parity:

```text
import wall seconds                 21398.347268733996
import wall time                    ~5h56m38s
import peak RSS bytes               13938348032

parity checked                      126418
parity failed                       0
parity wall seconds                 12541.871932070993
parity wall time                    ~3h29m02s
parity process peak RSS bytes       14095867904
```

Published size and semantic residual:

```text
database bytes                      13189001216
database size                       ~12.283 GiB
inline top-level JSON bytes         765900754
missing residual rows               62285221
missing residual bytes              1566825204
```

Physical gate:

```text
entity_rows                         absent
decoded_payload_zlib                absent
secondary indexes                   0
normal+external shared read         PASS
CURRENT preserved                   PASS
```

Bounded game-233558 queries against the corpus-wide compact generation:

```text
T-1/T wall seconds                  0.07014746399363503
T-1/T peak RSS bytes                142249984
VCR/site wall seconds               0.025252373015973717
VCR/site peak RSS bytes             117559296
```

Comparison with the canonical public36 typed1 generation:

```text
typed1 bytes                        38931017728
compact bytes                       13189001216
compact / typed1                    33.88%
reduction vs typed1                 66.12%

compact / decoded JSON               9.86%
reduction vs decoded JSON           90.14%

compact / source ZIP                 1.395x

typed1 import peak RSS              26944557056
compact import peak RSS             13938348032
RSS reduction vs typed1             48.27%
```

The compact result closes the public36 storage/correctness/shared-reader gate.

### Residual attribution

The global schema makes absence metadata materially larger than in the
single-game prototype. Missing residual accounts for about 11.88% of the final
DB and appears on about 19.82% of entity rows.

All missing-residual bytes are concentrated in five sections:

```text
planets        1023708422   65.34%
scores          269002122   17.17%
minefields      160337422   10.23%
players          97257374    6.21%
torpedos         16519864    1.05%
total          1566825204  100.00%
```

This is expected from a single union schema: fields present in one game/version
become schema fields whose absence must be represented for entities originating
from games/versions without those fields.

The next bounded physical optimization should therefore target presence
metadata, not typed values. A compact schema-variant/presence-mask
representation can replace repeated JSON missing-path arrays while retaining
exact absent-vs-null reconstruction. Temporal/cross-perspective dedup remains
out of scope for this optimization.


## Accepted backend / optimization stop

The canonical public36 compact runtime closes the current physical-storage
optimization milestone.

The schema is accepted for normal research use because it combines:

- complete-corpus schema discovery;
- native typed scalar/STRUCT/LIST entity state;
- exact absent-vs-null reconstruction;
- exact JSON fallback for incompatible type/shape cases;
- immutable archive/member provenance;
- 126418 / 126418 source-member semantic parity;
- bounded query behavior with no broad secondary indexes;
- simultaneous read-only access from both research containers.

This is sufficient generality for the active corpus. It does not imply that a
future unseen Nu payload can be appended without schema refresh; any expanded
corpus must still be rebuilt/validated against immutable ZIP evidence.

Further storage optimization is intentionally deferred. See
`docs/corpus-db/FUTURE_OPTIMIZATIONS.md`.

### Activation

Canonical generation:

```text
generations/corpus-v2compact-public36-20261002T083138Z-11cd75fa918d.duckdb
sha256 e1c0adc0a699d9d776f1fddb7dfc37c5a6714dfd9262f911a5939fda41cc7004
```

Activate only through:

```bash
export PLANETS_CORPUS_DB_ROOT=/root/projects/planets-corpus-db
bash tools/activate-corpus-db-compact-public36.sh
```

The activation runner validates SHA256, schema, corpus fingerprint, archive and
member counts and compact physical invariants before atomically replacing
`CURRENT`. It then runs the normal + external shared-read gate. A failed
post-switch gate automatically restores the previous CURRENT and verifies the
rollback backend.
