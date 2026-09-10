# C5 Host combat — candidate-set v2 runtime

GitHub is the source of truth. PR #28 remains draft/open. Game `591478` remains excluded from ordinary promotion.

## Runtime source

```text
c804575f4275f4454dbb282d9fcfc99fad0700d6
```

Artifact reported by the historical runtime:

```text
artifacts/combat-c5-candidate-set-v2-20260910-003515
```

Runtime result:

```text
tests rc=0
audit rc=0
payload_conflicts=0
```

## Population

```text
factual ship-combat sites        1220
factual unique pairs             1986
candidate-covered factual pairs   428
candidate-uncovered factual      1558
candidate pairs total            1092
```

This is a material coverage expansion over candidate-set v1 (`1/1986`).

Position status inside the site-conditioned v2 gate:

```text
factual pair position:
  exact       431
  mismatch      2
  unresolved 1553

factual ship position:
  exact      1508
  mismatch      2
  unresolved 1694
```

The two position mismatches are movement-scope residuals and are not interpreted as combat blockers. The v2 gate additionally fails closed routes crossing visible T-1 foreign mines/webs, so the position population is intentionally narrower than the repaired position-v3 diagnostic:

```text
normal_mine_route_risk 3907
web_mine_route_risk    1789
```

## Pair eligibility differential

Strict leave-pair-out profile:

```text
candidate status:
  eligible    737
  blocked     314
  unresolved   41

candidate-covered factual pairs:
  eligible    420
  unresolved    8
  blocked       0

eligible nonfactual 317
```

Conditional aggression profile:

```text
candidate status:
  eligible    758
  blocked     314
  unresolved   20

candidate-covered factual pairs:
  eligible    427
  unresolved    1
  blocked       0

eligible nonfactual 331
```

The single conditional factual unresolved row is `360690/T140`, pair `[198,458]`, where pair composition reaches `left_fuel_unknown`. It is a coverage gap, not a hard contradiction.

Most important result:

```text
candidate-covered factual pair conditionally hard-blocked = 0
```

This is the first broad candidate-set differential for the canonical pair layer that does not use factual VCR existence as the positive eligibility input. Factual VCR data supplies the site coordinate and held-out factual pair set only; per-ship position comes from owner-current T-1 reconstruction.

## Site-level boundary

```text
sites                                      1220
all factual positions covered              242
conditional factual subset of eligible     236
conditional eligible exactly factual       171
strict factual subset of eligible           227
strict eligible exactly factual             164
```

There is no nonzero `conditional_factual_not_subset_of_eligible` count. The six fully factual-position-covered sites not counted in `conditional_factual_subset_of_eligible` are unresolved at candidate-decision level; they are not known false negatives.

`eligible_nonfactual` is deliberately **not** treated as a pair-eligibility error. A physically co-located pair can be eligible but never produce a VCR because another combat destroys/captures one participant before that target-list entry is reached. Explaining those rows belongs to mutable target selection / queue state.

## Evidence promotion

Within the candidate-set v2 scope:

```text
T-1-derived position composition       TESTED + CORPUS_OBSERVED / bounded DIFF_VERIFIED scope
canonical pair eligibility composition TESTED
candidate-set v2 positive differential CORPUS_OBSERVED + DIFF_VERIFIED
```

The last line is intentionally scoped to the 428 candidate-covered factual pairs and does not claim full combat-set recall. Position uncertainty remains explicit.

## Next gate

Do **not** immediately implement the complete mutable queue. First isolate selection before any battle outcome mutation.

Primary documentation states that after Priority Intercept, ships are processed by Combat Priority; each ship proceeds through its target list while alive/uncaptured, and a blocked selected opponent (for example matching FC) causes selection of the next-highest-priority opponent. This motivates an initial STANDARD target-selection differential.

The next audit should:

1. reconstruct the same v2 site candidate context;
2. restrict the strong comparison to position-covered, conditional-decision-resolved sites;
3. exclude sites with eligible PIA/C&I or non-plain side overrides from the plain STANDARD population;
4. order the first-pass active ship by `standard_battle_priority_key(...)`;
5. order that ship's eligible target list by target `standard_battle_priority_key(...)`;
6. compare the resulting first pair/right-side prediction with the first factual ship VCR at the site;
7. report an exact-candidate-set control scope separately from the broader resolved scope.

Only after that first-selection rule is clean should mutable survivor/capture state and second-pass/repeated-pair continuation be composed.

Keep matching-FC, Priority Intercept, reciprocal PIA, Galactic Power and repeated-pair evidence boundaries unchanged unless the new audit produces a direct contradiction.