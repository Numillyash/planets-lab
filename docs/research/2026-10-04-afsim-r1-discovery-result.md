# AFSim 1.31 AFSIM-R1 discovery differential result

Date: 2026-10-04

Branch:

```text
research/external-engine-analysis
```

Frozen external model:

```text
AFSIM-R1
```

Authority:

```text
EXTERNAL_IMPLEMENTATION / independent AFSim 1.31 reverse engineering
```

This document records the first discovery-only differential result. It does
not promote AFSim behavior into NuHost mechanics.

## Runtime provenance

Research checkout:

```text
796b78d218ca0da306cc4fde4350ffeed5c0a3d4
```

Canonical main checkout used for site/history reconstruction:

```text
6c976da1e3db9ac3ee1a970cc7721023489e1e7f
```

Shared Corpus DB:

```text
generations/corpus-v2compact-public36-20261002T083138Z-11cd75fa918d.duckdb
```

Corpus DB was mounted read-only.

The gate first passed all model unit tests:

```text
8 passed
```

## Discovery population

The frozen discovery probe reported:

```text
capture rows:                    50
adjacent rows:                   31
resolved adjacent:               31
unresolved active state:          0
unresolved metadata:              0
fuel robust:                     31
fuel sensitive:                   0
```

Therefore every globally adjacent capture -> next-VCR row was comparable and
none of the result depends on the probe's two fuel mappings.

The two fuel mappings were:

```text
tminus1:
  fuel := T-1 neutronium > 0

all_active:
  fuel := true for every post-history active ship
```

Both produced the same pair prediction on all 31 adjacent rows.

## Frozen AFSIM-R1 pair result

Discovery result:

```text
fuel-robust pair exact:      6
fuel-robust pair mismatch:  25

T-1 fuel pair exact:         6
T-1 fuel pair mismatch:     25

all-active pair exact:       6
all-active pair mismatch:   25
```

Thus:

```text
AFSIM-R1 pair accuracy on adjacent discovery rows = 6 / 31
                                                   ~= 19.35%
```

This rejects AFSIM-R1 as a general Nu post-capture next-pair model on the
discovery partition.

The negative result is particularly useful because AFSIM-R1 was reconstructed
independently from the c2ng/PCC lineage and embodies the opposite structural
choice:

```text
AFSim:
  mutable writeback
  -> full re-sort
  -> traversal restart

c2ng/PCC2 candidate:
  frozen original-order cursor / continuation
```

Neither architecture by itself explains the Nu discovery population.

For reference, the previously tested external c2ng O-layer on the same
31-row adjacent population had only:

```text
O pair reachable:      5
O pair not reachable: 26
```

AFSim's 6/31 exact next pairs are therefore only a marginal improvement, not a
resolution of the Nu blocker.

## Conditional LEFT/RIGHT result

For the six rows where AFSIM-R1 predicted the factual next pair, its recovered
side rule produced:

```text
side exact:     5
side mismatch:  1
```

AFSim's side rule is:

```text
lower ship ID  -> LEFT
higher ship ID -> RIGHT
```

The 5/6 conditional result is not enough to promote this rule because it is
conditioned on the small subset where AFSim also selected the correct pair.

However, side assignment is independent of AFSim's failed queue selector.
Therefore the next discovery-only discriminator is to condition on the factual
next-pair identity and test only:

```text
captured_ship_id < factual_next_opponent_id
    ? captured side = LEFT
    : captured side = RIGHT
```

This is an identity-anchored side-only comparator, not an independent queue
prediction.

## Current conclusion

The following hypothesis is rejected as a general Nu rule:

> After capture, Nu behaves like AFSim 1.31: persist capture mutation, fully
> re-sort the battle array, restart selection from the beginning, choose via
> AFSim KILL/PE phases, and canonicalize the selected pair by ship ID.

Evidence status:

```text
AFSIM-R1_vs_Nu = REJECTED_ON_DISCOVERY_AS_GENERAL_PAIR_MODEL
```

What remains potentially useful from AFSim must now be tested component-wise,
not as the whole engine:

```text
1. lower-ID LEFT / higher-ID RIGHT side canonicalization
2. full re-sort/restart as a structural component without AFSim's exact selector
3. owner/crew capture mutation as historical external corroboration only
```

Held-out remains closed.
