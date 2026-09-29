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
