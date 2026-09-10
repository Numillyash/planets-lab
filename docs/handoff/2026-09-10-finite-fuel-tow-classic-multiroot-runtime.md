# Finite-fuel Tow classic multi-root runtime — 2026-09-10

This file records the completed bounded server runtime that tested the exact
nine-row post-classic-storm finite-fuel Tow residual against classic multi-root
ion-storm combinations.

## Runtime provenance

- repository: `Numillyash/planets-lab`
- candidate: `4f2dfa836e6e38936d5f26fcf671fb301081661d`
- source reclassification gate:
  `logs/finite-fuel-tow-classic-reclass-20260909T205859Z-fc65e873-11918`
- collected multi-root gate:
  `logs/finite-fuel-tow-classic-multiroot-20260909T213519Z-4f2dfa83-22450`

All runner stages completed `0/0`.

## Result

```text
post_classic_storm_input=9
cases=9
rows_with_any_multi_root_exact_lead=0
no_multi_root_exact_lead=9
before_static_subset_exact_rows=0
after_static_subset_exact_rows=0
before_sorted_sequential_exact_rows=0
after_sorted_sequential_exact_rows=0
before_any_permutation_subset_exact_rows=0
after_any_permutation_subset_exact_rows=0
before_storm_conflict=0
before_storm_invalid=0
after_storm_conflict=0
after_storm_invalid=0
```

Per-game accounting was also closed:

```text
360690: 6 / 6 no multi-root exact lead
511506: 2 / 2 no multi-root exact lead
620694: 1 / 1 no multi-root exact lead
```

The bounded search included static subsets of classic-origin-eligible roots,
stable root-id sequential processing with membership rechecked after each drag,
and arbitrary sequential subsets as a deliberately weaker search lead. Neither
direct nor warp-well endpoint handling produced an exact match for any of the
nine rows.

Some rows still have an individually classic-origin-eligible root in the
after-turn storm state, but its displacement does not explain the factual Tow
residual and no tested multi-root combination closes the gap. Those rows must
therefore remain in the nine-row non-storm residual population rather than be
reclassified from membership alone.

## Decision

- the previously attributed 44-row classic-storm family remains
  `CORPUS_OBSERVED + TESTED` within its bounded gate;
- the exact nine-row remainder has **no bounded classic multi-root exact lead**;
- do not spend further finite corpus fuel on additional unconstrained storm
  permutations without new independent evidence;
- finite-fuel Tow cost basis remains **OPEN**;
- no `planets-intel` production transfer is implied.

Next bounded step: inspect the nine rows for passenger Chunnel / special
relocation context. Keep independently observed active Chunnel routes separate
from weaker co-movement or structural candidates, and fail closed on identity,
visibility and phase ambiguity. Only after external relocation context is
excluded should the same-line rows return to Tow fuel inference.
