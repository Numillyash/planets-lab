# Finite-fuel Tow classic-storm reclassification runtime — 2026-09-09

This file records the completed bounded server runtime that reconciles the
finite-fuel Tow clean residual population after historical game mode was
resolved through public `loadinfo`.

## Runtime provenance

- repository: `Numillyash/planets-lab`
- candidate: `fc65e873fcc7e2935f3c761183027a5e850b4f97`
- source external-context gate:
  `logs/finite-fuel-tow-external-20260909T171801Z-2c5d841f-20098`
- source classic-membership gate:
  `logs/finite-fuel-tow-classic-storm-20260909T193531Z-6f125283-18812`
- source storm-mode gate:
  `logs/finite-fuel-tow-storm-mode-20260909T204843Z-4589d412-8435`
- collected reclassification gate:
  `logs/finite-fuel-tow-classic-reclass-20260909T205859Z-fc65e873-11918`

All runner stages completed `0/0`.

## Closed accounting

```text
clean_residual_input=53
cases=53
mode_false_games=3
mode_not_false_games=0
exact_root_vector_rows=44
classic_origin_rows=44
classic_storm_attributed=44
post_classic_storm_residual=9
remaining_due_mode=0
remaining_no_exact_root_vector=9
remaining_no_classic_origin_membership=0
```

Per-game classic-storm attribution:

```text
360690: 33 attributed / 6 remaining
511506:  4 attributed / 2 remaining
620694:  7 attributed / 1 remaining
```

The 44 attributed rows combine all three independently preserved facts required
by the bounded gate:

1. the complete factual residual vector equals an actual historical after-turn
   root ion-storm drag vector;
2. the corresponding classic constant-voltage root circle qualifies the Tow
   origin;
3. public `game/loadinfo` resolves `nuionstorms=false` for the contributing
   game.

Within this exact historical scope those 44 rows are therefore attributable
classic ion-storm confounders and are removed from the Tow fuel evidence-mining
residual population. This does not establish a general storm Host-order rule.

## Exact nine-row remainder

```text
360690 T41  tower425 target353 hull75 race8  W9  residual=(-1,3)   norm=3.162   same_line_route
360690 T44  tower291 target417 hull56 race6  W9  residual=(-33,-8) norm=33.956  same_line_route
360690 T84  tower22  target422 hull23 race2  W9  residual=(3,-31)  norm=31.145  off_route
360690 T123 tower190 target49  hull46 race11 W8  residual=(46,130) norm=137.899 off_route
360690 T124 tower190 target49  hull46 race11 W3  residual=(35,29)  norm=45.453  off_route
360690 T185 tower436 target124 hull17 race6  W9  residual=(5,17)   norm=17.720  same_line_route
511506 T34  tower188 target136 hull52 race6  W9  residual=(76,94)  norm=120.880 off_route
511506 T39  tower17  target321 hull17 race6  W9  residual=(-64,305) norm=311.642 off_route
620694 T126 tower408 target95  hull86 race10 W8  residual=(21,-16) norm=26.401  off_route
```

Shape summary:

```text
by_direction: same_line_route=3, off_route=6
by_baseline: reachable_other=5, above_nominal=3, partial_other=1
by_warp: W9=6, W8=2, W3=1
```

The two consecutive `360690/T123-T124` rows share tower 190 / target 49 and are
kept together as a contextual lead rather than split into independent fuel
observations.

## Decision

- 44-row classic-storm family: `CORPUS_OBSERVED + TESTED` in the bounded gate;
- finite-fuel Tow cost basis: **OPEN**;
- no nominal-vs-rasterized Tow discriminator is created by this
  reclassification;
- no `planets-intel` production transfer is implied.

Next bounded step: test the exact nine-row remainder against classic multi-root
storm combinations before investigating passenger Chunnel / other special
relocation context. Multi-root matches are leads until Host processing order is
independently established; do not silently promote them to a general storm
rule.
