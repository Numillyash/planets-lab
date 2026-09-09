# Finite-fuel Tow storm-vector follow-up — runtime result

Date: 2026-09-09

GitHub `main` is the source of truth. This handoff records the completed bounded storm-vector follow-up at candidate `1f21ada6654892f4f40dce352a5c275031df1ccd`. It does **not** promote finite-fuel Tow or change production storm semantics.

## Source gate

The pass reused the completed external-context gate:

```text
logs/finite-fuel-tow-external-20260909T171801Z-2c5d841f-20098
```

Runner output was collected in:

```text
logs/finite-fuel-tow-storm-vector-20260909T190242Z-1f21ada6-7761
```

All stages completed successfully:

```text
inputs        0 / 0
tooling       0 / 0
storm-vector  0 / 0
summary       0 / 0
```

The bounded input remained exactly the 53 Tow rows left clean after warp-well and external-context filtering.

## Vector result

```text
clean_residual_input                    53
cases                                   53
either_turn_single_root_vector_exact    44
no_single_root_vector_exact              9
before_single_root_vector_exact          7
after_single_root_vector_exact          44
before_single_root_vector_ambiguous      0
after_single_root_vector_ambiguous       5
```

By game:

```text
game 360690  cases 39  after-root exact 33  no root-vector match 6
game 511506  cases  6  after-root exact  4  no root-vector match 2
game 620694  cases  8  after-root exact  7  no root-vector match 1
```

The exact after-turn root vectors are overwhelmingly the documented 75%-of-storm-speed displacement family:

```text
after matched root Warp 6  44 root matches
after matched root Warp 8   5 root matches
```

The root-match count can exceed the row count because five rows have two vector-equivalent after-turn root storms. The row-level exact population remains 44 / 53.

This strongly attributes the **shape and magnitude** of most remaining Tow residuals to historical ion-storm movement vectors. It is not yet proof that those Tow pairs qualified for drag at the relevant Host subphase.

## Qualification mismatch

The current generic storm classifier assumption was deliberately tested at three points using both before-turn and after-turn stored storm states:

```text
any_resolved_point_exact                 0
no_resolved_point_exact                 53
before_resolved_origin_exact             0
before_resolved_geometry_exact           0
before_resolved_observed_exact           0
after_resolved_origin_exact              0
after_resolved_geometry_exact            0
after_resolved_observed_exact            0
```

There were no storm-context conflicts or invalid turns.

Many exact-vector rows have local voltage below the class-4 threshold in the persisted after-turn circles at origin, direct Tow geometry endpoint and factual endpoint. Several have zero persisted local voltage at all three points while their residual exactly equals the after-turn root drag vector.

Representative signatures include:

- a 27-ly residual exactly matching an after-turn Warp-6 root while persisted local voltage is below class 4;
- 48-ly residuals exactly matching after-turn Warp-8 roots while persisted after-turn membership is absent;
- five co-located Tow pairs on `360690 / T131 -> T132` sharing the same `(21,-17)` residual, equal to vector-equivalent historical Warp-6 roots.

The strongest current interpretation is therefore a **transient ion-storm state / Host-order lead**: the visible after-turn root heading/warp appears to carry the right drag vector, while neither persisted before-turn nor persisted after-turn circle geometry/strength reproduces class-4 qualification under the current point checks.

Do not convert this into a rule without testing the transient storm state and ordinary movement controls.

## Next bounded gate

The next diagnostic must pair stable before/after storm IDs and test a small explicit family of transient membership states while holding the observed exact after-turn root drag vector fixed:

```text
before stored geometry + before strength
before geometry translated by before storm movement + before strength
translated before geometry + after strength/radius
persisted after geometry + before strength/radius
persisted after geometry + after strength/radius
```

Membership should be checked at least at the pre-Tow origin and direct Tow geometry endpoint. The factual endpoint may be reported diagnostically but must not be used as a causal premise.

The same hypotheses must be run against ordinary non-Tow direct ion-storm transitions already reproduced by the current classifier. A candidate that only closes Tow residuals but breaks ordinary controls must not be generalized.

## Status

```text
finite-fuel Tow: OPEN
post-warp-well residual: 56
post-external-context clean residual: 53
clean rows with exact historical after-turn root drag vector: 44 / 53
persisted-state resolved classifier exact at tested points: 0 / 53
transient storm-state hypothesis: INFERRED LEAD, NOT YET ATTRIBUTED
nominal-vs-projected Tow discriminator: NONE FOUND
planets-intel Tow transfer: BLOCKED
```

No simulator mechanics and no `planets-intel` behavior change from this checkpoint.
