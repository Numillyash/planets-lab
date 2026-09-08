# Partial-fuel historical gate — verified checkpoint

Date: 2026-09-09

GitHub `main` remains the source of truth. This handoff records the actual server historical-corpus run and the resulting evidence promotion. It does not claim a `planets-intel` production deployment.

## Revisions

```text
gate candidate     f68a31376ff41810d72df0f3fadc165ff55e1017
planner candidate  993e76046c3ffaa40acf4b0aa7286d5bd9573480
baseline            1d01bf20c745e84162b6c5ae249e0e81b0ccdc6c
server log          logs/partial-fuel-20260908T212338Z-f68a3137-26041
```

The gate used the existing local historical archives and prepared caches. It did not rebuild L1/L2.

All 12 compiled games had both required `loadall` archives and `prepared-v1` caches:

```text
360690 511506 591478 620636 620694 620917
621103 621253 621896 622476 680435 680910
```

`missing_archive=0`.

## Gate status

Every stage completed with command and tee return code zero:

```text
source-diff           0 / 0
inputs                0 / 0
pytest                0 / 0
move-most-anchor      0 / 0
move-most-population  0 / 0
baseline-source       0 / 0
intercept-baseline    0 / 0
intercept-candidate   0 / 0
intercept-confounders 0 / 0
comparison            0 / 0
```

Full suite:

```text
371 passed
```

## Move Most nominal-leg discriminator

Targeted case:

```text
game                 360690
turn                 164
ship                  41
hull                  23
owner                  2
warp                   9
origin       (1949, 2950)
waypoint     (2008, 3067)
factual      (1959, 2969)
waypoint distance   131.034347
max distance         81
snapshot fuel        11
movement mass       517
```

Cost models:

```text
rasterized one-turn distance  80.498447
projected-distance cost       40
continuous nominal 81-ly cost 41
```

Phase-fuel scan:

```text
projected_exact_phase_fuel_ranges  ()
nominal_exact_phase_fuel_ranges    ((11, 11),)
projected_exact_post_fuel_ranges   ()
nominal_exact_post_fuel_ranges     ((0, 0),)
known_external_flags               ()
```

Only the continuous nominal-leg basis reproduces the factual endpoint. The targeted owner-visible context found no incoming transfer candidate or Tow candidate, and the external audit found no already-modelled mine/storm/damage/Tow/Chunnel explanation.

Population control:

```text
prefilter_true_partial_rows              32371
true_partial_route                       15560
prefilter_false_positive                  1495
same_integer_cost                        12633
cost_basis_differs                        2927
fuel_relation:below_both                     3
fuel_relation:between_costs                  0
fuel_relation:sufficient_both             2924
projected_cost_endpoint_exact             2811
nominal_cost_endpoint_exact               2812
discriminating_endpoint                      1
discriminating_nominal_cost_support          1
discriminating_projected_cost_support        0
discriminating_with_post_reset               0
```

The sole discriminating Move Most row is `360690/T164/ship41` and it supports the nominal basis.

## Intercept baseline -> candidate

Population is unchanged at 2,598 owner-visible ready Intercept rows. Scope filters remain unchanged, including sphere and unlimited-fuel exclusions.

Key differential:

```text
fuel_formula_ready                         542 -> 542
snapshot_fuel_limited                        3 -> 3
fuel_endpoint_exact                        437 -> 438
fuel_endpoint_differs                       99 -> 99
fuel_limited_discriminating_support          1 -> 2
fuel_limited_discriminating_contradiction    1 -> 1
after_reset_supporting_only                  0 -> 1
fuel_limited_support_with_after_reset        0 -> 1
fuel_plan_error                              0 -> 0
missing_archive                              0 -> 0
```

### Support 1 — proportional Intercept

`620636/T60/ship44` remains the existing finite-fuel support:

```text
origin             (1721, 1604)
target final       (1705, 1589)
factual            (1716, 1599)
snapshot fuel      1
movement mass      157
required           3
fuel endpoint      (1716, 1599)
geometry exact     false
fuel exact         true
known flags        ()
```

### Support 2 — independent nominal-leg discriminator

`620694/T73/ship278` becomes newly resolved under the candidate:

```text
origin             (2758, 2098)
target final       (2717, 2026)
factual            (2742, 2070)
warp               9
movement mass      893
snapshot fuel      29
required nominal   72
fuel endpoint      (2742, 2070)
geometry endpoint  (2718, 2028)
geometry exact     false
fuel exact         true
after reset        supporting only
known flags        ()
```

This is independent of the Move Most discriminator and supports charging the continuous effective 81-ly one-turn leg before integer endpoint rasterization.

### Unchanged contradiction / phase-fuel boundary

`360690/T69/ship391` remains:

```text
snapshot fuel      64
candidate required 66
factual endpoint   full reachable geometry
candidate endpoint snapshot-prorated and different
```

The contradiction count did not increase (`1 -> 1`). The targeted audit identifies the factual endpoint as `baseline:reachable_exact`. Together with next-turn fuel evidence from prior work, this remains a warning that snapshot neutronium is not automatically the Intercept-phase fuel value. It is not a new contradiction introduced by nominal-leg costing.

## Promotion decision

The candidate is promoted in the following exact scope:

```text
continuous effective one-turn fuel leg for true-partial normal movement
Move Most + Intercept
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Meaning:

- for a geometrically true partial normal route, compute movement fuel cost from the continuous effective one-turn leg (`max_distance`) before integer endpoint rasterization;
- if fuel is insufficient, prorate that effective one-turn leg;
- preserve the existing Host major/minor integer projection for the resulting endpoint.

This does not claim NuHost source-code identity; it is an empirical mechanics relation supported by independent historical discriminators.

## Boundaries that remain OPEN

1. **Finite-fuel Tow** — no promotion. Existing Tow lock/route audits do not isolate finite-fuel cost/proration semantics.
2. **Snapshot fuel phase attribution** — snapshot neutronium remains pre-Host evidence, not automatically movement-phase fuel.
3. **Next-turn fuel** — supporting evidence only; later Host phases can change neutronium.
4. **Production transfer** — no `planets-intel` code/runtime change is implied by this lab checkpoint.

Do not weaken Tow requirements: exact colocation, engine eligibility, visibility, target lock, same-target contests, chains/cycles, warp-well boundaries, Chunnel and other external movement confounders remain separate evidence requirements.

## Next work

- Keep the normal Move Most / Intercept nominal-leg rule closed unless a bounded contradiction appears.
- If transferring the rule into `planets-intel`, inspect the current production movement architecture first and preserve finite-fuel Tow as fail-closed.
- Build a separate historical finite-fuel Tow diagnostic only if Tow fuel semantics are needed next.
- Otherwise return to the current main roadmap priority: Host combat engagement/ordering around the already reconstructed pairwise resolver.
