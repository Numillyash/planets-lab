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


## Discovery post-analysis: AFSim side canonicalization also rejected globally

The post-analysis of all 31 resolved adjacent discovery rows tested the recovered
AFSim side rule independently of AFSim's failed queue selector.

Conditioning only on the factual next-pair identity:

```text
lower ship ID  -> LEFT
higher ship ID -> RIGHT
```

produced:

```text
ID-canonical side exact:     21
ID-canonical side mismatch:  10

factual LEFT:
  exact    18
  mismatch  7

factual RIGHT:
  exact     3
  mismatch  3
```

Thus the AFSim ID-canonical LEFT/RIGHT rule is also rejected as a general Nu
post-capture side rule on discovery:

```text
21 / 31 ~= 67.74%
```

The earlier conditional 5/6 result was therefore selection-biased: it looked
strong only inside the six rows where the complete AFSim queue happened to pick
the factual pair.

### Pair-mismatch decomposition

Both fuel variants remain identical and decompose as:

```text
exact                           6
prize_with_wrong_opponent       4
factual_opponent_without_prize  5
unrelated_pair                  3
no_pair                        13
                              ----
                               31
```

AFSim phase use:

```text
KILL            8
Primary Enemy  10
none           13
```

This is diagnostically important.

The dominant failure is not LEFT/RIGHT assignment. In 13/31 adjacent rows the
AFSim selector produces no ship-vs-ship pair at all, and in another 12/31 it
selects a different pair. Therefore AFSim's historical KILL/Primary-Enemy
selection policy is the primary incompatibility with Nu, not merely its
post-selection side canonicalization.

### Consequence

AFSim contributes a useful independent architectural counterexample, but none
of these AFSim components can currently be promoted as general Nu rules:

```text
full AFSim queue                  rejected  6/31 pair exact
lower-ID LEFT canonicalization    rejected 21/31 side exact
```

The next discriminator should therefore isolate the structural question from
AFSim's selector:

```text
post-capture mutable-state restart/recomposition
+
Nu-derived strict attacker ranking
```

rather than continuing to refine AFSim's KILL/PE logic.

Held-out remains closed.


## Strict-rank analyzer compatibility correction

The first strict-rank post-analysis attempt stopped before reading row evidence:

```text
ERROR: O-layer artifact must be partition=discovery
```

This was a schema-compatibility guard failure.

Legacy discovery O-layer artifacts used:

```text
evidence_status = DISCOVERY_...
source_discovery = ...discovery...
```

without an explicit top-level:

```text
partition = discovery
```

The analyzer now accepts both current and legacy discovery-only markers.

Because older artifacts may also predate the enriched
`active_dependency` rank context, a compatibility runner was added:

```text
tools/research/run-postcapture-strict-rank-discovery.sh
```

It:

1. checks the existing discovery O-layer artifact;
2. reuses it directly if every adjacent row already contains requester/strict
   rank context;
3. otherwise regenerates the discovery-only O-layer through the current
   canonical `main` runner and read-only Corpus DB;
4. runs the research strict-rank cross-analysis;
5. never reads held-out.

No strict-rank result existed before this correction.


## Nu-derived requester/strict-rank cross-analysis

The discovery-only strict-rank analysis completed without reading held-out.

Population:

```text
adjacent rows:                   31

strict rank 1:                   13
strict rank >1:                   2
strict rank missing:             16

requester rank 1:                13
requester rank >1:                2
requester rank missing:          16

dependency qualified:            15
dependency not qualified:        16
```

The 16 missing-rank rows align in count with the previously documented
discovery movement-position fail-closed population. They must not be treated as
queue-selection mismatches until their dependency class is confirmed row by
row.

On the 15 dependency-qualified rows:

```text
factual next opponent strict rank 1 = 13 / 15
factual next opponent strict rank >1 = 2 / 15
```

Therefore the naive candidate:

```text
post-capture recomposition
-> choose rank-1 strict attacker
```

is not yet universal even inside the currently qualified subset.

The two rank>1 rows are now the highest-value queue residuals. They may indicate
an elapsed-pair/history exclusion, already-consumed combat order, pair-cap
effect, or another mutable queue constraint that is not represented by the
static requester rank.

### Cross-tabulation against AFSim failure modes

AFSim categories with factual opponent strict-rank 1:

```text
AFSim exact                          6 / 6
prize_with_wrong_opponent            0 / 4
factual_opponent_without_prize       5 / 5
unrelated_pair                       2 / 3
no_pair                              0 / 13
```

Thus seven of AFSim's 25 pair failures occur even where the independently
reconstructed Nu-derived factual opponent is rank 1:

```text
AFSim nonexact + factual strict-rank 1 = 7 / 25
```

This is strong evidence that AFSim's KILL/PE pair selector is the wrong selector
for Nu. It does not, by itself, prove a complete Nu restart queue.

The next bounded step is to print the exact two rank>1 rows and classify the 16
rank-missing rows by dependency reason/source before any new queue candidate is
frozen.


## Residual split closed to two qualified queue cases

The residual reporter confirms that the 16 missing-rank rows are exactly the
previously known movement-position fail-closed population:

```text
pre_move_mkt_mass_change        5
intercept_movement              3
hyperjump_movement              3
normal_mine_route_risk          2
tow_target                      2
potential_chunnel_source_stack  1
                               --
                               16
```

Every one of those rows has:

```text
factual_opponent_site_predicted = false
```

so they remain movement/position dependency cases and are not evidence against
the post-capture queue ranking itself.

This leaves exactly two currently qualified strict-rank residuals:

```text
486109 / T55
VCR 191 -> 192
captured ship 450
factual opponent 467
strict rank = 2
requester rank = 2
factual prize side = LEFT

486109 / T88
VCR 518 -> 519
captured ship 296
factual opponent 454
strict rank = 2
requester rank = 2
factual prize side = RIGHT
```

Both have fully reconstructed ordinary stationary geometry:

```text
status            resolved
site_predicted    true
position source   stationary_effective_warp_zero
active            true
candidate         true
requests combat   true
strict permission true
```

Therefore they are genuine queue-order residuals rather than movement,
membership, diplomacy, or candidate-resolution failures.

Both occur in the same public game, 486109, at different turns.

AFSim behavior on the two cases differs:

```text
T55: unrelated_pair / primary_enemy
T88: prize_with_wrong_opponent / primary_enemy
```

The next targeted diagnostic reconstructs only these two sites and exposes:

```text
- the rank-1 competitor
- full requester / strict requester order
- static priorities and T-1 orders for rank1 and factual rank2
- elapsed local VCR history through the capture VCR
- prior prize/rank1 and prize/factual pair occurrence counts
- prior appearances of rank1/factual/prize
- post-combat mutation trace
- c2ng identity-anchored cursor context
```

Tracked tools:

```text
tools/research/probe-postcapture-rank2-residuals.py
tools/research/run-postcapture-rank2-targeted.sh
```

The immediate discriminator is whether the static rank-1 competitor is already
ineligible due to elapsed mutable combat history (for example a prior
prize/rank1 pair occurrence or another consumed-order constraint).

Held-out remains unread.


## Targeted rank>1 replay input correction

The first targeted replay stopped with:

```text
ERROR: targeted active replay unresolved: prize_owner_not_captor
```

This was not a corpus or queue residual.

Cause: the saved O-layer observation intentionally contains the compact
post-analysis projection but does not preserve the full capture transition
identity, including:

```text
captor_ship_id
captor_owner_id
owner_id_before
owner_id_after
```

The targeted probe incorrectly rebuilt `_capture_projection()` from that
compact O-layer row. The mutable replay correctly transferred the prize to the
captor's owner, but the final consistency check compared that owner against a
missing `captor_owner_id=None`, producing the false
`prize_owner_not_captor` result.

The targeted probe now joins each residual to the canonical discovery
capture-side artifact by:

```text
(game_id,
 turn,
 capture_vcr_id,
 next_vcr_id,
 captured_ship_id,
 next_opponent_ship_id)
```

and uses the full capture-side row for mutable capture replay. O-layer remains
the source of the already-computed queue/cursor context.

Tracked correction:

```text
35c5f4783838ae7e87b1b2ae2a5b6c08186e342d
research: join full capture transition in rank2 probe

dd0bd13d9255f9f93a01754308e5a2a27d0ee364
research: pass capture-side source into rank2 gate
```

No targeted rank>1 evidence was produced by the failed run. Held-out remained
unread.
