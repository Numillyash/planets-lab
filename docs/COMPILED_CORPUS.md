# Compiled historical corpus

`validation/corpus/cache/loadall/game-<id>.zip` is the immutable evidence/source layer. Compiled data is deterministic local output and must be rebuildable from cached archives plus manifests.

New chats should start from:

[`handoff/2026-09-05-new-chat-context.md`](handoff/2026-09-05-new-chat-context.md)

Current movement checkpoint:

[`handoff/2026-09-09-partial-fuel-historical-gate-verified.md`](handoff/2026-09-09-partial-fuel-historical-gate-verified.md)

## Current verified schema state

```text
prepared cache:                    planets-lab.prepared-game-cache.v1
L1 physical movement schema:       planets-lab.compiled-movement.v3
L1 post-compile context semantics: planets-lab.compiled-movement-storm-context.v3
L2 context labels:                 planets-lab.compiled-movement-context-labels.v6
```

Raw `/game/loadall` archives remain unchanged. Prepared projection stays privacy-minimal; raw `.trn` evidence is read directly only by diagnostics that need narrowly scoped historical metadata.

## Current runtime-verified 12-game invariants

The compiled-layer counters remain the last recorded L1/L2 rebuild checkpoint. The later partial-fuel historical gate read these existing archives/caches without rebuilding L1/L2 and verified the nominal-leg planner independently.

L1:

```text
transition_rows              254046
geometry_ready               247816
move_most_candidates         227468
baseline_explained           209574
baseline_unresolved           17894
external_context_explained    13970
post_external_residual         3924
damage_limited_warp_match       10
```

L2:

```text
external_residual_rows             3924
chunnel_explained                  1421
post_chunnel_residual              2503
horwasp_strong_explained            240
post_horwasp_strong_residual       2263
mine_strong_explained                60
post_mine_strong_residual          2203
fuel_proration_explained              6
post_fuel_proration_residual       2197
label_issues                          0
```

The latest L2 rebuild processed all 12 games with zero failures, all prepared caches hit, and completed in about 102 seconds with `--jobs 2`.

## Partial-fuel historical gate

Server gate candidate:

```text
candidate  f68a31376ff41810d72df0f3fadc165ff55e1017
baseline   1d01bf20c745e84162b6c5ae249e0e81b0ccdc6c
planner    993e76046c3ffaa40acf4b0aa7286d5bd9573480
pytest     371 passed
archives   12 / 12 present
```

Move Most control population:

```text
prefilter_true_partial_rows              32371
true_partial_route                       15560
prefilter_false_positive                  1495
same_integer_cost                        12633
cost_basis_differs                        2927
projected_cost_endpoint_exact             2811
nominal_cost_endpoint_exact               2812
discriminating_endpoint                      1
discriminating_nominal_cost_support          1
discriminating_projected_cost_support        0
```

Intercept baseline -> candidate:

```text
fuel_endpoint_exact                     437 -> 438
fuel_endpoint_differs                    99 -> 99
fuel_limited_discriminating_support       1 -> 2
fuel_limited_discriminating_contradiction 1 -> 1
after_reset_supporting_only               0 -> 1
missing_archive                           0 -> 0
```

Independent discriminators:

- `360690/T164/ship41` Move Most supports continuous nominal one-turn fuel cost and rejects rasterized endpoint-distance cost;
- `620694/T73/ship278` Intercept supports the same nominal-leg basis and reproduces factual `(2742,2070)` with `29/72` fuel proration;
- `620636/T60/ship44` remains an independent proportional finite-fuel Intercept support case.

Targeted confounder checks found no already-modelled mine/storm/damage/Tow/Chunnel explanation for the two supporting limited-fuel Intercept cases. The unchanged `360690/T69/ship391` contradiction remains a snapshot-vs-phase-fuel boundary, not a new candidate regression.

Scoped evidence status:

```text
continuous nominal one-turn fuel basis for true-partial Move Most / Intercept
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Finite-fuel Tow is not included in this promotion and remains OPEN.

## Current generic final endpoint

```text
final_residual_rows       2197
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               740
generic_games               12
generic_hulls               75
```

Largest coarse family:

```text
113  warp7-9 <0.5x observed=other same_line_forward
```

Largest detailed member:

```text
89  warp7-9 reachable_other <0.5x observed=other same_line_forward non-gravitonic
```

Residual clusters are investigation leads only; they are not mechanics without independent evidence.

## Verified / closed recent movement mechanics

- ordinary movement / Host major-minor geometry;
- warp-well ordering — **TESTED + DIFF_VERIFIED**;
- route-equivalent owner-visible Tow — **TESTED + DIFF_VERIFIED**;
- route-equivalent Chunnel multiplicity — **TESTED + DIFF_VERIFIED**;
- classic/cloudy ion storms — **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- scoped effective sphere topology for game `591478` — **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- strict mine/web interruption v5 — **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- strict damage-limited maximum warp — **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- strict Nu waypoint-distance fuel proration v6 — **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- continuous nominal one-turn fuel basis for true-partial normal Move Most / Intercept — **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**;
- short-waypoint normal-mine scaled-floor exact classifier — **CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**; underlying low-tech slowdown itself is **DOCUMENTED**;
- Red Mite tracking/fallback research — closed absent new evidence.

Crystal Web Drain remains one attributable `DOCUMENTED + CORPUS_OBSERVED` evidence-only transition and is not production-labeled.

Rejected broad post-v6 leads for the dominant residual family: outbound fuel transfer, standard Cloak fuel burn, Privateer Rob Ship, and Stellar Cartography speed terrain.

## Short-waypoint normal-mine production closure

Production category:

```text
normal_mine_hit_scaled_floor_exact
```

Runtime-verified population:

```text
rows     = 23
games    = 6
hulls    = 9
Horwasp  = 0
```

By game:

```text
360690  10
511506   4
620694   5
620917   1
621103   2
680910   1
```

All 23 current corpus rows resolve to one damage hit and one slowdown hit.

The empirical planar click penalty used only by the narrow exact production path is:

```text
floor(10 * slowdown_hits * nominal_max_distance / regular_distance)
```

This expression is a corpus-observed classifier relation, not a claim about NuHost source code.

The production path is fail-closed and requires planar topology, hull tech below 7, hostile normal-field crossing, a true short waypoint, same-line shortened movement, direct or exactly reconstructed automatic-repair mine damage, a unique hit model, and an exact predicted Host major-axis endpoint. Sphere/unknown topology and ambiguous hit models are not promoted.

Independent pre-production evidence was:

```text
production planar controls:       15/15 within +/-1 click
strict residual planar resolved:  31/31 within +/-1 click
strict residual exact:            27/31
production-visible equivalence:   23/23 report-backed exact short-waypoint references
misses:                            0
extras:                            0
```

Full-corpus production diff:

```text
mine_strong_explained        37 -> 60
post_mine_strong_residual  2226 -> 2203
fuel_proration_explained      6 -> 6
post_fuel_proration_residual 2220 -> 2197
label_issues                  0 -> 0
```

The original `511506 / T23 / ship160 / hull17` survivor is now production-closed with one mine hit plus exact automatic supply repair (`0 + 76 -> 66 damage`, `53 -> 3 supplies`).

## Current test state

```text
movement-mine targeted module: 10 passed
full GitHub Actions pytest:    green on mechanics/test commit
partial-fuel server gate:      371 passed / all stages 0/0
full 12-game L2 rebuild:       clean / zero failures
final generic clustering:      2197 total / 740 generic / 75 hulls / largest coarse 113
```
