# Insufficient-fuel movement proration

Planets.nu documents a movement rule that differs from classic VGA Planets when a ship has some fuel but not enough to complete the movement requested for the current Host movement step.

For an ordinary reachable waypoint, the documented proportional rule is:

```text
actual_distance = waypoint_distance * fuel_available / fuel_required
```

The documentation gives the concrete example that a 60 light-year trip requiring 12 KT, with only 11 KT aboard, results in 55 light-years traveled.

Primary sources:

- https://help.planets.nu/fuel-details
- https://help.planets.nu/VGAP-3-differences
- https://help.planets.nu/FuelEstimateErrors
- https://help.planets.nu/navigation-precision

## Implemented normal-movement semantics

`prorate_waypoint_distance()` implements the continuous proportional distance ratio.

`plan_full_normal_move()` distinguishes two cases:

1. reachable waypoint: fuel is calculated for the waypoint distance;
2. true partial route: fuel is calculated for the continuous effective one-turn leg (`max_distance`) before integer endpoint rasterization.

For a true partial route, the integer endpoint produced by Host major/minor projection can be fractionally closer than the nominal one-turn distance. Historical differential evidence rejects using that shorter rasterized distance as the fuel-cost basis.

If fuel is insufficient, proration is applied to the movement requested for that Host step. Therefore a true partial route prorates the effective one-turn leg, not the full distant waypoint.

## Historical differential evidence

The bounded 12-game historical gate at candidate `f68a31376ff41810d72df0f3fadc165ff55e1017` compared the planner introduced by `993e76046c3ffaa40acf4b0aa7286d5bd9573480` with baseline `1d01bf20c745e84162b6c5ae249e0e81b0ccdc6c`.

Move Most population:

```text
prefilter_true_partial_rows              32371
true_partial_route                       15560
cost_basis_differs                        2927
projected_cost_endpoint_exact             2811
nominal_cost_endpoint_exact               2812
discriminating_endpoint                      1
discriminating_nominal_cost_support          1
discriminating_projected_cost_support        0
```

The discriminator is `360690/T164/ship41`: W9, origin `(1949,2950)`, distant waypoint `(2008,3067)`, factual endpoint `(1959,2969)`, snapshot fuel `11`, movement mass `517`. Rasterized one-turn distance requires `40 KT`; continuous nominal 81-ly distance requires `41 KT`. Only the nominal basis reproduces the factual endpoint, and the targeted audit found no already-modelled mine/storm/damage/Tow/Chunnel explanation.

Independent Intercept evidence is `620694/T73/ship278`: W9, movement mass `893`, snapshot fuel `29`, candidate full-leg requirement `72`, factual endpoint `(2742,2070)`. The nominal-leg proration reproduces the factual endpoint while unlimited geometry does not. The targeted confounder audit found no already-modelled external explanation.

The Intercept differential changed:

```text
fuel_limited_discriminating_support       1 -> 2
fuel_limited_discriminating_contradiction 1 -> 1
fuel_endpoint_exact                     437 -> 438
missing_archive                           0 -> 0
```

The surviving contradiction `360690/T69/ship391` remains evidence that snapshot neutronium is not automatically the Intercept-phase fuel value; it did not increase under the nominal-leg candidate.

## Evidence status and boundary

- proportional insufficient-fuel ratio: `DOCUMENTED`;
- normal-movement integer proration behavior: `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` in the supported Move Most / Intercept scope;
- continuous effective one-turn leg as the fuel-cost basis for a true partial normal route: `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED` for Move Most / Intercept;
- finite-fuel Tow cost/proration semantics: **OPEN**.

Snapshot fuel remains pre-Host evidence and must not be silently treated as movement-phase fuel. Next-turn fuel is supporting evidence only because later Host phases can mutate neutronium.

This rule must not be generalized to finite-fuel Tow without separate attributable historical evidence. A `planets-intel` transfer is also a separate implementation/runtime-validation step.
