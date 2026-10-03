# Corpus DB v1 typed1 — game-233558 canonical runtime

Date: 2026-09-30

Branch: `feature/corpus-db-v1`

Runtime source HEAD:

```text
8aebaa3f33a632bffbd430496a9c2b58d804d572
```

## Result

The typed1 physical-layout correction closes the game-233558 prototype gate.

Source archive:

```text
validation/corpus/cache/loadall/game-233558.zip
bytes  691557421
sha256 8e2e7416675dfbc1bc32e6993010dbcc4deed23a76e594809da495f556bdd412
```

Published generation:

```text
corpus-v1typed-g233558-20260930T143229Z-8e2e7416675d
/corpus-db/generations/corpus-v1typed-g233558-20260930T143229Z-8e2e7416675d.duckdb
sha256 cd27dffa3871e2f70dfc0d58d9d6547a6b14b40e45fd7793dfc9548377ad7d58
```

## Size

```text
source ZIP bytes                691557421
decoded semantic JSON bytes    9568109828
typed DuckDB bytes             3058970624
```

Comparison:

```text
typed / decoded JSON             0.3197x
reduction vs decoded JSON       68.03%

typed / first v1 DuckDB          0.2577x
reduction vs first v1 DuckDB    74.23%

typed / source ZIP               4.4233x
```

The first v1 generation was 11,869,892,608 bytes because each entity retained a
complete `payload_json VARCHAR`. typed1 removes that per-entity copy and stores
native typed entity fields plus one compressed lossless source-member fallback
per TRN.

## Import

```text
turn members        6710
entity rows     28669768
member fields     208010

wall seconds    743.576329482
wall time       ~12m23.6s
peak RSS bytes  3788349440
peak RSS        ~3.53 GiB
```

The one-time build is about 46.8% slower than the first physical v1 importer,
because typed1 performs schema discovery and native conversion. Peak RSS fell by
about 66.3%, from ~10.46 GiB to ~3.53 GiB.

## Full semantic parity

```text
checked           6710
failed               0
mismatches           []
wall seconds    452.13253703700013
wall time       ~7m32.1s
peak RSS bytes  3788349440
```

Every canonical source member remains losslessly recoverable. The raw ZIP stays
the immutable oracle.

## Native type proof

The real game-233558 generation exposes no `payload_json` column in
`entity_rows`.

Observed typed ship fields:

```text
warp          BIGINT
damage        BIGINT
crew          BIGINT
friendlycode  VARCHAR
iscloaked     BOOLEAN
```

Nested structures such as VCR left/right are stored through native STRUCT fields.

## Bounded indexed queries

T-1/T:

```text
turns          608 -> 609
perspective    1
result rows    19
wall seconds   0.021777331000066624
peak RSS       114696192 bytes
```

VCR/site:

```text
turn            570
site            (2395,2640)
raw VCR rows    48
result rows     3
wall seconds    0.05098852099990836
peak RSS        215232512 bytes
```

Both are slightly faster than the first v1 generation while using essentially
the same bounded process memory.

## Shared generation

Normal planets-lab and research/external-engine-analysis containers opened the
same typed generation concurrently read-only:

```text
source_members=6710
shared_generation_concurrent_read: PASS
```

## Gate

```text
archive provenance                 GREEN
full member semantic parity        GREEN 6710/6710
native typed entity storage        GREEN
per-entity JSON duplication        REMOVED
published immutable generation     GREEN
CURRENT                            GREEN
T-1/T indexed query                GREEN
VCR/site indexed query             GREEN
normal+external concurrent read    GREEN
storage efficiency                 GREEN
```

The game-233558 Corpus DB v1 prototype is therefore closed.

## Next milestone

Prepare one typed generation for the stabilized 36-game public validation
population using the already immutable cached loadall archives. Keep raw ZIP as
the oracle, validate every source member, and record total DB bytes, build
time/RSS, parity and bounded query performance before migrating heavy
diagnostics.

No temporal delta encoding, RLE, state-version dedup or cross-perspective dedup
is needed for this step.
