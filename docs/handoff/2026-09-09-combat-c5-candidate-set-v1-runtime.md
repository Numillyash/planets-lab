# C5 Host combat — candidate-set v1 runtime — 2026-09-09

GitHub is the source of truth. PR #28 remains open/draft. Game `591478` remains excluded from ordinary promotion.

## Runtime source

```text
1ef175f77419970b244c5d69df2863a06390ab6c
```

Artifact:

```text
artifacts/combat-c5-candidate-set-20260909-223013
```

Runtime completed successfully:

```text
TARGETED TESTS: passed
tests rc=0
audit rc=0
payload_conflicts=0
```

## v1 population result

The deliberately conservative stationary-position gate produced:

```text
archives_considered=11
factual_ship_combat_sites=1220
factual_unique_pairs=1986
candidate_pairs=107
factual_pairs_candidate_covered=1
factual_pairs_movement_uncovered=1985
```

Movement exclusions were dominated by:

```text
self_movement_possible=1606
tow_target=75
hyperjump_movement=17
tow_attempt=5
potential_chunnel_source_stack=4
intercept_movement=1
```

The one independently position-covered factual pair was accepted by both pair-composition profiles:

```text
strict:
  candidate_pairs=107
  blocked=105
  eligible=1
  unresolved=1
  factual_pair_status={'eligible': 1}
  eligible_nonfactual=0

conditional:
  candidate_pairs=107
  blocked=105
  eligible=1
  unresolved=1
  factual_pair_status={'eligible': 1}
  eligible_nonfactual=0
```

Site-level result:

```text
sites=1220
all_factual_position_covered=1
strict_all_candidate_resolved=1219
conditional_all_candidate_resolved=1219
strict_factual_subset_of_eligible=1
conditional_factual_subset_of_eligible=1
strict_eligible_exact_factual=1
conditional_eligible_exact_factual=1
```

No example rows were emitted because there was no candidate-covered factual blocker and no eligible nonfactual row.

## Interpretation

This is a **clean but coverage-limited gate**.

What is supported:

- the v1 diagnostic/tests executed successfully;
- the only factual pair whose site membership was independently established by the strict Warp-0 stationary filter was classified `eligible` by both strict and conditional pair-composition profiles;
- there is no contradiction to the canonical pair eligibility/selection layer in the tiny covered subset.

What is **not** supported:

- broad candidate-set recall;
- full post-movement stack reconstruction;
- precision of pair eligibility against the factual queue;
- a claim that 105 blocked nonfactual pairs are Host queue negatives;
- any promotion of the whole candidate-set predictor to `DIFF_VERIFIED`.

Coverage is only:

```text
1 / 1986 factual unique ship pairs
```

so the gate is not population-strong enough to validate combat candidate generation.

## Evidence status

```text
v1 diagnostic/helper behavior:          TESTED
v1 one-row factual covered result:      CORPUS_OBSERVED
canonical pair layer contradiction:     NONE IN COVERED SUBSET
candidate-set prediction generally:     NOT YET DIFF_VERIFIED
post-movement stack reconstruction:     NOT YET COMPLETE
```

## Next gate

Do **not** relax the stationary filter merely to increase the counter.

The dominant missing population is `self_movement_possible=1606`, so the next justified expansion is to derive ordinary self-movement endpoints from owner-current `T-1` using the already canonical movement mechanics.

The next position profile must:

1. never use factual `T` ship position as an input;
2. keep Tow, Intercept, C&I, HYP and Chunnel outside the ordinary self-movement branch;
3. use the canonical Host major/minor normal-movement geometry rather than straight-line floating interpolation;
4. account for Gravitonic distance, fuel/mass, strict damage-limited warp and warp-well snapping where inputs are known;
5. fail closed when pre-movement transfer/repair/topology state can materially change the endpoint and cannot be reconstructed;
6. keep factual VCR site coordinates as the site-conditioned comparison frame only;
7. continue to distinguish `blocked`, `eligible`, `unresolved` and movement-uncovered rows.

Only after movement-derived position coverage becomes useful should mutable target-list/queue precision be interpreted.
