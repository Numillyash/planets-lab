# Corpus DB v2 compact prototype

Status: implementation green in CI; real game-233558 runtime pending.

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
