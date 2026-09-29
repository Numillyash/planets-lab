# Public corpus ingest benchmark and reuse optimization

Date: 2026-09-29

## Runtime evidence

The bounded six-round acquisition run published:

```text
runtime-logs/public-validation-corpus/20260928T185936Z_56db30677d9e
source main 56db30677d9efb83017c6750cc48cab30687f11a
started 2026-09-28T18:59:36Z
finished 2026-09-29T01:40:52Z
exit_code 1
```

Final state:

```text
selected              36
indexed               35
failed                 1
failed game        41752
snapshots         122601
transitions       122056
archive bytes  9117711471
```

The runner reached `MAX_BACKFILL_ROUNDS=6`. Late rounds repeatedly reprocessed
the same successful cached games even when only one replacement changed.

## Storage survey

Current selected corpus:

```text
36 ZIP archives
127401 .trn members
compressed       8.69 GiB
extracted       123.71 GiB
block-rounded   123.95 GiB
expansion ratio 14.23x
```

All immutable cache:

```text
83 ZIP archives
300274 .trn members
compressed       20.31 GiB
extracted       294.72 GiB
block-rounded   295.29 GiB
expansion ratio 14.51x
```

Only about 65 GiB was free during the survey, so a complete extracted cache was
not practical.

## Representative benchmark

Successful current-corpus game 233558:

```text
ZIP size            0.64 GiB
extracted size      8.91 GiB
members             6710
full current ingest 4:07.17
unzip once          0:31.69
ZIP read+JSON       1:40.74
files read+JSON     1:36.61
```

Moving the payload to an extracted directory improved the read+JSON
microbenchmark by only about 4.1%. That does not justify ~124 GiB of selected
corpus expansion.

The larger avoidable cost is repeated derivation. The same already-successful
game was being decompressed, normalized, mechanics-counted and canonical-imported
again on every backfill round.

## Optimization decision

Do not add a full extracted corpus cache.

Instead:

1. reuse compatible previous per-game index records from the existing
   `--index-output` when manifest identity matches and the immutable ZIP remains
   present with its recorded byte size;
2. allow `--no-reuse-index` for deliberate full rebuilds;
3. make `index_game_archive()` consume the ZIP in one CRC-checking member pass
   rather than repeatedly calling `testzip()` and reopening the archive.

The immutable ZIP remains the source-of-truth evidence artifact. Reuse is a
derived-data optimization only.

Expected late-round behavior changes from:

```text
1 replacement
-> re-index 36 archives
```

to:

```text
1 replacement
-> reuse 35 index records
-> index only the replacement
-> aggregate 36 compact records
```

No NuHost mechanic is promoted by this optimization.

## Post-optimization validation

The representative game-233558 benchmark was repeated on the optimized main
implementation.

Forced rebuild, which disables index reuse:

```text
old full ingest                 4:07.17  (247.17 s)
single-pass ZIP full rebuild    3:27.34  (207.34 s)
absolute improvement              39.83 s
relative improvement               16.1 %
speedup                             1.19x
```

The single-pass ZIP change therefore produces a measurable but secondary gain.

Immediate rerun with the same immutable archive and index output:

```text
source: index-cache
elapsed: 0:00.87
```

Compared with the optimized forced rebuild, per-game index reuse is about
238x faster for this representative cached game, eliminating about 99.58% of
the repeated wall-clock work. Relative to the pre-optimization full ingest the
same reuse path is about 284x faster.

This validates the intended late-backfill behavior: already successful games
should contribute only compact-record read/aggregation cost, while full
normalization remains limited to newly selected replacement archives.

These are representative per-game measurements, not a guarantee of an equal
whole-corpus speedup; replacement archives vary greatly in size and network
downloads remain outside the reuse benefit.

## Full-pipeline validation

The next canonical public-validation run published:

```text
runtime-logs/public-validation-corpus/20260929T145351Z_b62649f47dcb
source main b62649f47dcba903d570ca82f688b9c7c28420e5
started 2026-09-29T14:53:51Z
finished 2026-09-29T14:56:43Z
elapsed 2m52s
```

This is the decisive end-to-end performance validation. Across all six bounded
backfill rounds, the 35 already-compatible games were reused from the compact
index with `source: index-cache`; only the newly selected replacement archive
was fully inspected.

All six replacements selected during this run were legacy/binary turn archives:

```text
57025
46501
59938
42448
57535
40773
```

Each failed immediately at `player1-turn0.trn` with the known non-UTF-8
normalization boundary. The corpus therefore remained at 35 / 36, but the same
six-round acquisition that previously implied hours of repeated derivation now
completed in under three minutes.

This changes the appropriate safety bound. The default
`MAX_BACKFILL_ROUNDS` is raised from 6 to 24. The bound remains finite, but it
now reflects the cheap post-reuse runtime and allows the objective
selection/rejection chain to proceed through clusters of incompatible historical
archives without repeated operator intervention.

No game-id or age heuristic is introduced. Candidate selection remains unchanged;
compatibility continues to be established from the actual Planets.nu archive.
