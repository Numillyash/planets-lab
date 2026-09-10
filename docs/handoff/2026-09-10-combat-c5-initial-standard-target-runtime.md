# C5 Host combat — initial plain STANDARD target runtime

GitHub is the source of truth. PR #28 remains draft/open. Game `591478` remains excluded from ordinary promotion.

## Runtime

Source:

```text
d7ade79d1344ba21a99f21d3fcc2d3e911dff3c3
```

Artifact:

```text
artifacts/combat-c5-initial-standard-target-20260910-132746
```

Result:

```text
tests rc=0
audit rc=0
payload_conflicts=0
sites=1220
all_factual_positions_exact_sites=243
```

The gate tests only the **first plain STANDARD ship-vs-ship selection**, before any combat outcome can mutate survivors, ownership, fuel/damage, repeated-pair history or target availability.

## Exact-set result

When the reconstructed eligible set exactly equals the factual pair set:

```text
strict:
  sites=162
  first_pair_exact=162
  first_right_exact=162
  multi_candidate_sites=23
  target_order_informative_sites=15
  target_highest_priority_exact=15

conditional:
  sites=169
  first_pair_exact=169
  first_right_exact=169
  multi_candidate_sites=23
  target_order_informative_sites=15
  target_highest_priority_exact=15
```

There are **zero exact-set mismatches**. Every one of the 15 informative exact-set target-order sites chooses target rank 1 under the tested hypothesis:

```text
first active ship = highest standard Combat Priority ship having an eligible target
first target      = highest-priority eligible target for that active ship
```

The deliberately wrong low-priority-target control matches fewer rows and therefore does not explain the population better.

This strongly supports the ordering hypothesis **conditional on a correct eligible candidate set**, but no canonical target selector is promoted yet because broad scope still exposes two candidate-set residuals.

## Broad-scope residuals

Both strict and conditional broad scopes have the same two mismatches:

```text
360690/T83 site 2374,2260
  factual first: (190,264), RIGHT=264
  reconstructed eligible: (98,264), (190,264)
  active ship: 264
  predicted highest-priority target: 98
  factual target rank: 2

511506/T94 site 2716,1999
  factual first: (332,496), RIGHT=496
  reconstructed eligible: (202,496), (332,496)
  active ship: 496, FC 001
  predicted highest-priority target: 202
  factual target rank: 2
```

In both rows:

- the factual active ship is already correct;
- the factual pair is contained in the reconstructed eligible set;
- the mismatch appears only because one additional nonfactual pair is considered eligible;
- the low-priority-target control happens to choose the factual target because it selects the other member of a two-target list.

Therefore **do not invert target ordering** from these two rows. First investigate why `[98,264]` and `[202,496]` survive candidate eligibility.

## Immediate follow-up

A concrete modeling gap exists in the current candidate diagnostics: `has_fuel` is derived from positive **T-1 neutronium**, while combat happens after movement. A ship can therefore spend its final fuel reaching the site and be incorrectly retained as combat-eligible.

New focused diagnostic:

```text
tools/diagnostics/combat_host_initial_standard_target_residual_audit.py
tests/test_combat_host_initial_standard_target_residual_audit.py
```

It reconstructs ordinary normal-movement fuel for only the two broad residual sites using the existing canonical `plan_full_normal_move(...)` / movement fuel machinery. It prints T state only as attribution/control and never uses T to compute the predictor.

If both extra targets independently resolve to zero post-movement fuel, treat the broad target-order residuals as candidate-set fuel-state errors, not target-order errors. Then integrate safe post-movement fuel into candidate inputs and rerun candidate-set v2 + initial target-order gate before promoting a selector.

If either extra target retains fuel, investigate another blocker. Do not change standard Combat Priority or target ordering merely to fit these two rows.

Keep `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED` distinct.