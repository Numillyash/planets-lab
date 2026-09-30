# Corpus DB v1 — game-233558 archive-host runtime

Date: 2026-09-30

Branch: `feature/corpus-db-v1`

Runtime source HEAD:

```text
66c8ef8e3a97bbffde4ee4bfe773aad8145407df
```

## Scope

This runtime validates only the Corpus DB storage workstream. It does not change
or promote NuHost mechanics.

Source evidence remained the immutable archive:

```text
validation/corpus/cache/loadall/game-233558.zip
sha256 8e2e7416675dfbc1bc32e6993010dbcc4deed23a76e594809da495f556bdd412
```

The database is reproducible derived storage and remains outside both repository
checkouts under `PLANETS_CORPUS_DB_ROOT`.

## Published generation

```text
build_id
corpus-v1-g233558-20260930T041155Z-8e2e7416675d

generation
/corpus-db/generations/corpus-v1-g233558-20260930T041155Z-8e2e7416675d.duckdb

generation sha256
c1520eb5620e382433407fabc8719f5a454057670cda65c57e3e2034670c4894
```

`CURRENT` was atomically updated to the generation above.

## Source and database sizes

```text
source ZIP bytes                 691557421
decoded semantic JSON bytes     9568109828
published DuckDB bytes         11869892608

decoded JSON / ZIP                 13.8356x
DuckDB / ZIP                       17.1640x
DuckDB / decoded JSON               1.2406x
DuckDB overhead vs decoded JSON    +24.06%
```

The first direct physical layout therefore does not achieve a disk-space win.
This does not invalidate the semantic/query result, but it is a material
scale-out warning.

## Import

```text
turn members          6710
entity rows       28669768
member fields       208010

wall seconds      506.67934049799806
wall time         ~8m26.7s
peak RSS bytes    11229298688
peak RSS          ~10.46 GiB
```

The importer avoided the historical ~30 GiB whole-game Python object graph, but
one-time import RSS remains high enough to justify later memory attribution.

## Full semantic parity

```text
members checked      6710
failures                 0
mismatches               []
wall seconds      829.8552294809997
wall time         ~13m49.9s
peak RSS bytes    11811893248
peak RSS          ~11.00 GiB
```

This is the required full-source-member proof:

```text
A = current JSON decoder from original .trn
B = semantic tree reconstructed from DuckDB

A == B for 6710 / 6710 members
```

The result also validates stored source archive/member provenance during the
parity pass.

No mismatch was bypassed or downgraded to a mechanics projection comparison.

## Bounded indexed query results

T-1/T:

```text
perspective_player_id   1
archive turns           608 -> 609
result rows             19
wall seconds            0.02508335300080944
peak RSS bytes          114585600
peak RSS                ~109.27 MiB
```

VCR/site:

```text
archive turn            570
site                    (2395, 2640)
raw VCR rows at site    48
result rows             3
wall seconds            0.058298714000557084
peak RSS bytes          217964544
peak RSS                ~207.87 MiB
```

These are the important operational result of the workstream: narrow research
queries no longer require loading the entire 9.57 GB semantic turn stream or a
tens-of-gigabytes Python object graph.

Do not interpret these timings as a direct apples-to-apples speedup factor over
the older full-archive JSON benchmark. The query shapes are intentionally
bounded and different. The relevant property is that runtime/RSS now scale with
the requested indexed subset rather than the whole game.

## Shared generation access

Two containers opened the same published generation concurrently, read-only:

```text
normal planets-lab reader
READY source_members=6710
OK    source_members=6710

research/external-engine-analysis reader
READY source_members=6710
OK    source_members=6710

shared_generation_concurrent_read: PASS
```

This closes the shared `PLANETS_CORPUS_DB_ROOT -> /corpus-db` access contract
for the prototype.

## Gate status

Semantic/query/shared-reader prototype status:

```text
archive provenance       GREEN
member parity            GREEN  6710 / 6710
published immutable DB   GREEN
CURRENT publication      GREEN
T-1/T indexed query      GREEN
VCR/site indexed query   GREEN
two-container read       GREEN
```

Storage efficiency status:

```text
direct DB smaller than decoded JSON   NO
36-game blind scale-out               HOLD
```

The original milestone defined size/time/RSS as measurements rather than
hard pass/fail thresholds, so the correctness gate is green. However, the
observed +24.06% disk overhead versus decoded semantic JSON is large enough that
the next action is storage attribution before multiplying the layout across all
36 public games.

## Next bounded action

Do **not** add temporal deltas, state-version dedup, RLE spans or
cross-perspective dedup.

Instead, on a disposable copy of the published generation, measure:

1. data-only DuckDB size with no secondary indexes;
2. incremental size contribution of:
   - source-member lookup indexes;
   - member-field lookup index;
   - entity member/order index;
   - entity id/turn lookup index;
   - entity site index;
3. memory/time of each stage;
4. whether repeated snapshot metadata in `entity_rows` is a material physical
   cost relative to joining it through `member_id`.

Only after that attribution should v1 either:

- accept the current physical layout explicitly; or
- tighten the physical representation while preserving exactly the same
  semantic/provenance model and full parity gate.

The ZIP backend remains the oracle throughout.


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
