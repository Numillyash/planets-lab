# Corpus DB typed1 — public36 canonical runtime

Date: 2026-10-01

Branch: `feature/corpus-db-v1`

Runtime source HEAD:

```text
eb7edc0e56d8c9175e0c8691cd7d178237830610
```

## Population

```text
archives                 36
source archive bytes     9456773573
turn members             126418
entity rows              314311240
member fields            3936641
decoded JSON bytes       133808928311
```

Corpus fingerprint:

```text
11cd75fa918dec3d6839f6dbdcb3537bcb66d6f4c9d935f1866003998aab9e42
```

## Import

```text
wall seconds             9816.091785177
wall time                ~2h43m36s
peak RSS bytes           26944557056
peak RSS                 ~25.09 GiB
```

## Full semantic parity

```text
checked                  126418
failed                   0
mismatches               []
wall seconds             6188.201072546
wall time                ~1h43m08s
```

The reported process peak RSS for parity is inherited from the same process
after import; it is not an independent parity-only peak measurement.

## Published generation

```text
build_id
corpus-v1typed-public36-20260930T211714Z-11cd75fa918d

generation
/corpus-db/generations/corpus-v1typed-public36-20260930T211714Z-11cd75fa918d.duckdb

sha256
c615dab02b4d7965288f6d590a157a90101935bb33931f6e3571338e5a71cb15

database bytes
38931017728
```

## Ratios

```text
source ZIP                 ~8.807 GiB
decoded JSON               ~124.619 GiB
typed1 DB                  ~36.257 GiB

decoded / ZIP               14.1495x
typed1 DB / ZIP              4.1167x
typed1 DB / decoded JSON      0.2909x
reduction vs decoded JSON    70.91%
```

Compared with the single-game typed1 prototype, disk scaling is slightly better
than linear relative to decoded JSON:

```text
game-233558 typed1 / decoded JSON   31.97%
public36 typed1 / decoded JSON      29.09%
```

## Shared read gate

Both normal planets-lab and research/external-engine-analysis containers opened
the same published public36 generation concurrently read-only:

```text
source_members=126418
shared_generation_concurrent_read: PASS
```

## Gate status

```text
36 immutable source archives       GREEN
full member parity                 GREEN 126418 / 126418
published immutable generation     GREEN
CURRENT                            GREEN
normal + external shared read      GREEN
disk reduction vs decoded JSON     GREEN
import peak RSS                    NEEDS OPTIMIZATION
```

## Compact2 implication

The single-game typed1 attribution showed that the current physical layout is
still dominated by generic entity ART indexes, a complete compressed member
fallback, and duplicated generic entity_rows.

The public36 typed1 generation is therefore retained as the canonical baseline,
not the final storage format. The next storage iteration should target:

1. no global entity_rows ART indexes unless a measured query requires them;
2. no generic entity_rows duplication for known typed sections;
3. sparse semantic residual instead of a complete decoded_payload_zlib member
   copy;
4. exact reconstruction parity against immutable ZIP before publication;
5. bounded-memory import/index construction.

No temporal delta encoding, RLE, state-version dedup or cross-perspective dedup
is required for this compact2 step.
